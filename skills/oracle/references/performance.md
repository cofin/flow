# Performance Tuning

## Overview

Use this reference when diagnosing slow queries, choosing index strategies, interpreting execution plans, or tuning Oracle memory and workload characteristics. Performance tuning is iterative: measure first, change one thing, measure again.

## Reading Execution Plans

### Generate Plans

Use `EXPLAIN PLAN` for estimated plans and `DBMS_XPLAN.DISPLAY_CURSOR` for actual runtime statistics. Prefer actual stats because the optimizer's row estimates can be wildly wrong.

```sql
-- Estimated plan
EXPLAIN PLAN FOR
SELECT /*+ GATHER_PLAN_STATISTICS */ e.name, d.dept_name
FROM employees e JOIN departments d ON e.dept_id = d.id
WHERE e.salary > 100000;

SELECT * FROM TABLE(DBMS_XPLAN.DISPLAY(format => 'TYPICAL'));

-- Actual plan with runtime stats (run the query first)
SELECT /*+ GATHER_PLAN_STATISTICS */ e.name, d.dept_name
FROM employees e JOIN departments d ON e.dept_id = d.id
WHERE e.salary > 100000;

SELECT * FROM TABLE(DBMS_XPLAN.DISPLAY_CURSOR(format => 'ALLSTATS LAST'));
```

### Interpret the Plan

- **A-Rows vs E-Rows**: Compare actual rows returned to estimated rows. A ratio beyond 10x signals stale or missing statistics.
- **Starts**: How many times an operation executed. High starts in a nested loop means the inner table is hit repeatedly — consider a hash join.
- **Cost**: Relative measure within a single plan only. Never compare cost numbers across different queries.
- **Predicate Information**: Look for `access` (index-driven) vs `filter` (post-fetch discard). Filters on high-volume steps waste I/O.
- **TABLE ACCESS FULL**: Not always bad. For analytical queries touching most rows, a full scan beats an index lookup.

## Index Strategy

Choose the index type based on the data and query pattern, not by default.

### B-tree Indexes

Default workhorse. Use for high-cardinality columns in equality and range predicates.

```sql
CREATE INDEX idx_emp_salary ON employees(salary);
```

### Bitmap Indexes

Use for low-cardinality columns (status, gender, region) in data warehouse workloads. Never use in OLTP — bitmap indexes cause severe contention under concurrent DML.

```sql
CREATE BITMAP INDEX idx_order_status ON orders(status);
```

### Function-Based Indexes

When queries apply functions to columns, a standard index is useless. Index the expression instead.

```sql
CREATE INDEX idx_emp_upper_name ON employees(UPPER(last_name));

-- This query now uses the index
SELECT * FROM employees WHERE UPPER(last_name) = 'SMITH';
```

### Composite Indexes

Column order matters. Place equality columns first, range columns last. The index is useful for queries that filter on a leading prefix.

```sql
-- Supports: WHERE dept_id = 10, WHERE dept_id = 10 AND salary > 50000
-- Does NOT support: WHERE salary > 50000 (alone)
CREATE INDEX idx_emp_dept_sal ON employees(dept_id, salary);
```

### Invisible Indexes

Test a new index on production without affecting existing plans. The optimizer ignores invisible indexes unless a session explicitly enables them.

```sql
CREATE INDEX idx_emp_hire ON employees(hire_date) INVISIBLE;

-- Test in your session only
ALTER SESSION SET OPTIMIZER_USE_INVISIBLE_INDEXES = TRUE;
```

## Gathering Statistics with DBMS_STATS

Statistics drive optimizer decisions. Stale or missing stats are the single most common cause of bad plans.

### Basic Gathering

```sql
-- Gather for a single table
EXEC DBMS_STATS.GATHER_TABLE_STATS('HR', 'EMPLOYEES', CASCADE => TRUE);

-- Gather for entire schema
EXEC DBMS_STATS.GATHER_SCHEMA_STATS('HR');

-- Gather stale stats only (efficient for scheduled jobs)
EXEC DBMS_STATS.GATHER_SCHEMA_STATS('HR', OPTIONS => 'GATHER STALE');
```

### Histograms

Histograms help the optimizer understand skewed data distributions. Without them, Oracle assumes uniform distribution, which produces bad cardinality estimates for skewed columns.

```sql
-- Force histogram on a specific column
EXEC DBMS_STATS.GATHER_TABLE_STATS('HR', 'EMPLOYEES',
  METHOD_OPT => 'FOR COLUMNS SIZE 254 department_id');
```

### Extended Statistics

Capture column group correlations that the optimizer cannot infer on its own.

```sql
-- Tell the optimizer that country and state are correlated
SELECT DBMS_STATS.CREATE_EXTENDED_STATS('HR', 'CUSTOMERS', '(country, state)')
FROM DUAL;

EXEC DBMS_STATS.GATHER_TABLE_STATS('HR', 'CUSTOMERS');
```

### Pending Stats

Test stats before publishing them to production workloads.

```sql
EXEC DBMS_STATS.SET_TABLE_PREFS('HR', 'EMPLOYEES', 'PUBLISH', 'FALSE');
EXEC DBMS_STATS.GATHER_TABLE_STATS('HR', 'EMPLOYEES');

-- Verify the pending stats with your problem query
ALTER SESSION SET OPTIMIZER_USE_PENDING_STATISTICS = TRUE;

-- If the plan improves, publish
EXEC DBMS_STATS.PUBLISH_PENDING_STATS('HR', 'EMPLOYEES');
```

### Detect Stale Stats

```sql
SELECT table_name, last_analyzed, stale_stats
FROM ALL_TAB_STATISTICS
WHERE owner = 'HR' AND stale_stats = 'YES';
```

## AWR Reports

AWR (Automatic Workload Repository) captures periodic performance snapshots. Use AWR reports for after-the-fact analysis of performance degradation.

### Generate a Report

```sql
-- List available snapshots
SELECT snap_id, begin_interval_time FROM DBA_HIST_SNAPSHOT
ORDER BY snap_id DESC FETCH FIRST 20 ROWS ONLY;

-- Generate HTML report between two snapshots
@$ORACLE_HOME/rdbms/admin/awrrpt.sql

-- Programmatic generation
EXEC DBMS_WORKLOAD_REPOSITORY.CREATE_SNAPSHOT;  -- force a snapshot now
```

### Key Sections to Read

- **Top SQL by Elapsed Time**: Identifies the heaviest queries. Start tuning here.
- **Top Wait Events**: Reveals what the database spends time waiting for (I/O, locks, latches).
- **Instance Efficiency**: Buffer cache hit ratio, parse ratios. Low values signal configuration issues.
- **Segment Statistics**: Identifies hot tables and indexes causing the most physical reads.

## Active Session History (ASH)

ASH samples active sessions every second. Use it for real-time and recent-past diagnosis without the overhead of tracing.

```sql
-- What is happening right now?
SELECT sql_id, event, session_state, COUNT(*)
FROM V$ACTIVE_SESSION_HISTORY
WHERE sample_time > SYSDATE - INTERVAL '5' MINUTE
GROUP BY sql_id, event, session_state
ORDER BY COUNT(*) DESC;

-- Who is blocking whom?
SELECT blocking_session, session_id, sql_id, event, wait_time
FROM V$ACTIVE_SESSION_HISTORY
WHERE blocking_session IS NOT NULL
  AND sample_time > SYSDATE - INTERVAL '10' MINUTE;

-- Historical ASH (from AWR, for analysis beyond the ASH buffer)
SELECT sql_id, event, COUNT(*)
FROM DBA_HIST_ACTIVE_SESS_HISTORY
WHERE sample_time BETWEEN TIMESTAMP '2026-03-25 14:00:00'
                      AND TIMESTAMP '2026-03-25 15:00:00'
GROUP BY sql_id, event
ORDER BY COUNT(*) DESC;
```

## Common Wait Events and Remediation

| Wait Event | Meaning | Action |
|---|---|---|
| `db file sequential read` | Single-block I/O (index lookup) | Check for excessive index access; verify statistics |
| `db file scattered read` | Multi-block I/O (full table scan) | Expected for large scans; reduce if scan is unintended |
| `log file sync` | Commit waiting for redo write | Reduce commit frequency; check redo log I/O performance |
| `enq: TX - row lock contention` | Row-level lock conflict | Investigate application logic; reduce transaction duration |
| `latch: shared pool` | Parsing contention | Use bind variables; increase shared pool if undersized |
| `direct path read` | Parallel or serial direct read | Generally normal for large operations |
| `buffer busy waits` | Contention on a hot block | Reduce index contention; consider hash partitioning |

## SGA/PGA Memory Tuning

### SGA

- **Buffer Cache** (`DB_CACHE_SIZE`): Caches data blocks. Size it so the buffer cache hit ratio stays above 95% for OLTP.
- **Shared Pool** (`SHARED_POOL_SIZE`): Stores parsed SQL and PL/SQL. Hard-parsing (not using bind variables) thrashes this.
- **Large Pool** (`LARGE_POOL_SIZE`): Used by RMAN, parallel execution, shared servers. Size separately from the shared pool.
- Use `SGA_TARGET` for automatic SGA management. Set `SGA_TARGET` and let Oracle distribute among components.

### PGA

- **PGA Aggregate Target** (`PGA_AGGREGATE_TARGET`): Controls memory for sorts, hash joins, bitmap merges.
- Undersized PGA forces operations to disk (`TEMP` tablespace), which is orders of magnitude slower.
- Monitor with `V$PGA_TARGET_ADVICE` to find the optimal setting.

```sql
-- Check PGA advice
SELECT pga_target_for_estimate/1024/1024 AS pga_mb,
       estd_extra_bytes_rw, estd_pga_cache_hit_percentage
FROM V$PGA_TARGET_ADVICE;
```

## Optimizer Hints

Use hints sparingly and as a last resort. Hints override the optimizer, which means they do not adapt when data changes. A hint that helps today can hurt tomorrow.

### When Hints Are Justified

- Emergency production fix while you gather proper stats or file a bug.
- Forcing parallelism for a known-heavy batch job.
- Working around a confirmed optimizer bug with a specific plan shape.

### Common Hints

```sql
-- Force join order: process employees first, then departments
SELECT /*+ LEADING(e d) */ e.name, d.dept_name
FROM employees e JOIN departments d ON e.dept_id = d.id;

-- Force nested loop join (good when driving table is small)
SELECT /*+ USE_NL(d) */ e.name, d.dept_name
FROM employees e JOIN departments d ON e.dept_id = d.id;

-- Force full table scan (skip index when you know you need most rows)
SELECT /*+ FULL(e) */ * FROM employees e WHERE salary > 10000;

-- Force a specific index
SELECT /*+ INDEX(e idx_emp_salary) */ * FROM employees e WHERE salary > 10000;

-- Parallel execution
SELECT /*+ PARALLEL(e, 4) */ * FROM employees e;
```

### Why Not to Rely on Hints

- They embed physical assumptions (index names, table sizes) into SQL text.
- They prevent the optimizer from adapting to data growth.
- They create maintenance burden: if you rename an index, the hint silently stops working.
- Prefer fixing the root cause: gather stats, add the right index, restructure the query.

## Learn More (Official)

- Oracle Database Performance Tuning Guide: <https://docs.oracle.com/en/database/oracle/oracle-database/19/tgdba/index.html>
- DBMS_XPLAN Reference: <https://docs.oracle.com/en/database/oracle/oracle-database/19/arpls/DBMS_XPLAN.html>
- DBMS_STATS Reference: <https://docs.oracle.com/en/database/oracle/oracle-database/19/arpls/DBMS_STATS.html>
- AWR/ADDM Documentation: <https://docs.oracle.com/en/database/oracle/oracle-database/19/tgdba/automatic-performance-diagnostics.html>

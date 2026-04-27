# Oracle Enterprise Manager

## Overview

Use this reference when working with Oracle Enterprise Manager (OEM) Cloud Control for monitoring, performance analysis, job management, and compliance. OEM provides a web-based interface for managing the full Oracle estate — databases, middleware, hosts, and cloud infrastructure.

## Architecture

OEM Cloud Control consists of three main components. Understand them to troubleshoot connectivity and performance issues.

### Oracle Management Service (OMS)

The middle tier that processes monitoring data, serves the web console, and communicates with agents. Deploy on a dedicated host for production. Multiple OMS instances provide high availability.

### Management Agent

A lightweight process installed on every monitored host. It collects metrics, runs jobs, and sends data to OMS. Keep agents at the same version as OMS or within one major release.

### Management Repository

An Oracle Database that stores all monitoring data, configuration, and job history. Size it generously — undersized repositories cause OEM sluggishness. Use RAC for the repository database in production.

## Target Discovery and Monitoring

### Discover Targets

```bash
# Auto-discover targets on a host (after agent install)
emcli add_target -name="prod-db01" -type="oracle_database" \
  -host="prodhost01" -credentials="set_name:DBCredsNormal"

# Discover all targets on a host
emcli discover_targets -host="prodhost01"
```

### Promote Discovered Targets

After discovery, targets appear in the OEM console under "Targets > All Targets." Promote them to enable monitoring:

1. Navigate to **Setup > Add Target > Auto Discovery Results**.
2. Select discovered targets and click **Promote**.
3. Assign monitoring credentials and preferred credentials for each target.

### Set Preferred Credentials

Preferred credentials let OEM run jobs and collect metrics without prompting for passwords. Set them per-target or globally.

1. Navigate to **Setup > Security > Preferred Credentials**.
2. Set credentials for target types: Database, Host, Listener.
3. Use named credential sets to avoid duplicating credential entries.

## Performance Hub

Performance Hub consolidates real-time and historical performance data in a single view. Access it from any database target: **Performance > Performance Hub**.

### Real-Time View

- **ASH Analytics**: Visualize active sessions by wait class, SQL ID, module, or any dimension. Drill down by clicking a time slice.
- **SQL Monitoring**: Shows currently executing SQL statements with execution plan, progress, and parallel query details.
- **Blocking Sessions**: Identify lock holders and waiters in real time.

### Historical View

- Switches to AWR-based data for past analysis.
- Correlate SQL performance changes with time periods.
- Compare SQL plan changes over time using the Plan Comparison tab.

## SQL Monitor

SQL Monitor tracks individual SQL execution in detail. It activates automatically for SQL running longer than 5 seconds or using parallel execution.

### Access SQL Monitor

1. **Performance > SQL Monitor** from any database target.
2. Search by SQL ID, username, or time range.

### What SQL Monitor Shows

- Execution plan with actual rows, estimated rows, and time per operation.
- I/O statistics per plan step.
- Parallel execution details: distribution method, DOP, slave activity.
- Wait events per execution plan step.

### Force Monitoring for Short SQL

```sql
SELECT /*+ MONITOR */ e.name, d.dept_name
FROM employees e JOIN departments d ON e.dept_id = d.id;
```

Use the `MONITOR` hint to track statements that would not normally qualify. Remove the hint after debugging.

## Custom Metrics and Alerts

### Create Custom Metrics

Define metrics that OEM collects on a schedule and evaluates against thresholds.

1. Navigate to **Monitoring > Metric and Collection Settings**.
2. Click **Create Custom Metric** (or use **Metric Extensions** for reusable definitions).
3. Define the SQL query that returns the metric value.

```sql
-- Example: count of unprocessed orders older than 1 hour
SELECT COUNT(*) FROM orders
WHERE status = 'PENDING'
  AND created_at < SYSDATE - 1/24;
```

1. Set warning and critical thresholds.
2. Assign a notification rule to send alerts via email, SNMP, or PagerDuty integration.

### Metric Extensions

Metric extensions package custom metrics for deployment across many targets.

1. **Enterprise > Monitoring > Metric Extensions**.
2. Create, test, deploy to target groups.
3. Export/import metric extensions between OEM environments.

### Alert Rules

Configure incident rules to route alerts:

1. **Setup > Incidents > Incident Rules**.
2. Define conditions (target type, metric, severity).
3. Assign actions: email notifications, event connectors, or auto-remediation scripts.

## Job System

OEM's job system schedules and executes tasks across managed targets. Use it for maintenance windows, patching, and administrative scripts.

### Create a Job

1. **Enterprise > Job > Create Job**.
2. Choose job type: SQL Script, OS Command, PL/SQL Block, RMAN Script.
3. Specify targets (single, group, or dynamic).
4. Set schedule: immediate, one-time, or recurring.

### Common Job Types

- **SQL Script**: Execute SQL or PL/SQL against database targets.
- **OS Command**: Run shell commands on host targets.
- **RMAN Script**: Backup/recovery operations.
- **Multi-Task Job**: Chain multiple steps with conditional logic.

### Monitor Jobs

Navigate to **Enterprise > Job > Activity** to see running, succeeded, and failed jobs. Click any job for execution details, output logs, and step-by-step status.

### Job Best Practices

- Use **Corrective Actions** to auto-remediate common alerts (e.g., restart a listener, clear temp space).
- Group targets into **Administration Groups** to apply jobs to dynamic sets of targets.
- Set **Blackout** periods during maintenance to suppress false alerts.

## Compliance Frameworks

OEM includes built-in compliance frameworks and supports custom standards.

### Built-In Standards

- **Oracle Database Security Configuration**: Checks for common misconfigurations (open passwords, excessive privileges, missing auditing).
- **CIS Benchmarks**: Center for Internet Security guidelines for Oracle Database.
- **STIG**: Security Technical Implementation Guide for government compliance.

### Compliance Workflow

1. **Enterprise > Compliance > Library**: Browse available standards.
2. Associate a standard with target groups.
3. OEM evaluates targets and generates a compliance score.
4. Drill into violations for remediation guidance.

### Drift Detection

Compare a target's configuration to a baseline or to other targets.

1. **Enterprise > Configuration > Comparison Templates**.
2. Create a template defining which parameters to compare.
3. Compare a target against the template or against another target.
4. Generate a drift report showing differences.

Use drift detection to verify that production, staging, and DR environments match.

## Patch Management

OEM automates Oracle software patching across the estate.

### Workflow

1. **Enterprise > Provisioning and Patching > Patches & Updates**.
2. Search for patches by number or product.
3. Download patches through OEM (requires My Oracle Support credentials).
4. Create a patching plan: select targets, patches, and schedule.
5. Run pre-checks to validate prerequisites.
6. Apply patches with automatic backup and rollback capability.

### Best Practices

- Patch non-production environments first and validate.
- Use the **Fleet Maintenance** feature for rolling patches across RAC clusters.
- Schedule patching during maintenance blackout windows.
- Keep OMS, agents, and repository patched to the same quarterly release.

## Learn More (Official)

- Oracle Enterprise Manager Documentation: <https://docs.oracle.com/en/enterprise-manager/>
- OEM Cloud Control Administration Guide: <https://docs.oracle.com/en/enterprise-manager/cloud-control/enterprise-manager-cloud-control/13.5/emadm/index.html>
- OEM CLI (emcli) Reference: <https://docs.oracle.com/en/enterprise-manager/cloud-control/enterprise-manager-cloud-control/13.5/emcli/index.html>
- Performance Hub Documentation: <https://docs.oracle.com/en/enterprise-manager/cloud-control/enterprise-manager-cloud-control/13.5/emdba/performance-hub.html>

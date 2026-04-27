# AlloyDB Operations

## Query Analysis with EXPLAIN ANALYZE

Always run `EXPLAIN (ANALYZE, BUFFERS)` before promoting queries to production. The `BUFFERS` flag exposes cache hit/miss data, revealing I/O bottlenecks.

```sql
-- Full analysis with buffer stats
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT *
FROM orders o
JOIN customers c ON o.customer_id = c.id
WHERE o.created_at >= NOW() - INTERVAL '7 days';
```

### Reading the Output

| Field | What to look for |
|---|---|
| `Seq Scan` | Missing index — consider adding one if rows filtered > 10% |
| `Rows Removed by Filter` | High values indicate poor selectivity or missing partial index |
| `Buffers: shared hit=N read=M` | High `read` relative to `hit` indicates cache misses |
| `Columnar Scan` | Confirms the AlloyDB columnar engine is being used |
| `actual time=X..Y` | Actual vs estimated row count divergence signals stale statistics |
| `Planning Time` | > 100ms suggests complex join graphs; consider `pg_hint_plan` |

### Force Fresh Statistics

```sql
-- Update statistics on a specific table
ANALYZE orders;

-- Update statistics with verbose output
ANALYZE VERBOSE orders;
```

---

## Active Query Monitoring (pg_stat_activity)

```sql
-- All active queries with duration
SELECT
    pid,
    now() - pg_stat_activity.query_start AS duration,
    query,
    state,
    wait_event_type,
    wait_event,
    client_addr
FROM pg_stat_activity
WHERE state != 'idle'
ORDER BY duration DESC;
```

### Identify Long-Running Queries

```sql
-- Queries running longer than 5 minutes
SELECT
    pid,
    now() - query_start AS duration,
    usename,
    application_name,
    state,
    query
FROM pg_stat_activity
WHERE state = 'active'
  AND query_start < NOW() - INTERVAL '5 minutes'
ORDER BY duration DESC;
```

### Kill a Blocking Query

```sql
-- Graceful cancel (sends SIGINT)
SELECT pg_cancel_backend(pid);

-- Forceful termination (sends SIGTERM)
SELECT pg_terminate_backend(pid);
```

### Lock Monitoring

```sql
-- Find blocking lock chains
SELECT
    blocked.pid AS blocked_pid,
    blocked.query AS blocked_query,
    blocking.pid AS blocking_pid,
    blocking.query AS blocking_query
FROM pg_stat_activity blocked
JOIN pg_stat_activity blocking
    ON blocking.pid = ANY(pg_blocking_pids(blocked.pid))
WHERE cardinality(pg_blocking_pids(blocked.pid)) > 0;
```

---

## Bloat Detection

### Table Bloat (pg_stat_user_tables)

```sql
-- Tables with high dead tuple counts
SELECT
    schemaname,
    relname AS table_name,
    n_dead_tup AS dead_tuples,
    n_live_tup AS live_tuples,
    ROUND(n_dead_tup::numeric / NULLIF(n_live_tup + n_dead_tup, 0) * 100, 2) AS dead_ratio_pct,
    last_autovacuum,
    last_autoanalyze
FROM pg_stat_user_tables
WHERE n_dead_tup > 10000
ORDER BY dead_ratio_pct DESC;
```

### Index Bloat Estimate

```sql
-- Rough index bloat estimate using pg_class
SELECT
    t.relname AS table_name,
    i.relname AS index_name,
    pg_size_pretty(pg_relation_size(i.oid)) AS index_size,
    idx_scan AS scans_since_reset
FROM pg_index x
JOIN pg_class t ON t.oid = x.indrelid
JOIN pg_class i ON i.oid = x.indexrelid
ORDER BY pg_relation_size(i.oid) DESC
LIMIT 20;
```

### Manual VACUUM on Bloated Tables

```sql
-- Reclaim space without locking (VACUUM) or with full rewrite (VACUUM FULL — locks table)
VACUUM (VERBOSE, ANALYZE) orders;

-- VACUUM FULL: use only during maintenance windows
VACUUM FULL orders;
```

---

## Autovacuum Tuning

AlloyDB runs autovacuum automatically. For high-write tables, tighten the thresholds.

```sql
-- Per-table autovacuum override (high-write table example)
ALTER TABLE orders SET (
    autovacuum_vacuum_scale_factor = 0.01,   -- trigger at 1% dead tuples (default: 0.2)
    autovacuum_analyze_scale_factor = 0.005, -- trigger analyze at 0.5% (default: 0.1)
    autovacuum_vacuum_cost_delay = 2         -- ms (reduce to run faster)
);
```

### Monitor Autovacuum Activity

```sql
-- Currently running autovacuum workers
SELECT
    pid,
    now() - query_start AS duration,
    query
FROM pg_stat_activity
WHERE query LIKE 'autovacuum:%'
ORDER BY duration DESC;
```

---

## Invalid Index Detection

Indexes can become invalid (e.g., after a failed `CREATE INDEX CONCURRENTLY`). Invalid indexes waste space and are never used.

```sql
-- Find invalid indexes
SELECT
    schemaname,
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
FROM pg_stat_user_indexes
JOIN pg_index ON pg_index.indexrelid = pg_stat_user_indexes.indexrelid
WHERE NOT pg_index.indisvalid
ORDER BY pg_relation_size(indexrelid) DESC;
```

```sql
-- Drop an invalid index and rebuild it
DROP INDEX CONCURRENTLY idx_orders_customer_id;
CREATE INDEX CONCURRENTLY idx_orders_customer_id ON orders (customer_id);
```

---

## Security Hardening

### IAM Database Authentication

```bash
# Enable IAM database authentication on the cluster
gcloud alloydb instances update INSTANCE_ID \
    --cluster=CLUSTER_ID \
    --region=REGION \
    --database-flags=alloydb.iam_authentication=on

# Grant a GCP user IAM DB access
gcloud projects add-iam-policy-binding PROJECT_ID \
    --member="user:user@example.com" \
    --role="roles/alloydb.databaseUser"
```

```sql
-- Create the IAM-authenticated database user (one-time)
CREATE USER "user@example.com" WITH LOGIN;
GRANT CONNECT ON DATABASE mydb TO "user@example.com";
```

### SSL Enforcement

```sql
-- Verify SSL is required (AlloyDB enforces SSL by default)
SHOW ssl;

-- Confirm your connection is using SSL
SELECT ssl, version, cipher, bits FROM pg_stat_ssl WHERE pid = pg_backend_pid();
```

Always include `sslmode=require` (or `sslmode=verify-full` for certificate validation) in connection strings.

### Audit Logging

```bash
# Enable data access audit logs for AlloyDB
gcloud projects get-iam-policy PROJECT_ID --format=json > policy.json
# Add auditLogConfigs for alloydb.googleapis.com with DATA_READ and DATA_WRITE
gcloud projects set-iam-policy PROJECT_ID policy.json
```

```json
{
  "auditConfigs": [
    {
      "service": "alloydb.googleapis.com",
      "auditLogConfigs": [
        { "logType": "DATA_READ" },
        { "logType": "DATA_WRITE" },
        { "logType": "ADMIN_READ" }
      ]
    }
  ]
}
```

---

## Credential Rotation

### Rotation Procedure

1. Generate a new password and store it in Secret Manager as a new version.
2. Update AlloyDB to accept the new password.
3. Perform a rolling restart of application workloads to pick up the new credential.
4. Disable the old Secret Manager version after rollout is confirmed.

```bash
# Step 1: Create new secret version
echo -n "new-secure-password" | gcloud secrets versions add DB_PASSWORD_SECRET --data-file=-

# Step 2: Update AlloyDB cluster password
gcloud alloydb users set-password postgres \
    --cluster=CLUSTER_ID \
    --region=REGION \
    --password="new-secure-password"

# Step 3: Disable old version (after workloads rotated)
gcloud secrets versions disable OLD_VERSION_ID --secret=DB_PASSWORD_SECRET
```

### Retry with Exponential Backoff (Python Example)

Use exponential backoff when reconnecting after a credential rotation to avoid thundering-herd connection storms.

```python
import time
import random
import psycopg2
from google.cloud import secretmanager

def get_db_password(secret_name: str) -> str:
    client = secretmanager.SecretManagerServiceClient()
    response = client.access_secret_version(name=f"{secret_name}/versions/latest")
    return response.payload.data.decode("utf-8")

def connect_with_retry(dsn_template: str, secret_name: str, max_attempts: int = 5):
    delay = 1.0
    for attempt in range(1, max_attempts + 1):
        try:
            password = get_db_password(secret_name)
            conn = psycopg2.connect(dsn_template.format(password=password))
            return conn
        except psycopg2.OperationalError as e:
            if attempt == max_attempts:
                raise
            jitter = random.uniform(0, delay * 0.2)
            time.sleep(delay + jitter)
            delay = min(delay * 2, 60.0)  # cap at 60 seconds
```

---

## Disaster Recovery

### Point-in-Time Recovery (PITR)

AlloyDB continuous backup enables PITR to any second within the retention window (default 14 days).

```bash
# View available backup window
gcloud alloydb clusters describe CLUSTER_ID \
    --region=REGION \
    --format="value(continuousBackupInfo)"

# Restore to a specific point in time (creates a new cluster)
gcloud alloydb clusters restore RESTORED_CLUSTER_ID \
    --region=REGION \
    --network=projects/PROJECT_ID/global/networks/NETWORK \
    --source-cluster=projects/PROJECT_ID/locations/REGION/clusters/CLUSTER_ID \
    --point-in-time="2025-06-15T14:30:00Z"

# Create primary instance on the restored cluster
gcloud alloydb instances create restored-primary \
    --cluster=RESTORED_CLUSTER_ID \
    --region=REGION \
    --instance-type=PRIMARY \
    --cpu-count=4
```

### Cross-Region Replica Promotion (Failover Runbook)

Use when the primary region is unavailable and the secondary cluster must be promoted.

```bash
# Step 1: Promote the secondary cluster to standalone
gcloud alloydb clusters promote SECONDARY_CLUSTER_ID \
    --region=SECONDARY_REGION

# Step 2: Verify the promoted cluster is accepting writes
gcloud alloydb instances describe SECONDARY_INSTANCE_ID \
    --cluster=SECONDARY_CLUSTER_ID \
    --region=SECONDARY_REGION \
    --format="value(state)"
# Expected: READY

# Step 3: Update application connection strings to point to the promoted cluster
# (update Secret Manager or environment config — no hardcoded IPs)

# Step 4: After primary region recovery, re-establish replication
gcloud alloydb clusters create PRIMARY_CLUSTER_ID \
    --region=PRIMARY_REGION \
    --network=NETWORK \
    --primary-cluster=projects/PROJECT_ID/locations/SECONDARY_REGION/clusters/SECONDARY_CLUSTER_ID
```

#### Failover Checklist

- [ ] Confirm primary region is truly unavailable (not a transient network blip)
- [ ] Check replication lag on secondary before promotion (aim for < 30s at time of failure)
- [ ] Notify stakeholders before promoting
- [ ] Update DNS / load balancer to point to promoted cluster endpoint
- [ ] Re-enable read pool on promoted cluster if needed
- [ ] Document RTO/RPO actuals for post-incident review

---

## Auth Proxy Sidecar Pattern (Kubernetes)

Run the AlloyDB Auth Proxy as a sidecar container to avoid exposing credentials in application pods.

```yaml
# Kubernetes pod spec excerpt
spec:
  serviceAccountName: workload-sa  # must have roles/alloydb.client
  containers:
    - name: app
      image: my-app:latest
      env:
        - name: DATABASE_URL
          value: "postgresql://postgres@127.0.0.1:5432/mydb?sslmode=disable"
          # SSL handled by proxy; disable in app connection string

    - name: alloydb-auth-proxy
      image: gcr.io/cloud-sql-connectors/alloydb-auth-proxy:latest
      args:
        - "projects/PROJECT_ID/locations/REGION/clusters/CLUSTER_ID/instances/INSTANCE_ID"
        - "--port=5432"
        - "--structured-logs"
      resources:
        requests:
          memory: "32Mi"
          cpu: "10m"
        limits:
          memory: "128Mi"
          cpu: "500m"
      securityContext:
        runAsNonRoot: true
        allowPrivilegeEscalation: false
```

The sidecar handles IAM token refresh automatically. The application connects to `127.0.0.1:5432` with no additional auth config.

---

## pg18 Production Defaults

When running AlloyDB with PostgreSQL 18 engine, set `max_connections=200` as the baseline. Pair with a connection pooler (PgBouncer or built-in AlloyDB connection management) to handle burst traffic without exhausting connections.

```bash
gcloud alloydb instances update INSTANCE_ID \
    --cluster=CLUSTER_ID \
    --region=REGION \
    --database-flags=max_connections=200
```

For workloads exceeding 200 concurrent connections, deploy PgBouncer in transaction mode in front of the AlloyDB instance rather than raising `max_connections` further, which increases shared memory overhead.

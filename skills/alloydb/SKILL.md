---
name: alloydb
description: "Auto-activate for AlloyDB in GCP configs or docs. Google AlloyDB expertise: PostgreSQL-compatible managed database on GCP. Produces AlloyDB cluster configurations, connection patterns, and columnar engine setups on GCP. Use when: provisioning AlloyDB clusters, configuring read pools, using columnar engine, Private Service Access networking, or migrating from Cloud SQL. Not for AlloyDB Omni (see alloydb-omni) or vanilla PostgreSQL without AlloyDB features."
---

# AlloyDB

## Overview

AlloyDB is a fully managed, PostgreSQL-compatible database service on Google Cloud. It combines the familiarity of PostgreSQL with Google's storage and compute innovations for high performance and availability.

## Operating Layers

Use this skill in three distinct layers:

1. **Provision** the managed database on GCP.
2. **Connect** an agent or client to the database.
3. **Operate** the database with tuning, observability, backups, and failover guidance.

Keep those layers separate when giving guidance. Provisioning is not the same thing as agent connectivity.

## Quick Reference

### AlloyDB vs Standard PostgreSQL

| Feature | AlloyDB | Cloud SQL for PostgreSQL |
|---|---|---|
| Storage | Disaggregated, log-based | Attached disk |
| Columnar engine | Built-in adaptive columnar cache | Not available |
| ML embeddings | Native Vertex AI integration | Manual setup |
| Read scaling | Read pool (auto-managed replicas) | Manual read replicas |
| Availability | 99.99% SLA (regional) | 99.95% SLA |
| Networking | Private IP only (PSA required) | Public or private IP |

### Key Commands

| Action | Command |
|---|---|
| Create cluster | `gcloud alloydb clusters create NAME --region=REGION --network=NETWORK --password=PASS` |
| Create primary | `gcloud alloydb instances create NAME --cluster=CLUSTER --region=REGION --instance-type=PRIMARY --cpu-count=N` |
| Create read pool | `gcloud alloydb instances create NAME --cluster=CLUSTER --region=REGION --instance-type=READ_POOL --read-pool-node-count=N` |
| Connect via proxy | `./alloydb-auth-proxy "projects/P/locations/R/clusters/C/instances/I" --port=5432` |
| Enable columnar engine | `SELECT google_columnar_engine_add('table_name');` |

### Connection Pattern

```bash
# From GCE VM in same VPC (private IP)
psql "host=ALLOYDB_IP dbname=postgres user=postgres sslmode=require"

# Via AlloyDB Auth Proxy (recommended for external access)
./alloydb-auth-proxy \
    "projects/PROJECT/locations/REGION/clusters/CLUSTER/instances/INSTANCE" \
    --port=5432

psql "host=127.0.0.1 port=5432 dbname=postgres user=postgres"
```

<workflow>

## Workflow

### Step 1: Set Up Private Service Access

AlloyDB requires Private Service Access (PSA) before any cluster can be created. Allocate an IP range and create the VPC peering connection.

### Step 2: Create Cluster and Primary Instance

Create the cluster with `gcloud alloydb clusters create`, then add a primary instance. Choose CPU count based on workload (start with 4 vCPUs for small workloads).

### Step 3: Configure Read Pool (if needed)

For read-heavy workloads, add a read pool with `--instance-type=READ_POOL`. AlloyDB automatically manages the read replicas within the pool.

### Step 4: Enable Columnar Engine (for analytics)

For analytical query patterns, enable the columnar engine on tables with `SELECT google_columnar_engine_add('table')`. Check `g_columnar_recommended_columns` for automatic recommendations.

### Step 5: Connect Applications

Use the AlloyDB Auth Proxy for connections from outside the VPC. For applications within GCE/GKE on the same VPC, connect directly via private IP.

</workflow>

## Host Integration Order

Use the lowest-admin supported path for the current host, and degrade cleanly:

1. **Gemini CLI**: use the dedicated `alloydb` and `alloydb-observability` extensions.
2. **Other agents with MCP support**: use MCP Toolbox with the official AlloyDB prebuilt config.
3. **No extension / no MCP**: fall back to `gcloud`, Auth Proxy, `psql`, and SQL guidance from this skill's references.

Do not make the skill Gemini-only. The Gemini extension path is preferred when available, but the operational guidance in this skill must still work for Claude, Codex, OpenCode, Antigravity, and plain terminal workflows.

<guardrails>

## Guardrails

- **Always use Private Service Access** — AlloyDB does not support public IP; PSA must be configured before cluster creation
- **Use the AlloyDB Auth Proxy** for connections outside the VPC — never expose the private IP directly
- **Columnar engine is for analytics only** — do not enable on tables with heavy OLTP write patterns; it adds overhead to writes
- **Size read pools based on read traffic** — do not use read pools as a substitute for query optimization
- **Set `--password` at cluster creation** — there is no way to recover the initial password; store it in Secret Manager
- **Always specify `sslmode=require`** in connection strings for security
- **Enable Cloud Monitoring** — configure `roles/monitoring.viewer` and set alerts on CPU, connections, and replication lag before going to production
- **Run EXPLAIN ANALYZE before promoting queries** — always validate query plans with `EXPLAIN (ANALYZE, BUFFERS)` on a representative dataset before production deployment
- **Rotate credentials periodically** — store passwords in Secret Manager and rotate on a schedule; use exponential backoff during rolling restarts

</guardrails>

<validation>

### Validation Checkpoint

Before delivering configurations, verify:

- [ ] Private Service Access is configured (IP allocation + VPC peering)
- [ ] Cluster uses a VPC network, not the `default` network in production
- [ ] Primary instance has appropriate CPU count for the workload
- [ ] Connection pattern uses Auth Proxy or private IP (no public exposure)
- [ ] Passwords are sourced from Secret Manager, not hardcoded

</validation>

<example>

## Example

Columnar engine setup for an analytics workload:

```sql
-- Enable columnar engine on the orders table
SELECT google_columnar_engine_add('orders');

-- Check which columns AlloyDB recommends for columnar caching
SELECT table_name, column_name, estimated_benefit
FROM g_columnar_recommended_columns
ORDER BY estimated_benefit DESC;

-- Verify a query uses the columnar engine
EXPLAIN (ANALYZE) SELECT region, SUM(amount)
FROM orders
WHERE order_date >= '2025-01-01'
GROUP BY region;
-- Look for "Columnar Scan" in the plan output
```

Connection string for a Python application using the Auth Proxy:

```python
DATABASE_URL = "postgresql+asyncpg://postgres:password@127.0.0.1:5432/mydb"
# Auth Proxy runs locally, forwarding to AlloyDB private IP
```

</example>

---

## Observability

AlloyDB metrics are available under `alloydb.googleapis.com/database/postgresql/*` in Cloud Monitoring. Enable Cloud Monitoring before production launch.

**Key metrics to watch:**

- CPU utilization — alert above 80% sustained
- Active connections — alert above 80% of `max_connections` (200 on pg18)
- Replication lag on read pool nodes — alert above 30 seconds
- Dead tuple count — high values indicate autovacuum falling behind

**PromQL patterns** (Cloud Monitoring / Google Managed Prometheus):

```promql
# CPU utilization
avg_over_time(alloydb_googleapis_com:database_postgresql_cpu_utilization[5m])

# Active connections vs capacity
alloydb_googleapis_com:database_postgresql_network_connections

# Replication lag
max by (instance_id)(alloydb_googleapis_com:database_postgresql_replication_replica_lag_seconds)
```

Required role: `roles/monitoring.viewer`. See [Observability Reference](references/observability.md) for full PromQL patterns, alert policy examples, and dashboard recommendations.

---

## Data Plane Operations

Before promoting any query to production, validate with `EXPLAIN (ANALYZE, BUFFERS)`. Monitor live workload via `pg_stat_activity`.

**Quick patterns:**

```sql
-- Active queries with duration
SELECT pid, now() - query_start AS duration, state, query
FROM pg_stat_activity
WHERE state != 'idle'
ORDER BY duration DESC;

-- Tables with bloat
SELECT relname, n_dead_tup, n_live_tup, last_autovacuum
FROM pg_stat_user_tables
WHERE n_dead_tup > 10000
ORDER BY n_dead_tup DESC;
```

See [Operations Reference](references/operations.md) for EXPLAIN ANALYZE interpretation, bloat detection, autovacuum tuning, invalid index detection, and security hardening.

---

## Production Patterns

### Auth Proxy Sidecar (Kubernetes)

Run `alloydb-auth-proxy` as a sidecar container alongside the application pod. The sidecar uses the pod's workload identity (requires `roles/alloydb.client`) and refreshes IAM tokens automatically. The application connects to `127.0.0.1:5432` with no credential management in the app layer.

### Credential Rotation

Store the database password in Secret Manager. On rotation: add a new secret version, update the AlloyDB user password via `gcloud alloydb users set-password`, perform a rolling restart with exponential backoff, then disable the old secret version.

### pg18 max_connections

Set `max_connections=200` for PostgreSQL 18 instances as the production baseline. For workloads exceeding 200 concurrent connections, add PgBouncer in transaction mode rather than raising the limit further.

See [Operations Reference](references/operations.md) for the full Kubernetes sidecar spec, rotation runbook, and connection pooling guidance.

---

## Disaster Recovery

### Point-in-Time Recovery (PITR)

AlloyDB continuous backup enables PITR to any second within the retention window (default 14 days). Restoration creates a new cluster — the original cluster is unaffected.

```bash
gcloud alloydb clusters restore RESTORED_CLUSTER_ID \
    --region=REGION \
    --network=NETWORK \
    --source-cluster=projects/PROJECT_ID/locations/REGION/clusters/CLUSTER_ID \
    --point-in-time="2025-06-15T14:30:00Z"
```

### Cross-Region Replica Promotion

When the primary region is unavailable, promote the secondary cluster with:

```bash
gcloud alloydb clusters promote SECONDARY_CLUSTER_ID --region=SECONDARY_REGION
```

After promotion, update connection strings (via Secret Manager or environment config) to the promoted cluster endpoint. See [Operations Reference](references/operations.md) for the full failover runbook and checklist.

---

## Gemini CLI and MCP Toolbox

This section is for the **connection layer**, not for provisioning the AlloyDB cluster itself.

Prefer the dedicated Gemini CLI extensions for managed AlloyDB. They embed the underlying MCP Toolbox flow directly, so Gemini users do not need to configure a separate MCP server first.

Install the core AlloyDB extension:

```bash
gemini extensions install https://github.com/gemini-cli-extensions/alloydb --auto-update
```

Install the observability extension when the user wants metrics, dashboards, alerts, or query-performance monitoring:

```bash
gemini extensions install https://github.com/gemini-cli-extensions/alloydb-observability --auto-update
```

Prefer workspace-scoped configuration:

```bash
gemini extensions config alloydb --scope workspace
```

Guide the user through configuration before starting Gemini:

```bash
export ALLOYDB_POSTGRES_PROJECT="<your-gcp-project-id>"
export ALLOYDB_POSTGRES_REGION="<your-alloydb-region>"
export ALLOYDB_POSTGRES_CLUSTER="<your-alloydb-cluster-id>"
export ALLOYDB_POSTGRES_INSTANCE="<your-alloydb-instance-id>"
export ALLOYDB_POSTGRES_DATABASE="<your-database-name>"
export ALLOYDB_POSTGRES_USER="<your-database-user>"        # optional
export ALLOYDB_POSTGRES_PASSWORD="<your-database-password>" # optional
export ALLOYDB_POSTGRES_IP_TYPE="PRIVATE"                   # PRIVATE / PUBLIC / PSC
```

Important configuration guidance:

- Gemini CLI should be `v0.6.0` or newer.
- Application Default Credentials must be available before starting Gemini.
- For read-only discovery, require `roles/alloydb.viewer`.
- For SQL access, require `roles/alloydb.client`.
- For admin actions, require `roles/alloydb.admin` plus `roles/serviceusage.serviceUsageConsumer`.
- For observability, also require `roles/monitoring.viewer`.
- Prefer IAM-first auth. Password prompts are fallback-only.
- If the instance uses private IP, Gemini CLI must run in the same VPC network.
- The extension binds connection settings at session start; if the user needs a different instance or database, save/resume chat and restart Gemini with the new environment.
- Recent upstream changes removed broken keychain password behavior, so do not promise keychain-backed credential storage.

For non-Gemini agents, or when the user explicitly wants a shared MCP server, guide them through MCP Toolbox with the AlloyDB prebuilt config instead of inventing a custom server:

```json
{
  "mcpServers": {
    "alloydb": {
      "command": "./toolbox",
      "args": ["--prebuilt", "alloydb-postgres", "--stdio"],
      "env": {
        "ALLOYDB_POSTGRES_PROJECT": "PROJECT_ID",
        "ALLOYDB_POSTGRES_REGION": "REGION",
        "ALLOYDB_POSTGRES_CLUSTER": "CLUSTER_NAME",
        "ALLOYDB_POSTGRES_INSTANCE": "INSTANCE_NAME",
        "ALLOYDB_POSTGRES_DATABASE": "DATABASE_NAME",
        "ALLOYDB_POSTGRES_USER": "USERNAME",
        "ALLOYDB_POSTGRES_PASSWORD": "PASSWORD",
        "ALLOYDB_POSTGRES_IP_TYPE": "PRIVATE"
      }
    }
  }
}
```

For reusable project workflows, prefer generated workspace skills over one-off prompts:

```bash
toolbox --prebuilt alloydb-postgres skills-generate \
  --name alloydb-monitor \
  --toolset monitor \
  --description "AlloyDB monitoring skill" \
  --output-dir .agents/skills
```

If neither Gemini extensions nor MCP Toolbox are available, fall back to the manual `gcloud`, Auth Proxy, and SQL workflows already documented in this skill's reference files.

---

## References Index

For detailed guides and code examples, refer to the following documents in `references/`:

- **[Cluster Setup](references/setup.md)**
  - Cluster creation, instance types (primary, read pool), Private Service Access, gcloud commands.
- **[Features](references/features.md)**
  - Columnar engine, adaptive caching, ML embeddings, vector search, pgvector integration.
- **[Migration](references/migration.md)**
  - Migration from Cloud SQL or on-prem PostgreSQL, Database Migration Service patterns.
- **[Observability](references/observability.md)**
  - PromQL patterns, Cloud Monitoring setup, key metrics, alert policies, dashboard recommendations, Query Insights.
- **[Operations](references/operations.md)**
  - EXPLAIN ANALYZE, pg_stat_activity, bloat detection, autovacuum tuning, invalid indexes, security hardening, PITR, cross-region failover, credential rotation, Auth Proxy sidecar.
- **[Gemini + MCP Guidance](references/gemini-mcp.md)**
  - Extension install, IAM prerequisites, env vars, private-IP constraints, and MCP Toolbox fallback config.

---

## Official References

- <https://cloud.google.com/alloydb/docs>
- <https://docs.cloud.google.com/alloydb/docs/connect-ide-using-mcp-toolbox>
- <https://github.com/gemini-cli-extensions/alloydb>
- <https://github.com/gemini-cli-extensions/alloydb-observability>

## Shared Styleguide Baseline

- Use shared styleguides for generic language/framework rules to reduce duplication in this skill.
- [General Principles](https://github.com/cofin/flow/blob/main/templates/styleguides/general.md)
- [PostgreSQL / psql](https://github.com/cofin/flow/blob/main/templates/styleguides/databases/postgres_psql.md)
- [GCP Scripting](https://github.com/cofin/flow/blob/main/templates/styleguides/cloud/gcp_scripting.md)
- Keep this skill focused on tool-specific workflows, edge cases, and integration details.

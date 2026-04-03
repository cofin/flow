---
name: alloydb
description: "Auto-activate for AlloyDB in GCP configs or docs. Google AlloyDB expertise: PostgreSQL-compatible managed database on GCP. Produces AlloyDB cluster configurations, connection patterns, and columnar engine setups on GCP. Use when: provisioning AlloyDB clusters, configuring read pools, using columnar engine, Private Service Access networking, or migrating from Cloud SQL. Not for AlloyDB Omni (see alloydb-omni) or vanilla PostgreSQL without AlloyDB features."
---

# AlloyDB

## Overview

AlloyDB is a fully managed, PostgreSQL-compatible database service on Google Cloud. It combines the familiarity of PostgreSQL with Google's storage and compute innovations for high performance and availability.

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

<guardrails>

## Guardrails

- **Always use Private Service Access** — AlloyDB does not support public IP; PSA must be configured before cluster creation
- **Use the AlloyDB Auth Proxy** for connections outside the VPC — never expose the private IP directly
- **Columnar engine is for analytics only** — do not enable on tables with heavy OLTP write patterns; it adds overhead to writes
- **Size read pools based on read traffic** — do not use read pools as a substitute for query optimization
- **Set `--password` at cluster creation** — there is no way to recover the initial password; store it in Secret Manager
- **Always specify `sslmode=require`** in connection strings for security

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

## References Index

For detailed guides and code examples, refer to the following documents in `references/`:

- **[Cluster Setup](references/setup.md)**
  - Cluster creation, instance types (primary, read pool), Private Service Access, gcloud commands.
- **[Features](references/features.md)**
  - Columnar engine, adaptive caching, ML embeddings, vector search, pgvector integration.
- **[Migration](references/migration.md)**
  - Migration from Cloud SQL or on-prem PostgreSQL, Database Migration Service patterns.

---

## Official References

- <https://cloud.google.com/alloydb/docs>

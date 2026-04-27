---
name: cloud-sql
description: "Use when provisioning Google Cloud SQL, configuring Cloud SQL Auth Proxy, connection strings, read replicas, backups, PITR, private IP, database migrations, or managed PostgreSQL/MySQL/SQL Server on GCP."
---

# Cloud SQL

## Overview

Cloud SQL is Google Cloud's fully managed relational database service supporting PostgreSQL, MySQL, and SQL Server. It handles automated backups, replication, patching, high availability, and scaling — letting you focus on your application instead of database administration.

## Quick Reference

### Cloud SQL vs AlloyDB

| Feature | Cloud SQL | AlloyDB |
|---|---|---|
| Engines | PostgreSQL, MySQL, SQL Server | PostgreSQL only |
| Storage | Attached SSD (up to 64 TB) | Disaggregated, log-based |
| Availability SLA | 99.95% (HA config) | 99.99% (regional) |
| Columnar engine | Not available | Built-in adaptive |
| ML embeddings | Manual setup | Native Vertex AI |
| Read scaling | Manual read replicas | Read pool (auto-managed) |
| Networking | Public IP or private IP | Private IP only (PSA required) |
| Cost | Lower entry cost | Higher, performance-optimized |
| Best for | General workloads, MySQL/SQL Server | High-performance PostgreSQL |

### Instance Management

| Action | Command |
|---|---|
| Create instance | `gcloud sql instances create NAME --database-version=POSTGRES_15 --tier=db-g1-small --region=REGION` |
| Clone instance | `gcloud sql instances clone SOURCE DEST` |
| Restart instance | `gcloud sql instances restart NAME` |
| Patch/resize | `gcloud sql instances patch NAME --tier=db-n1-standard-4` |
| Delete instance | `gcloud sql instances delete NAME` |
| Set maintenance window | `gcloud sql instances patch NAME --maintenance-window-day=SUN --maintenance-window-hour=3` |

### Key Commands

| Action | Command |
|---|---|
| Create database | `gcloud sql databases create DBNAME --instance=INSTANCE` |
| Create user | `gcloud sql users create USERNAME --instance=INSTANCE --password=PASS` |
| Connect via proxy | `cloud-sql-proxy PROJECT:REGION:INSTANCE` |
| Connect directly | `gcloud sql connect INSTANCE --user=postgres --database=DBNAME` |
| Create backup | `gcloud sql backups create --instance=INSTANCE` |
| List backups | `gcloud sql backups list --instance=INSTANCE` |
| Restore backup | `gcloud sql backups restore BACKUP_ID --restore-instance=INSTANCE` |

### Connection Patterns Overview

| Pattern | When to Use |
|---|---|
| **Auth Proxy** | Recommended default — handles IAM auth and TLS automatically |
| **Private IP** | GKE/GCE on same VPC — lowest latency, no proxy overhead |
| **PSC (Private Service Connect)** | Cross-project or cross-org access without VPC peering |
| **Public IP + authorized networks** | Legacy only — always enforce SSL, restrict to known CIDRs |

```bash
# Enable required APIs
gcloud services enable sqladmin.googleapis.com
gcloud services enable sql-component.googleapis.com

# Create a PostgreSQL instance with HA
gcloud sql instances create my-postgres \
    --database-version=POSTGRES_15 \
    --tier=db-n1-standard-4 \
    --region=us-central1 \
    --availability-type=REGIONAL \
    --storage-type=SSD \
    --storage-size=100GB \
    --storage-auto-increase \
    --backup-start-time=03:00 \
    --enable-bin-log \
    --maintenance-window-day=SUN \
    --maintenance-window-hour=4 \
    --no-assign-ip \
    --network=projects/MY_PROJECT/global/networks/MY_VPC

# Connect via Auth Proxy
cloud-sql-proxy MY_PROJECT:us-central1:my-postgres --port=5432 &
psql "host=127.0.0.1 port=5432 dbname=mydb user=postgres"
```

### Engine-Specific Notes

**PostgreSQL** — Use `POSTGRES_15` or `POSTGRES_16`. Supports pgvector, PostGIS, pg_stat_statements. Set `max_connections` conservatively; use PgBouncer for connection pooling.

**MySQL** — Use `MYSQL_8_0`. InnoDB only. `innodb_buffer_pool_size` defaults to 75% of instance RAM. Binary logging required for read replicas.

**SQL Server** — Use `SQLSERVER_2022_STANDARD` or `ENTERPRISE`. Always-on availability groups supported. Windows Authentication not available; use SQL Server auth or IAM.

### Backup and Restore

```bash
# Enable automated backups with PITR
gcloud sql instances patch my-postgres \
    --backup-start-time=03:00 \
    --enable-bin-log \
    --retained-backups-count=14 \
    --retained-transaction-log-days=7

# On-demand backup
gcloud sql backups create --instance=my-postgres --description="pre-migration"

# Point-in-time restore (PostgreSQL/MySQL)
gcloud sql instances clone my-postgres my-postgres-restored \
    --point-in-time="2025-06-15T14:30:00Z"

# Cross-region replica for disaster recovery
gcloud sql instances create my-postgres-replica \
    --master-instance-name=my-postgres \
    --region=us-east1
```

### Replication

```bash
# Create read replica (same region)
gcloud sql instances create my-postgres-read \
    --master-instance-name=my-postgres \
    --region=us-central1

# Promote replica to standalone (for migrations)
gcloud sql instances promote-replica my-postgres-read

# List replicas
gcloud sql instances list --filter="masterInstanceName=my-postgres"
```

### Security

```bash
# Enable IAM database authentication
gcloud sql instances patch my-postgres \
    --database-flags=cloudsql.iam_authentication=on

# Add IAM user (PostgreSQL)
gcloud sql users create user@example.com \
    --instance=my-postgres \
    --type=CLOUD_IAM_USER

# Enforce SSL
gcloud sql instances patch my-postgres \
    --require-ssl

# Enable audit logging
gcloud sql instances patch my-postgres \
    --database-flags=cloudsql.enable_pgaudit=on
```

<workflow>

## Workflow

### Step 1: Plan Instance Configuration

Choose engine version, tier (machine type), and storage based on workload. For production, always use `--availability-type=REGIONAL` for HA with automatic failover. Size memory to fit the working dataset with ~30% headroom.

### Step 2: Configure Networking

Prefer private IP over public IP. If using private IP, ensure a VPC exists and pass `--network=` and `--no-assign-ip` at creation time. Private IP cannot be added after creation without recreation. For cross-project access, use PSC instead of VPC peering.

### Step 3: Create Instance and Database Objects

Create the instance, then create databases and users. Use IAM database authentication over password auth when possible. Store passwords in Secret Manager.

### Step 4: Set Up Auth Proxy for Application Connections

Deploy the Cloud SQL Auth Proxy as a sidecar (GKE), standalone binary (GCE), or let Cloud Run handle it automatically with `--add-cloudsql-instances`. The proxy handles TLS and IAM authentication transparently.

### Step 5: Configure Backups and Monitoring

Enable automated backups, set PITR retention, and configure maintenance windows during off-peak hours. Enable Query Insights for performance monitoring. Set up alerts for disk usage, CPU, and active connections.

### Step 6: (Optional) Add Read Replicas

For read-heavy workloads, create read replicas and update application connection strings to route read queries to replicas. For PostgreSQL, consider PgBouncer as a connection pool in front of both primary and replicas.

</workflow>

<guardrails>

## Guardrails

- **Never expose public IP without authorized networks and SSL** — use Auth Proxy or private IP; if public IP is required, set `--require-ssl` and restrict `--authorized-networks` to known CIDRs
- **Always enable automated backups and PITR** — set `--backup-start-time` and `--retained-backups-count` at creation; enabling after the fact risks a gap
- **Set maintenance windows to off-peak hours** — patch windows cause brief downtime on non-HA instances; set `--maintenance-window-day` and `--maintenance-window-hour`
- **Prefer IAM database authentication** over password auth for GCP service accounts and human users; passwords must still be rotated for legacy drivers
- **Size for peak + 30% headroom** — Cloud SQL scales storage automatically but compute requires a patch operation with brief restart
- **Use read replicas for read-heavy workloads** — replicas are not a substitute for connection pooling; address both separately
- **Enable Query Insights** — critical for diagnosing slow queries; off by default on older instances
- **Private IP cannot be added post-creation** — decide at instance creation time; recreation is required to switch

</guardrails>

<validation>

### Validation Checkpoint

Before delivering configurations, verify:

- [ ] Instance uses `--availability-type=REGIONAL` for production HA
- [ ] Private IP is configured (`--no-assign-ip --network=`) or Auth Proxy is in place
- [ ] Automated backups and PITR are enabled with appropriate retention
- [ ] Maintenance window is set to off-peak hours
- [ ] SSL is enforced (`--require-ssl`) if public IP exists
- [ ] Passwords are stored in Secret Manager, not hardcoded
- [ ] Storage auto-increase is enabled (`--storage-auto-increase`)

</validation>

<example>

## Example

Create a PostgreSQL 15 instance with HA, configure Auth Proxy, and connect a Python application:

```bash
# 1. Create instance
gcloud sql instances create app-postgres \
    --database-version=POSTGRES_15 \
    --tier=db-n1-standard-2 \
    --region=us-central1 \
    --availability-type=REGIONAL \
    --storage-type=SSD \
    --storage-size=50GB \
    --storage-auto-increase \
    --no-assign-ip \
    --network=projects/my-project/global/networks/my-vpc \
    --backup-start-time=02:00 \
    --retained-backups-count=14 \
    --enable-bin-log \
    --retained-transaction-log-days=7 \
    --maintenance-window-day=SAT \
    --maintenance-window-hour=3 \
    --database-flags=cloudsql.iam_authentication=on

# 2. Create database and user
gcloud sql databases create myapp --instance=app-postgres
gcloud sql users create myapp-user \
    --instance=app-postgres \
    --password="$(gcloud secrets versions access latest --secret=db-password)"

# 3. Grant IAM access for a service account
gcloud sql users create sa@my-project.iam \
    --instance=app-postgres \
    --type=CLOUD_IAM_SERVICE_ACCOUNT

# 4. Start Auth Proxy (local development)
cloud-sql-proxy my-project:us-central1:app-postgres --port=5432 &
```

Python connection string using the Auth Proxy (local) or Unix socket (Cloud Run):

```python
# Via Auth Proxy (local dev / GCE)
DATABASE_URL = "postgresql+asyncpg://myapp-user:password@127.0.0.1:5432/myapp"

# Via Unix socket (Cloud Run — set INSTANCE_CONNECTION_NAME env var)
import os
INSTANCE = os.environ["INSTANCE_CONNECTION_NAME"]  # project:region:instance
DATABASE_URL = f"postgresql+asyncpg://myapp-user:password@/myapp?host=/cloudsql/{INSTANCE}"
```

</example>

---

## References Index

For detailed guides and code examples, refer to the following documents in `references/`:

- **[Connection Patterns](references/connections.md)**
  - GKE sidecar, Cloud Run, Compute Engine, local development, PSC, connection strings, pooling.
- **[Engine-Specific Tuning](references/engines.md)**
  - PostgreSQL flags and extensions, MySQL InnoDB tuning, SQL Server settings, migration paths.

---

## Cross-References

- **Gemini CLI extensions**: `gemini extensions install https://github.com/gemini-cli-extensions/cloud-sql-postgresql` (also `cloud-sql-mysql`, `cloud-sql-sqlserver`)
- **Higher performance PostgreSQL**: see `flow:alloydb`
- **GKE deployment patterns**: see `flow:gke` → Cloud SQL on GKE section

---

## Official References

- <https://cloud.google.com/sql/docs>
- <https://cloud.google.com/sql/docs/postgres/connect-auth-proxy>
- <https://cloud.google.com/sql/docs/postgres/instance-settings>
- <https://cloud.google.com/sql/pricing>

## Shared Styleguide Baseline

- Use shared styleguides for generic language/framework rules to reduce duplication in this skill.
- [General Principles](https://github.com/cofin/flow/blob/main/templates/styleguides/general.md)
- [GCP Scripting](https://github.com/cofin/flow/blob/main/templates/styleguides/cloud/gcp_scripting.md)
- Keep this skill focused on tool-specific workflows, edge cases, and integration details.

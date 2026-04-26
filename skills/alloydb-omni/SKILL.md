---
name: alloydb-omni
description: "Use when running AlloyDB Omni locally or outside GCP, configuring container deployments, Kubernetes operators, RPM installs, columnar engine tests, or local development that needs AlloyDB behavior."
---

# AlloyDB Omni

## Overview

AlloyDB Omni is the downloadable edition of AlloyDB that runs anywhere: local machines, on-premises data centers, or other cloud providers. It is distributed as a container image and includes the same query processing and columnar engine as the managed AlloyDB service.

## Operating Layers

Use this skill in three distinct layers:

1. **Deploy** AlloyDB Omni on Docker, Podman, Kubernetes, or RPM-based hosts.
2. **Connect** an agent or client to the running database.
3. **Operate** the database with lifecycle, tuning, backups, diagnostics, and upgrades.

Keep those layers separate when giving guidance. Deployment is not the same thing as agent connectivity.

## Quick Reference

### Deployment Methods

| Method | Image | Use Case |
|---|---|---|
| Docker | `google/alloydbomni:latest` | Local development, CI |
| Podman | `google/alloydbomni:latest` | Rootless containers, RHEL |
| Kubernetes | AlloyDB Omni Operator | Production on-prem/multi-cloud |
| RPM | `alloydbomni` package | Bare metal / VM (RHEL/CentOS) |

### Key Environment Variables

| Variable | Purpose | Example |
|---|---|---|
| `POSTGRES_PASSWORD` | Initial superuser password (required) | `mysecretpassword` |
| `POSTGRES_DB` | Database to create on first start | `myapp` |
| `POSTGRES_USER` | Superuser name (default: `postgres`) | `postgres` |

### Dev Workflow

1. Start container with `docker compose up -d`
2. Connect with `psql -h localhost -U postgres`
3. Use AlloyDB features (columnar engine, ML embeddings) locally
4. Tear down with `docker compose down` (data persists in named volume)

<workflow>

## Workflow

### Step 1: Choose Deployment Method

Use Docker/Podman for local development and CI. Use the Kubernetes operator for production non-GCP deployments. Use RPM for bare-metal servers.

### Step 2: Configure Container Resources

Set `--memory`, `--cpus`, and `--shm-size` based on workload. For development, 2 CPUs / 4GB RAM / 256MB shared memory is a reasonable starting point.

### Step 3: Set Up Persistence

Always use a named volume for `/var/lib/postgresql/data`. Without a volume, data is lost when the container stops. Optionally mount `./init-scripts` to `/docker-entrypoint-initdb.d` for first-run SQL.

### Step 4: Tune PostgreSQL Parameters

For non-trivial workloads, configure `shared_buffers` (25% of container memory), `effective_cache_size` (75%), and `work_mem` via `ALTER SYSTEM SET` or a mounted config file.

### Step 5: Connect and Develop

Connect via `localhost:5432`. AlloyDB Omni supports all AlloyDB features including the columnar engine, so you can test analytical queries locally.

</workflow>

## Host Integration Order

Use the lowest-admin supported path for the current host, and degrade cleanly:

1. **Gemini CLI**: use the dedicated `alloydb-omni` extension.
2. **Other agents with MCP support**: use MCP Toolbox with the official AlloyDB Omni prebuilt config.
3. **No extension / no MCP**: fall back to Docker/Podman/Kubernetes/RPM plus `psql` and SQL guidance from this skill's references.

Do not make the skill Gemini-only. The Gemini extension path is preferred when available, but the deployment and operational guidance in this skill must still work across other agents and plain terminal workflows.

<guardrails>

## Guardrails

- **Always set container resource limits** — without `--memory` and `--cpus`, the container can consume all host resources and destabilize the machine
- **Always use a named volume** for data persistence — bind mounts work but named volumes are more portable and easier to manage
- **Set `shm_size` to at least 256MB** — the default 64MB is too small for PostgreSQL and causes "could not resize shared memory segment" errors
- **Never use `POSTGRES_PASSWORD` in production** — use secrets management (Docker secrets, Kubernetes secrets, or Vault)
- **Back up the data volume regularly** — use `pg_dump` or volume snapshots; there is no managed backup like GCP AlloyDB
- **Pin the image tag in CI** — `google/alloydbomni:latest` can change between runs; use a specific version tag for reproducibility

</guardrails>

<validation>

### Validation Checkpoint

Before delivering configurations, verify:

- [ ] Container has explicit memory and CPU limits set
- [ ] Data directory uses a named volume, not a tmpfs or anonymous volume
- [ ] `shm_size` is set to at least 256MB
- [ ] `POSTGRES_PASSWORD` is set (container will not start without it)
- [ ] Port mapping is correct (default: 5432:5432)

</validation>

<example>

## Example

Docker Compose for local AlloyDB Omni development:

```yaml
# docker-compose.yml
services:
  alloydb:
    image: google/alloydbomni:latest
    container_name: alloydb-omni
    environment:
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-devsecret}
      POSTGRES_DB: myapp
      POSTGRES_USER: postgres
    ports:
      - "5432:5432"
    volumes:
      - alloydb-data:/var/lib/postgresql/data
      - ./init-scripts:/docker-entrypoint-initdb.d
    restart: unless-stopped
    shm_size: "256m"
    deploy:
      resources:
        limits:
          cpus: "2"
          memory: 4G

volumes:
  alloydb-data:
```

Initialization script to enable the columnar engine:

```sql
-- init-scripts/01-extensions.sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS google_ml_integration;
```

</example>

## Kubernetes Operator Lifecycle

The AlloyDB Omni Kubernetes Operator manages `DBCluster` custom resources (CRD: `dbclusters.alloydbomni.dbadmin.goog/v1`). Key lifecycle operations:

- **HA failover**: enable automatic standby with `availabilityOptions.standby: Enabled` in `primarySpec`; the operator promotes the standby automatically on primary failure
- **Read replica scaling**: `kubectl patch dbcluster <name> --type=merge -p '{"spec":{"readPoolSpec":{"replicas":<N>}}}'`
- **Rolling parameter updates**: patching `primarySpec.parameters` triggers a controlled rolling restart with no data loss
- **Backup**: annotate the DBCluster with `alloydbomni.dbadmin.goog/backup=true` to trigger an immediate backup
- **Upgrades**: update `databaseVersion` or the image tag; the operator orchestrates a rolling restart

See [references/kubernetes-operator.md](references/kubernetes-operator.md) for the full CRD spec, HA configuration YAML, scaling examples, health monitoring, and upgrade procedures.

## RPM Lifecycle

RPM-based AlloyDB Omni installs are a first-class deployment path for RHEL-family hosts, VMs, and bare-metal systems where containers are not the right fit.

Key lifecycle operations:

- **Install repository + package**: add the AlloyDB Omni yum repo, then `yum install alloydbomni`
- **Initialize data directory**: run `alloydb-omni init --data-dir=...` before first start
- **Manage the service**: use `systemctl enable --now alloydb-omni`, `status`, `restart`, and `journalctl`
- **Tune PostgreSQL settings**: change parameters with `ALTER SYSTEM SET ...` and restart the service
- **Upgrade in place**: update the RPM package, restart the service, and verify version + extension state
- **Back up and validate**: verify local storage, service health, and extension availability before and after upgrades

See [references/rpm.md](references/rpm.md) for the full install, service-management, configuration, validation, and upgrade workflow.

## Performance Diagnostics

Key diagnostics for AlloyDB Omni production workloads:

- **Query plans**: use `EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)` to identify sequential scans, high-cost nodes, and buffer hit ratios
- **Invalid indexes**: query `pg_class JOIN pg_index` where `indisvalid = false` to find indexes that need rebuilding with `REINDEX CONCURRENTLY`
- **Bloat detection**: query `pg_stat_user_tables` for `n_dead_tup` and `n_live_tup` ratios; tables with dead-tuple ratio above 20% are candidates for `VACUUM ANALYZE`
- **Active query monitoring**: `pg_stat_activity` filtered on `state = 'active'` and `wait_event_type` to identify lock waits and long-running queries

See [references/performance.md](references/performance.md) for ready-to-run diagnostic queries, autovacuum tuning, and connection lifecycle management.

## Columnar Engine Tuning

The columnar engine accelerates analytical queries by caching selected columns in a compressed in-memory format.

- **Memory limit**: set `google_columnar_engine.memory_limit` (e.g., `ALTER SYSTEM SET google_columnar_engine.memory_limit = '4GB'`) — allocate 10–25% of total container/node memory
- **Recommended columns**: add wide tables with high read frequency and low update frequency via `SELECT google_columnar_engine_add('<table>')` or individual column-level population
- **Cost/benefit check**: compare `EXPLAIN` output before and after adding a table — look for `Custom Scan (columnar scan)` nodes replacing `Seq Scan`
- **Cache inspection**: `SELECT * FROM g_columnar_memory_usage` shows per-relation memory consumption and hit rates

## Gemini CLI and MCP Toolbox

This section is for the **connection layer**, not for deploying AlloyDB Omni itself.

For AlloyDB Omni, prefer the dedicated Gemini CLI extension when Gemini is the active host. Use the generic PostgreSQL route only as a fallback when the dedicated extension is unavailable.

```bash
gemini extensions install https://github.com/gemini-cli-extensions/alloydb-omni --auto-update
gemini extensions config alloydb-omni --scope workspace
```

Guide the user through the required connection variables before starting Gemini:

```bash
export ALLOYDB_OMNI_HOST="<database-host>"
export ALLOYDB_OMNI_PORT="<database-port>"
export ALLOYDB_OMNI_DATABASE="<database-name>"
export ALLOYDB_OMNI_USER="<database-user>"
export ALLOYDB_OMNI_PASSWORD="<database-password>"
export ALLOYDB_OMNI_QUERY_PARAMS="<optional-query-string>"
```

Important configuration guidance:

- Gemini CLI should be `v0.6.0` or newer.
- Load the variables from a `.env` file when possible.
- Connection settings are fixed at session start; restart Gemini to switch databases.
- Treat configuration as workspace-scoped by default, not user-global.

For non-Gemini agents, or when the user needs a shared MCP endpoint, guide them to MCP Toolbox using the AlloyDB Omni prebuilt config rather than inventing a custom setup.

For reusable project workflows, prefer generated workspace skills:

```bash
toolbox --prebuilt alloydb-omni skills-generate \
  --name alloydb-omni-optimize \
  --toolset optimize \
  --description "AlloyDB Omni optimization skill" \
  --output-dir .agents/skills
```

If neither Gemini extensions nor MCP Toolbox are available, fall back to the manual Docker/Podman/Kubernetes/RPM workflows and `psql` diagnostics already documented in this skill's references.

---

## References Index

For detailed guides and code examples, refer to the following documents in `references/`:

- **[Setup & Deployment](references/setup.md)**
  - Container deployment (Docker/Podman), Kubernetes operator, local development workflows.
- **[Configuration](references/config.md)**
  - Memory/CPU tuning, persistence volumes, networking, PostgreSQL parameter overrides.
- **[Kubernetes Operator](references/kubernetes-operator.md)**
  - DBCluster CRD spec, HA failover, read replica scaling, rolling updates, backup annotations, health monitoring, upgrade procedures.
- **[RPM Deployment](references/rpm.md)**
  - RHEL-family installation, `systemd` lifecycle, configuration, upgrades, and operational validation.
- **[Performance Diagnostics](references/performance.md)**
  - Query planning, invalid index detection, bloat analysis, active query monitoring, columnar engine tuning, autovacuum, connection lifecycle.
- **[Gemini + MCP Guidance](references/gemini-mcp.md)**
  - PostgreSQL extension install, env vars, and MCP Toolbox fallback guidance for Omni workflows.

---

## Official References

- <https://cloud.google.com/alloydb/docs/omni>
- <https://docs.cloud.google.com/alloydb/omni/containers/17.5.0/docs/connect-ide-using-mcp-toolbox>
- <https://github.com/gemini-cli-extensions/alloydb-omni>

## Shared Styleguide Baseline

- Use shared styleguides for generic language/framework rules to reduce duplication in this skill.
- [General Principles](https://github.com/cofin/flow/blob/main/templates/styleguides/general.md)
- [PostgreSQL / psql](https://github.com/cofin/flow/blob/main/templates/styleguides/databases/postgres_psql.md)
- Keep this skill focused on tool-specific workflows, edge cases, and integration details.

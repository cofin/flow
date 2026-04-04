---
name: alloydb-omni
description: "Auto-activate for alloydb-omni in compose/k8s configs. AlloyDB Omni expertise: run AlloyDB anywhere (local, on-prem, other clouds) with container-based deployment. Produces container-based AlloyDB Omni deployments for local dev and non-GCP environments. Use when: running AlloyDB locally for development, deploying Omni containers, configuring Kubernetes operators, or testing AlloyDB features without GCP. Not for GCP-managed AlloyDB (see alloydb) or vanilla PostgreSQL."
---

# AlloyDB Omni

## Overview

AlloyDB Omni is the downloadable edition of AlloyDB that runs anywhere: local machines, on-premises data centers, or other cloud providers. It is distributed as a container image and includes the same query processing and columnar engine as the managed AlloyDB service.

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

## Gemini CLI Extension

The AlloyDB Omni Gemini CLI extension provides 24 tools for managing clusters, running diagnostics, and executing administrative operations from the command line:

```bash
gemini extensions install https://github.com/gemini-cli-extensions/alloydb-omni
```

Use this extension to complement operator-based workflows with interactive diagnostics, query analysis, and cluster introspection without writing raw `psql` or `kubectl` commands.

---

## References Index

For detailed guides and code examples, refer to the following documents in `references/`:

- **[Setup & Deployment](references/setup.md)**
  - Container deployment (Docker/Podman), Kubernetes operator, local development workflows.
- **[Configuration](references/config.md)**
  - Memory/CPU tuning, persistence volumes, networking, PostgreSQL parameter overrides.
- **[Kubernetes Operator](references/kubernetes-operator.md)**
  - DBCluster CRD spec, HA failover, read replica scaling, rolling updates, backup annotations, health monitoring, upgrade procedures.
- **[Performance Diagnostics](references/performance.md)**
  - Query planning, invalid index detection, bloat analysis, active query monitoring, columnar engine tuning, autovacuum, connection lifecycle.

---

## Official References

- <https://cloud.google.com/alloydb/docs/omni>

## Shared Styleguide Baseline

- Use shared styleguides for generic language/framework rules to reduce duplication in this skill.
- [General Principles](https://github.com/cofin/flow/blob/main/templates/styleguides/general.md)
- [PostgreSQL / psql](https://github.com/cofin/flow/blob/main/templates/styleguides/databases/postgres_psql.md)
- Keep this skill focused on tool-specific workflows, edge cases, and integration details.

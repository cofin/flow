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

---

## References Index

For detailed guides and code examples, refer to the following documents in `references/`:

- **[Setup & Deployment](references/setup.md)**
  - Container deployment (Docker/Podman), Kubernetes operator, local development workflows.
- **[Configuration](references/config.md)**
  - Memory/CPU tuning, persistence volumes, networking, PostgreSQL parameter overrides.

---

## Official References

- <https://cloud.google.com/alloydb/docs/omni>

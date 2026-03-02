---
name: oracle-26ai-container
description: Oracle AI Database 26ai Free container operations with Podman, including image selection (Full vs Lite), password setup, persistence strategy, health checks, SQL*Plus connectivity, and setup/startup script hooks. Use when provisioning Oracle 26ai containers for local development, CI, integration tests, or troubleshooting runtime behavior.
---

# Oracle 26ai Container

## Overview

Use this skill to run repeatable Oracle AI Database 26ai Free container workflows with current Oracle docs.

## Choose Image Flavor

- Full image: `container-registry.oracle.com/database/free:latest`
- Lite image: `container-registry.oracle.com/database/free:latest-lite`
- Use Lite for faster CI pull/start and lower footprint.
- Use Full when you need features that Lite excludes.
- For CI reproducibility, pin an explicit image version or digest (avoid relying on mutable `latest*` tags alone).

## Start Containers

```bash
# Full image
podman run -d \
  --name oracle26 \
  -p 1521:1521 \
  -e ORACLE_PWD='<strong-password>' \
  container-registry.oracle.com/database/free:latest

# Lite image
podman run -d \
  --name oracle26lite \
  -p 1521:1521 \
  -e ORACLE_PWD='<strong-password>' \
  container-registry.oracle.com/database/free:latest-lite
```

- Wait for container status `healthy` before client connections.
- If `ORACLE_PWD` is omitted, SYS/SYSTEM/PDBADMIN passwords are auto-generated.

## Configure Passwords

- Set `ORACLE_PWD` at container start for deterministic credentials.
- Rotate after startup when needed:

```bash
podman exec <container_name> ./setPassword.sh '<new-password>'
```

## Configure Persistence

- Mount data at `/opt/oracle/oradata` to persist DB state across container recreation.
- A fresh DB setup on an empty mounted directory can take around 10 minutes.
- Ensure mounted host paths are writable by container uid `54321` (`oracle` user in container).

## Connect and Verify

- Oracle listener port is `1521`.
- Service names: `FREE` (root/CDB), `FREEPDB1` (default PDB).
- Connect from inside container:

```bash
podman exec -it <container_name> sqlplus system/<password>@FREE
podman exec -it <container_name> sqlplus pdbadmin/<password>@FREEPDB1
```

## Run Post-Setup and Startup Scripts

- Mount setup scripts to `/opt/oracle/scripts/setup`.
- Mount startup scripts to `/opt/oracle/scripts/startup`.
- Use `.sql` or `.sh` files and prefix with numeric ordering (`01_`, `02_`, ...).
- Setup scripts run after database setup.
- Startup scripts run after database startup.
- Reused persisted data skips new database setup, so setup scripts are not re-applied.

## Handle Full vs Lite Differences

- `ORACLE_PWD` is supported.
- Oracle docs list `ORACLE_PDB` in Full image startup options.
- Oracle docs list `ORACLE_CHARACTERSET`, `ENABLE_ARCHIVELOG`, and `ENABLE_FORCE_LOGGING` in Full image custom configuration.
- Lite excludes a set of advanced features. Validate feature needs before choosing Lite.

## Use Recommended Defaults

- Use Lite + ephemeral storage for CI validation and adapter smoke tests.
- Use Full + persisted volume + explicit port mapping for feature validation and deeper local debugging.
- Gate tests that depend on advanced Oracle features so Lite-based CI jobs skip them explicitly.

## Learn More (Official)

- Oracle AI Database Free overview: https://www.oracle.com/database/free/
- Oracle Database Free container image docs (Full/Lite, env vars, scripts): https://container-registry.oracle.com/ords/ocr/ba/database/free
- Oracle Database Free connect and service naming docs: https://docs.oracle.com/en/database/oracle/oracle-database/23/xeinl/connecting-oracle-database-free.html
- Podman run reference: https://docs.podman.io/en/latest/markdown/podman-run.1.html

## Shared Styleguide Baseline

- Use shared styleguides for generic language/framework rules to reduce duplication in this skill.
- [General Principles](https://github.com/cofin/flow/blob/main/templates/styleguides/general.md)
- [Oracle SQL*Plus](https://github.com/cofin/flow/blob/main/templates/styleguides/databases/oracle_sqlplus.md)
- [Bash](https://github.com/cofin/flow/blob/main/templates/styleguides/languages/bash.md)
- Keep this skill focused on tool-specific workflows, edge cases, and integration details.

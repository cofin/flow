---
name: oracle-26ai-container
description: Oracle AI Database 26ai Free container operations with Podman, including image selection (Full vs Lite), secure password setup, persistence strategy, health checks, SQL*Plus connectivity, startup/setup script hooks, and True Cache network topology basics. Use when provisioning Oracle 26ai containers for local development, CI, integration tests, or troubleshooting runtime behavior.
---

# Oracle 26ai Container

## Overview

Use this skill to choose the right Oracle 26ai image and run repeatable Podman workflows for dev/test environments.

## Choose Image Flavor

- Use Full image (`container-registry.oracle.com/database/free:latest`) when advanced features are required.
- Use Lite image (`container-registry.oracle.com/database/free:latest-lite`) when faster pull/start and smaller footprint are preferred (for example CI smoke tests).
- Expect Lite to exclude a set of advanced features; do not assume feature parity with Full.

## Start Containers

```bash
# Full image
podman run -d --name oracle26 container-registry.oracle.com/database/free:latest

# Lite image
podman run -d --name oracle26lite container-registry.oracle.com/database/free:latest-lite
```

- Wait for `podman ps` to report status `healthy` before connecting clients.
- Expect random SYS/SYSTEM/PDBADMIN passwords when no password input is provided.
- For reproducible CI, pin explicit image tags or digests instead of relying only on mutable `latest` tags.

## Configure Passwords

- Prefer `--secret` inputs on Podman for sensitive credentials.
- Use `-e ORACLE_PWD=<password>` only for local, low-risk workflows.
- Rotate account passwords after startup when needed:

```bash
podman exec <container_name> ./setPassword.sh <new_password>
```

## Configure Persistence

- Mount data at `/opt/oracle/oradata` to persist DB state across container recreation.
- Prefer named Podman volumes for fast startup from prebuilt datafiles.
- Expect first-time initialization to take significantly longer when mounting an empty host directory.
- Ensure mounted host paths are writable by container uid `54321` (`oracle` user in container).

## Connect and Verify

- Publish listener port `1521` with `-p <host_port>:1521` or `-P`.
- Use service `FREE` for CDB root and `FREEPDB1` for default PDB.
- Connect from inside container:

```bash
podman exec -it <container_name> sqlplus system/<password>@FREE
podman exec -it <container_name> sqlplus pdbadmin/<password>@FREEPDB1
```

## Run Post-Setup and Startup Scripts

- Mount setup scripts to `/opt/oracle/scripts/setup`.
- Mount startup scripts to `/opt/oracle/scripts/startup`.
- Use `.sql` or `.sh` files and prefix with numeric ordering (`01_`, `02_`, ...).
- Expect setup scripts to run only during fresh database creation; prebuilt DB startup alone does not re-run setup scripts.

## Handle Full vs Lite Differences

- `ORACLE_PWD` is available across Full and Lite images.
- Use Full-specific env toggles (`ORACLE_CHARACTERSET`, `ENABLE_ARCHIVELOG`, `ENABLE_FORCE_LOGGING`) only when Full image behavior is required.
- Use Lite-specific options (for example `ORACLE_PDB`) only when running Lite image workflows.
- Avoid Lite for scenarios that need Oracle True Cache or other excluded advanced components.

## Use Recommended Defaults

- Use Lite + ephemeral storage for CI validation and adapter smoke tests.
- Use Full + persisted volume + explicit port mapping for feature validation and deeper local debugging.
- Gate tests that depend on advanced Oracle features so Lite-based CI jobs skip them explicitly.

## Official References

- https://container-registry.oracle.com/ords/ocr/ba/database/free
- https://www.oracle.com/database/free/
- https://www.oracle.com/database/free/get-started/
- https://docs.oracle.com/en/database/oracle/property-graph/25.3/spgdg/quick-start-graph-server-26ai-lite-container.html
- https://docs.podman.io/en/latest/markdown/podman-run.1.html
- https://docs.podman.io/en/latest/markdown/podman-secret-create.1.html

## Shared Styleguide Baseline

- Use shared styleguides for generic language/framework rules to reduce duplication in this skill.
- [General Principles](https://github.com/cofin/flow/blob/main/templates/styleguides/general.md)
- [Oracle SQL*Plus](https://github.com/cofin/flow/blob/main/templates/styleguides/databases/oracle_sqlplus.md)
- [Bash](https://github.com/cofin/flow/blob/main/templates/styleguides/languages/bash.md)
- Keep this skill focused on tool-specific workflows, edge cases, and integration details.

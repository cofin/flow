# Oracle OCI Best Practices

## Overview

Use this reference when working with OCI-based data paths (connect, execute, fetch, bind, transaction control) and when configuring Oracle Instant Client across local dev and CI.

## OCI implementation rules

1. Wrap OCI handles in RAII-style owners to guarantee cleanup.
2. Check OCI return codes immediately and include context in diagnostics.
3. Keep NLS/session settings explicit instead of relying on ambient defaults.
4. Reuse prepared statements and array operations for throughput.

## Connection and credential handling

1. Prefer secrets/secure config flow instead of embedding credentials.
2. Support wallet/TNS-based flows where applicable.
3. Keep connection string parsing strict and explicit.
4. Cache connections only with clear invalidation/reconnect behavior.

## Data-path best practices

1. Use array fetch/bind for bulk transfer; tune prefetch/array sizes with measured data.
2. Be explicit in LOB and long-text handling.
3. Handle Oracle-specific types (for example spatial/vector) via deliberate conversion policies.
4. Treat transaction behavior as an explicit contract and test it.

## Instant Client and build hygiene

1. Ensure both Basic and SDK components are available when compiling OCI-dependent code.
2. Keep `ORACLE_HOME`/library path handling deterministic in local and CI builds.
3. Validate platform differences (Linux/macOS/Windows) with dedicated setup scripts.
4. Document fallback behavior when OCI libraries are not found.

## Validation checklist

1. Connection success/failure paths are covered with actionable messages.
2. Statement execution paths cover bind, fetch, and error cases.
3. Type mappings have targeted tests for edge values.
4. Integration tests run against a real Oracle container/environment.

## Learn more (official)

1. Oracle Call Interface Programmer's Guide (19c): <https://docs.oracle.com/en/database/oracle/oracle-database/19/lnoci/index.html>
2. Oracle Instant Client install/config docs: <https://www.oracle.com/database/technologies/instant-client.html>
3. Oracle Database Free docs: <https://www.oracle.com/database/free/get-started/>
4. Oracle SQL and datatype references: <https://docs.oracle.com/en/database/>

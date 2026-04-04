# Project Patterns

> Ralph-style consolidated learnings extracted from completed tracks.
> Read this file before starting new work to prime context.
> Update this file at phase/track completion with elevated patterns.

## Code Conventions

<!-- Patterns related to code style, imports, naming, structure -->

## Architecture

<!-- Patterns related to module organization, data flow, boundaries -->

## Gotchas

<!-- Common mistakes, edge cases, things to watch out for -->

## Testing

<!-- Testing patterns, mocking strategies, coverage approaches -->

## Context

<!-- Where things live, key files, navigation tips -->

## Skill Associations

<!-- Map specific domains to the best skills for analysis -->

### Cross-Cutting (Use Across All Domains)

| Domain | Recommended Skill | When to Use |
|--------|-------------------|-------------|
| Security | `flow:security-auditor` | Auth, input handling, secrets, API keys |
| Architecture | `flow:architecture-critic` | New modules, boundary changes, coupling |
| Performance | `flow:performance-analyst` | Hot paths, DB queries, loops, caching |
| Decision Making | `flow:consensus` | Choosing between A/B approaches |
| Challenge Claims | `flow:challenge` | Reviewing assertions, preventing bias |
| Deep Analysis | `flow:deepthink` | Resistant problems, shallow analysis |
| Code Tracing | `flow:tracer` | Execution paths, call chains, data flow |
| Multiple Viewpoints | `flow:perspectives` | Trade-offs, risk assessment, pros/cons |
| Devil's Advocate | `flow:devils-advocate` | PR review, design proposals, pushback |
| Documentation | `flow:docgen` | API docs, module docs, reference guides |
| API/Framework Lookup | `flow:apilookup` | External docs, versions, breaking changes |

### Languages

| Domain | Recommended Skill | When to Use |
|--------|-------------------|-------------|
| Python | `flow:python` | .py files, pyproject.toml, uv, ruff, mypy |
| Rust | `flow:rust` | .rs files, Cargo.toml, FFI (PyO3/napi-rs) |
| C++ | `flow:cpp` | .cpp/.hpp files, CMakeLists.txt |
| Mojo | `flow:mojo` | .mojo files, SIMD, Python interop |
| Bash | `flow:bash` | .sh files, shell scripts |
| TypeScript/JS | See framework skills | Use react/vue/svelte/angular as appropriate |

### Backend Frameworks

| Domain | Recommended Skill | When to Use |
|--------|-------------------|-------------|
| Litestar | `flow:litestar` | Route handlers, guards, middleware, DTOs |
| HTMX | `flow:htmx` | hx-* attributes, partial HTML responses |
| Inertia.js | `flow:inertia` | Server routing with client rendering |

### Frontend Frameworks

| Domain | Recommended Skill | When to Use |
|--------|-------------------|-------------|
| React | `flow:react` | .tsx/.jsx, hooks, server components |
| Vue | `flow:vue` | .vue files, Composition API |
| Svelte | `flow:svelte` | .svelte files, runes ($state, $derived) |
| Angular | `flow:angular` | angular.json, signals, standalone components |
| TanStack | `flow:tanstack` | Router, Query, Table, Form |
| Tailwind/Shadcn | `flow:tailwind` / `flow:shadcn` | Utility classes, cn(), Radix primitives |

### Data & Databases

| Domain | Recommended Skill | When to Use |
|--------|-------------------|-------------|
| SQLAlchemy/ORM | `flow:advanced-alchemy` | ORM models, repositories, Alembic migrations |
| SQLSpec | `flow:sqlspec` | Raw SQL, query builder, driver adapters |
| PostgreSQL | `flow:postgres` | .sql files, psql, indexing, PL/pgSQL |
| MySQL | `flow:mysql` | MySQL/MariaDB queries, stored procedures |
| Oracle | `flow:oracle` | PL/SQL, ORDS, cx_Oracle/oracledb |
| DuckDB | `flow:duckdb` | Analytical SQL, ETL, multi-source reads |
| SQL Server | `flow:sqlserver` | T-SQL, execution plans, sqlcmd |
| Dishka DI | `flow:dishka` | Dependency injection, providers, scopes |
| Pydantic | `flow:pydantic` | Data validation, settings, model config |
| msgspec | `flow:msgspec` | High-perf serialization, structs |

### Build & DevOps

| Domain | Recommended Skill | When to Use |
|--------|-------------------|-------------|
| Docker/Podman | `flow:docker` / `flow:podman` | Dockerfiles, compose, distroless, rootless |
| Makefile | `flow:makefile` | GNU Make targets, uv-based automation |
| Vite | `flow:vite` | vite.config.ts, HMR, plugins, bundling |
| Biome | `flow:biome` | biome.json, JS/TS linting/formatting |
| Bun | `flow:bun` | bun.lockb, bunfig.toml, Bun runtime |
| Testing | `flow:testing` | pytest, vitest, fixtures, mocking |
| pytest-databases | `flow:pytest-databases` | Docker test containers, DB fixtures |
| Type Checking | `flow:ty` | ty.toml, fast Python type checking |

### Cloud & Deployment

| Domain | Recommended Skill | When to Use |
|--------|-------------------|-------------|
| GCP | `flow:gcp` | gcloud, IAM, Cloud Storage, Pub/Sub |
| Cloud Run | `flow:cloud-run` | Serverless containers, traffic splitting |
| GKE | `flow:gke` | Kubernetes, Helm charts, kubectl |
| AlloyDB | `flow:alloydb` / `flow:alloydb-omni` | Managed PostgreSQL on GCP / local |
| Cloud SQL | `flow:cloud-sql` | Managed databases on GCP |
| Railway | `flow:railway` | Railway deployment, services, databases |

### Extension Development (Native Bindings)

| Domain | Recommended Skill | When to Use |
|--------|-------------------|-------------|
| Rust + Python | `flow:rust` | PyO3, maturin, extension modules |
| C++ + Python | `flow:cpp` | C extensions, pybind11 |
| Mojo + Python | `flow:mojo` | Mojo kernels, hatch-mojo, SIMD |
| IPC | `flow:ipc` | Shared memory, ring buffers, SPSC/MPMC |

---

## Pattern Sources

<!-- Track which tracks contributed patterns -->

| Pattern | Source Track | Date |
|---------|--------------|------|

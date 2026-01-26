# Code Style Guides

Comprehensive style guides for languages and frameworks. These guides are designed to be generic and applicable across projects.

## Structure

```
styleguides/
├── general.md              # Universal principles
├── languages/              # Core language guides
│   ├── python.md           # Python with async patterns
│   ├── typescript.md       # TypeScript with strict mode
│   ├── javascript.md       # ES modules, modern JS
│   ├── rust.md             # Rust with FFI patterns
│   ├── go.md               # Idiomatic Go
│   ├── bash.md             # Bash/shell scripting (Google style)
│   └── powershell.md       # PowerShell scripting
├── databases/              # Database scripting guides
│   ├── postgres_psql.md    # PostgreSQL psql automation
│   ├── mysql_mariadb.md    # MySQL/MariaDB scripting
│   ├── oracle_sqlplus.md   # Oracle SQL*Plus scripting
│   └── mongodb.md          # MongoDB mongosh scripting
├── cloud/                  # Cloud platform automation
│   └── gcp_scripting.md    # GCP BigQuery & Cloud Storage
└── frameworks/             # Framework-specific guides
    ├── react.md            # React 18+ with hooks
    ├── vue.md              # Vue 3 Composition API
    ├── svelte.md           # Svelte 5 with runes
    ├── angular.md          # Angular 18+ with signals
    ├── litestar.md         # Litestar web framework
    ├── htmx.md             # HTMX hypermedia
    ├── inertia.md          # Inertia.js SPAs
    ├── tanstack.md         # Router, Query, Table, Form
    ├── tailwind.md         # Tailwind CSS & Shadcn
    ├── testing.md          # pytest & Vitest
    ├── orm.md              # SQLAlchemy & Advanced Alchemy
    ├── dishka.md           # Dishka dependency injection
    ├── sqlspec.md          # SQLSpec SQL query mapper
    ├── pytest-databases.md # Database testing with Docker
    └── google-adk.md       # Google ADK AI agents
```

## Quick Reference

### Languages

| Language | Key Features |
|----------|--------------|
| [Python](languages/python.md) | Async-first, PEP 604 unions, Dishka DI |
| [TypeScript](languages/typescript.md) | Strict mode, named exports, discriminated unions |
| [JavaScript](languages/javascript.md) | ES modules, const/let, arrow functions |
| [Rust](languages/rust.md) | Unsafe documentation, FFI (PyO3/napi-rs) |
| [Go](languages/go.md) | gofmt, explicit errors, channels |
| [Bash](languages/bash.md) | Strict mode, Google style, shellcheck |
| [PowerShell](languages/powershell.md) | CmdletBinding, approved verbs, modules |

### Frontend Frameworks

| Framework | Key Features |
|-----------|--------------|
| [React](frameworks/react.md) | Hooks, Server Components, TanStack integration |
| [Vue](frameworks/vue.md) | Composition API, `<script setup>`, Pinia |
| [Svelte](frameworks/svelte.md) | Runes (`$state`, `$derived`), snippets |
| [Angular](frameworks/angular.md) | Signals, standalone components, control flow |

### Backend & Integration

| Guide | Key Features |
|-------|--------------|
| [Litestar](frameworks/litestar.md) | Controllers, DTOs, plugins, Vite integration |
| [HTMX](frameworks/htmx.md) | Partial HTML, OOB swaps, triggers |
| [Inertia](frameworks/inertia.md) | Server routing with client rendering |
| [ORM](frameworks/orm.md) | SQLAlchemy models, services, migrations |
| [Dishka](frameworks/dishka.md) | Dependency injection, providers, scopes |
| [SQLSpec](frameworks/sqlspec.md) | Raw SQL, query builder, named statements |
| [Google ADK](frameworks/google-adk.md) | AI agents, tools, Vertex AI integration |

### Tools & Libraries

| Guide | Key Features |
|-------|--------------|
| [TanStack](frameworks/tanstack.md) | Router, Query, Table, Form |
| [Tailwind](frameworks/tailwind.md) | Utility classes, Shadcn/ui components |
| [Testing](frameworks/testing.md) | pytest, Vitest, mocking |
| [pytest-databases](frameworks/pytest-databases.md) | Docker containers, test isolation, fixtures |

### Database Scripting

| Guide | Key Features |
|-------|--------------|
| [PostgreSQL](databases/postgres_psql.md) | psql, transactional DDL, \copy, pg_dump |
| [MySQL/MariaDB](databases/mysql_mariadb.md) | mysql CLI, safe modes, mysqldump |
| [Oracle SQL*Plus](databases/oracle_sqlplus.md) | SQL*Plus scripting, bind variables, wallets |
| [MongoDB](databases/mongodb.md) | mongosh, aggregation pipelines, upserts |

### Cloud Automation

| Guide | Key Features |
|-------|--------------|
| [GCP Scripting](cloud/gcp_scripting.md) | BigQuery bq CLI, gcloud storage, parameterized queries |

## Core Principles

From [general.md](general.md):

1. **Simplicity Over Cleverness** - Prefer straightforward solutions
2. **Avoid Over-Engineering** - Only add what's needed
3. **Type Safety** - Use the strongest type system available
4. **Explicit Error Handling** - Validate at boundaries, handle gracefully
5. **Consistency** - Follow existing patterns

## Usage

These guides are designed for:

- **AI assistants** - As context for code generation
- **New team members** - Quick onboarding to patterns
- **Code review** - Reference for style decisions
- **Skill discovery** - Finding relevant patterns for a technology

Each guide includes:

- Core rules and patterns
- Code examples
- Best practices
- Anti-patterns to avoid
- Integration with other tools

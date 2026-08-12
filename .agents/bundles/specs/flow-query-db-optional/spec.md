---
type: flow
id: flow-query-db-optional
title: Optional Query CLI & Database Layer
description: Implement a Python-based query CLI using sqlspec and duckdb to query
  bundles, knowledge, and map codebase targets.
status: planned
parent_prd: remove-beads
created_at: '2026-07-09T00:27:33+00:00'
updated_at: '2026-07-09T00:27:33+00:00'
tags:
- cli
- database
- query
- sqlspec
- duckdb
flow_id: flow-query-db-optional
---

# Specification: Optional Query CLI & Database Layer

This flow implements a lightweight, fast, in-memory query database and command-line interface (CLI) to query the active flows, tasks, knowledge articles, and codebase file targets. 

By parsing the filesystem-based specifications and knowledge documents on-the-fly and loading them into an in-memory DuckDB instance, we provide developer-friendly CLI commands and a raw SQL query interface, all without the overhead of external database servers or persistent caches.

## Requirements

1. **Schema Mapping & Persistence**:
   - The database runs **in-memory** on every command invocation, parsing `.agents/bundles/specs/` and `.agents/bundles/knowledge/` directories.
   - Tables created:
     - `specs`: Stores flow specifications (metadata from frontmatter).
       - Columns: `id` (VARCHAR PRIMARY KEY), `title` (VARCHAR), `description` (VARCHAR), `status` (VARCHAR), `parent_prd` (VARCHAR), `created_at` (TIMESTAMP), `updated_at` (TIMESTAMP), `tags` (VARCHAR)
     - `tasks`: Stores tasks parsed from `spec.md` checklist files (status, description, target files, implementation details, verification).
       - Columns: `id` (VARCHAR PRIMARY KEY), `flow_id` (VARCHAR REFERENCES specs(id)), `title` (VARCHAR), `status` (VARCHAR), `priority` (VARCHAR), `depends_on` (VARCHAR), `created_at` (TIMESTAMP), `updated_at` (TIMESTAMP), `assigned_to` (VARCHAR), `files` (VARCHAR), `tests` (VARCHAR), `commit` (VARCHAR), `description` (VARCHAR), `verification` (VARCHAR)
     - `knowledge`: Stores global knowledge base articles (frontmatter + content).
       - Columns: `id` (VARCHAR PRIMARY KEY), `category` (VARCHAR), `path` (VARCHAR), `title` (VARCHAR), `description` (VARCHAR), `tags` (VARCHAR), `content` (VARCHAR), `created_at` (TIMESTAMP), `updated_at` (TIMESTAMP)
     - `targets`: Maps file targets (codebase files) to flow IDs and task IDs to show which files are modified/affected by which flows or tasks.
       - Columns: `file_path` (VARCHAR), `flow_id` (VARCHAR), `task_id` (VARCHAR), PRIMARY KEY (`file_path`, `flow_id`, `task_id`)

2. **Parser Engine**:
   - Parse YAML frontmatter of all `.md` files under specs and knowledge directories. Supporting both `id` and `flow_id` keys in frontmatter for flow ID mapping.
   - Parse tasks from the `## Implementation Plan` section in `spec.md` files:
     - Checkbox status mapping:
       - `[ ]` -> `open`
       - `[~]` -> `in_progress`
       - `[x]` -> `closed`
       - `[!]` -> `blocked`
       - `[-]` -> `skipped`
     - Sub-bullets parser:
       - Extract relative paths from `**Target Files**` (e.g. `[path/to/file](./path/to/file)` -> `path/to/file`).
       - Extract description from `**Implementation Details**`.
       - Extract commands/methods from `**Verification**`.
   - Relative Path Normalization:
     - All linked file targets (e.g. `../../../../pyproject.toml`) parsed from target files must be normalized relative to the directory containing the spec/knowledge file, and then converted to a path relative to the repository root (e.g. `pyproject.toml` or `tools/query.py`).

3. **CLI Interface**:
   - `python tools/query.py flows [options]`: List specs, filter by status.
     - Options: `--status <status>`, `--json`
   - `python tools/query.py tasks [options]`: List tasks, filter by flow_id, status, or target file path.
     - Options: `--flow-id <flow_id>`, `--status <status>`, `--target <path>`, `--json`
   - `python tools/query.py knowledge [options]`: Search knowledge base using DuckDB LIKE search, filter by tag/category.
     - Options: `--query <query>`, `--tag <tag>`, `--category <category>`, `--json`
   - `python tools/query.py targets [options]`: List all mapped codebase targets and their associated flows/tasks.
     - Options: `--file <path>`, `--flow-id <flow_id>`, `--json`
   - `python tools/query.py sql "<query>" [options]`: Run a raw SQL query against the in-memory DuckDB tables and output the results as a formatted table (or JSON if `--json` is specified).
     - Options: `--json`

---

## Implementation Plan

### Phase 1: Dependency Setup & Schema Modeling

- [ ] 1.1 Add dependencies to `pyproject.toml`
  - **Target Files**: [pyproject.toml](../../../../pyproject.toml)
  - **Implementation Details**: Add `duckdb>=1.0.0` and `sqlspec>=0.51.0` to the `project.dependencies` list in `pyproject.toml`.
  - **Verification**: Run `pip install -e .` to verify successful installation.

- [ ] 1.2 Write Schema and Model tests
  - **Target Files**: [tests/test_query_cli.py](../../../../tests/test_query_cli.py)
  - **Implementation Details**: Write unit tests checking Pydantic validation of data structures/models representing database rows for `Flow`, `Task`, `Knowledge`, and `TargetMapping`.
  - **Verification**: Run `pytest tests/test_query_cli.py -k "test_models"` and verify they fail (Red).

- [ ] 1.3 Implement Data Schemas and SQLSpec Models
  - **Target Files**: [tools/query.py](../../../../tools/query.py)
  - **Implementation Details**: Implement schemas using Pydantic or standard library dataclasses for `FlowModel`, `TaskModel`, `KnowledgeModel`, and `TargetMappingModel`.
  - **Verification**: Run `pytest tests/test_query_cli.py -k "test_models"` and verify they pass (Green).

### Phase 2: Spec & Task File Parser

- [ ] 2.1 Write Parser Tests
  - **Target Files**: [tests/test_query_cli.py](../../../../tests/test_query_cli.py)
  - **Implementation Details**: Write unit tests verifying YAML frontmatter extraction and spec task parser logic using mock/simulated markdown contents.
  - **Verification**: Run `pytest tests/test_query_cli.py -k "test_parser"` and verify they fail (Red).

- [ ] 2.2 Implement Parser Engine
  - **Target Files**: [tools/query.py](../../../../tools/query.py)
  - **Implementation Details**: Implement `parse_frontmatter` to extract YAML metadata block, and `parse_spec_tasks` to extract status checkboxes, target files (with relative-path repo root normalization), details, and verification commands.
  - **Verification**: Run `pytest tests/test_query_cli.py -k "test_parser"` and verify they pass (Green).

### Phase 3: SQLSpec & DuckDB Connection Layer

- [ ] 3.1 Write Connection & Loader Tests
  - **Target Files**: [tests/test_query_cli.py](../../../../tests/test_query_cli.py)
  - **Implementation Details**: Write tests checking database setup, table DDL creation, and directory walking loader logic under a temporary mock directory.
  - **Verification**: Run `pytest tests/test_query_cli.py -k "test_db"` and verify they fail (Red).

- [ ] 3.2 Initialize Connection and Implement Loader
  - **Target Files**: [tools/query.py](../../../../tools/query.py)
  - **Implementation Details**: Initialize sync `DuckDBConfig` using `:memory:` database. Implement tables creation (`specs`, `tasks`, `knowledge`, `targets`). Implement `load_database` scanner to walk specs and knowledge directories, parse markdown files, and insert parsed objects using SQLSpec bulk loads.
  - **Verification**: Run `pytest tests/test_query_cli.py -k "test_db"` and verify they pass (Green).

### Phase 4: CLI Commands & Formatting

- [ ] 4.1 Write CLI and Console Formatting Tests
  - **Target Files**: [tests/test_query_cli.py](../../../../tests/test_query_cli.py)
  - **Implementation Details**: Write tests mocking command line execution arguments for all CLI subcommands (`flows`, `tasks`, `knowledge`, `targets`, `sql`) and verifying their stdout outputs match either the tabular console representation or the parsed JSON array when `--json` is supplied.
  - **Verification**: Run `pytest tests/test_query_cli.py -k "test_cli"` and verify they fail (Red).

- [ ] 4.2 Implement CLI Commands and Console Formatter
  - **Target Files**: [tools/query.py](../../../../tools/query.py)
  - **Implementation Details**: Use `argparse` to declare subcommands and filter arguments. Implement formatted printing: if `--json` is passed, serialize rows to JSON; otherwise print a clean ASCII layout table. Implement the `sql` command executing queries directly on the in-memory DuckDB connection.
  - **Verification**: Run `pytest tests/test_query_cli.py -k "test_cli"` and verify they pass (Green). Also manually execute `python tools/query.py flows` and `python tools/query.py sql "SELECT count(*) FROM tasks"`.

### Phase 5: Verification & Edge Cases

- [ ] 5.1 Run complete test suite and verify coverage
  - **Target Files**: [tests/test_query_cli.py](../../../../tests/test_query_cli.py)
  - **Implementation Details**: Verify suite behavior against empty spec/knowledge directories, malformed yaml frontmatter (warn and skip instead of crashing), and tasks with missing attributes.
  - **Verification**: Run `pytest tests/test_query_cli.py --cov=tools/query` and confirm coverage is above 90%.

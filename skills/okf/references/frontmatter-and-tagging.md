# OKF Frontmatter and Tagging Guide

This reference provides concrete frontmatter templates, tagging taxonomies, and integrity rules for authoring Open Knowledge Format (OKF v0.2) concept documents.

## Contents

- [Standard Frontmatter Template](#1-standard-frontmatter-template)
- [Frontmatter by Concept Type](#2-frontmatter-by-concept-type)
- [Tagging Best Practices](#3-tagging-best-practices)
- [State vs Status Invariant](#4-state-vs-status-invariant)

---

## 1. Standard Frontmatter Template

Every concept document starts with a YAML frontmatter block:

```yaml
---
type: <Type name>                  # REQUIRED: non-empty string
title: <Optional display name>     # Optional string
description: <Optional summary>    # Optional single sentence
resource: <Optional canonical URI> # Optional URI string
tags: [<tag>, <tag>, ...]          # Optional list of strings
# ... optional provenance, trust, lifecycle, or state fields
---
```

---

## 2. Frontmatter by Concept Type

### 2.1 Technical & Data Concepts

#### Table / Dataset

```yaml
---
type: BigQuery Table
title: Customer Orders
description: One row per completed customer order across all channels.
resource: https://console.cloud.google.com/bigquery?p=acme&d=sales&t=orders
tags: [sales, orders, revenue]
sources:
  - id: bq-schema
    resource: https://console.cloud.google.com/bigquery
    last_modified: 2026-05-30
---
```

#### API Endpoint

```yaml
---
type: API Endpoint
title: User Authentication Endpoint
description: POST endpoint for authenticating users and issuing JWT session tokens.
resource: https://api.example.com/v1/auth/login
tags: [api, auth, security]
---
```

#### Metric / SLA

```yaml
---
type: Metric
title: Order Ingestion Freshness SLA
description: Maximum allowed lag between order event submission and BigQuery availability.
tags: [monitoring, freshness, sla, data-pipeline]
---
```

### 2.2 Operational & Procedural Concepts

#### Playbook / Runbook

```yaml
---
type: Playbook
title: "Incident Response: Pipeline Freshness Alert"
description: Triage and recovery steps when data pipeline exceeds 30m SLA.
tags: [oncall, incident, triage, pipeline]
---
```

#### Guide / Knowledge Chapter

```yaml
---
type: Guide
title: Repository Workflow and Canonical Commands
description: Build, test, lint, and verification commands used across all flows.
tags: [workflow, commands, developer-guide]
---
```

#### Pattern / Convention

```yaml
---
type: Pattern
title: Repository Patterns and Conventions
description: Elevated conventions, architectural invariants, and gotchas.
tags: [architecture, conventions, patterns]
---
```

### 2.3 Flow Specification, Chapter, & Task Concepts

#### Spec (`specs/<flow_id>/spec.md` and `specs/<flow_id>/chapters/<ch_id>/spec.md`)

```yaml
---
type: Spec
flow_id: user-auth
title: User Authentication
description: Repository-native user authentication with JWT signing and session middleware.
status: stable
state: active
has_chapters: true
chapters: [ch01-token-signer, ch02-session-middleware]
current_chapter: ch02-session-middleware
current_task: user-auth:ch02:t01
plan_revision: 1
plan_commit: 8775d6c
state_revision: 1
last_verified_checkpoint: 4f91c2a
last_reviewed_chapter: ch01-token-signer
last_reviewed_commit: 4f91c2a
created_at: 2026-11-06T00:00:00Z
updated_at: 2026-11-06T01:00:00Z
generated: { by: flow/0.26.0, at: 2026-11-06T00:00:00Z }
verified:
  - by: agent:code-reviewer
    at: 2026-11-06T01:00:00Z
    commit: 4f91c2a
sources:
  - id: auth-entry
    resource: src/auth/middleware.py::AuthMiddleware
    title: Request authentication middleware seam
tags: [feature, auth, security]
---
```

Nested chapter specs (`specs/<flow_id>/chapters/<ch_id>/spec.md`) additionally declare `parent_flow: <flow_id>`, `chapter_id: ch01-<slug>`, `planning_status: complete | empirical_dependent`, `depends_on_chapters: [...]`, `replan_trigger: null | "<empirical output>"`, and `last_reviewed_commit: null | "<sha>"`.

#### Task (`specs/<flow_id>/tasks/<id>-<slug>.md` or `specs/<flow_id>/chapters/<ch_id>/tasks/<id>-<slug>.md`)

```yaml
---
type: Task
id: user-auth:ch01:t01
chapter_id: ch01-token-signer
title: Add JWT token signer and canonical unit tests
description: Implement EdDSA JWT signing/verification with parameterized public-seam tests.
status: stable
state: pending
priority: P1
verification_strategy: behavior_tdd
depends_on: []
read_set: [src/auth/tokens.py, tests/auth/test_tokens.py]
files: [src/auth/tokens.py]
tests: [tests/auth/test_tokens.py]
estimated_loc: 120
plan_revision: 1
plan_commit: 8775d6c
state_revision: 0
claimed_by: null
claimed_at: null
blocked_reason: null
unblock_condition: null
next_step: null
last_verified_at: null
last_verified_commit: null
verification_evidence: null
created_at: 2026-11-06T00:00:00Z
updated_at: 2026-11-06T00:00:00Z
commit: null
sources:
  - id: token-mod
    resource: src/auth/tokens.py::TokenSigner
    title: JWT token signer module
tags: [feature, auth, tdd]
---
```

---

## 3. Tagging Best Practices

Tags enable multi-dimensional discovery, faceted search, and cross-cutting categorization across bundles without rigid folder hierarchies.

### 3.1 Tag Format Rules

1. **Lowercase and hyphenated**: Use `data-pipeline`, `user-auth`, `order-processing` (avoid camelCase or spaces).
2. **Concise and specific**: Prefer `orders` over `all-order-related-things`.
3. **List of strings**: Always declare `tags:` as a YAML array: `tags: [auth, security, api]`.

### 3.2 Standard Tag Categories

| Category | Purpose | Examples |
| --- | --- | --- |
| **Domain** | Business or technical domain | `sales`, `finance`, `billing`, `identity`, `inventory` |
| **Asset Kind** | Layer or architecture tier | `api`, `database`, `pipeline`, `service`, `ui` |
| **Operation** | Lifecycle or procedural role | `oncall`, `incident`, `triage`, `migration`, `deployment` |
| **Compliance** | Security, privacy, governance | `pii`, `audit`, `sox`, `gdpr`, `security` |
| **Work Kind** | Nature of the change (Flow specs/tasks) | `feature`, `bugfix`, `refactor`, `migration`, `performance`, `security`, `docs`, `test`, `chore` |

Flow specs and tasks carry exactly one **Work Kind** tag plus 1–4 domain tags,
so `state:` answers "what is current" and tags answer "what kind of work".

### 3.3 Anti-Patterns to Avoid

- **Tag Sprawl**: Do not add 20 tags to a single file; 2 to 5 targeted tags are optimal.
- **Workflow State in Tags**: Do not use tags like `[open]`, `[in-progress]`, or `[completed]` — state belongs in `state:`.
- **Document Lifecycle in Tags**: Do not use `[draft]` or `[deprecated]` in tags — use `status: draft` or `status: deprecated`.

---

## 4. State vs Status Invariant

| Field | Purpose | Permitted Values |
| --- | --- | --- |
| **`state`** | Flow task or plan workflow state | Spec: `planned`, `active`, `completed`<br>Task: `open`, `in_progress`, `closed`, `blocked`, `skipped` |
| **`status`** | OKF document lifecycle only | `draft`, `stable`, `deprecated` |

**NEVER** put workflow state values in `status:`.

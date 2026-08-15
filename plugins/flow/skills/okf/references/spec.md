# Open Knowledge Format (OKF) Specification Reference

> Version 0.2

OKF is an open, human- and agent-friendly format for representing knowledge: the metadata, context, and curated insight that surrounds data, code, and systems.

## Contents

- [Terminology](#1-terminology)
- [Bundle Structure & Reserved Files](#2-bundle-structure--reserved-files)
- [Concept Documents](#3-concept-documents)
- [Progressive Disclosure](#4-progressive-disclosure-indexmd)
- [History & Change Tracking](#5-history--change-tracking-logmd)
- [Attested Computations](#6-attested-computations)
- [Conformance Checklist](#7-conformance-checklist)

---

## 1. Terminology

- **Knowledge Bundle** (or **bundle**): A self-contained, hierarchical collection of knowledge documents. The unit of distribution.
- **Concept**: A single unit of knowledge within a bundle, represented as one markdown document.
- **Concept ID**: The path of the concept's file within the bundle, with the `.md` suffix removed.
- **Frontmatter**: A YAML metadata block delimited by `---` on its own line at the start and end.
- **Body**: Everything in the file after the frontmatter.
- **Link**: Standard markdown link to another concept (`[label](path/to/concept.md)`).
- **Source**: A material a concept derives from, recorded in `sources`.
- **Provenance**: The set of sources a concept derives from.
- **Credibility signal**: Objective facts (`author`, `usage_count`, `last_modified`) on a source.
- **Actor**: String identifying who/what acted (`<producer>/<version>`, `human:<id>`, `process:<id>`).
- **Trust tier**: Level inferred from verification (`unverified`, `machine-confirmed`, `human-reviewed`).
- **Attested Computation**: A concept (`type: Attested Computation`) with a sanctioned execution contract.

---

## 2. Bundle Structure & Reserved Files

A bundle is a directory tree of markdown files.

```text
path/to/bundle/
  index.md                      # Optional root/directory listing (carries okf_version at root)
  log.md                        # Optional chronological change history
  <concept>.md                  # Concept document at root
  <subdirectory>/               # Subdirectories organize concepts into groups
    index.md                    # Subdirectory index
    <concept>.md
```

### Reserved Filenames

| Filename | Purpose |
| --- | --- |
| `index.md` | Directory listing for progressive disclosure. Bundle root index carries `okf_version: "0.2"`. |
| `log.md` | Chronological update history (newest first, ISO dates). |

All other `.md` files in the tree are concept documents.

---

## 3. Concept Documents

Every concept document is a UTF-8 markdown file with:

1. **YAML Frontmatter block** delimited by `---`.
2. **Markdown Body** containing structured headings, tables, and prose.

### 3.1 Frontmatter Schema

```yaml
---
type: <Type name>                  # REQUIRED: non-empty string
title: <Optional display name>     # Optional string
description: <Optional summary>    # Optional single sentence
resource: <Optional canonical URI> # Optional URI string
tags: [<tag>, <tag>, ...]          # Optional list of strings
# ... trust, lifecycle, provenance, computation families
# ... other producer-defined key/value pairs
---
```

#### Field Rules

- **`type` (REQUIRED)**: Short string identifying the kind of concept (`BigQuery Table`, `API Endpoint`, `Metric`, `Playbook`, `Guide`, `Pattern`, `Spec`, `Task`, `Attested Computation`, etc.). Producers use descriptive names; consumers MUST tolerate unknown types.
- **`title`**: Human-readable display name. Defaults to filename stem if omitted.
- **`description`**: One-line summary used for search previews and indexes.
- **`resource`**: Canonical URI identifying the underlying asset (e.g. table URI, URL).
- **`tags`**: List of lowercase hyphenated strings for cross-cutting categorization.
- **`status`**: OKF document lifecycle ONLY (`draft`, `stable`, `deprecated`). Never store workflow state in `status:`.
- **`stale_after`**: ISO-8601 date or timestamp (`YYYY-MM-DD` or `YYYY-MM-DDTHH:MM:SSZ`).
- **`created_at` / `updated_at`**: ISO-8601 UTC timestamps (`YYYY-MM-DDTHH:MM:SSZ`).

### 3.2 Provenance, Trust & Lifecycle Families

#### Provenance (`sources`)

```yaml
sources:
  - id: ga4-schema
    resource: https://developers.google.com/analytics/bigquery/export-schema
    title: GA4 BigQuery Export schema
    author: team:ga4-docs
    usage_count: 5000
    last_modified: 2026-05-30
usage_window: { from: 2026-06-01, to: 2026-06-30 }
```

- `resource`: REQUIRED within each source entry.
- `id`, `title`, `author`, `usage_count`, `last_modified`: Optional signals.

#### Verification & Trust

```yaml
verified:
  by: human:cody
  at: 2026-08-11T12:00:00Z
  method: manual_inspection
```

Trust tiers are inferred from signals:

- **Unverified**: No `verified` block.
- **Machine-confirmed**: `verified.by` is an agent/tool.
- **Human-reviewed**: `verified.by` is `human:<id>`.

---

## 4. Progressive Disclosure (`index.md`)

Index files provide directory summaries so agents can explore bundles efficiently:

- Root `index.md` MUST declare `okf_version: "0.2"`.
- Lists child concepts with `title`, `description`, `type`, and `tags`.
- Summarizes subdirectories.

---

## 5. History & Change Tracking (`log.md`)

The bundle changelog records updates grouped by ISO-8601 dates (newest first):

```markdown
# Changelog

## 2026-08-15
- `human:cody`: Added orders table documentation with freshness SLA.
- `agent:flow-planner/1.0`: Created implementation plan for user-auth.
```

---

## 6. Attested Computations

Concepts with `type: Attested Computation` declare sanctioned execution methods:

```yaml
---
type: Attested Computation
title: Fiscal Revenue
computation:
  contract:
    inputs:
      year: { type: integer, required: true }
    outputs:
      revenue_usd: { type: numeric }
  executor:
    resource: references/scripts/revenue.py
  attester:
    resource: references/scripts/verify_receipt.py
---
```

---

## 7. Conformance Checklist

A bundle is fully conformant with OKF v0.2 when:

1. Root `index.md` exists and carries `okf_version: "0.2"`.
2. Every non-reserved `.md` file starts with a valid YAML frontmatter block.
3. Every frontmatter block contains a non-empty `type:` string.
4. Reserved filenames (`index.md`, `log.md`) follow their defined structure.
5. All markdown links resolve to valid destinations.
6. Workflow state is stored in `state:`, never in `status:`.

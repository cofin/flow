
# Flow Validate

Validate project integrity and fix issues. All checks are file checks — read the bundle files directly.

## Usage

`flow-validate`

## Phase 1: Structure Validation

### 1.1 Required Files

Check existence of:

- `.agents/bundles/index.md` (bundle root; frontmatter carries `okf_version`)
- `.agents/bundles/product/product.md`
- `.agents/bundles/product/tech-stack.md`
- `.agents/bundles/knowledge/workflow.md`
- `.agents/bundles/knowledge/patterns.md`

### 1.2 Flow Directories

For each directory under `.agents/bundles/specs/`:

- Verify `spec.md` exists
- Verify `tasks/` exists when the Implementation Plan has tasks

## Phase 2: Frontmatter Validation

### 2.1 Spec Frontmatter

For each `spec.md`: `type: Spec`, `flow_id` equals the directory name, `title`, `state` in `planned|active|completed`, valid `created_at`/`updated_at`.

### 2.2 Task Frontmatter

For each `tasks/<short_id>.md`:

- Required fields present: `type: Task`, `id`, `title`, `state`, `depends_on`, `created_at`, `updated_at`
- `id` matches `<flow_id>:<short_id>` and `<short_id>` matches the filename
- `state` in `open|in_progress|closed|blocked|skipped` (workflow state lives in `state:`, never `status:`)
- `depends_on` uses short ids that resolve to task files in the same flow
- `closed` tasks carry a `commit:` SHA that exists in git history

## Phase 3: Content Validation

### 3.1 Plan Tasks

For each spec.md:

- All checklist markers are valid: `[ ]`, `[~]`, `[x]`, `[!]`, `[-]`
- Each marker agrees with its task file's `state` (task file wins on conflict)
- Every checklist entry has a task file; no orphaned task files without a checklist entry
- File references exist

### 3.2 Patterns

For each pattern in `.agents/bundles/knowledge/patterns.md`:

- Referenced files exist
- Code examples still valid

### 3.3 Brownfield migration integrity

Before setup can report completion, read the consumer tree and produce
`.agents/migration-inventory.json`. Validation is read-only: it reports exact
source and postcondition paths and never applies or removes migration content.

The version 1 report contains a sorted, unique `items` list. Every legacy source
has one repository-relative `source`, `destination`, and one disposition:

- `migrate` for active specs/tasks and operational skills
- `synthesize` for knowledge and completed history
- `remove_after_verify` for superseded product/workflow/pattern authorities
- `preserve_local_policy` for tracker settings such as local-only/no-auto-push

The report also contains `semantic_mappings` entries for `priority`,
`dependencies`, `claims`, `blockers`, `notes`, `commit_evidence`, `history`, and
`local_only_policy`. Each entry records `status: mapped|warning` plus a non-empty
`detail`; a warning is visible but does not silently discard the source field.

Validation fails when active legacy work lacks a destination spec with full task
worksheets, duplicate legacy/bundle authorities coexist, operational skills
remain under `.agents/bundles/skills/`, archive trees violate contraction, stale
backend/path authority remains, or setup/log completion claims precede those
postconditions. Destination writes do not make a live legacy source disappear:
sources marked `remove_after_verify` remain an error until verified cleanup.

Legacy-path scanning is scope-aware. Live setup state, manifests, hook targets,
operational instructions, templates, and discovered consumer skill trees cannot
route agents to legacy authorities. Research, migration documentation,
diagnostics, and explicitly marked negative fixtures may quote the same paths as
evidence. The repository-default validator continues to exclude Flow's ignored
local `.agents/bundles/` working state.

## Phase 4: Git State

```bash
git status
```

- Check for uncommitted changes
- Verify no conflicts

## Phase 5: Verification Gate

```text
IRON LAW: NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE
```

Every validation check must produce evidence, not assertions. Follow the **Critical Thinking Iron Law** for every finding:

| Check | Evidence Required | Not Sufficient |
|-------|-------------------|----------------|
| Structure OK | File existence confirmed | Assumed from last run |
| Checklist synced | Markers compared against task-file `state` | "Should be synced" |
| Patterns valid | File refs verified on disk | Previous check |
| Git clean | `git status` output shown | Assumed clean |

Run each check fresh. Read output. Report actual results. **Deliver honest assessment** without hedging or meta-commentary.

Maintainers can verify the committed migration regression pair independently:

```text
uv run python tools/validate.py --scope migration-fixtures
```

This scope succeeds only when the Beekeeper-shaped negative fixture produces
every required migration diagnostic and the corrected fixture produces none.

## Phase 6: Report & Fix

```text
Validation Results

- Structure: OK (verified: {N} files checked)
- Checklist: Synced (verified: {N} tasks matched)
- Patterns: 2 stale references (verified: {N} refs checked)
- Git: Clean (verified: git status output)

Issues Found:
1. patterns.md:45 - File 'src/old.ts' not found
2. auth/spec.md - Task marker mismatch with tasks/1.3.md

Auto-fix available for 2 issues. Apply? [Y/n]
```

### Auto-Fix Options

- Remove stale pattern references
- Reconcile checklist markers with task file `state` (task file wins)
- Scaffold missing task files with default `Task` frontmatter

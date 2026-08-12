
# Flow Validate

Validate project integrity and fix issues. All checks are file checks — read the bundle files directly.

## Usage

`flow-validate`

## Phase 1: Structure Validation

### 1.1 Required Files

Check existence of:

- `.agents/bundles/index.md` (bundle root; frontmatter carries `okf_version`)
- `.agents/bundles/knowledge/product/product.md`
- `.agents/bundles/knowledge/product/tech-stack.md`
- `.agents/bundles/knowledge/workflow/workflow.md`
- `.agents/bundles/knowledge/patterns/patterns.md`

### 1.2 Flow Directories

For each directory under `.agents/bundles/specs/`:

- Verify `spec.md` exists
- Verify `tasks/` exists when the Implementation Plan has tasks

## Phase 2: Frontmatter Validation

### 2.1 Spec Frontmatter

For each `spec.md`: `type: Spec`, `flow_id` equals the directory name, `title`, `state` in `planned|active|completed|archived`, valid `created_at`/`updated_at`.

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

For each pattern in `.agents/bundles/knowledge/patterns/patterns.md`:

- Referenced files exist
- Code examples still valid

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

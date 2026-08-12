---
description: Initialize project with OKF knowledge bundles and first flow
---

# Flow Setup

Initialize a project for context-driven development backed by OKF v0.2 knowledge bundles under `.agents/bundles/`.

> **Harness boundary:** This command runs under OpenCode. Only OpenCode-owned files are created (e.g., `AGENTS.md`). Do not create `CLAUDE.md`, `.claude/*`, `.codex/*`, or `.cursor/*` — each harness's setup command owns its own configuration surface.

## Phase 0: Setup State Check

```bash
if [ -f ".agents/setup-state.json" ]; then
  cat .agents/setup-state.json
fi
```

**Treat setup as completed if** `setup_status` is `"complete"`.

**If setup is complete:**

> **Existing Flow setup detected. What would you like to do?**
>
> - **A) Align** (recommended) - Validate and update to latest best practices
> - **B) Re-setup** - Start fresh (preserves existing specs)
> - **C) Exit** - Keep current setup

**If A (Align) selected:** Jump to **Phase 0.1: Alignment Mode**

**If B (Re-setup) selected:** Continue to Phase 1 (will skip existing files unless changed)

**If C (Exit) selected:** Announce "Setup unchanged." and HALT

**If state exists with incomplete step:** Offer to resume from last successful step.

**If no state exists:** Continue to Phase 1.

---

## Phase 0.1: Alignment Mode

**PROTOCOL: Validate existing setup and update to latest best practices.**

### 0.1.1 Legacy Layout Migration

**Scan for legacy locations:**

- `specs/` or `.agents/specs/` (pre-bundle spec layout — migrate)
- Flat context files (migrate): `.agents/product.md`, `.agents/tech-stack.md`, `.agents/workflow.md`, `.agents/patterns.md`, `.agents/knowledge/`, `.agents/code-styleguides/`
- legacy task-tracker artifacts to migrate away from and delete: `.agents/beads.json`, `.beads/`, `metadata.json` files

**For each discovered legacy spec directory:**

```text
Found [N] specs in legacy locations:

Active (specs/):
  - user-auth (3/5 tasks complete)
  - api-refactor (complete, has learnings)

Options:
A) Migrate all to .agents/bundles/specs/ (recommended)
B) Migrate active only, skip archive
C) Review each spec individually
D) Skip migration
```

**Migration steps for each spec:**

1. Read legacy `spec.md` content (and legacy `metadata.json` if present, then delete it after extracting status).
2. Prepend OKF YAML frontmatter: `type: Spec`, `flow_id` (directory name), `title`, `state` (map legacy status values — in_progress→active, completed/done→completed, else planned), `created_at`, `updated_at`.
3. Write to `.agents/bundles/specs/{flow_id}/spec.md`; copy `learnings.md` alongside with `type: Learnings` frontmatter if it exists.
4. For task checklists without task files, scaffold `tasks/<short_id>.md` per the reconciler rules.

**Flat context files** migrate into the bundle: `product.md` and `tech-stack.md` → `knowledge/product/`, `workflow.md` → `knowledge/workflow/`, `patterns.md` and `code-styleguides/*` → `knowledge/patterns/`, legacy `.agents/knowledge` chapters → the bundle's `knowledge/`. Add `type:` frontmatter (`Guide` or `Pattern`) to each. Delete the legacy `.agents/beads.json` after confirming with the user — task state now lives in the bundle files.

### 0.1.2 Learnings Ingestion with Validation

**For each spec with learnings.md:**

1. Parse learnings entries
2. Cross-reference with current codebase:

```text
From user-auth/learnings.md:

✓ VALID: "Use Zod for form validation"
  → Referenced file src/lib/validators.ts exists

⚠ REVIEW: "Auth uses /api/v1/login endpoint"
  → File src/routes/api/v1/login.ts not found
  → Keep anyway? [Y/n]

✗ STALE: "Use deprecated-package for X"
  → Package not in package.json/pyproject.toml
  → Removing from migration
```

1. Present validated learnings for confirmation
2. Merge confirmed patterns into `.agents/bundles/knowledge/patterns/patterns.md`
3. Archive original learnings.md with migration note

### 0.1.3 Core Artifacts Check

Check for `knowledge/product/product.md` and `knowledge/product/tech-stack.md`.

- If missing, offer to create them from templates.
- If present but missing `<!-- truth: start -->` markers or `type:` frontmatter, offer to add them.

### 0.1.4 Workflow Revalidation & Sync

**PROTOCOL: Synchronize the workflow chapter with the latest template while preserving local "truth" markers.**

Read `.agents/bundles/knowledge/workflow/workflow.md` and check for content between `<!-- truth: start -->` and `<!-- truth: end -->`.

- **If markers exist:** Replace everything OUTSIDE the markers with the latest workflow template content. Keep the local truth section intact.
- **If markers are missing:** Propose wrapping the "Essential Commands" and "Guiding Principles" in truth markers before performing the sync.

Compare with the current repo's real command surfaces:

- `Makefile`, `justfile`, `Taskfile.yml`, `package.json`, `pyproject.toml`, `Cargo.toml`, `.pre-commit-config.yaml`, CI files.

Ask the user to revalidate:

> **Workflow settings may be stale. Revalidate now?**
>
> - **A) Refresh workflow template and keep current preferences** (recommended)
> - **B) Refresh template and update preferences**
> - **C) Keep current workflow.md**

### 0.1.5 Bundle Integrity Check

- Confirm `.agents/bundles/index.md` exists and declares `okf_version: "0.2"`; create it if absent.
- Confirm `.agents/bundles/log.md` exists; create it with today's dated entry if absent.
- Confirm every non-reserved bundle `.md` file carries a non-empty `type:` frontmatter key; offer to add missing ones.
- Confirm no task file stores workflow state in `status:` — move such values to `state:`.

### 0.1.6 Context Validation

**PROTOCOL: Ensure the OpenCode context file is present.**

This setup runs under OpenCode. Only OpenCode-owned files are touched. Claude Code/Codex/Cursor artifacts are out of scope and must not be created here.

- Check for `AGENTS.md` in the project root. If missing, offer to create it so OpenCode has project context and rules.

```text
AGENTS.md missing or outdated. Create it now?

A) Yes (recommended)
B) Skip
```

### 0.1.7 Alignment Summary

```text
Alignment Complete

✓ Bundle: okf_version 0.2, index + log present
✓ Specs migrated: {N} active, {M} archived
✓ Learnings merged: {X} patterns added to knowledge/patterns/patterns.md
✓ Workflow revalidated and synced
✓ Context files configured

No action needed / Issues found:
- {list any warnings}

Run `/flow-status` to see current state.
```

**After alignment, HALT (don't continue to full setup).**

---

## Phase 1: Project Detection

Detect if this is a brownfield (existing) or greenfield (new) project:

1. Check for existing code: `src/`, `lib/`, `app/`, `packages/`
2. Check for build files: `package.json`, `pyproject.toml`, `Cargo.toml`, `go.mod`
3. Check for an existing `.agents/` directory

**Output**: "Detected: [Brownfield|Greenfield] project"

The Flow root is always `.agents/` with bundles at `.agents/bundles/`. To relocate bundle directories, write `.agents/config.json` with `bundles_dir` and/or `knowledge_dir` — offer this only if the user asks for a nonstandard layout.

---

## Phase 2: Context Gathering (Interactive)

Ask the user these questions ONE AT A TIME:

### 2.1 Product Definition

> **What is this project?**
> Describe your product in 2-3 sentences. Include:
>
> - What problem it solves
> - Who it's for
> - Key differentiator

Write response to `.agents/bundles/knowledge/product/product.md` with `type: Guide` frontmatter. Wrap the most critical high-level project summary in `<!-- truth: start -->` and `<!-- truth: end -->` markers for efficient agent priming.

### 2.2 Product Guidelines

> **What are your brand/style guidelines?**
> Include:
>
> - Tone of voice
> - Visual style preferences
> - Any constraints or requirements

Write response to `.agents/bundles/knowledge/product/product-guidelines.md` with `type: Guide` frontmatter.

### 2.3 Tech Stack

> **What technologies are you using?**
> Include:
>
> - Languages (Python, TypeScript, Rust, etc.)
> - Frameworks (Litestar, React, etc.)
> - Database (PostgreSQL, SQLite, etc.)
> - Package manager (uv, npm, bun, cargo)

Detect from existing files if possible, then confirm with user.

Write response to `.agents/bundles/knowledge/product/tech-stack.md` with `type: Guide` frontmatter. Wrap the core technology list in `<!-- truth: start -->` and `<!-- truth: end -->` markers for efficient agent priming.

### 2.4 Workflow Preferences

> **What are your development preferences?**
>
> - Test coverage target? (default: 80%)
> - Commit message format? (default: conventional commits)
> - CI integration? (GitHub Actions, GitLab CI, etc.)
> - Canonical repo commands for setup, lint, test, typecheck, and full verification?
> - Local-only or shared ignore policy for Flow artifacts?

Before asking, inspect the repo's real command surfaces (`Makefile`, `justfile`, `Taskfile.yml`, `package.json`, `pyproject.toml`, `Cargo.toml`, `.pre-commit-config.yaml`, CI files) and propose those commands back to the user. Copy the workflow template to `.agents/bundles/knowledge/workflow/workflow.md` and customize it to preserve those canonical commands instead of leaving generic placeholders.

---

## Phase 3: Style & Convention Chapters

Based on detected languages, offer relevant style chapters:

1. List detected languages
2. Show available styleguides from the Flow templates (`templates/styleguides/`)
3. Ask user which to include
4. Copy selected into `.agents/bundles/knowledge/patterns/` as chapters with `type: Pattern` frontmatter (alongside `patterns.md`)

---

## Phase 4: Create the Bundle Skeleton

Create:

- `.agents/bundles/index.md` - Bundle root index with `okf_version: "0.2"` frontmatter and a directory listing
- `.agents/bundles/log.md` - Date-grouped change log (newest first, ISO dates) with a creation entry
- `.agents/bundles/knowledge/patterns/patterns.md` - Patterns template with `type: Pattern` frontmatter

```bash
mkdir -p .agents/bundles/specs
mkdir -p .agents/bundles/knowledge/product
mkdir -p .agents/bundles/knowledge/workflow
mkdir -p .agents/bundles/knowledge/patterns
```

---

## Phase 5: Git Configuration

**PROTOCOL: Ask whether the knowledge bundle is shared or private.**

### 5.1 Bundle Tracking Policy

> **Should your team share the `.agents/bundles/` knowledge bundle in git?**
>
> - **A) Shared** (recommended for teams) - Track `.agents/bundles/` so agents and teammates inherit the same context
> - **B) Local-only** - Append `.agents/` to `.git/info/exclude`

**If A selected**, keep scratch content private while tracking the bundle — append to `.git/info/exclude`:

```bash
printf '\n# Flow local scratch (not shared)\n.agents/*\n!.agents/bundles/\n!.agents/config.json\n' >> .git/info/exclude
```

**If B selected:**

1. Check if `.git/info/exclude` already has the entry:

    ```bash
    [ -f ".git/info/exclude" ] && grep -q ".agents" .git/info/exclude && echo "ALREADY_EXISTS" || echo "NEEDS_UPDATE"
    ```

2. **CRITICAL: APPEND only, never overwrite:**

    ```bash
    printf '\n# Flow context files (local-only)\n.agents/\n' >> .git/info/exclude
    ```

Use `.gitignore` instead of `.git/info/exclude` only when the user explicitly wants the policy shared with the whole team.

### 5.2 Respect Ignored Files During Commits

Check whether `.agents` paths are ignored before staging:

```bash
git check-ignore -q ".agents/bundles" && echo "bundles: IGNORED" || echo "bundles: TRACKED"
```

- If a path is ignored, leave it unstaged.
- Never use `git add -f` to force-add ignored Flow files.
- Commit only the non-ignored setup artifacts.

> **Note:** Harness-foreign artifacts are out of scope for OpenCode setup. Other harnesses own their own configuration surfaces.

---

## Phase 6: First Flow (Optional)

> **Would you like to create your first flow?**
> Describe what you want to build.

If yes, invoke `/flow-prd` with description.

---

## Phase 7: Save State

Save setup state to `.agents/setup-state.json`:

```json
{
  "setup_status": "complete",
  "last_successful_step": "complete",
  "project_type": "brownfield|greenfield",
  "workflow_revision": "flow-template-v2",
  "workflow_preferences": {
    "coverage_target": "80%",
    "commit_cadence": "task",
    "bundle_policy": "shared|local-only",
    "canonical_commands": {
      "setup": "<command>",
      "lint": "<command>",
      "test": "<command>",
      "typecheck": "<command>",
      "verify": "<command>"
    }
  },
  "timestamp": "ISO timestamp"
}
```

---

## Phase 8: OpenCode Context File

**PROTOCOL: Ensure `AGENTS.md` is present at the project root.**

1. If `AGENTS.md` already exists, skip — do not overwrite.
2. Otherwise, create a minimal `AGENTS.md` that points at `.agents/bundles/knowledge/product/product.md` and `.agents/bundles/knowledge/workflow/workflow.md` as the source of truth.
3. Announce: "Created `AGENTS.md` so OpenCode has project context."

> **Harness boundary:** Do not create `CLAUDE.md`, `.claude/*`, `.codex/*`, or `.cursor/*` artifacts from this file. Each harness's setup command owns its own configuration surface.

---

## Final Summary

```text
Flow Setup Complete

Bundle: .agents/bundles/ (OKF v0.2)

Created:
- index.md, log.md
- knowledge/product/product.md
- knowledge/product/product-guidelines.md
- knowledge/product/tech-stack.md
- knowledge/workflow/workflow.md
- knowledge/patterns/patterns.md (+ style chapters)
- specs/

Next Steps:
1. Run `/flow-prd "description"` to create your first flow
2. Run `/flow-implement {flow_id}` to start coding
```

---

## Critical Rules

1. **BUNDLE FIRST** - All context and task state lives in `.agents/bundles/` OKF files; no task database or CLI
2. **TYPED FRONTMATTER** - Every non-reserved bundle markdown file gets a non-empty `type:` key
3. **FIXED ROOT** - `.agents/` is the root; relocations go through `.agents/config.json` only
4. **ONE QUESTION AT A TIME** - Don't overwhelm the user
5. **DETECT FIRST** - Auto-detect tech stack before asking
6. **APPEND ONLY** - Never overwrite `.gitignore` or `.git/info/exclude`
7. **HARNESS ISOLATION** - Only write OpenCode-owned files; never write Claude Code, Codex, or Cursor artifacts
8. **SAVE STATE** - Enable resume if interrupted
9. **NO FORCE-ADD** - If a Flow file is ignored, leave it out of the commit
10. **REVALIDATE EXISTING INSTALLS** - Existing installs must be offered workflow refresh/update, not just syntax checks
11. **PREFER REPO-NATIVE COMMANDS** - Capture and reuse canonical commands like `make lint`, `make test`, `make check`, `just check`, `task test`, or equivalent wrappers

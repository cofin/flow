---
description: Initialize project with OKF knowledge bundles and first flow
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, AskUserQuestion, mcp__sequential-thinking__sequentialthinking
---

# Flow Setup

> Lifecycle skill: use `flow-setup` through the `flow` router.

Initialize a project for context-driven development backed by OKF v0.2 knowledge bundles under `.agents/bundles/`.

> **Harness boundary:** This command runs under Claude Code. Only Claude-owned files are created (e.g., `CLAUDE.md`). Do not write `.codex/*`, `.cursor/*`, or `.opencode/*` — each harness's setup command owns its own configuration surface.

## Phase 0: Environment Detection

**PROTOCOL: Before starting, check if the environment has already been detected via hooks.**

1. **Check Hook Context:** Look for Flow project context (`## Project Purpose`, `## Core Project Invariants`, `## Active Flows & Tasks`) in your `<hook_context>`. If present, the bundle already resolves — treat setup as at least partially complete.
2. **Manual Check (Fallback only):** Only if the hook context is missing or incomplete, perform the following:

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

- `specs/` or `.agents/specs/` (pre-bundle spec layout)
- Legacy flat context files (to migrate): `.agents/product.md`, `.agents/tech-stack.md`, `.agents/workflow.md`, `.agents/patterns.md`, `.agents/knowledge/`, `.agents/code-styleguides/`
- Legacy task-tracker artifacts: `.agents/beads.json`, `.beads/`, `metadata.json` files
- Legacy Flow git hook: `.git/hooks/pre-commit` containing Beads sync logic

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

1. Read legacy `spec.md` content (and `metadata.json` if present, then delete it after extracting status).
2. Prepend OKF YAML frontmatter: `type: Spec`, `flow_id` (directory name), `title`, `state` (map legacy status: in_progress→active, completed/done→completed, else planned), `created_at`, `updated_at`.
3. Write to `.agents/bundles/specs/{flow_id}/spec.md`; copy `learnings.md` alongside with `type: Learnings` frontmatter if it exists.
4. For task checklists without task files, scaffold `tasks/<short_id>.md` per the reconciler rules.

**Legacy flat context files** migrate into the bundle categories: `product.md`, `product-guidelines.md`, and `tech-stack.md` → `product/`; `workflow.md` → `knowledge/workflow.md`; `patterns.md` → `knowledge/patterns.md`; `code-styleguides/*` → `knowledge/<topic>-style.md` chapters; `.agents/knowledge/*` chapters → `knowledge/`; `.agents/bundles/research/*` → `research/`. Add `type:` frontmatter (`Guide`, `Pattern`, or `Research`) to each. This is a MOVE, not a copy — the flat originals are removed once migrated.

### 0.1.1b Remove Legacy Tracker Machinery

**PROTOCOL: The old tracker must leave no live machinery behind. Offer each removal explicitly.**

1. **Flow git hook**: if `.git/hooks/pre-commit` exists and mentions `bd`, Beads, or Flow sync, show its first lines and offer to delete it (it is dead weight at best, a broken commit gate at worst).
2. **Tracker data**: offer to delete `.beads/` and `.agents/beads.json` (task state now lives in the bundle files; confirm before deleting).
3. **CLI**: note that the legacy `bd` binary is no longer used by Flow and may be uninstalled.

### 0.1.1c Scrub Tracker Instructions from Context Files

Old Flow setups wrote tracker-era instructions into harness context files. Scan and offer to clean each hit:

- **`CLAUDE.md` / `AGENTS.md` / `GEMINI.md`** (project root): sections instructing `bd` usage, "Beads is the source of truth", `beads.json` sync policy, or legacy `.agents/specs/` paths → replace with the bundle equivalents (task files as source of truth, `/flow:sync` reconciliation) or remove.
- **`.claude/settings.local.json`**: `Bash(bd:*)` permission allowlist entries → remove (back up the file first, merge — never clobber).
- **`opencode.json` / `.cursor/rules/*.mdc`**: tracker-era instructions or paths → same treatment.

Show each proposed edit and apply only on approval.

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
2. Merge confirmed patterns into `.agents/bundles/knowledge/patterns.md`
3. Archive original learnings.md with migration note

### 0.1.3 Core Artifacts Check

Check for `product/product.md` and `product/tech-stack.md` in the bundle.

- If missing, offer to create them from templates.
- If present but missing `<!-- truth: start -->` markers or `type:` frontmatter, offer to add them.

### 0.1.4 Workflow Revalidation & Sync

**PROTOCOL: Synchronize the workflow chapter with the latest template while preserving local "truth" markers.**

Read `.agents/bundles/knowledge/workflow.md` and check for content between `<!-- truth: start -->` and `<!-- truth: end -->`.

- **If markers exist:** Replace everything OUTSIDE the markers with the latest `templates/agent/workflow.md` content. Keep the local truth section intact.
- **If markers are missing:** Propose wrapping the "Essential Commands" and "Guiding Principles" in truth markers before performing the sync.

Compare with the current repo's real command surfaces:

- `Makefile`, `justfile`, `Taskfile.yml`, `package.json`, `pyproject.toml`, `Cargo.toml`, `.pre-commit-config.yaml`, CI files.

Ask the user to revalidate:

> **Workflow settings may be stale. Revalidate now?**
>
> - **A) Refresh workflow template and keep current preferences** (recommended)
> - **B) Refresh template and update preferences**
> - **C) Keep current workflow.md**

### 0.1.4b Knowledge Resynthesis

**PROTOCOL: Migration is not done when files have moved — the knowledge must be RE-synthesized.**

1. Read every migrated chapter (`knowledge/*.md`, `product/*.md`) together with the merged learnings.
2. Rewrite each chapter as coherent current-state documentation: merge duplicated guidance (e.g. flat `patterns.md` overlapping old knowledge chapters), resolve contradictions in favor of what the codebase actually does, drop stale or low-value notes, and organize by topic.
3. Knowledge chapters must contain no dated entries, flow attributions, or completion notes — history lives in `log.md` only.
4. Present the restructured chapters for approval before writing.

### 0.1.4c Spec Review Against the Codebase

For each migrated spec that is `planned` or `active`:

1. Verify task `state` values against SOURCE CODE reality: do the files in `files:` exist, do the tests in `tests:` pass, is the described behavior implemented?
2. Propose corrections (e.g. a task marked `open` whose feature already ships → `closed` with the implementing commit SHA; a `closed` task whose files are gone → reopen or skip).
3. Reconcile the spec checklist after applying corrections.

### 0.1.5 Bundle Integrity Check

- Confirm `.agents/bundles/index.md` exists and declares `okf_version: "0.2"`; create it if absent.
- Confirm `.agents/bundles/log.md` exists; create it with today's dated entry if absent.
- Confirm every non-reserved bundle `.md` file carries a non-empty `type:` frontmatter key; offer to add missing ones.
- Confirm no spec or task file stores workflow state in `status:` — move such values to `state:`.

### 0.1.6 Context Validation

**PROTOCOL: Ensure the Claude Code context file is present.**

This setup runs under Claude Code. Only Claude-owned files are touched. Antigravity/Codex/Cursor/OpenCode artifacts are out of scope and must not be created here.

- Check for `CLAUDE.md` in the project root. If missing, offer to create it from the latest template to provide project context and rules.

```text
CLAUDE.md missing or outdated. Create it now?

A) Yes (recommended)
B) Skip
```

### 0.1.7 Alignment Summary

```text
Alignment Complete

✓ Bundle: okf_version 0.2, index + log present
✓ Legacy tracker machinery removed: git hook, .beads/, beads.json
✓ Context files scrubbed of tracker instructions
✓ Specs migrated: {N} active, {M} archived — task states reviewed against the codebase
✓ Knowledge resynthesized into coherent chapters
✓ Workflow revalidated and synced

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

## Phase 1.5: Environment & Harness Detection

**PROTOCOL: Detect the workspace environment and active harness to configure session hooks.**

1. **Detect Workspace Environment:**
   - Git repository: `git rev-parse --is-inside-work-tree` succeeds.
   - Non-git workspace (VFS monorepo, cloud workspace, plain directory): anything else. Bundle paths are unchanged; if the environment needs hook config in a nonstandard location, set `hooks_dir` in `.agents/config.json` and use it as the destination below.

2. **Detect Active Harness:** trust the session's own signals — the hook-provided context banner and harness env vars (`ANTIGRAVITY_PLUGIN_ROOT`, `CLAUDE_PLUGIN_ROOT`, `CODEX_PLUGIN_ROOT`) — rather than guessing from the filesystem.

3. **Configure Hooks (only the active harness's own surface):**
   - **Antigravity CLI**: no manual hook placement — install Flow through the CLI's extension/plugin installer and hooks ship with the plugin.
   - **Antigravity IDE**: copy `hooks/hooks-agy.json` to the workspace hook config `.agents/hooks.json` (or `~/.gemini/config/hooks.json` for a global install; honor `hooks_dir` from `.agents/config.json` when set). If the destination file already exists, prompt the user before overwriting.
   - **Claude Code / Codex / Cursor**: no manual hook placement — the harness loads `hooks/hooks-claude.json`, `hooks/hooks-codex.json`, or `hooks/hooks-cursor.json` from the installed plugin automatically. Do not copy hook manifests into the project.

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

Write response to `.agents/bundles/product/product.md` with `type: Guide` frontmatter. Wrap the most critical high-level project summary in `<!-- truth: start -->` and `<!-- truth: end -->` markers for efficient agent priming.

### 2.2 Product Guidelines

> **What are your brand/style guidelines?**
> Include:
>
> - Tone of voice
> - Visual style preferences
> - Any constraints or requirements

Write response to `.agents/bundles/product/product-guidelines.md` with `type: Guide` frontmatter.

### 2.3 Tech Stack

> **What technologies are you using?**
> Include:
>
> - Languages (Python, TypeScript, Rust, etc.)
> - Frameworks (Litestar, React, etc.)
> - Database (PostgreSQL, SQLite, etc.)
> - Package manager (uv, npm, bun, cargo)

Detect from existing files if possible, then confirm with user.

Write response to `.agents/bundles/product/tech-stack.md` with `type: Guide` frontmatter. Wrap the core technology list in `<!-- truth: start -->` and `<!-- truth: end -->` markers for efficient agent priming.

### 2.4 Workflow Preferences

> **What are your development preferences?**
>
> - Test coverage target? (default: 80%)
> - Commit message format? (default: conventional commits)
> - CI integration? (GitHub Actions, GitLab CI, etc.)
> - Canonical repo commands for setup, lint, test, typecheck, and full verification?
> - Local-only or shared ignore policy for Flow artifacts?
> - Enable branched workspaces (Workspace='branch') for execution tasks? (y/N) (default: N)

Before asking, inspect the repo's real command surfaces (`Makefile`, `justfile`, `Taskfile.yml`, `package.json`, `pyproject.toml`, `Cargo.toml`, `.pre-commit-config.yaml`, CI files) and propose those commands back to the user. Copy the workflow template from `templates/agent/workflow.md` to `.agents/bundles/knowledge/workflow.md` and customize it to preserve those canonical commands instead of leaving generic placeholders.

---

## Phase 3: Style & Convention Chapters

Based on detected languages, offer relevant style chapters:

1. List detected languages
2. Show available styleguides from `templates/styleguides/`
3. Ask user which to include
4. Copy selected into `.agents/bundles/knowledge/` as `<topic>-style.md` chapters with `type: Pattern` frontmatter (siblings of `patterns.md`)

---

## Phase 3.5: Blueprint Scaffolding (Optional)

**PROTOCOL: Offer to scaffold project structure based on available blueprints.**

1. **List Blueprints:** List available blueprints from `templates/blueprints/`.
2. **Ask User:**
    > **Would you like to scaffold your project structure using a blueprint?**
    > - **A) Python App** (uv, hatchling, ruff, mypy, pyright, pytest)
    > - **B) Maturin** (Rust + Python polyglot with native extensions)
    > - **C) Mojo Python** (Mojo + Python with hatch-mojo build hook)
    > - **D) Skip** (Keep existing structure)

3. **If A-D selected:**
    - Ask for `project_name` and `project_description` if not already known.
    - Copy template files from selected blueprint.
    - Perform variable substitution in `.template` files and rename them (remove `.template`).
    - **CRITICAL:** Respect `src/py` vs `src/` rules (use `src/py` only if `src/js`, `src/rs`, etc. exist).

---

## Phase 4: Create the Bundle Skeleton

Create:

- `.agents/bundles/index.md` - Bundle root index with `okf_version: "0.2"` frontmatter and a directory listing
- `.agents/bundles/log.md` - Date-grouped change log (newest first, ISO dates) with a creation entry
- `.agents/bundles/knowledge/patterns.md` - Patterns template with `type: Pattern` frontmatter

```bash
mkdir -p .agents/bundles/specs .agents/bundles/product .agents/bundles/knowledge .agents/bundles/research
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

> **Note:** Harness-foreign artifacts are out of scope for Claude Code setup. Other harnesses own their own configuration surfaces.

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

## Phase 7.1: Save Configuration

Save configuration to `.agents/config.json`:

```json
{
  "use_branched_workspaces": true|false
}
```

If `.agents/config.json` already exists, merge this key into it.

---

## Phase 8: Claude Code Context File

**PROTOCOL: Ensure `CLAUDE.md` is present at the project root.**

1. If `CLAUDE.md` already exists, skip — do not overwrite.
2. Otherwise, create `CLAUDE.md` from the Flow template (`templates/agent/CLAUDE.md` if shipped, or a minimal stub that points at `.agents/bundles/product/product.md` and `.agents/bundles/knowledge/workflow.md` as the source of truth).
3. Announce: "Created `CLAUDE.md` so Claude Code has project context."

> **Harness boundary:** Do not create `.codex/*`, `.cursor/*`, or `.opencode/*` artifacts from this file. Each harness's setup command owns its own configuration surface.

---

## Final Summary

```text
Flow Setup Complete

Bundle: .agents/bundles/ (OKF v0.2)

Created:
- index.md, log.md
- product/product.md
- product/product-guidelines.md
- product/tech-stack.md
- knowledge/workflow.md
- knowledge/patterns.md (+ style chapters)
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
7. **HARNESS ISOLATION** - Only write Claude-owned files; never write Antigravity, Codex, Cursor, or OpenCode artifacts
8. **SAVE STATE** - Enable resume if interrupted
9. **NO FORCE-ADD** - If a Flow file is ignored, leave it out of the commit
10. **REVALIDATE EXISTING INSTALLS** - Existing installs must be offered workflow refresh/update, not just syntax checks
11. **PREFER REPO-NATIVE COMMANDS** - Capture and reuse canonical commands like `make lint`, `make test`, `make check`, `just check`, `task test`, or equivalent wrappers

---
description: Initialize project with context files, Beads, and first flow
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, AskUserQuestion, mcp__sequential-thinking__sequentialthinking
---

# Flow Setup

Initialize a project for context-driven development with Beads integration.

> **Host boundary:** This command runs under Claude Code. Only Claude-owned files are created (e.g., `CLAUDE.md`). Do not write `.gemini/*`, `.geminiignore`, `.codex/*`, `.cursor/*`, or `.opencode/*` — each host's setup command owns its own configuration surface.

## Phase 0: Environment Detection

**PROTOCOL: Before starting, check if the environment has already been detected via hooks.**

1. **Check Hook Context:** Look for `## Flow Environment Context` in your `<hook_context>`.
    - If **Flow Root** is present, use that as the authoritative root directory.
    - If **Beads Backend** is present and NOT `Missing`, note the active backend.
2. **Manual Check (Fallback only):** Only if the hook context is missing or incomplete, perform the following:

Resolve the configured Flow root first:

```bash
if [ -f ".agents/setup-state.json" ]; then
  cat .agents/setup-state.json
elif [ -f "specs/setup-state.json" ]; then
  cat specs/setup-state.json
fi
```

**Treat setup as completed if either of these is true:**

- `setup_status` is `"complete"`
- legacy `last_successful_step` is `"complete"` or `"3.3_initial_prd_generated"`

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

### 0.1.1 Beads Validation

**SKIP if Beads Backend is already detected in hook context.**

```bash
if command -v bd >/dev/null 2>&1; then
  echo "BEADS_BD"
  bd --version
else
  echo "BEADS_MISSING"
fi
```

If outdated, suggest the official install: `curl -fsSL https://raw.githubusercontent.com/steveyegge/beads/main/scripts/install.sh | bash`

### 0.1.2 Legacy Specs Migration

**Scan for legacy spec locations:**

- `specs/active/`
- `specs/archive/`
- `.agents/specs/active/` (if different from current)
- `.agents/specs/archive/`

**For each discovered spec directory:**

```text
Found [N] specs in legacy locations:

Active (specs/active/):
  - user-auth (3/5 tasks complete)
  - api-refactor (complete, has learnings)

Archived (specs/archive/):
  - initial-mvp (archived, has learnings)

Options:
A) Migrate all to .agents/specs/ (recommended)
B) Migrate active only, skip archive
C) Review each spec individually
D) Skip migration
```

**Migration steps for each spec:**

1. Read `metadata.json` to understand status
2. Read `spec.md`
3. Read `learnings.md` if exists
4. Check if referenced files still exist in codebase
5. Copy to `.agents/specs/{flow_id}/`
6. Update `.agents/flows.md` registry
7. Create Beads epic if not exists:

    ```bash
    bd create "Flow: {flow_id}" -t epic -p 2 \
      --description="{flow_description}"
    bd update {epic_id} --notes "Migrated from legacy location. Created by Flow during setup"
    ```

### 0.1.3 Learnings Ingestion with Validation

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
2. Merge confirmed patterns into `.agents/patterns.md`
3. Archive original learnings.md with migration note

### 0.1.4 Core Artifacts Check

Check for existence of `product.md` and `tech-stack.md`.

- If missing, offer to create them from templates.
- If present but missing `<!-- truth: start -->` markers, offer to add them.

### 0.1.5 Workflow Revalidation & Sync

**PROTOCOL: Synchronize workflow.md with the latest template while preserving local "truth" markers.**

Read `<root_directory>/workflow.md` and check for content between `<!-- truth: start -->` and `<!-- truth: end -->`.

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

### 0.1.6 Knowledge Base Check

Check for missing `.agents/knowledge/` directory. If absent, create it and write `knowledge/index.md` from template.

### 0.1.7 Context Validation

**PROTOCOL: Ensure the Claude Code context file is present.**

This setup runs under Claude Code. Only Claude-owned files are touched — Gemini/Codex/Cursor/OpenCode artifacts (`.gemini/policies/*`, `.geminiignore`, etc.) are out of scope and must not be created here.

- Check for `CLAUDE.md` in the project root. If missing, offer to create it from the latest template to provide project context and rules.

```text
CLAUDE.md missing or outdated. Create it now?

A) Yes (recommended)
B) Skip
```

### 0.1.8 Configuration Validation

Check and update:

- `<root_directory>/beads.json` - Ensure valid configuration
- `<root_directory>/setup-state.json` - Update `workflow_revision` and status

### 0.1.9 Alignment Summary

```text
Alignment Complete

✓ Beads: v{version} (up to date)
✓ Hooks: Installed
✓ Specs migrated: {N} active, {M} archived
✓ Learnings merged: {X} patterns added to patterns.md
✓ Workflow revalidated and synced
✓ Policy/Context: Host-specific overrides and context files configured
✓ Configuration validated

No action needed / Issues found:
- {list any warnings}

Run `/flow-status` to see current state.
```

**After alignment, HALT (don't continue to full setup).**

## Phase 1: Beads Backend Check

**CRITICAL: Use official Beads, or run in no-Beads mode if persistence is not desired.**

**SKIP if Beads Backend is already detected in hook context.**

```bash
if command -v bd >/dev/null 2>&1; then
  echo "BEADS_BD"
else
  echo "BEADS_MISSING"
fi
```

If no backend is found, ask user:

> Choose a Flow task-memory backend:
>
> - **A) Official Beads** (recommended) - Run `curl -fsSL https://raw.githubusercontent.com/steveyegge/beads/main/scripts/install.sh | bash`
> - **B) No Beads** - Continue with markdown-only Flow state (reduced memory/resume)

If a backend is installed, verify version is current and remember the selected mode for Phase 5.

---

## Phase 1.5: Configure Root Directory

**PROTOCOL: Ask user where to store Flow specification files.**

> **Where would you like to store Flow specification files?**
>
> - **A) `.agents/`** (Recommended - hidden from project root)
> - **B) `specs/`** (Visible at project root)
> - **C) Custom path** (Type your own)

**Store Configuration:** Based on user's choice, set `root_directory` variable.

- Default to `.agents/` if A selected
- Use `specs/` if B selected
- Use custom path if C selected

**Create Directory:**

```bash
mkdir -p <root_directory>
```

**All subsequent file paths use `<root_directory>` instead of hardcoded `.agents/`.**

---

## Phase 2: Project Detection

Detect if this is a brownfield (existing) or greenfield (new) project:

1. Check for existing code: `src/`, `lib/`, `app/`, `packages/`
2. Check for build files: `package.json`, `pyproject.toml`, `Cargo.toml`, `go.mod`
3. Check for existing `<root_directory>` directory

**Output**: "Detected: [Brownfield|Greenfield] project"

---

## Phase 3: Context Gathering (Interactive)

Ask the user these questions ONE AT A TIME:

### 3.1 Product Definition

> **What is this project?**
> Describe your product in 2-3 sentences. Include:
>
> - What problem it solves
> - Who it's for
> - Key differentiator

Write response to `<root_directory>/product.md`. Wrap the most critical high-level project summary in `<!-- truth: start -->` and `<!-- truth: end -->` markers for efficient agent priming.

### 3.2 Product Guidelines

> **What are your brand/style guidelines?**
> Include:
>
> - Tone of voice
> - Visual style preferences
> - Any constraints or requirements

Write response to `<root_directory>/product-guidelines.md`

### 3.3 Tech Stack

> **What technologies are you using?**
> Include:
>
> - Languages (Python, TypeScript, Rust, etc.)
> - Frameworks (Litestar, React, etc.)
> - Database (PostgreSQL, SQLite, etc.)
> - Package manager (uv, npm, bun, cargo)

Detect from existing files if possible, then confirm with user.

Write response to `<root_directory>/tech-stack.md`. Wrap the core technology list in `<!-- truth: start -->` and `<!-- truth: end -->` markers for efficient agent priming.

### 3.4 Workflow Preferences

> **What are your development preferences?**
>
> - Test coverage target? (default: 80%)
> - Commit message format? (default: conventional commits)
> - CI integration? (GitHub Actions, GitLab CI, etc.)
> - Canonical repo commands for setup, lint, test, typecheck, and full verification?
> - Local-only or shared ignore policy for Flow artifacts?

Before asking, inspect the repo's real command surfaces (`Makefile`, `justfile`, `Taskfile.yml`, `package.json`, `pyproject.toml`, `Cargo.toml`, `.pre-commit-config.yaml`, CI files) and propose those commands back to the user. Copy workflow template from `templates/agent/workflow.md` and customize it to preserve those canonical commands instead of leaving generic placeholders.

---

## Phase 4: Code Styleguides

Based on detected languages, offer relevant styleguides:

1. List detected languages
2. Show available styleguides from `templates/styleguides/`
3. Ask user which to include
4. Copy selected to `<root_directory>/code-styleguides/`

---

## Phase 4.5: Blueprint Scaffolding (Optional)

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

## Phase 5: Beads Backend Initialization

**CRITICAL: Prefer local-only defaults with `.git/info/exclude`, not repo `.gitignore`.**

If official Beads was selected:

```bash
bd init --stealth --prefix <project_name_slug>
```

If no-Beads mode was selected:

- Skip CLI initialization.
- Create `<root_directory>/beads.json` with Flow's no-backend configuration so later commands know to use markdown-only state.

Or prompt user:

> **Beads mode:**
>
> - **Local-only** (recommended) - Add local ignores to `.git/info/exclude`
> - **Shared repo policy** - Update `.gitignore` for the whole team

Create `<root_directory>/beads.json` with configuration.

---

## Phase 6: Create Supporting Files

Create:

- `<root_directory>/index.md` - File resolution index
- `<root_directory>/flows.md` - Empty flow registry
- `<root_directory>/patterns.md` - Empty patterns template
- `<root_directory>/knowledge/index.md` - Knowledge base index (from template)

```bash
mkdir -p <root_directory>/knowledge
```

Copy `knowledge/index.md` from the Flow templates (`templates/agent/knowledge/index.md`).

---

## Phase 7: Git Configuration (Optional)

**PROTOCOL: Prefer `.git/info/exclude` for local-only defaults.**

### 7.1 Local Ignore Configuration

> **Would you like to keep Flow context local-only?**
>
> - **A) Yes** (recommended) - Append to `.git/info/exclude`
> - **B) Shared** - Update `.gitignore` for the repo

**If A selected:**

1. Check if `.git/info/exclude` exists and already has the entry:

    ```bash
    [ -f ".git/info/exclude" ] && grep -q "<root_directory>" .git/info/exclude && echo "ALREADY_EXISTS" || echo "NEEDS_UPDATE"
    ```

2. **CRITICAL: APPEND only, never overwrite:**

    ```bash
    printf '\n# Flow specification files (local-only)\n<root_directory>/\n.beads/\n' >> .git/info/exclude
    ```

**If B selected:**

1. Check if `.gitignore` exists and already has the entry:

    ```bash
    [ -f ".gitignore" ] && grep -q "<root_directory>" .gitignore && echo "ALREADY_EXISTS" || echo "NEEDS_UPDATE"
    ```

2. **CRITICAL: APPEND only, never overwrite:**

    ```bash
    printf '\n# Flow specification files\n<root_directory>/\n.beads/\n' >> .gitignore
    ```

### 7.2 Respect Ignored Files During Commits

Check whether `<root_directory>` or `.beads` are ignored before staging:

```bash
for path in "<root_directory>" ".beads"; do
  [ -e "$path" ] || continue
  git check-ignore -q "$path" && echo "$path: IGNORED" || echo "$path: TRACKED"
done
```

- If a path is ignored, leave it unstaged.
- Never use `git add -f` to force-add ignored Flow files.
- Commit only the non-ignored setup artifacts.

> **Note:** Host-foreign artifacts (`.geminiignore`, `.gemini/policies/*`) are out of scope for Claude Code setup. Gemini CLI users run Gemini's own `/flow:setup` to configure those.

---

## Phase 8: First Flow (Optional)

> **Would you like to create your first flow?**
> Describe what you want to build.

If yes, invoke `/flow-prd` with description.

---

## Phase 9: Save State

Save setup state to `<root_directory>/setup-state.json`:

```json
{
  "setup_status": "complete",
  "last_successful_step": "complete",
  "project_type": "brownfield|greenfield",
  "root_directory": "<root_directory>",
  "workflow_revision": "flow-template-v1",
  "shadcn_official_prompted": false,
  "mojo_official_prompted": false,
  "railway_official_prompted": false,
  "workflow_preferences": {
    "coverage_target": "80%",
    "commit_cadence": "task",
    "task_summary_mode": "git-notes|commit-body|host-native",
    "backend_mode": "bd|none",
    "ignore_policy": "local-only|shared",
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

## Phase 10: Claude Code Context File

**PROTOCOL: Ensure `CLAUDE.md` is present at the project root.**

1. If `CLAUDE.md` already exists, skip — do not overwrite.
2. Otherwise, create `CLAUDE.md` from the Flow template (`templates/agent/CLAUDE.md` if shipped, or a minimal stub that points at `<root_directory>/product.md` and `<root_directory>/workflow.md` as the source of truth).
3. Announce: "Created `CLAUDE.md` so Claude Code has project context."

> **Host boundary:** Do not create `.gemini/*`, `.codex/*`, `.cursor/*`, or `.opencode/*` artifacts from this file. Each host's setup command owns its own configuration surface.

---

## Final Summary

```text
Flow Setup Complete

Directory: <root_directory>

Created:
- product.md
- product-guidelines.md
- tech-stack.md
- workflow.md
- beads.json
- index.md
- flows.md
- patterns.md
- knowledge/index.md
- code-styleguides/

Next Steps:
1. Load the active backend state (`bd`) or continue in no-Beads mode
2. Run `/flow-prd "description"` to create your first flow
3. Run `/flow-implement {flow_id}` to start coding
```

---

## Phase 8: Install Git Hooks

**PROTOCOL: Install pre-commit hook to automate Beads sync.**

Copy the `pre-commit` hook to the `.git/hooks/` directory to ensure Bead states remain synchronized before any commit:

```bash
# Resolve the Flow install root for the current host. CLAUDE_PLUGIN_ROOT is
# exported by Claude Code when this command runs from the installed plugin.
FLOW_INSTALL_ROOT="${CLAUDE_PLUGIN_ROOT:-$HOME/.flow}"
if [ -f "$FLOW_INSTALL_ROOT/hooks/pre-commit" ]; then
  cp "$FLOW_INSTALL_ROOT/hooks/pre-commit" .git/hooks/pre-commit
  chmod +x .git/hooks/pre-commit
fi
```

---

## Critical Rules

1. **BEADS MODE FIRST** - Use `bd`, allow no-Beads when admin overhead should stay low
2. **CLI CHECK** - Ensure the chosen backend is installed and available
3. **ROOT DIRECTORY PROMPT** - Ask user where to store files
4. **LOCAL DEFAULT** - Configure Beads for local-only use
5. **ONE QUESTION AT A TIME** - Don't overwhelm the user
6. **DETECT FIRST** - Auto-detect tech stack before asking
7. **APPEND ONLY** - Never overwrite `.gitignore` or `.git/info/exclude`
8. **HOST ISOLATION** - Only write Claude-owned files; never write `.gemini/*`, `.geminiignore`, `.codex/*`, `.cursor/*`, or `.opencode/*`
9. **SAVE STATE** - Enable resume if interrupted
10. **NO FORCE-ADD** - If a Flow file is ignored, leave it out of the commit
11. **REVALIDATE EXISTING INSTALLS** - Existing installs must be offered workflow refresh/update, not just syntax checks
12. **PREFER REPO-NATIVE COMMANDS** - Capture and reuse canonical commands like `make lint`, `make test`, `make check`, `just check`, `task test`, or equivalent wrappers

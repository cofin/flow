---
description: Initialize project with context files, Beads, and first flow
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, AskUserQuestion, mcp__sequential-thinking__sequentialthinking
---

# Flow Setup

Initialize a project for context-driven development with Beads integration.

## Phase 0: Setup State Check

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

```bash
if command -v bd >/dev/null 2>&1 && command -v br >/dev/null 2>&1; then
  echo "BEADS_BOTH"
  bd --version
  br version
elif command -v bd >/dev/null 2>&1; then
  echo "BEADS_BD"
  bd --version
elif command -v br >/dev/null 2>&1; then
  echo "BEADS_BR"
  br version
else
  echo "BEADS_MISSING"
fi
```

If `BEADS_BOTH` is found, ask user:

> **Both official Beads (bd) and beads_rust (br) detected. Which would you like to use for Flow projects?**
>
> - **A) Official Beads (bd)** (recommended)
> - **B) beads_rust compatibility (br)**

If outdated, suggest the official install first: `curl -fsSL https://raw.githubusercontent.com/steveyegge/beads/main/scripts/install.sh | bash`
Compatibility fallback: `curl -fsSL https://raw.githubusercontent.com/Dicklesworthstone/beads_rust/main/install.sh | bash`

**Note:** `br` is non-invasive and never executes git commands. If you track `.beads/` in git and it is not ignored, run `git add .beads/` manually after `br sync --flush-only`.

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
    br create "Flow: {flow_id}" -t epic -p 2 \
      --description="{flow_description}"
    br update {epic_id} --notes "Migrated from legacy location. Created by Flow during setup"
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

### 0.1.4 Knowledge Base Check

Check for missing `.agents/knowledge/` directory. If absent, create it and write `knowledge/index.md` from template.

### 0.1.5 Configuration Validation

Check and update:

- `<root_directory>/beads.json` - Ensure valid configuration
- `<root_directory>/workflow.md` - Check for outdated workflow content, backend assumptions, and command syntax
- `<root_directory>/tech-stack.md` - Verify detected languages match codebase

### 0.1.6 Workflow Revalidation

Read `<root_directory>/workflow.md` and compare it with the latest template plus the current repo's actual command surfaces:

- `Makefile`
- `justfile`
- `Taskfile.yml`
- `package.json`
- `pyproject.toml`
- `tox.ini`
- `noxfile.py`
- `Cargo.toml`
- `.pre-commit-config.yaml`
- CI files such as `.github/workflows/*`

Ask the user to revalidate workflow behavior instead of blindly overwriting the file:

> **Workflow settings may be stale. Revalidate now?**
>
> - **A) Refresh workflow template and keep current preferences** (recommended)
> - **B) Refresh template and update preferences**
> - **C) Keep current workflow.md**

If A or B is selected, confirm at minimum:

- coverage target
- commit cadence (per-task vs per-phase)
- task-summary mechanism (git notes vs commit body or other host-native notes)
- backend mode (`bd`, `br`, or no-Beads)
- local-only vs shared ignore policy
- canonical repo commands for setup, lint, test, typecheck, and full verification

Prefer existing repo-native aggregate commands such as `make lint`, `make test`, `make check`, `just check`, `task test`, package-script wrappers, and pre-commit entrypoints. Merge them into `<root_directory>/workflow.md` instead of leaving placeholders.

### 0.1.7 Alignment Summary

```text
Alignment Complete

✓ Beads: v{version} (up to date)
✓ Hooks: Installed
✓ Specs migrated: {N} active, {M} archived
✓ Learnings merged: {X} patterns added to patterns.md
✓ Workflow revalidated
✓ Configuration validated

No action needed / Issues found:
- {list any warnings}

Run `/flow-status` to see current state.
```

**After alignment, HALT (don't continue to full setup).**

---

## Phase 1: Beads Backend Check

**CRITICAL: Prefer official Beads, but Flow can also run with `br` compatibility mode or no-Beads mode.**

```bash
if command -v bd >/dev/null 2>&1 && command -v br >/dev/null 2>&1; then
  echo "BEADS_BOTH"
elif command -v bd >/dev/null 2>&1; then
  echo "BEADS_BD"
elif command -v br >/dev/null 2>&1; then
  echo "BEADS_BR"
else
  echo "BEADS_MISSING"
fi
```

If `BEADS_BOTH` is found, ask user:

> **Both official Beads (bd) and beads_rust (br) detected. Which would you like to use?**
>
> - **A) Official Beads (bd)** (recommended)
> - **B) beads_rust compatibility (br)**

If no backend is found, ask user:

> Choose a Flow task-memory backend:
>
> - **A) Official Beads** (recommended) - Run `curl -fsSL https://raw.githubusercontent.com/steveyegge/beads/main/scripts/install.sh | bash`
> - **B) beads_rust compatibility** - Run `curl -fsSL https://raw.githubusercontent.com/Dicklesworthstone/beads_rust/main/install.sh | bash`
> - **C) No Beads** - Continue with markdown-only Flow state (reduced memory/resume)

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

If `br` compatibility mode was selected:

```bash
br init --prefix <project_name_slug>
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
    printf '\n# Flow specification files (local-only)\n<root_directory>/\n.beads/\n.geminiignore\n' >> .git/info/exclude
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

### 7.2 Geminiignore Configuration (for Gemini CLI users)

1. Check if `.geminiignore` exists:

    ```bash
    [ -f ".geminiignore" ] && echo "EXISTS" || echo "NEW"
    ```

2. **If EXISTS:**
    - Read current content
    - Check if the Flow allowlist block is already present (for example `!<root_directory>/` or `!AGENTS.md`)
    - **If NOT present, APPEND (don't overwrite):**

        ```bash
        printf '\n# Allow Gemini to access Flow and agent context\n!<root_directory>/\n!<root_directory>/**\n!.agents/\n!.agents/**\n!AGENTS.md\n!GEMINI.md\n!CLAUDE.md\n' >> .geminiignore
        ```

3. **If NEW:**
    - If `.gitignore` exists, seed `.geminiignore` from it first so Gemini inherits the repo ignore baseline.
    - Then append the Flow allowlist block so Flow specs and agent instructions remain readable.

        ```bash
        if [ -f ".gitignore" ]; then
          cp .gitignore .geminiignore
        else
          : > .geminiignore
        fi
        printf '\n# Allow Gemini to access Flow and agent context\n!<root_directory>/\n!<root_directory>/**\n!.agents/\n!.agents/**\n!AGENTS.md\n!GEMINI.md\n!CLAUDE.md\n' >> .geminiignore
        ```

4. **If `.geminiignore` should stay local-only, prefer `.git/info/exclude`:**

    ```bash
    [ -f ".git/info/exclude" ] && ! grep -q ".geminiignore" .git/info/exclude && printf '\n.geminiignore\n' >> .git/info/exclude
    ```

5. **Respect ignored files during commits:**
    - Check whether `<root_directory>`, `.geminiignore`, or `.beads` are ignored before staging:

    ```bash
    for path in "<root_directory>" ".geminiignore" ".beads"; do
      [ -e "$path" ] || continue
      git check-ignore -q "$path" && echo "$path: IGNORED" || echo "$path: TRACKED"
    done
    ```

    - If a path is ignored, leave it unstaged.
    - Never use `git add -f` to force-add ignored Flow files.
    - Commit only the non-ignored setup artifacts.

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
    "backend_mode": "bd|br|none",
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

## Phase 10: Gemini CLI Configuration

**PROTOCOL: Generate project-specific policy for Plan Mode.**

Create `.gemini/policies/flow-overrides.toml` to allow common development tools in **Plan Mode**, resolving common permission issues:

```toml
[[rule]]
toolName = "run_shell_command"
commandRegex = "^(bd|uv|pip|ruff|make|git|npx|bunx|pnpm|railway|bash|python3|cat|ls) .*"
decision = "allow"
priority = 100
modes = ["plan"]
```

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
1. Load the active backend state (`bd` or `br`) or continue in no-Beads mode
2. Run `/flow-prd "description"` to create your first flow
3. Run `/flow-implement {flow_id}` to start coding
```

---

## Phase 8: Install Git Hooks

**PROTOCOL: Install pre-commit hook to automate Beads sync.**

Copy the `pre-commit` hook to the `.git/hooks/` directory to ensure Bead states remain synchronized before any commit:

```bash
if [ -f ~/.flow/hooks/pre-commit ]; then
  cp ~/.flow/hooks/pre-commit .git/hooks/pre-commit
  chmod +x .git/hooks/pre-commit
elif [ -f ~/.gemini/extensions/flow/tools/scripts/hooks/pre-commit ]; then
  cp ~/.gemini/extensions/flow/tools/scripts/hooks/pre-commit .git/hooks/pre-commit
  chmod +x .git/hooks/pre-commit
fi
```

---

## Critical Rules

1. **BEADS MODE FIRST** - Prefer `bd`, allow `br`, allow no-Beads when admin overhead should stay low
2. **CLI CHECK** - Ensure the chosen backend is installed and available
3. **ROOT DIRECTORY PROMPT** - Ask user where to store files
4. **LOCAL DEFAULT** - Configure Beads for local-only use
5. **ONE QUESTION AT A TIME** - Don't overwhelm the user
6. **DETECT FIRST** - Auto-detect tech stack before asking
7. **APPEND ONLY** - Never overwrite .gitignore or .geminiignore
8. **SAVE STATE** - Enable resume if interrupted
9. **NO FORCE-ADD** - If a Flow file is ignored, leave it out of the commit
10. **REVALIDATE EXISTING INSTALLS** - Existing installs must be offered workflow refresh/update, not just syntax checks
11. **PREFER REPO-NATIVE COMMANDS** - Capture and reuse canonical commands like `make lint`, `make test`, `make check`, `just check`, `task test`, or equivalent wrappers

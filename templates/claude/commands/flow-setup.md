---
description: Initialize Flow project with context files, Beads integration, and first flow
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, AskUserQuestion, mcp__sequential-thinking__sequentialthinking
---

# Flow Setup

Initialize a project for context-driven development with Beads integration.

## Phase 0: Setup State Check

Check for existing setup state:

```bash
cat .agent/setup-state.json 2>/dev/null
```

**If state exists AND `last_successful_step` is "complete":**

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
command -v bd &> /dev/null && echo "BEADS_OK" || echo "BEADS_MISSING"
bd version
```

If outdated, suggest: `npm update -g beads-cli`

Check hooks:

```bash
bd setup claude --check 2>/dev/null && echo "HOOKS_OK" || echo "HOOKS_MISSING"
```

If HOOKS_MISSING, offer to install: `bd setup claude`

### 0.1.2 Legacy Specs Migration

**Scan for legacy spec locations:**

- `specs/active/`
- `specs/archive/`
- `.agent/specs/active/` (if different from current)
- `.agent/specs/archive/`

**For each discovered spec directory:**

```
Found [N] specs in legacy locations:

Active (specs/active/):
  - user-auth_20260110 (3/5 tasks complete)
  - api-refactor_20260115 (complete, has learnings)

Archived (specs/archive/):
  - initial-mvp_20260101 (archived, has learnings)

Options:
A) Migrate all to .agent/specs/ (recommended)
B) Migrate active only, skip archive
C) Review each spec individually
D) Skip migration
```

**Migration steps for each spec:**

1. Read `metadata.json` to understand status
2. Read `spec.md` and `plan.md`
3. Read `learnings.md` if exists
4. Check if referenced files still exist in codebase
5. Copy to `.agent/specs/{flow_id}/`
6. Update `.agent/flows.md` registry
7. Create Beads epic if not exists:

    ```bash
    bd create "Flow: {flow_id}" -t epic -p 2 \
      --description="{flow_description}" \
      --notes="Migrated from legacy location. Created by Flow during setup"
    ```

### 0.1.3 Learnings Ingestion with Validation

**For each spec with learnings.md:**

1. Parse learnings entries
2. Cross-reference with current codebase:

```
From user-auth_20260110/learnings.md:

✓ VALID: "Use Zod for form validation"
  → Referenced file src/lib/validators.ts exists

⚠ REVIEW: "Auth uses /api/v1/login endpoint"
  → File src/routes/api/v1/login.ts not found
  → Keep anyway? [Y/n]

✗ STALE: "Use deprecated-package for X"
  → Package not in package.json/pyproject.toml
  → Removing from migration
```

3. Present validated learnings for confirmation
4. Merge confirmed patterns into `.agent/patterns.md`
5. Archive original learnings.md with migration note

### 0.1.4 Configuration Validation

Check and update:

- `.agent/beads.json` - Ensure valid configuration
- `.agent/workflow.md` - Check for outdated bd command syntax
- `.agent/tech-stack.md` - Verify detected languages match codebase

### 0.1.5 Alignment Summary

```
Alignment Complete

✓ Beads: v{version} (up to date)
✓ Hooks: Installed
✓ Specs migrated: {N} active, {M} archived
✓ Learnings merged: {X} patterns added to patterns.md
✓ Configuration validated

No action needed / Issues found:
- {list any warnings}

Run `/flow-status` to see current state.
```

**After alignment, HALT (don't continue to full setup).**

---

## Phase 1: Beads Installation Check

**CRITICAL: Beads is required.**

```bash
command -v bd &> /dev/null && echo "BEADS_OK" || echo "BEADS_MISSING"
```

If `bd` not found, ask user:

> Beads CLI is required for Flow. Install it now?
>
> - **A) Yes** (recommended) - Run `npm install -g beads-cli`
> - **B) No** - Cannot proceed without Beads

If installed, check hooks:

```bash
bd setup claude --check 2>/dev/null && echo "HOOKS_OK" || echo "HOOKS_MISSING"
```

If HOOKS_MISSING:

> Beads hooks not installed for Claude Code. Install now?
>
> - **A) Yes** (recommended) - Run `bd setup claude`
> - **B) No** - Skip (Beads sync may not work properly)

---

## Phase 1.5: Configure Root Directory

**PROTOCOL: Ask user where to store Flow specification files.**

> **Where would you like to store Flow specification files?**
>
> - **A) `.agent/`** (Recommended - hidden from project root)
> - **B) `specs/`** (Visible at project root)
> - **C) Custom path** (Type your own)

**Store Configuration:** Based on user's choice, set `root_directory` variable.

- Default to `.agent/` if A selected
- Use `specs/` if B selected
- Use custom path if C selected

**Create Directory:**

```bash
mkdir -p <root_directory>
```

**All subsequent file paths use `<root_directory>` instead of hardcoded `.agent/`.**

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

Write response to `<root_directory>/product.md`

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

Write response to `<root_directory>/tech-stack.md`

### 3.4 Workflow Preferences

> **What are your development preferences?**
>
> - Test coverage target? (default: 80%)
> - Commit message format? (default: conventional commits)
> - CI integration? (GitHub Actions, GitLab CI, etc.)

Copy workflow template from `templates/agent/workflow.md` and customize.

---

## Phase 4: Code Styleguides

Based on detected languages, offer relevant styleguides:

1. List detected languages
2. Show available styleguides from `templates/styleguides/`
3. Ask user which to include
4. Copy selected to `<root_directory>/code-styleguides/`

---

## Phase 5: Beads Initialization

**CRITICAL: Initialize in stealth mode by default.**

```bash
bd init --stealth
```

Or prompt user:

> **Beads mode:**
>
> - **Stealth** (recommended) - Local-only, personal use
> - **Normal** - Committed to repo, team-shared

Create `<root_directory>/beads.json` with configuration.

---

## Phase 6: Create Supporting Files

Create:

- `<root_directory>/index.md` - File resolution index
- `<root_directory>/flows.md` - Empty flow registry
- `<root_directory>/patterns.md` - Empty patterns template

---

## Phase 7: Git Configuration (Optional)

**PROTOCOL: Configure gitignore and geminiignore with APPEND logic.**

### 7.1 Gitignore Configuration

> **Would you like to add `<root_directory>` to `.gitignore` to keep context local-only?**
>
> - **A) Yes** (recommended for personal use)
> - **B) No** (commit to repo for team sharing)

**If A selected:**

1. Check if `.gitignore` exists and already has the entry:

    ```bash
    [ -f ".gitignore" ] && grep -q "<root_directory>" .gitignore && echo "ALREADY_EXISTS" || echo "NEEDS_UPDATE"
    ```

2. **CRITICAL: APPEND only, never overwrite:**

    ```bash
    echo "" >> .gitignore
    echo "# Flow specification files (local-only)" >> .gitignore
    echo "<root_directory>/" >> .gitignore
    ```

### 7.2 Geminiignore Configuration (for Gemini CLI users)

1. Check if `.geminiignore` exists:

    ```bash
    [ -f ".geminiignore" ] && echo "EXISTS" || echo "NEW"
    ```

2. **If EXISTS:**
    - Read current content
    - Check if `!<root_directory>/` already present
    - **If NOT present, APPEND (don't overwrite):**

        ```bash
        echo "" >> .geminiignore
        echo "# Allow Gemini to access Flow specification files" >> .geminiignore
        echo "!<root_directory>/" >> .geminiignore
        ```

3. **If NEW:**
    - Create with content:

        ```bash
        echo "# Allow Gemini to access Flow specification files" > .geminiignore
        echo "!<root_directory>/" >> .geminiignore
        ```

4. **Add `.geminiignore` to `.gitignore`** (if gitignore exists and user wants):

    ```bash
    [ -f ".gitignore" ] && ! grep -q ".geminiignore" .gitignore && echo ".geminiignore" >> .gitignore
    ```

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
  "last_successful_step": "complete",
  "project_type": "brownfield|greenfield",
  "beads_mode": "stealth|normal",
  "root_directory": "<root_directory>",
  "timestamp": "ISO timestamp"
}
```

---

## Final Summary

```
Flow Setup Complete

Directory: <root_directory>
Beads Mode: [stealth|normal]

Created:
- product.md
- product-guidelines.md
- tech-stack.md
- workflow.md
- beads.json
- index.md
- flows.md
- patterns.md
- code-styleguides/

Next Steps:
1. Run `bd prime` to load Beads context
2. Run `/flow-prd "description"` to create your first flow
3. Run `/flow-implement {flow_id}` to start coding
```

---

## Critical Rules

1. **BEADS REQUIRED** - Cannot proceed without Beads CLI
2. **HOOKS CHECK** - Ensure `bd setup claude` has been run
3. **ROOT DIRECTORY PROMPT** - Ask user where to store files
4. **STEALTH DEFAULT** - Initialize Beads in stealth mode
5. **ONE QUESTION AT A TIME** - Don't overwhelm the user
6. **DETECT FIRST** - Auto-detect tech stack before asking
7. **APPEND ONLY** - Never overwrite .gitignore or .geminiignore
8. **SAVE STATE** - Enable resume if interrupted

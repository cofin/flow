---
description: Initialize Flow project with context files, Beads integration, and first track
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, AskUserQuestion, mcp__sequential-thinking__sequentialthinking
---

# Flow Setup

Initialize a project for context-driven development with Beads integration.

## Phase 0: Resume Check

Check for existing setup state:

```bash
cat .agent/setup-state.json 2>/dev/null
```

If state exists, offer to resume from last successful step.

---

## Phase 1: Beads Installation Check

**CRITICAL: Beads is required.**

```bash
if ! command -v bd &> /dev/null; then
    echo "Beads CLI not found."
fi
```

If `bd` not found, ask user:

> Beads CLI is required for Flow. Install it now?
> - **Yes** (recommended) - Run `npm install -g beads-cli`
> - **No** - Cannot proceed without Beads

---

## Phase 2: Project Detection

Detect if this is a brownfield (existing) or greenfield (new) project:

1. Check for existing code: `src/`, `lib/`, `app/`, `packages/`
2. Check for build files: `package.json`, `pyproject.toml`, `Cargo.toml`, `go.mod`
3. Check for existing `.agent/` directory

**Output**: "Detected: [Brownfield|Greenfield] project"

---

## Phase 3: Context Gathering (Interactive)

Ask the user these questions ONE AT A TIME:

### 3.1 Product Definition

> **What is this project?**
> Describe your product in 2-3 sentences. Include:
> - What problem it solves
> - Who it's for
> - Key differentiator

Write response to `.agent/product.md`

### 3.2 Product Guidelines

> **What are your brand/style guidelines?**
> Include:
> - Tone of voice
> - Visual style preferences
> - Any constraints or requirements

Write response to `.agent/product-guidelines.md`

### 3.3 Tech Stack

> **What technologies are you using?**
> Include:
> - Languages (Python, TypeScript, Rust, etc.)
> - Frameworks (Litestar, React, etc.)
> - Database (PostgreSQL, SQLite, etc.)
> - Package manager (uv, npm, bun, cargo)

Detect from existing files if possible, then confirm with user.

Write response to `.agent/tech-stack.md`

### 3.4 Workflow Preferences

> **What are your development preferences?**
> - Test coverage target? (default: 80%)
> - Commit message format? (default: conventional commits)
> - CI integration? (GitHub Actions, GitLab CI, etc.)

Copy workflow template from `templates/workflow.md` and customize.

---

## Phase 4: Code Styleguides

Based on detected languages, offer relevant styleguides:

1. List detected languages
2. Show available styleguides from `templates/code_styleguides/`
3. Ask user which to include
4. Copy selected to `.agent/code-styleguides/`

---

## Phase 5: Beads Initialization

**CRITICAL: Initialize in stealth mode by default.**

```bash
bd init --stealth
```

Or prompt user:

> **Beads mode:**
> - **Stealth** (recommended) - Local-only, personal use
> - **Normal** - Committed to repo, team-shared

Create `.agent/beads.json` with configuration.

---

## Phase 6: Create Supporting Files

Create:
- `.agent/index.md` - File resolution index
- `.agent/prds.md` - Empty track registry
- `.agent/patterns.md` - Empty patterns template

---

## Phase 7: First Track (Optional)

> **Would you like to create your first track?**
> Describe what you want to build.

If yes, invoke `/flow-newtrack` with description.

---

## Phase 8: Save State

Save setup state to `.agent/setup-state.json`:

```json
{
  "last_successful_step": "complete",
  "project_type": "brownfield|greenfield",
  "beads_mode": "stealth|normal",
  "timestamp": "ISO timestamp"
}
```

---

## Final Summary

```
Flow Setup Complete

Directory: .agent/
Beads Mode: [stealth|normal]

Created:
- product.md
- product-guidelines.md
- tech-stack.md
- workflow.md
- beads.json
- index.md
- prds.md
- patterns.md
- code-styleguides/

Next Steps:
1. Run `bd prime` to load Beads context
2. Run `/flow-newtrack "description"` to create your first track
3. Run `/flow-implement {track_id}` to start coding
```

---

## Critical Rules

1. **BEADS REQUIRED** - Cannot proceed without Beads CLI
2. **STEALTH DEFAULT** - Initialize Beads in stealth mode
3. **ONE QUESTION AT A TIME** - Don't overwhelm the user
4. **DETECT FIRST** - Auto-detect tech stack before asking
5. **SAVE STATE** - Enable resume if interrupted

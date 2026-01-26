# Flow Setup

Initialize a project for context-driven development with Beads integration.

## Phase 0: Check Existing Setup

```bash
cat .agent/setup-state.json 2>/dev/null
```

**If `last_successful_step` is "complete":**

Offer options:

- **A) Align** - Validate and update to latest best practices
- **B) Re-setup** - Start fresh (preserves existing specs)
- **C) Exit** - Keep current setup

## Phase 1: Beads Installation

```bash
command -v bd &> /dev/null && echo "BEADS_OK" || echo "BEADS_MISSING"
```

If missing, install: `npm install -g beads-cli`

## Phase 2: Project Detection

Detect brownfield (existing) or greenfield (new) project by checking for:

- Existing code: `src/`, `lib/`, `app/`, `packages/`
- Build files: `package.json`, `pyproject.toml`, `Cargo.toml`, `go.mod`

## Phase 3: Context Gathering

Ask ONE question at a time:

### 3.1 Product Definition
>
> What is this project? (problem, users, differentiator)

Write to `.agent/product.md`

### 3.2 Tech Stack
>
> What technologies are you using?

Detect from existing files, confirm with user. Write to `.agent/tech-stack.md`

### 3.3 Workflow Preferences
>
> Development preferences? (test coverage, commit format, CI)

Write to `.agent/workflow.md`

## Phase 4: Beads Initialization

```bash
bd init --stealth
```

Create `.agent/beads.json` configuration.

## Phase 5: Create Supporting Files

Create:

- `.agent/index.md` - File resolution index
- `.agent/flows.md` - Empty flow registry
- `.agent/patterns.md` - Empty patterns template

## Phase 5.5: Git Configuration

> Add `.agent/` to `.gitignore`? (keep context local)

If yes, append to `.gitignore`.

## Phase 6: Save State

Save to `.agent/setup-state.json`:

```json
{
  "last_successful_step": "complete",
  "project_type": "brownfield|greenfield",
  "beads_mode": "stealth",
  "timestamp": "ISO timestamp"
}
```

## Final Summary

```
Flow Setup Complete

Directory: .agent/
Beads Mode: stealth

Next Steps:
1. Run `bd prime` to load Beads context
2. Run `/flow:prd "description"` to create your first flow
3. Run `/flow:implement {flow_id}` to start coding
```

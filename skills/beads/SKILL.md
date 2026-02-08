---
name: beads
description: "Beads CLI integration for persistent task memory across sessions. Auto-activates when .beads/ directory exists. Provides dependency-aware task graphs, cross-session notes, and context compaction survival."
---

# Beads - Persistent Task Memory

## Auto-Activation

This skill activates when:

- `.beads/` directory exists
- User mentions "beads", "bd", "tasks", or "session"
- Beads commands are invoked

## Installation

```bash
npm install -g @beads/bd
```

## Initialization

Always initialize in **stealth mode** by default:

```bash
bd init --stealth
```

**Modes:**

- `stealth` - Local-only, .beads/ gitignored (personal use)
- `normal` - Committed to repo (team-shared)

## CLI Integration (Hooks)

Beads provides built-in hooks for each CLI:

```bash
bd setup claude   # SessionStart + PreCompact hooks
bd setup gemini   # SessionStart + PreCompress hooks
bd setup codex    # AGENTS.md section
bd setup cursor   # Cursor IDE rules
bd setup aider    # Aider config
```

Check installation: `bd setup <cli> --check`
Remove: `bd setup <cli> --remove`

## Session Protocol

### Session Start

```bash
bd prime        # Load AI-optimized context (auto-detects MCP mode)
bd ready        # List unblocked tasks
```

### During Work

```bash
bd show {id}                           # View task + notes
bd update {id} --status in_progress    # Claim task
bd update {id} --notes "learning: ..." # Add notes (survives compaction!)
bd close {id} --reason "commit: abc"   # Complete task
```

### Session End

```bash
bd sync         # Push to git (if normal mode)
```

## CRITICAL: Task Creation

**ALWAYS include `--description` and `--notes` with `bd create`:**

```bash
bd create "Task title" --parent {epic_id} -p 2 \
  --description="WHY this issue exists and WHAT needs to be done" \
  --notes="CONTEXT: files affected, dependencies, origin command, timestamp"
```

- `--description`: Purpose and goal of this task
- `--notes`: Context for future agents (survives compaction!)

## Command Reference

### Working With Issues

| Command | Purpose |
|---------|---------|
| `bd create "Title" -p 2` | Create task with priority |
| `bd create "Title" --parent {epic} -t task` | Create child task |
| `bd q "Quick title"` | Quick capture (outputs only ID) |
| `bd show {id}` | View task with notes |
| `bd update {id} --status {s}` | Update status |
| `bd update {id} --notes "..."` | Add notes |
| `bd update {id} --append-notes "..."` | Append to notes |
| `bd close {id} [--reason "..."]` | Complete task |
| `bd close {id1} {id2} ...` | Close multiple tasks |
| `bd reopen {id}` | Reopen closed task |
| `bd delete {id}` | Delete task |

### Discovery & Views

| Command | Purpose |
|---------|---------|
| `bd prime` | AI-optimized workflow context |
| `bd ready` | List unblocked ready tasks |
| `bd list` | List all open issues |
| `bd list --status=in_progress` | Filter by status |
| `bd status` | Overview and statistics |
| `bd graph {id}` | Show dependency graph |
| `bd stale` | Show stale issues |

### Dependencies

| Command | Purpose |
|---------|---------|
| `bd dep add {id} {depends-on}` | Add dependency |
| `bd dep remove {id} {depends-on}` | Remove dependency |
| `bd blocked` | Show blocked issues |

### Advanced

| Command | Purpose |
|---------|---------|
| `bd gate` | Manage async coordination gates |
| `bd lint` | Check for missing template sections |
| `bd search "query"` | Full-text search |
| `bd label add {id} {label}` | Add label |
| `bd epic` | Epic management commands |
| `bd compact` | Compact Beads database |
| `bd mol squash` | Aggressive compaction (molecule-level) |

### Export and Import

| Command | Purpose |
|---------|---------|
| `bd show {id} --children --json` | Export epic with all tasks as JSON |
| `bd export --parent {epic_id}` | Export all tasks under epic |
| `bd sync` | Sync Beads state with git |

## Issue Types

- `task` - Work item (default)
- `bug` - Something broken
- `feature` - New functionality
- `epic` - Large feature with subtasks
- `chore` - Maintenance (dependencies, tooling)
- `molecule` - Multi-agent workflow template
- `gate` - Async coordination point
- `agent` - Agent definition

## Priority Levels

- `P0` / `0` - Critical (do now)
- `P1` / `1` - High (do soon)
- `P2` / `2` - Medium (default)
- `P3` / `3` - Low (backlog)
- `P4` / `4` - Backlog (future ideas)

## Status Values

- `pending` - Not started
- `in_progress` - Being worked on
- `blocked` - Has blocker
- `completed` - Done

## Notes (Compaction Survival)

Notes survive context compaction - use them for:

- Learnings discovered during implementation
- Key decisions and rationale
- Links to related commits/PRs
- Context for future sessions

```bash
# Add detailed notes
bd update {id} --notes "
Pattern: Use Zod for validation
Gotcha: Must update barrel exports
Commit: abc1234
"

# Append to existing notes
bd update {id} --append-notes "Additional learning: ..."
```

## Flow Integration

When used with Flow:

| Action | Command |
|--------|---------|
| Track creation | `bd create -t epic -p 1 --description="..." --notes="..."` |
| Task start | `bd update {id} --status in_progress` |
| Task complete | `bd close {id} --reason "commit: {sha}"` |
| Log learnings | `bd update {id} --notes "..."` |
| Mark blocked | `bd update {id} --status blocked --notes "reason: ..."` |

## Configuration

`.agent/beads.json`:

```json
{
  "enabled": true,
  "mode": "stealth",
  "sync": "bidirectional",
  "epicPrefix": "flow",
  "autoSyncOnComplete": true
}
```

## Prime Command Options

```bash
bd prime          # Auto-detect mode (MCP vs CLI)
bd prime --full   # Force full CLI output
bd prime --mcp    # Force minimal MCP output
bd prime --stealth  # No git operations
bd prime --export   # Export default content for customization
```

Custom override: Place `.beads/PRIME.md` to override default output.

## Troubleshooting

**bd not found:**

```bash
npm install -g @beads/bd
```

**Permission denied:**

```bash
bd init --stealth  # Use stealth mode
```

**Sync failed:**

```bash
bd sync --force   # Force sync
```

**Check hooks:**

```bash
bd setup claude --check
bd setup gemini --check
```

## When to Track in Beads

**Rule: If work takes >5 minutes, track it in Beads.**

| Duration | Action | Example |
|----------|--------|---------|
| <5 min | Just do it | Fix typo, update config |
| 5-30 min | Create task | Add validation, write test |
| 30+ min | Create task with subtasks | Implement feature |

**Why this matters:**

- Notes survive context compaction - critical for multi-session work
- `bd ready` finds unblocked work automatically
- If resuming in 2 weeks would be hard without context, use Beads

## Boundaries

**Use Beads for:**

- Multi-session work
- Dependency tracking
- Notes that must survive compaction
- Team coordination (normal mode)

**Use TodoWrite for:**

- Single-session tracking
- Quick task lists
- Ephemeral checklists

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
br init --stealth
```

**Modes:**

- `stealth` - Local-only, .beads/ gitignored (personal use)
- `normal` - Committed to repo (team-shared)

## CLI Integration

**Note:** `br` is non-invasive and never executes git commands. After `br sync --flush-only`, you must manually run `git add .beads/ && git commit`.

Beads works with any CLI agent. No hooks or setup commands required — just ensure `br` is on your PATH.

## Session Protocol

### Session Start

```bash
br prime        # Load AI-optimized context (auto-detects MCP mode)
br ready        # List unblocked tasks
```

### During Work

```bash
br show {id}                           # View task + notes
br update {id} --status in_progress    # Claim task
br update {id} --notes "learning: ..." # Add notes (survives compaction!)
br close {id} --reason "commit: abc"   # Complete task
```

### Session End

```bash
br sync --flush-only         # Push to git (if normal mode)
git add .beads/
git commit -m "sync beads"
```

## CRITICAL: Task Creation

**ALWAYS include `--description` and `--notes` with `br create`:**

```bash
br create "Task title" --parent {epic_id} -p 2 \
  --description="WHY this issue exists and WHAT needs to be done" \
  --notes="CONTEXT: files affected, dependencies, origin command, timestamp"
```

- `--description`: Purpose and goal of this task
- `--notes`: Context for future agents (survives compaction!)

## Command Reference

### Working With Issues

| Command | Purpose |
|---------|---------|
| `br create "Title" -p 2` | Create task with priority |
| `br create "Title" --parent {epic} -t task` | Create child task |
| `br q "Quick title"` | Quick capture (outputs only ID) |
| `br show {id}` | View task with notes |
| `br update {id} --status {s}` | Update status |
| `br update {id} --notes "..."` | Add notes |
| `br update {id} --append-notes "..."` | Append to notes |
| `br close {id} [--reason "..."]` | Complete task |
| `br close {id1} {id2} ...` | Close multiple tasks |
| `br reopen {id}` | Reopen closed task |
| `br delete {id}` | Delete task |

### Discovery & Views

| Command | Purpose |
|---------|---------|
| `br prime` | AI-optimized workflow context |
| `br ready` | List unblocked ready tasks |
| `br list` | List all open issues |
| `br list --status=in_progress` | Filter by status |
| `br status` | Overview and statistics |
| `br graph {id}` | Show dependency graph |
| `br stale` | Show stale issues |

### Dependencies

| Command | Purpose |
|---------|---------|
| `br dep add {id} {depends-on}` | Add dependency |
| `br dep remove {id} {depends-on}` | Remove dependency |
| `br blocked` | Show blocked issues |

### Advanced

| Command | Purpose |
|---------|---------|
| `br gate` | Manage async coordination gates |
| `br lint` | Check for missing template sections |
| `br search "query"` | Full-text search |
| `br label add {id} {label}` | Add label |
| `br epic` | Epic management commands |
| `br compact` | Compact Beads database |
| `br mol squash` | Aggressive compaction (molecule-level) |

### Export and Import

| Command | Purpose |
|---------|---------|
| `br show {id} --children --json` | Export epic with all tasks as JSON |
| `br export --parent {epic_id}` | Export all tasks under epic |
| `br sync --flush-only` | Sync Beads state with git |

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
br update {id} --notes "
Pattern: Use Zod for validation
Gotcha: Must update barrel exports
Commit: abc1234
"

# Append to existing notes
br update {id} --append-notes "Additional learning: ..."
```

## Flow Integration

When used with Flow:

| Action | Command |
|--------|---------|
| Track creation | `br create -t epic -p 1 --description="..." --notes="..."` |
| Task start | `br update {id} --status in_progress` |
| Task complete | `br close {id} --reason "commit: {sha}"` |
| Log learnings | `br update {id} --notes "..."` |
| Mark blocked | `br update {id} --status blocked --notes "reason: ..."` |

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
br prime          # Auto-detect mode (MCP vs CLI)
br prime --full   # Force full CLI output
br prime --mcp    # Force minimal MCP output
br prime --stealth  # No git operations
br prime --export   # Export default content for customization
```

Custom override: Place `.beads/PRIME.md` to override default output.

## Troubleshooting

**bd not found:**

```bash
npm install -g @beads/bd
```

**Permission denied:**

```bash
br init --stealth  # Use stealth mode
```

**Sync failed:**

```bash
br sync --flush-only --force   # Force sync
git add .beads/
git commit -m "sync beads"
```

**Check CLI:**

```bash
command -v br &> /dev/null && echo "BEADS_OK" || echo "BEADS_MISSING"
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
- `br ready` finds unblocked work automatically
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

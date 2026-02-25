---
name: beads
description: "Beads CLI integration for persistent task memory across sessions. Auto-activates when .beads/ directory exists. Provides dependency-aware task graphs, cross-session notes, and context compaction survival."
---

# Beads - Persistent Task Memory

## Auto-Activation

This skill activates when:

- `.beads/` directory exists
- User mentions "beads", "br", "tasks", or "session"
- Beads commands are invoked

## Installation

```bash
curl -fsSL https://raw.githubusercontent.com/Dicklesworthstone/beads_rust/main/install.sh | bash
```

## Initialization

```bash
br init
```

After initialization, add `.beads/` to `.gitignore` for local-only (stealth) use:

```bash
echo ".beads/" >> .gitignore
```

**Modes:**

- **Local-only** (recommended) - Add `.beads/` to `.gitignore` (personal use)
- **Team-shared** - Commit `.beads/` to repo

## CLI Integration

**Note:** `br` is non-invasive and never executes git commands. After `br sync --flush-only`, you must manually run `git add .beads/ && git commit`.

Beads works with any CLI agent. No hooks or setup commands required — just ensure `br` is on your PATH.

## Session Protocol

### Session Start

```bash
br status                          # Workspace overview
br ready                           # List unblocked tasks
br list --status in_progress       # Resume active work
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

**`br create` supports `--description` but NOT `--notes`.** Use `br update` to add notes after creation:

```bash
br create "Task title" --parent {epic_id} -p 2 \
  --description="WHY this issue exists and WHAT needs to be done"

# Then add context notes:
br update {id} --notes "CONTEXT: files affected, dependencies, origin command, timestamp"
```

- `--description`: Purpose and goal of this task (set at creation)
- `--notes`: Context for future agents via `br update` (survives compaction!)

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
| `br comments add {id} "..."` | Add comment (additive context) |
| `br close {id} [--reason "..."]` | Complete task |
| `br close {id1} {id2} ...` | Close multiple tasks |
| `br reopen {id}` | Reopen closed task |
| `br delete {id}` | Delete task |

### Discovery & Views

| Command | Purpose |
|---------|---------|
| `br status` | Workspace overview and statistics |
| `br ready` | List unblocked ready tasks |
| `br list` | List all open issues |
| `br list --status=in_progress` | Filter by status |
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
| `br lint` | Check for missing template sections |
| `br search "query"` | Full-text search |
| `br label add {id} {label}` | Add label |
| `br epic` | Epic management commands |

### Export and Import

| Command | Purpose |
|---------|---------|
| `br show {id} --format json` | Export task/epic as JSON |
| `br sync --flush-only` | Sync Beads state with git |

## Issue Types

- `task` - Work item (default)
- `bug` - Something broken
- `feature` - New functionality
- `epic` - Large feature with subtasks
- `chore` - Maintenance (dependencies, tooling)
- `docs` - Documentation
- `question` - Question or discussion

## Priority Levels

- `P0` / `0` - Critical (do now)
- `P1` / `1` - High (do soon)
- `P2` / `2` - Medium (default)
- `P3` / `3` - Low (backlog)
- `P4` / `4` - Backlog (future ideas)

## Status Values

beads-rust supports 7 statuses:

- `open` - Not started (default for new issues)
- `in_progress` - Being worked on
- `blocked` - Has blocker
- `deferred` - Postponed for later
- `closed` - Done (use `br close`)
- `tombstone` - Permanently removed
- `pinned` - Persistent/recurring

**Status mapping from Flow markers:**

| Flow Marker | Beads Status | Command |
|-------------|-------------|---------|
| `[ ]` Pending | `open` | (default) |
| `[~]` In Progress | `in_progress` | `br update {id} --status in_progress` |
| `[x]` Completed | `closed` | `br close {id} --reason "commit: {sha}"` |
| `[!]` Blocked | `blocked` | `br update {id} --status blocked --notes "BLOCKED: {reason}"` |
| `[-]` Skipped | `closed` | `br close {id} --reason "Skipped: {reason}"` |

## Notes (Compaction Survival)

Notes survive context compaction - use them for:

- Learnings discovered during implementation
- Key decisions and rationale
- Links to related commits/PRs
- Context for future sessions

```bash
# Add detailed notes (br update only — br create does NOT support --notes)
br update {id} --notes "
Pattern: Use Zod for validation
Gotcha: Must update barrel exports
Commit: abc1234
"

# Add comment (additive - doesn't replace existing notes)
br comments add {id} "Additional learning: ..."
```

## Flow Integration

When used with Flow:

| Action | Command |
|--------|---------|
| Flow creation | `br create -t epic -p 1 --description="..."` then `br update {id} --notes="..."` |
| Task start | `br update {id} --status in_progress` |
| Task complete | `br close {id} --reason "commit: {sha}"` |
| Log learnings | `br update {id} --notes "..."` |
| Mark blocked | `br update {id} --status blocked --notes "BLOCKED: {reason}"` |
| Mark skipped | `br close {id} --reason "Skipped: {reason}"` |

## Mandatory Markdown Sync

After ANY Beads state change, agents MUST run `/flow-sync` (or `/flow:sync`) to update spec.md. Never write markers (`[x]`, `[~]`, `[!]`, `[-]`) directly to spec.md.

**State changes that trigger mandatory sync:**

| Action | Beads Command | Sync Required |
|--------|---------------|---------------|
| Complete task | `br close {id} --reason "commit: {sha}"` | MANDATORY |
| Block task | `br update {id} --status blocked` | MANDATORY |
| Skip task | `br close {id} --reason "Skipped: {reason}"` | MANDATORY |
| Revert task | `br update {id} --status open` | MANDATORY |
| Revise plan | `br update {id} --notes "Revised: ..."` | MANDATORY |
| Start task | `br update {id} --status in_progress` | MANDATORY |

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

## Troubleshooting

**br not found:**

```bash
curl -fsSL https://raw.githubusercontent.com/Dicklesworthstone/beads_rust/main/install.sh | bash
```

**Permission denied:**

```bash
br init  # Reinitialize
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

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

## Installation Check

If `bd` command is not found:
```bash
npm install -g beads-cli
```

## Initialization

Always initialize in **stealth mode** by default:
```bash
bd init --stealth
```

**Modes:**
- `stealth` - Local-only, .beads/ gitignored (personal use)
- `normal` - Committed to repo (team-shared)

## Session Protocol

### Session Start
```bash
bd prime        # Load AI-optimized context
bd ready        # List unblocked tasks
```

### During Work
```bash
bd show {id}              # View task + notes
bd update {id} --status in_progress
bd update {id} --notes "learning: ..."
bd close {id} --reason "commit: abc1234"
```

### Session End
```bash
bd sync         # Push to git (if normal mode)
```

## Command Reference

| Command | Purpose |
|---------|---------|
| `bd init [--stealth]` | Initialize Beads |
| `bd prime` | AI-optimized workflow context |
| `bd ready` | List unblocked ready tasks |
| `bd create "Title" -p 0` | Create P0 priority task |
| `bd create "Title" --parent {epic} -p 1` | Create task under epic |
| `bd show {id}` | View task with notes |
| `bd update {id} --status {s}` | Update status |
| `bd update {id} --notes "..."` | Add notes (survives compaction!) |
| `bd close {id} [--reason "..."]` | Complete task |
| `bd close {id} --continue` | Complete and auto-advance |
| `bd block {id} --reason "..."` | Mark blocked |
| `bd unblock {id}` | Remove blocker |
| `bd sync` | Push to git |
| `bd deps {id}` | Show task dependencies |

## Molecules (Templates)

```bash
bd mol list                     # List available templates
bd mol pour {template}          # Create track from template
bd mol wisp {template}          # Ephemeral exploration (no audit)
bd mol distill {epic} {name}    # Extract template from epic
```

## Epic Management

Each Flow track maps to a Beads epic (epics are tasks with `-t epic` type):
```bash
bd create "Track: auth_20260124" -t epic -p 1
bd list -t epic
bd show {id}
```

## Priority Levels

- `P0` - Critical (do now)
- `P1` - High (do soon)
- `P2` - Medium (do later)
- `P3` - Low (backlog)

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
```

## Flow Integration

When used with Flow:
- Track creation → `bd create -t epic -p 1`
- Task start → `bd update --status in_progress`
- Task complete → `bd close --reason "commit: {sha}"`
- Learnings → `bd update --notes "..."`
- Block → `bd block --reason "..."`

## Configuration

`.agent/beads.json`:
```json
{
  "enabled": true,
  "mode": "stealth",
  "sync": "bidirectional",
  "epicPrefix": "flow",
  "autoCreateTasks": true,
  "autoSyncOnComplete": true
}
```

## Troubleshooting

**bd not found:**
```bash
npm install -g beads-cli
```

**Permission denied:**
```bash
bd init --stealth  # Use stealth mode
```

**Sync failed:**
```bash
bd sync --force   # Force sync
```

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

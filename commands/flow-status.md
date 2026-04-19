---
description: Display progress overview from Beads
allowed-tools: Read, Glob, Grep, Bash
---

# Flow Status

Display progress overview for all active flows.

## The Dashboard Mandate

**CRITICAL:** `/flow:status` is the live dashboard. It pulls directly from **Beads** (source of truth). If Markdown views are out of sync, it will recommend running `/flow:sync`.

---

## 1.0 Environment Detection

**PROTOCOL: Check hook context for environment metadata.**

1. **Check Hook Context:** Scan `<hook_context>` for `## Flow Environment Context`.
2. **Verify Backend:** Use the injected Beads Backend.

---

## 2.0 Beads Status (Source of Truth)

1. **Pull Active State**: Run `bd ready` and `bd status` (or `br` equivalents).
2. **Match to Flows**: Link Beads Epics to the flows registered in `.agents/flows.md`.

---

## 3.0 Display Dashboard

```text
Flow Status Dashboard (Beads Source of Truth)

=== Active Flows ===

[~] auth - Add user authentication
    Beads Epic: flow-auth
    Progress: 5/12 tasks (41%)
    Ready Tasks: 2
    Blocked: 1 [!]

[ ] dark-mode - Add dark mode toggle
    Beads Epic: flow-dark-mode
    Progress: 0/8 tasks (0%)

=== Beads Queue ===

Ready to claim (bd ready):
  - auth: Task 6 - Implement login endpoint
  - auth: Task 7 - Add session middleware

=== Recent Notes ===

- auth: "Root cause found in services/auth.py:45" (10m ago)
- auth: "Using Zod for validation" (25m ago)

=== Next Steps ===

- Ready to code? Run `/flow:implement <flow_id>`
- Out of sync? Run `/flow:sync`
```

---

## Critical Rules

1. **BEADS FIRST** - Always prefer backend state over Markdown markers.
2. **SHOW NOTES** - Include recent Beads notes to maintain context.
3. **SYNC WARNING** - If Markdown and Beads differ, warn the user.

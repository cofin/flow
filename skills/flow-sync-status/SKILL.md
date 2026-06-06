---
name: flow-sync-status
description: "Use when syncing Beads state to markdown, checking Flow status, refreshing context docs, validating task markers, or reporting ready/blocked Flow work."
---

# Flow Sync And Status

Use this lifecycle skill for status dashboards, sync, context refresh, cleanup checks, and drift reporting.

> **Beads mode:** Skip every `bd` invocation when the SessionStart hook reports `Beads Backend: Missing (None)` or `Disabled via plugin config (useBeads=false)`. With no backend, `/flow:sync` is a no-op (announce and exit) and status falls back to `spec.md` markers. Never halt for missing Beads. See `../flow/references/discipline.md`.

## Workflow

1. Read `.agents/beads.json` before any sync/export decision.
2. Pull Beads state and notes as the source of truth.
3. Regenerate synchronized markdown views without changing requirement text.
4. Detect drift in workflow commands, tech stack, patterns, knowledge chapters, and references.
5. Report ready, blocked, in-progress, and stale work with clear next actions.

## Guardrails

- **`/flow:sync` ALWAYS writes the reconciled markdown to disk.** It is mandatory: regenerate **every markdown file in `.agents/specs/<flow_id>/`** (`spec.md`, `learnings.md`, and any other tracked markdown in the flow folder) — not just `spec.md` — so they all match Beads exactly, and persist them. Sync is never read-only/dry-run and must never finish without writing the markdown.
- **"Sync"/"export" means reconciling markdown ↔ Beads to identical reality on disk — NOT Dolt.** NEVER run `bd dolt` commands (`bd dolt push`/`pull`/`export`) as part of sync. They are out of scope and only run if the user explicitly and separately asks for Dolt.
- Sync reads backend state; do not close, block, or mutate tasks during status reporting.
- Do not auto-stage/commit unless policy or the user explicitly allows it.
- Preserve human-written spec content; only update synchronized task/status regions.
- Ask before applying context-doc updates when sync detects drift.

## Validation

- Confirm status comes from Beads, not markdown markers.
- Confirm broken file references, workflow drift, and sync policy decisions are reported.
- For this repo, run `make validate-skills` after skill or command sync changes.

## References Index

- [Sync](../flow/references/sync.md)
- [Status](../flow/references/status.md)
- [Refresh](../flow/references/refresh.md)
- [Cleanup](../flow/references/cleanup.md)

## Example

User: "Flow status."

Action: read Beads state, summarize active flows, ready tasks, blockers, recent notes, and whether markdown views need sync.

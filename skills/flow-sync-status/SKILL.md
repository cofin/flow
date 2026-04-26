---
name: flow-sync-status
description: "Use when syncing Beads state to markdown, checking Flow status, refreshing context docs, validating task markers, or reporting ready/blocked Flow work."
---

# Flow Sync And Status

Use this lifecycle skill for status dashboards, sync, context refresh, cleanup checks, and drift reporting.

## Workflow

1. Read `.agents/beads.json` before any sync/export decision.
2. Pull Beads state and notes as the source of truth.
3. Regenerate synchronized markdown views without changing requirement text.
4. Detect drift in workflow commands, tech stack, patterns, knowledge chapters, and references.
5. Report ready, blocked, in-progress, and stale work with clear next actions.

## Guardrails

- Sync reads backend state; do not close, block, or mutate tasks during status reporting.
- Do not run export, auto-stage, or Dolt push unless policy or the user explicitly allows it.
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

# Command Compatibility Matrix

This document defines the canonical 20-command inventory for the Flow Framework and their availability across host adapters.

| Canonical Name | Claude Code | Gemini CLI | OpenCode | Codex | Antigravity | Description |
|----------------|-------------|------------|----------|-------|-------------|-------------|
| `setup` | `/flow-setup` | `/flow:setup` | `/flow:setup` | `flow-setup` | `flow-setup` | Initialize project with context files, Beads, and first flow |
| `prd` | `/flow-prd` | `/flow:prd` | `/flow:prd` | `flow-prd` | `flow-prd` | Analyze goals and generate Master Roadmap (Sagas) |
| `plan` | `/flow-plan` | `/flow:plan` | `/flow:plan` | `flow-plan` | `flow-plan` | Create unified spec.md for a single Flow |
| `sync` | `/flow-sync` | `/flow:sync` | `/flow:sync` | `flow-sync` | `flow-sync` | Export Beads state to spec.md (source of truth sync) |
| `research` | `/flow-research` | `/flow:research` | `/flow:research` | `flow-research` | `flow-research` | Conduct pre-PRD research |
| `docs` | `/flow-docs` | `/flow:docs` | `/flow:docs` | `flow-docs` | `flow-docs` | Five-phase documentation workflow |
| `implement` | `/flow-implement` | `/flow:implement` | `/flow:implement` | `flow-implement` | `flow-implement` | Execute tasks from plan (context-aware) |
| `status` | `/flow-status` | `/flow:status` | `/flow:status` | `flow-status` | `flow-status` | Display progress overview with Beads status |
| `revert` | `/flow-revert` | `/flow:revert` | `/flow:revert` | `flow-revert` | `flow-revert` | Git-aware revert of flows, phases, or tasks |
| `validate` | `/flow-validate` | `/flow:validate` | `/flow:validate` | `flow-validate` | `flow-validate` | Validate project integrity and fix issues |
| `block` | `/flow-block` | `/flow:block` | `/flow:block` | `flow-block` | `flow-block` | Mark task as blocked with reason |
| `skip` | `/flow-skip` | `/flow:skip` | `/flow:skip` | `flow-skip` | `flow-skip` | Skip current task with justification |
| `revise` | `/flow-revise` | `/flow:revise` | `/flow:revise` | `flow-revise` | `flow-revise` | Update spec/plan when implementation reveals issues |
| `archive` | `/flow-archive` | `/flow:archive` | `/flow:archive` | `flow-archive` | `flow-archive` | Archive completed flows + elevate patterns |
| `export` | `/flow-export` | `/flow:export` | `/flow:export` | `flow-export` | `flow-export` | Generate project summary export |
| `handoff` | `/flow-handoff` | `/flow:handoff` | `/flow:handoff` | `flow-handoff` | `flow-handoff` | Create context handoff for session transfer |
| `refresh` | `/flow-refresh` | `/flow:refresh` | `/flow:refresh` | `flow-refresh` | `flow-refresh` | Sync context docs with current codebase state |
| `formula` | `/flow-formula` | `/flow:formula` | `/flow:formula` | `flow-formula` | `flow-formula` | List and manage flow templates |
| `wisp` | `/flow-wisp` | `/flow:wisp` | `/flow:wisp` | `flow-wisp` | `flow-wisp` | Create ephemeral exploration flow (no audit trail) |
| `distill` | `/flow-distill` | `/flow:distill` | `/flow:distill` | `flow-distill` | `flow-distill` | Extract reusable template from completed flow |

# Parity Validation Report

**Date:** 2026-03-02
**Flow ID:** `agent-parity-cleanup_20260302`

## Executed Phases

### Phase 1: Canonical Command Matrix
- `docs/compatibility/command-matrix.md` created with the 20 canonical commands.
- `docs/compatibility/plan-mode-matrix.md` created.

### Phase 2: Description Coverage and Command Parity
- Missing OpenCode command description metadata added (11 files updated).
- `flow:docs` added to `templates/opencode/opencode.json`.
- `templates/codex/AGENTS.md` and `templates/opencode/agents/flow.md` updated with the full 20-command parity list.

### Phase 3: Artifact Cleanup
- Old `templates/codex/prompts/` removed.
- Installer `scripts/install.sh` updated to stop checking/creating Codex `prompts/` paths.

### Phase 3.5 & 4: Beads Prefix & Checkpoints
- `br init` changed to `br init --prefix <project_name_slug>` in all setup commands/skills.
- `git tag checkpoint/` references replaced with commit hashes + Beads notes tracking in `implement` files and `.md` documentation.

### Phase 5 & 7: Wording, Plan-Mode, and Safety
- Removed references to obsolete `.agent/prd/` and updated them to `.agent/specs/`.
- Added Plan Mode capability requirements and `.agent/` writable safety checks to planning commands (`flow-plan`, `flow-prd`).

### Phase 6: Final Validation
- `scripts/validate-parity.sh` script created and executed successfully.
- Output confirms 0 errors (all parity checks and legacy path/string checks pass).

## Conclusion
Command descriptions, checkpoint policies, Beads prefix rules, plan-mode rules, and workspace safety policies are unified and verified across all Flow adapters.
---
name: flow-dispatch
description: "Use when choosing between inline work, subagents, packaged workflows, or bounded worker swarms, routing models and task briefs, dispatching work across CLI harnesses, or coordinating separate workspace conversations. Don't use for planning specs (use flow-planning), writing code (use flow-execution), or reviews (use flow-completion)."
---

# Flow Dispatch & Coordination

<!-- lifecycle-ownership: owner=flow-dispatch; operations=dispatch,delegate,coordinate -->

Choose the lightest execution mechanism that fits the job, route live model roles without hardcoding vendor IDs, dispatch work across installed CLI harnesses, and coordinate active conversations across separate workspaces.

## Choosing the Execution Surface

| Need | Surface | Primary Tool / Command |
| --- | --- | --- |
| Small edit (`<= 5` files or `<= 300` LOC) or narrow read (`<= 12` files) | Direct inline work | Edit and verify inside the current session |
| One isolated investigation or heavy standalone module | Single subagent | `invoke_subagent` with compact path list and stop condition |
| Multi-chapter spec, parallel research, or batched execution | Packaged workflow | `run_workflow` (`flow-scout`, `flow-spec-planning`, `flow-chapter-pipeline`, `flow-dual-review`) |
| Ready tasks editing separate files (`<= 4` at once) | Bounded swarm / parallel workers | `flow tasks plan --flow <id> --briefs --json` |
| Second-opinion review or cross-harness task | Cross-harness CLI bridge | `flow harness detect`, `dispatch`, or `delegate` |
| Separate repository conversation in Google Antigravity | Peer session bridge | `flow agent list`, `inspect`, `send`, or `start` |

## Workflow

### 1. Size Scope Before Delegating

1. Keep small edits (`<= 5` files, `<= 300` LOC) and quick lookups inside the main session so worker startup does not waste latency or tokens.
2. When multiple changes touch the same file, group them into one worker task instead of racing concurrent writers.
3. For larger multi-chapter work, prepare task briefs via `flow tasks plan --flow <flow_id> --briefs --json` before spawning workers (`workers <= 4`).

### 2. Route Models Without Hardcoding IDs

1. Query `flow models route --task-kind <kind> --json` to pick `(model, effort)` dynamically for `strong`, `standard`, `fast`, or `light` roles. Keep user overrides in `~/.config/flow/models.json`, never inside tracked repo specs or skills.
2. Materialize harness-specific agent profiles with `flow models materialize --harness <harness>` when delegating to `claude`, `codex`, `cursor`, `vscode`, or `opencode`.
3. Reserve the `strong` role for planning, spec review, bug diagnosis, and cross-vendor checks. Use `standard` or `fast` for well-scoped implementation tasks with compact briefs.

### 3. Write Self-Contained Worker Briefs

Every delegated brief (`invoke_subagent`, workflow task, swarm worker, or `flow agent send`) must carry on-disk paths rather than pasted chat history:

- **Goal & pinned boundary:** 1 to 2 lines stating what changes and what stays untouched.
- **Exclusive write paths:** exact files the worker owns (`files:` and `tests:`), or `read-only`.
- **Narrow read list:** `path:start-end` or `path::Symbol` targets plus the active schema card (`templates/agent/*.md`).
- **Fast check & stop rule:** one targeted verification command and when to stop (e.g., blocked contract or repeated failure).

### 4. Dispatch Cross-Harness or Coordinate Peer Workspaces

1. **Cross-harness runs (`flow harness`):** Detect installed CLIs via `flow harness detect --json`. Use `worktree-isolated` when another conversation may edit the same repository root, or `direct-workspace` for sequential handoffs.
2. **Cross-workspace sessions (`flow agent`):** Inspect existing sessions (`flow agent list --json` and `flow agent inspect <id> --steps 10 --json`) before writing to a sibling workspace or starting a duplicate conversation.
3. If the target repository already has a `running` conversation, hand work off with `flow agent send <id> --prompt "<brief>" --json` instead of editing its files directly. Re-run `flow agent inspect <id>` after a pause to confirm delivery instead of polling in a tight loop.

## Guardrails

- **Bounded concurrency (`<= 4` workers):** Never spawn large uncoordinated swarms without user confirmation because parallel worker startup drains quota and increases merge conflicts.
- **No overlapping writes:** Never assign two concurrent workers to the same file path in `files:` or `tests:`; concurrent writes overwrite sibling edits.
- **On-disk briefs over chat history:** Pass repository-relative paths and schema cards rather than pasting long transcripts so workers stay fast and unbiased.
- **No concurrent edits in busy peer repos:** Never edit files in a sibling workspace that already has an active running conversation; send a self-contained message via `flow agent send` instead.
- **Verify worker output before trusting it:** Check modified files, `git status --porcelain`, and verification exit codes before stamping checklists or closing a step.
- **No hardcoded model names:** Keep model pins out of tracked repository skills, specs, and workflows so teams can swap models in `~/.config/flow/models.json`.

## Example

Plan model routing, check available harnesses, and inspect or nudge an active peer session:

```bash
flow models route --task-kind planning --risk normal --json
flow harness detect --json
flow agent list --status running --json
flow agent inspect <conversation_id> --steps 10 --json
```

Start or message a peer workspace session when no overlapping write session is running:

```bash
flow harness dispatch --harness codex --mode worktree-isolated --prompt "Run targeted auth tests." --json
flow agent start --ws ../sibling-repo --title "Sync API schema" --prompt "Align consumer types and run tests." --json
```

## Output

Report the selected execution surface, resolved model role, dispatched worker or conversation ID, checked exit codes, and the next coordinator action.

## Validation

Confirm worker briefs name exclusive write paths (or read-only mode), background processes define timeouts, `git status --porcelain` shows no unintended mutations on read-only runs, and `flow status --json` matches reported progress.

## References

- [Model Routing & Parallel Workers](../flow/references/orchestration.md) — Role mapping, capability floors, brief sizing, and cross-harness transports.
- [Skills, Subagents, & MCP Limits](../multi-harness-plugins/references/skills-subagents-and-mcp-limits.md) — Antigravity `run_workflow` rules, `type_name="self"`, and profile materialization.
- [Flow Execution](../flow-execution/SKILL.md) — Chapter-level task implementation using task briefs and `flow sync`.
- [Flow Completion](../flow-completion/SKILL.md) — Independent code, spec, and subtraction-only `simplify` reviews.

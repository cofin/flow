---
trigger: model_decision
description: Flow operational and structured-decision rules evaluated before skills.
---

# Flow Operational Rule

When a repository (or its primary Git worktree) contains `.agents/`, resolve the configured bundle root from `.agents/setup-state.json` (default `.agents/bundles/`): inside a linked `git worktree`, reuse the symlinked `.venv` (`uv run --no-sync`, skipping `make install`), work in the worktree's `.agents/` when `ignore_policy` is `shared`, and work in the primary checkout's `.agents/` when `ignore_policy` is `local-only`. Read `index.md`, the active specification (`specs/<flow_id>/spec.md`), active chapter (`specs/<flow_id>/chapters/<ch_id>/spec.md` when `has_chapters: true`), task worksheets (`tasks/<id>-<slug>.md`), and applicable `.agents/bundles/knowledge/` chapters before acting.

## Lifecycle Routing & Proportional Scaling

Route work through [the Flow router](../skills/flow/SKILL.md) and the matching lifecycle skill:

- **`flow-setup`** (`/flow:setup`): Bootstrap or align `.agents/bundles/`, configure `ignore_policy` (`shared` vs. `local-only` with worktree guidance) and `model_routing`, and synthesize `.agents/skills/` + `.agents/agents/`.
- **`flow-planning`**:
  - `/flow:prd <goal>` & `/flow:spec <goal_or_flow_id>` (alias `/flow:plan`): Default cohesive deliverables of any size to a concise single-chapter `spec.md` + `compact` worksheets (`full` when complex public contracts require all 8 sections); split into `chapters/index.md` + `ch01..chNN` only for real review gates, independent parallel subsystems (`per_chapter` parallel planning in `flow-spec-planning` whenever `>= 2` chapters exist, `1` combined reviewer up to `4` chapters), or `empirical_dependent` boundaries. Validate OKF v0.2 writes immediately via `/flow:validate` and warn explicitly whenever `planning_quality: degraded` indicates planning fell back from the primary frontier thinking model.
  - `/flow:revise <flow_id> [chapter_id] [changes]` (alias `/flow:refine`): Rewrite affected chapter blueprints AND root `specs/<flow_id>/spec.md` + `chapters/index.md` in place in present tense, validate OKF, re-run zero-context review on changed chapters, and re-anchor `plan_commit = HEAD`.
  - `/flow:research <topic>` (alias `/flow:task`): Primary-source research and time-boxed `.agents/scratch/<slug>/` spikes promoted to OKF v0.2 `research/<topic>_<YYYYMMDD>.md`.
- **`flow-execution`**:
  - `/flow:implement [flow_id] [chapter_id] [--all]`: Execute one active chapter per invocation (or consecutive ready non-`empirical_dependent` chapters when `--all` is passed, closing out each chapter cleanly before the next). Compile disjoint micro-slices (`<= 250` LOC, `<= 3` files, `< 4k`-token pre-extracted `ContextPack`s) via `node <plugin_root>/sidecars/studio/flow-cli.mjs slices compile --flow <id> --chapter <ch> --packs`, run waves (`<= 4` disjoint workers per wave) via **Small Swarm** or `flow-chapter-pipeline`, run zero-token `flow-cli.mjs spec sync` between waves, validate once at closeout, and pass Zero-Context Review ([`orchestration.md`](../skills/flow/references/orchestration.md)). Uncoordinated large swarms (`> 4` workers) remain forbidden.
  - `/flow:status`: Report active flows, `planning_quality` warnings, completed vs. remaining chapters, `empirical_dependent` triggers, and ready tasks.
- **`flow-learn`** (`/flow:learn`, aliases `resynthesize`, `refresh`, `sync`): Anytime drift assessment, worktree reorientation, OKF v0.2 knowledge resynthesis, and `.agents/skills/` + `.agents/agents/` sync.
- **`flow-docs`** (`/flow:docs`): User guides, module/API docs, READMEs, changelogs, signed commits, and clean pull requests (`## Summary` + `## Key Changes` only).
- **`flow-completion`** (`/flow:review`, `/flow:finish`, `/flow:archive`, `/flow:cleanup`, `/flow:revert`, `/flow:validate`): Zero-context review, single full-release-gate run at `/flow:finish`, anti-skip Git ownership verification, OKF contraction, and archival.

## Dynamic Model Routing & Packaged Workflows

- **Orchestration CLI & Ephemeral Profiles**: Resolve dynamic `(model, effort)` pairs and materialize conversation-scoped profiles via `node <plugin_root>/sidecars/studio/flow-cli.mjs` (`models route`, `slices compile`, `harness delegate`, `spec sync`, `worktree`) rather than regex aliases ([`orchestration.md`](../skills/flow/references/orchestration.md)). Keep `type_name="self"` as default fallback in `run_workflow` `agent(...)` and `invoke_subagent(...)` calls with [`plan-schema-card.md`](../templates/agent/plan-schema-card.md) or [`executor-schema-card.md`](../templates/agent/executor-schema-card.md) ([`skills-subagents-and-mcp-limits.md`](../skills/multi-harness-plugins/references/skills-subagents-and-mcp-limits.md)). Note that `post_message`, `read_board`, and `swarm_wait` exist only in Coordinator turns (never inside `run_workflow` scripts).
- **Upward Frontier Floor**: Reserve high-capability Frontier models for planning, cold-read spec review, semantic validation, and orthogonal-vendor adversarial review; stamp `planning_quality: degraded` whenever quota constraints force lower-capability fallback during planning.
- **Anti-Skip Discipline**: Never mark a chapter or task `completed` without `exit 0` verification and Git commits touching declared `files:`/`tests:`, and never mark anything `deferred`/`skipped` without `deferred_by: "user"` and `deferred_reason`.

## Structured Decisions (`structured-choice-v1`)

Ask `1` question at a time for dependent architectural forks, and batch `2–3` orthogonal leaf questions per round once on a settled frontier (`skills/flow/references/interaction.md`) with `2–4` choices and `<Label> (Recommended)` first.

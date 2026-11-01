# Flow Finish (`/flow:finish`)

Complete a flow on the current branch after verifying that all task worksheets are `completed` (or `deferred`/`skipped`), full verification gates pass, and zero-context correctness and quality reviews (`quality-review-v1`) are clean.

## Phase 1: Scope-Cap & Task Completion Check

1. Read `.agents/bundles/specs/<flow_id>/spec.md` and `tasks/*.md`.
2. Confirm every task worksheet is `state: completed` (or `closed` / `deferred` / `skipped`) and matches its `spec.md` checklist marker (`[x] [<sha>]` or `[-]`).
3. **Branch-Local Closure Rule**: Flow completion (`state: completed`) and archival (`/flow:archive`) are branch-local transitions—never block completion waiting for a remote PR merge. If remaining open tasks represent newly discovered follow-up scope, offer to mark them `deferred` (`[-]`) and spawn a follow-up spec via `/flow:plan <new_flow_id>`.

## Phase 2: Full Verification & Review Gates

1. Run the repository's canonical verification commands from `.agents/bundles/knowledge/workflow.md` (lint, typecheck, validator, and full unit/integration test suite) and confirm exit code `0`.
2. If `/flow:review <flow_id>` has not yet run on the current `base_commit..HEAD` range, execute [`review.md`](review.md) (`@code-reviewer` + `@quality-reviewer`) and resolve any adopted findings before proceeding.
3. If the flow established a new cross-cutting architectural decision, record a concise ADR in `.agents/bundles/knowledge/decisions/adr-NNN-<slug>.md`.

## Phase 3: Mark Spec Completed & Present Next Action (`structured-choice-v1`)

1. Update `.agents/bundles/specs/<flow_id>/spec.md` frontmatter (`state: completed`, `current_task: null`, `last_verified_checkpoint: <HEAD_SHA>`, `updated_at`) and `.agents/bundles/log.md`.
2. Present the next-step decision via `structured-choice-v1` ([`interaction.md`](interaction.md)):
   - `archive` — **Archive flow now (Recommended)**: Run `/flow:archive <flow_id>` on this branch to synthesize durable learnings into `.agents/bundles/knowledge/**` and `.agents/skills/**` and contract the completed spec directory.
   - `pr` — **Archive and open/update Pull Request**: Run `/flow:archive <flow_id>`, push the branch, and create/update the PR following [`../../flow-docs/references/prs-commits-and-changelogs.md`](../../flow-docs/references/prs-commits-and-changelogs.md) (`<type>(<scope>): <concise summary>` title, `## Summary` and `## Key Changes` only, zero internal review/audit ceremony, and no `## Verification` block).
   - `keep` — **Keep completed spec directory on disk**: Leave `specs/<flow_id>/` in `state: completed` for now.

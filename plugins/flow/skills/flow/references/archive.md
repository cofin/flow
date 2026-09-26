# Flow Archive

Archiving is a rigorous knowledge contraction: durable engineering insights, domain invariants, and code patterns are synthesized into `.agents/bundles/knowledge/`, one summary line lands in `.agents/bundles/log.md`, and only then is the completed spec directory deleted—including its promoted `research/`. `.agents/bundles/specs/` holds only planned and active flows. The terminal journal remains outside the bundle under the configured transaction directory; no resident archive tree is created.

## Contents

- [Branch-local eligibility and tracking policy](#branch-local-eligibility--tracking-policy)
- [Mandatory 5-dimension knowledge synthesis](#mandatory-5-dimension-knowledge--pattern-synthesis)
- [Procedure](#procedure)
- [Verification](#verification)

## Branch-Local Eligibility & Tracking Policy

A spec is eligible for archive as soon as its `state` is `completed` (all tasks `closed` or `skipped` and verified on the current branch). **Archive never requires the branch or Pull Request to be merged into `main` first.** Contracting a completed spec directly on a feature branch or PR branch is encouraged so the synthesized knowledge chapters and spec removal travel together in the branch/PR.

Read `workflow_preferences.ignore_policy` from `<configured-root>/setup-state.json`; if absent, ask once and persist it:

- **`shared`** — bundles are tracked; step 7 writes the `chore(archive)` commit.
- **`local-only` (stealth mode)** — nothing in `.agents/` is committed. Contraction runs identically, minus the commit. Knowledge chapters and `log.md` are the whole durable record, so preserve borderline architectural or pattern learnings rather than dropping them.

Never force-add ignored Flow files to make an archive "recoverable". Git notes under `refs/notes/flow` are supplementary audit evidence only; their absence or an attachment failure never changes archive eligibility: canonical Markdown and the archive journal are sufficient for recovery. Archive never pushes, copies, rewrites, prunes, or requires the notes ref. Never create or mutate Git tags for archive evidence or as a notes fallback.

Archive follows the ordered gates `archive_candidate -> verification -> code_review -> quality_review -> archive`. The quality gate is mandatory and uses the `quality-review-v1` contract in [Review](review.md).

## Mandatory 5-Dimension Knowledge & Pattern Synthesis

**IRON LAW: NEVER DELETE A SPEC BEFORE DEEP KNOWLEDGE & PATTERN SYNTHESIS.**
Appending a few superficial lines to a single pattern file and deleting `specs/<flow_id>/` is a contract violation. Before preparing any spec deletion fragment, audit `spec.md`, every `tasks/*.md` (`## Objective`, `## Context`, `## Steps`, `## Notes & Discoveries`, `## Verification Evidence`), `learnings.md`, and promoted `research/` across all five dimensions:

1. **Domain Model & Invariants (`knowledge/domains/<domain>.md`)**: Ubiquitous terminology, entity lifecycles, state-machine invariants, and domain constraints established or refined by the flow.
2. **Architecture & Deep Module Seams (`knowledge/architecture/<area>.md`)**: Component boundaries, narrow public interfaces vs hidden implementation details, data/control flow, and dependency direction rules.
3. **Idiomatic Code Patterns & Anti-Patterns (`knowledge/patterns/<topic>.md`)**: Reusable implementation patterns backed by concrete `path/to/file::Symbol` anchors, paired with explicit anti-patterns or rejected approaches.
4. **Build, Verification & Testing Recipes (`knowledge/testing/<topic>.md` or `knowledge/workflow.md`)**: Non-obvious test fixtures, verification strategies (`behavior_tdd`, `static_validation`, `characterization`), and fast inner-loop commands.
5. **Hard-Won Gotchas & Edge Cases (`knowledge/gotchas/<topic>.md` or `knowledge/patterns/<topic>.md`)**: Subtle failure modes, concurrency/runtime traps, and environment quirks discovered during implementation or review.

Always evaluate the `.agents/bundles/knowledge/` folder taxonomy during synthesis:

- Split any chapter that covers multiple distinct concerns or exceeds ~200 lines into focused nested chapters (`architecture/`, `domains/`, `patterns/<subsystem>/`, `testing/`, `gotchas/`, `decisions/`, `standards/`).
- Rewrite affected chapters as cohesive, present-tense documentation without AI puffery, dated changelog lines, or flow attributions—history belongs in `log.md` only.
- Update `.agents/bundles/knowledge/index.md` and `.agents/bundles/index.md` routing pointers (`covers`, `related`, `tags`) whenever chapters are created, split, or reorganized.

## Procedure

1. **Validate**: Resolve `flow_id` (scan spec frontmatter for `state: completed` when not given; if all tasks are `closed` or `skipped` on an `active` spec, complete it first rather than getting stuck). Confirm every task file is `state: closed` or `skipped`. Resolve the tracking policy above. Under `shared`, check recoverability with `git ls-files --error-unmatch`. Under `local-only`, skip the tracked-file check.
2. **Render candidate (synthesize knowledge before live contraction)**:
   - Consolidate all task `## Notes & Discoveries`, `learnings.md`, `spec.md` architectural decisions, and promoted `research/` into a transient working synthesis matrix covering the 5 dimensions above.
   - Research is contracted, not shelved: findings that describe how the codebase or its dependencies work belong in `knowledge/`; findings that only justified a past decision are dropped or distilled into `knowledge/decisions/<decision>.md`. Never relocate research to `bundles/research/` (which is for un-promoted work only).
   - Draft the complete current-state edits for every target chapter under `knowledge/**`, plus `knowledge/index.md` and `product/` docs if affected. Present the proposed knowledge synthesis summary for user approval before writing.
   - Delete any transient `extracted_learnings.md`.
   - Render the complete archive request: `knowledge_destinations` and full before/after bytes, `log.md` entry, `notes_incorporation`, sorted `archive_inventory`, and full file fragments for every spec deletion (`spec.md`, `tasks/`, `learnings.md`, `research/`).
3. **Create disposable local review range**: Apply the rendered candidate in a disposable local branch/worktree (`base_commit..head_commit`) containing the exact knowledge, log, and deletion bytes. Never use a Git tag and never push the candidate.
4. **Review exact candidate**:
   - Run archive-relevant verification (`documentation_validation` / link and OKF checks) on `base_commit..head_commit`.
   - Run correctness review on that exact range, verifying that no durable pattern, architectural seam, or gotcha from the spec was lost before deletion.
   - Dispatch the read-only `quality-reviewer` afterward on the same range (resolving `.agents/skills/debloat/SKILL.md`, then packaged `skills/debloat/SKILL.md`, then the inline fallback).
   - Critical/Important findings block archive; fix the knowledge synthesis or markdown defects, render a fresh candidate, and re-verify. A fresh user waiver applies to one named finding and this range only; it cannot replace dispatch.
5. **Bind candidate**: Confirm `archive_candidate_manifest` and every before/after fragment match the reviewed candidate byte-for-byte.
6. **Request archive (strict write order)**: Submit the exact range, manifest, and review evidence to `flow-state`. The transaction writes synthesized `knowledge/**` chapters and `index.md` **first**, `.agents/bundles/log.md` **second**, and deletes `specs/<flow_id>/` **last**. Never delete the live spec directory directly before knowledge synthesis is committed. Also prune superseded/obsolete prior terminal journals for the archived flow so only the terminal archive journal remains.
7. **Commit** (`shared` policy only): After the archive transaction commits and postconditions pass, stage only its recorded bundle paths and create one `chore(archive)` commit. Under `local-only`, skip this step.

## Verification

- Confirm `.agents/bundles/specs/<flow_id>/` is absent and `.agents/bundles/research/` has no leftover promoted files for the flow.
- Confirm `.agents/bundles/knowledge/` contains the newly created or updated chapters, `knowledge/index.md` routes to them accurately, and `.agents/bundles/log.md` has the new archive entry at the top.
- Knowledge chapters must read as if written fresh today—an agent reading `knowledge/` must learn how to build in the codebase now, never which historical flow taught us.

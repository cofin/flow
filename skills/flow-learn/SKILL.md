---
name: flow-learn
description: "Use when reorienting across machines or harnesses (/flow:refresh), reconciling spec checklists (/flow:sync), auditing codebase or spec drift, sharpening domain glossaries and ADRs, or resynthesizing OKF v0.2 knowledge and .agents/skills/ (/flow:learn, /flow:resynthesize)."
disable-model-invocation: true
---

# Flow Learn (Drift True-Up, Cross-Harness Refresh, & OKF Resynthesis)

<!-- lifecycle-ownership: owner=flow-learn; operations=learn,resynthesize,refresh,sync,docs -->

## Trigger

Use for `/flow:learn [scope]` (and aliases `resynthesize`, `refresh`, `sync`, `docs`). Can run at any point in a project's lifecycle—when switching machines or harnesses, mid-flow, post-flow, or standalone. Follow [`../flow/references/learn.md`](../flow/references/learn.md).

## Workflow

1. **Cross-Machine/Harness Reorientation & Multi-Chapter Drift Audit (`refresh` + `sync` + `true-up`)**:
   - **Spec, Chapter, & Task Reconciliation (`sync` / `refresh`)**:
     - Compare `tasks/*.md` frontmatter (`state`, `commit`, `claimed_by`), `chapters/<ch_id>/spec.md` (`state`, `planning_status`, `last_reviewed_commit`), `chapters/index.md`, and root `specs/<flow_id>/spec.md` (`chapters:`, `current_chapter`, checklist markers, `## 6. Current State & Remaining Plan Snapshot`) against live `git log` and working-tree state.
     - Mark tasks whose commits landed on another machine/session `state: completed` with their verified Git `commit` SHA, release stale cross-harness `in_progress` claims when no active work matches the working tree, and rewrite `chapters/index.md`, chapter `spec.md`, and root `spec.md` checklists and state snapshots in place in present tense.
     - Flag any open `tasks/<id>-<slug>.md` or downstream chapters whose target `files:` or `path/to/file::Symbol` signatures drifted so `/flow:revise <flow_id> [chapter_id]` can re-baseline them.
   - **Source-to-Knowledge Drift (`sources[].resource` Intersection)**:
     - Intersect modified or deleted files/symbols (`git status`, `git diff <last_verified_commit>..HEAD`) against every `.agents/bundles/knowledge/**/*.md` chapter's `sources[].resource` paths and `path/to/file::Symbol` anchors (sharding across `1` read-only subagent per domain on multi-domain repos; `type_name="self"` on Google Antigravity).
   - **Manifest & Toolchain Drift**:
     - Compare `pyproject.toml`, `Cargo.toml`, `package.json`, `go.mod`, `Makefile`, and CI workflows against `product/tech-stack.md`, `product/product.md`, and `knowledge/workflow.md`.
2. **Subagent-Sharded OKF v0.2 Knowledge Resynthesis (`.agents/bundles/knowledge/`)**:
   - Harvest confirmed discoveries across single-chapter and nested `chapters/<ch_id>/tasks/*.md` (`## Notes & Discoveries`) and promoted `research/*.md`.
   - When resynthesizing `>= 2` domains, fan out **1 isolated synthesis subagent per domain** (`type_name="self"` on Google Antigravity) so each domain chapter receives thorough present-tense updates with `status: stable`, `<= 40`-line `<!-- truth: start -->` blocks, `sources:` + `[^id]:` footnotes, and zero standalone `---` body rules.
   - Sharpen `knowledge/domains/<domain>.md` and apply the **ADR Filter** (*hard to reverse + surprising without context + genuine trade-off*) for `knowledge/decisions/adr-NNN-<slug>.md`, pruning chronological sediment and model-relative no-ops ([`../flow-docs/references/agent-context.md`](../flow-docs/references/agent-context.md)).
3. **Dynamic Project-Local Skill, Subagent, & Documentation Synchronization (`.agents/skills/`, `.agents/agents/`, & `docs/`)**:
   - Follow [`../multi-harness-plugins/SKILL.md`](../multi-harness-plugins/SKILL.md) to update `.agents/skills/<domain>/SKILL.md` (`<= 200` lines + `references/*.md`), `.agents/skills/review-<domain>/SKILL.md` (`references/checklist.md` + `references/false-positive-suppressions.md`), `.agents/skills/index.md`, paired subagents (`.agents/agents/<domain>-reviewer.md` and `<domain>-specialist.md` with `commandExecutionPolicy: sandbox`), and root `AGENTS.md`.
   - When updating user-facing guides, READMEs, or module docs, follow [`../flow-docs/SKILL.md`](../flow-docs/SKILL.md).
   - Remove any legacy `.agents/skills/flow-memory-keeper/` or copied global Flow skills.
4. **Frontmatter-Free Index Rebuild, `log.md` Audit Entry & True-Up Dashboard**:
   - Rebuild root `.agents/bundles/index.md` (`okf_version: "0.2"`) and frontmatter-free subdirectory `index.md` files (`product/index.md`, `knowledge/index.md`, `knowledge/<ns>/index.md`, `specs/index.md`, `chapters/index.md`), prepend a `synthesize` / `verify` entry to `.agents/bundles/log.md`, and report the **Project True-Up & Reorientation Dashboard**.

## Guardrails

- Never overwrite uncommitted user code changes or developer-owned content inside `<!-- project-customization: start -->` blocks.
- Rewrite updated knowledge chapters in place in present tense; never append chronological revision logs inside concept documents.
- Every knowledge claim must cite a verified repository path (`path/to/file::Symbol`) or primary source in `sources:`.

## Output

Return the **Project True-Up & Reorientation Dashboard** listing reconciled commits/claims, repaired `knowledge/**` chapters, updated `.agents/skills/` and `.agents/agents/`, and the next exact step.

## Validation

Confirm all `sources[].id` entries have matching `[^id]` footnotes in body prose, all relative links in `.agents/bundles/index.md` and `.agents/skills/index.md` resolve on disk, `spec.md` checklists match `tasks/*.md` frontmatter, and `.agents/bundles/log.md` records the synthesis entry.

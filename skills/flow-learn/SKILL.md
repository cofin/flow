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

1. **Cross-Machine/Harness Reorientation & Drift Audit (`refresh` + `sync` + `true-up`)**:
   - **Spec & Task Reconciliation (`sync` / `refresh`)**:
     - Compare `tasks/*.md` frontmatter (`state`, `commit`, `claimed_by`) and `spec.md` checklist markers (`[ ]`, `[~]`, `[x] [<sha>]`, `[!]`, `[-]`) against live `git log` and working-tree state.
     - Mark tasks whose commits landed on another machine/session `state: completed` with their verified Git `commit` SHA, release stale cross-harness `in_progress` claims when no active work matches the working tree, and synchronize `spec.md` checklists and `## 5. Continuity Snapshot`.
     - Flag any open `tasks/<id>-<slug>.md` worksheets whose target `files:` or `path/to/file::Symbol` signatures drifted so `/flow:revise` can re-baseline them.
   - **Source-to-Knowledge Drift (`sources[].resource` Intersection)**:
     - Intersect modified or deleted files/symbols (`git status`, `git diff <last_verified_commit>..HEAD`) against every `.agents/bundles/knowledge/**/*.md` chapter's `sources[].resource` paths and `path/to/file::Symbol` anchors.
   - **Manifest & Toolchain Drift**:
     - Compare `pyproject.toml`, `Cargo.toml`, `package.json`, `go.mod`, `Makefile`, and CI workflows against `product/tech-stack.md`, `product/product.md`, and `knowledge/workflow.md`.
2. **Active Domain Modeling & OKF v0.2 Knowledge Resynthesis (`.agents/bundles/knowledge/`)**:
   - Harvest confirmed discoveries from `tasks/*.md` (`## Notes & Discoveries`), `learnings.md`, and promoted `research/*.md`.
   - Sharpen `knowledge/domains/<domain>.md` (eliminating overloaded nouns and documenting entity invariants) and apply the **ADR Filter** (*hard to reverse + surprising without context + genuine trade-off*) for `knowledge/decisions/adr-NNN-<slug>.md`.
   - Rewrite drifted chapters in place in present tense across `knowledge/{domains,architecture,patterns,testing,gotchas,decisions}/`, split chapters `> 200` lines or covering multiple seams, and prune chronological sediment, duplicate cache lines, and model-relative no-ops ([`../flow-docs/references/agent-context.md`](../flow-docs/references/agent-context.md)).
3. **Dynamic Project-Local Skill, Subagent, & Documentation Synchronization (`.agents/skills/`, `.agents/agents/`, & `docs/`)**:
   - Follow [`../multi-harness-plugins/SKILL.md`](../multi-harness-plugins/SKILL.md) to update `.agents/skills/<domain>/SKILL.md` (`<= 200` lines + `references/*.md`), `.agents/skills/review-<domain>/SKILL.md` (`references/checklist.md` + `references/false-positive-suppressions.md`), `.agents/skills/index.md`, paired subagents (`.agents/agents/<domain>-reviewer.md` and `<domain>-specialist.md`), and root `AGENTS.md`.
   - When updating user-facing guides, READMEs, or module docs, follow [`../flow-docs/SKILL.md`](../flow-docs/SKILL.md).
   - Remove any legacy `.agents/skills/flow-memory-keeper/` or copied global Flow skills.
4. **Index Rebuild, `log.md` Audit Entry & True-Up Dashboard**:
   - Rebuild `.agents/bundles/index.md` and `knowledge/index.md` (verifying all relative links resolve on disk), prepend a `synthesize` / `verify` entry to `.agents/bundles/log.md`, and report the **Project True-Up & Reorientation Dashboard**.

## Guardrails

- Never overwrite uncommitted user code changes or developer-owned content inside `<!-- project-customization: start -->` blocks.
- Rewrite updated knowledge chapters in place in present tense; never append chronological revision logs inside concept documents.
- Every knowledge claim must cite a verified repository path (`path/to/file::Symbol`) or primary source in `sources:`.

## Output

Return the **Project True-Up & Reorientation Dashboard** listing reconciled commits/claims, repaired `knowledge/**` chapters, updated `.agents/skills/` and `.agents/agents/`, and the next exact step.

## Validation

Confirm all `sources[].id` entries have matching `[^id]` footnotes in body prose, all relative links in `.agents/bundles/index.md` and `.agents/skills/index.md` resolve on disk, `spec.md` checklists match `tasks/*.md` frontmatter, and `.agents/bundles/log.md` records the synthesis entry.

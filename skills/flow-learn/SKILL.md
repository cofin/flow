---
name: flow-learn
description: "Use when auditing codebase, Git, or spec drift, reconciling active specs and task worksheets, resynthesizing OKF v0.2 knowledge chapters, or synchronizing project-local .agents/skills/ and .agents/agents/ (/flow:learn)."
disable-model-invocation: true
---

# Flow Learn

<!-- lifecycle-ownership: owner=flow-learn; operations=learn,resynthesize,refresh,sync,docs -->

## Trigger

Use for `/flow:learn [scope]` (and aliases `resynthesize`, `refresh`, `sync`, `docs`). Can run at any point in a project's lifecycle—whether a flow is mid-flight, completed, or not yet started. Follow [`../flow/references/learn.md`](../flow/references/learn.md).

## Workflow

1. **Phase 1 — Codebase, Git & Spec Drift Assessment (True-Up Audit)**:
   - **Source-to-Knowledge Drift (`sources[].resource` Intersection)**: Inspect `git status`, recent `git log`, and `git diff <last_verified_commit>..HEAD`, intersecting modified or deleted files/symbols against every `.agents/bundles/knowledge/**/*.md` chapter's `sources[].resource` paths and `path/to/file::Symbol` anchors.
   - **Manifest & Toolchain Drift**: Compare `pyproject.toml`, `Cargo.toml`, `package.json`, `go.mod`, `Makefile`, and CI workflows against `product/tech-stack.md`, `product/product.md`, and `knowledge/workflow.md`.
   - **Active & Completed Spec/Task Reconciliation**:
     - Reconcile `tasks/*.md` frontmatter (`state`, `commit`) and `spec.md` checklist markers (`[ ]`, `[~]`, `[x] [<sha>]`, `[!]`, `[-]`) against actual Git history.
     - Flag any open `tasks/<id>-<slug>.md` worksheets whose target `files:` or `path/to/file::Symbol` signatures drifted so `/flow:revise` can re-baseline them.
     - Harvest confirmed mid-flow discoveries from `tasks/*.md` (`## Notes & Discoveries`), `learnings.md`, and promoted `research/*.md`.
2. **Phase 2 — Comprehensive OKF v0.2 Knowledge Resynthesis (`.agents/bundles/knowledge/`)**:
   - Rewrite drifted sections in place in present tense, remove claims referencing deleted symbols, split oversized chapters (`> 200` lines), and synthesize new evidence-backed chapters across `knowledge/{architecture,patterns,domains,testing,gotchas,decisions}/` with `sources: [{ id, resource, title }]` + `[^id]` footnotes, `verified: [{ by, at }]`, and bounded `<= 40`-line `<!-- truth: start -->` blocks.
3. **Phase 3 — Dynamic Project-Local Skill, Subagent, & Documentation Synchronization (`.agents/skills/`, `.agents/agents/`, & `docs/`)**:
   - Follow [`../multi-harness-plugins/SKILL.md`](../multi-harness-plugins/SKILL.md) to update `.agents/skills/<domain>/SKILL.md` (`<= 200` lines + `references/*.md`), `.agents/skills/review-<domain>/SKILL.md` (`references/checklist.md` + `references/false-positive-suppressions.md`), `.agents/skills/index.md`, paired subagents (`.agents/agents/<domain>-reviewer.md` and `<domain>-specialist.md`), and root `AGENTS.md`.
   - When updating user-facing guides, API references, or READMEs, follow [`../flow-docs/SKILL.md`](../flow-docs/SKILL.md).
   - Remove any legacy `.agents/skills/flow-memory-keeper/` or copied global Flow skills.
4. **Phase 4 — Index Rebuild, `log.md` Audit Entry & True-Up Summary**:
   - Rebuild `.agents/bundles/index.md` and `knowledge/index.md` (verifying all relative links resolve on disk), append a `synthesize` / `verify` entry to `.agents/bundles/log.md`, and report the **Project True-Up Summary**.

## Guardrails

- Never overwrite developer-owned content inside `<!-- project-customization: start -->` blocks.
- Rewrite updated knowledge chapters in place in present tense; never append chronological revision logs inside concept documents.
- Every knowledge claim must cite a verified repository path (`path/to/file::Symbol`) or primary source in `sources:`.

## Output

Return the **Project True-Up Summary** listing repaired `knowledge/**` chapters, updated `.agents/skills/` and `.agents/agents/`, and reconciled `specs/<flow_id>/` task states.

## Validation

Confirm all `sources[].id` entries have matching `[^id]` footnotes in body prose, all relative links in `.agents/bundles/index.md` and `.agents/skills/index.md` resolve on disk, and `.agents/bundles/log.md` records the synthesis entry.

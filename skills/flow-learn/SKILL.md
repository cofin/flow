---
name: flow-learn
description: "Use when catching up across machines or harnesses, syncing spec checklists against Git, auditing drift, sharpening domain glossaries and ADRs, or updating OKF v0.2 knowledge and .agents/skills/. Don't use for planning new specs (use flow-planning) or public README/PR drafting (use flow-docs)."
disable-model-invocation: true
---

# Flow Learn

<!-- lifecycle-ownership: owner=flow-learn; operations=learn,refresh,sync -->

## Trigger

Use for `/flow:learn [scope]` (and aliases `refresh`, `sync`). Can run at any point in a project's lifecycle—when switching machines or harnesses, mid-flow, post-flow, or standalone. Follow [`../flow/references/learn.md`](../flow/references/learn.md). When asked to **"finish and sync"** a reviewed flow, run the full closeout and archive pass via [`../flow-completion/SKILL.md`](../flow-completion/SKILL.md). For user-facing guides, READMEs, or PR bodies, route to [`../flow-docs/SKILL.md`](../flow-docs/SKILL.md).

## Workflow

1. **Cross-Machine Catch-Up & Drift Audit (`refresh` + `sync`)**:
   - **Linked Git Worktree & Environment Check**: Inside a linked `git worktree`, verify `.venv` / `node_modules` symlinks (`uv run --no-sync`). Confirm `shared` (worktree `.agents/`) vs. `local-only` (primary checkout `.agents/`, using `flow worktree sync-from-main` / `flow worktree sync-to-main`) routing, and flag untracked worktree `.agents/` files.
   - **Spec, Chapter, & Task Sync (`sync` / `refresh`)**:
     - Compare `tasks/*.md` frontmatter (`state`, `commit`, `claimed_by`), `chapters/<ch_id>/spec.md`, `chapters/index.md`, and root `specs/<flow_id>/spec.md` (`chapters:`, `current_chapter`, checklists, `## 6. Current State & Remaining Plan Snapshot`) against live `git log` and working-tree state.
     - Mark tasks whose commits landed on another machine `state: completed` with their verified Git `commit` SHA. Release stale `in_progress` claims and rewrite `chapters/index.md`, chapter `spec.md`, and root `spec.md` in place in present tense.
     - Flag any open `tasks/<id>-<slug>.md` or downstream chapters whose target `files:` or `path/to/file::Symbol` signatures drifted so `/flow:revise <flow_id> [chapter_id]` can update them.
   - **Source-to-Knowledge Drift (`sources[].resource` Intersection)**:
     - Intersect modified or deleted files/symbols (`git status`, `git diff <last_verified_commit>..HEAD`) against every `.agents/bundles/knowledge/**/*.md` chapter's `sources[].resource` paths. Use `1` read-only subagent per domain on multi-domain repos (`type_name="self"` on Google Antigravity).
   - **Manifest & Toolchain Drift**:
     - Compare `pyproject.toml`, `Cargo.toml`, `package.json`, `go.mod`, `Makefile`, and CI workflows against `product/tech-stack.md`, `product/product.md`, and `knowledge/workflow.md`.
2. **Parallel OKF v0.2 Knowledge Update (`.agents/bundles/knowledge/`)**:
   - Harvest confirmed discoveries across single-chapter and nested `chapters/<ch_id>/tasks/*.md` (`## Notes & Discoveries`) and promoted `research/*.md`.
   - When updating `>= 2` domains, fan out `1` isolated subagent per domain (`type_name="self"` on Google Antigravity). Update each domain chapter in present tense with `status: stable`, `<= 40`-line `<!-- truth: start -->` blocks, `sources:` + `[^id]:` footnotes, and zero standalone `---` body rules.
   - Sharpen `knowledge/domains/<domain>.md` and apply the **ADR Filter** (*hard to reverse + surprising without context + genuine trade-off*) for `knowledge/decisions/adr-NNN-<slug>.md`. Prune stale history and model-relative no-ops ([`../flow-docs/references/agent-context.md`](../flow-docs/references/agent-context.md)).
3. **Project Skill, Subagent, & Doc Sync**:
   - Follow [`../multi-harness-plugins/SKILL.md`](../multi-harness-plugins/SKILL.md) to update `.agents/skills/<domain>/SKILL.md` (`<= 200` lines + `references/*.md`), `.agents/skills/review-<domain>/SKILL.md`, `.agents/skills/index.md`, paired subagents (`.agents/agents/<domain>-reviewer.md` and `<domain>-specialist.md`), and root `AGENTS.md`.
   - When updating user-facing guides, READMEs, or module docs, follow [`../flow-docs/SKILL.md`](../flow-docs/SKILL.md).
   - Remove any copied global Flow skills from `.agents/skills/`.
4. **Index Rebuild, `log.md` Entry, & Status Summary**:
   - Rebuild root `.agents/bundles/index.md` (`okf_version: "0.2"`) and frontmatter-free subdirectory `index.md` files (`product/index.md`, `knowledge/index.md`, `knowledge/<ns>/index.md`, `specs/index.md`, `chapters/index.md`). Prepend a `synthesize` / `verify` entry to `.agents/bundles/log.md` and report the **Project Status Summary**.

## Guardrails

- Preserve uncommitted user edits and content inside `<!-- project-customization: start -->` blocks so automated sync never drops local work.
- Rewrite updated knowledge chapters in place in present tense because chronological logs inside concept docs confuse isolated readers.
- Anchor every knowledge claim to a verified repository path (`path/to/file::Symbol`) or primary source in `sources:` so readers can audit freshness directly.

## Example

```bash
flow sync --dry-run --json
flow status --branches
```

## Output

Return the **Project Status Summary** listing synced commits and claims, repaired `knowledge/**` chapters, updated `.agents/skills/` and `.agents/agents/`, and the next step.

## Validation

Confirm all `sources[].id` entries have matching `[^id]` footnotes in body prose, all relative links in `.agents/bundles/index.md` and `.agents/skills/index.md` resolve on disk, `spec.md` checklists match `tasks/*.md` frontmatter, and `.agents/bundles/log.md` records the update entry.

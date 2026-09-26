# Flow Resynthesize Reference

Deep, repository-wide audit, hierarchical reorganization, and rewrite of `.agents/bundles/knowledge/` to conform to OKF v0.2 and current codebase reality.

## Contents

- [Mandate](#10-the-resynthesis-mandate)
- [Workflow](#20-workflow)
- [Critical Rules](#30-critical-rules)

---

## 1.0 THE RESYNTHESIS MANDATE

`/flow:resynthesize [scope]` rewrites the knowledge base in depth so an agent reading `.agents/bundles/knowledge/` learns how to build for the project today without wading through append-only sediment, stale claims, or AI-generated filler.

Resynthesis enforces five non-negotiable invariants:

1. **Codebase Truth Only**: Every architectural, domain, pattern, data-model, or workflow claim must cite existing repository-relative paths and real symbols or observed behavior. Delete claims whose files or symbols no longer exist.
2. **Hierarchical Taxonomy (`knowledge/<namespace>/<topic>.md`)**: Never leave a catch-all `patterns.md` or flat file dump. Organize concepts into scope-derived folders (`architecture/`, `domains/`, `patterns/`, `data-model/`, `decisions/`, `standards/`).
3. **Single-Sentence Scope Test**: If a chapter requires more than one crisp sentence in its frontmatter `description:` or exceeds ~150 lines, split it into focused sub-chapters under a nested folder. Merge overlapping fragments that describe the same seam.
4. **Zero Historical Narration or Slop**: Strip flow attributions ("added in flow X"), dated changelog bullets, throat-clearing transitions, puffery, and restatements of obvious framework syntax. History belongs in `.agents/bundles/log.md` only.
5. **Routing Index Integrity**: Rebuild `.agents/bundles/knowledge/index.md` and `.agents/bundles/index.md` as compact routing tables of context pointers (`path`, `type`, `description`, `tags`) where every link resolves on disk.

---

## 2.0 WORKFLOW

### Phase 1: Inventory & Codebase Truth Audit

1. **Resolve Bundle Roots**: Read `.agents/setup-state.json` and `.agents/config.json` (default `.agents/bundles/` and `.agents/bundles/knowledge/`). Confirm root `index.md` carries `okf_version: "0.2"`.
2. **Scan Existing Knowledge**: Recursively read every Markdown file under `knowledge/` and `product/`. If `[scope]` is provided (e.g., `architecture`, `patterns`, or a domain name), focus the deep rewrite on that subtree while validating cross-links globally.
3. **Verify Against Live Source**:
   - Inspect `Makefile`, `pyproject.toml`, `package.json`, `Cargo.toml`, and CI workflows to verify `knowledge/workflow.md` and `product/tech-stack.md`.
   - Verify every file path, module boundary, and symbol referenced in `knowledge/**/*.md` against the current working tree.
   - Identify undocumented core seams: domain vocabulary, module boundaries, test fixture boundaries, and non-obvious build/runtime gotchas.

### Phase 2: Taxonomy & Structural Reorganization

1. **Eliminate Flat Catch-Alls**: Migrate any remaining entries from legacy flat `patterns.md` files into topic-specific `knowledge/patterns/<topic>.md` chapters and remove the catch-all file.
2. **Split & Merge Chapters**:
   - Split any chapter covering multiple distinct subsystems or exceeding ~150 lines into `knowledge/<namespace>/<subsystem>/<topic>.md`.
   - Merge micro-fragments that share the same source seam and audience.
3. **Enforce OKF v0.2 Frontmatter**:
   - Ensure every non-reserved concept file starts with valid YAML frontmatter containing non-empty `type:`, `title:`, single-sentence `description:`, `status: stable | draft | deprecated`, and 2-5 lowercase hyphenated `tags: [...]`.
   - Preserve `<!-- truth: start -->` and `<!-- truth: end -->` invariant blocks in `product/tech-stack.md`, `knowledge/workflow.md`, and `knowledge/patterns/**/*.md`.

### Phase 3: Deep Anti-Slop Rewrite

Rewrite each chapter as authoritative, current-state engineering documentation:

- Lead with the module seam, invariant, or command contract.
- Include concrete repository-relative file paths and symbol names.
- Apply the `debloat` anti-slop audit: delete puffery ("robust", "seamless", "pivotal", "delve"), negative parallelisms ("not just X, but Y"), bold-bullet filler, and superficial participle tails.
- Retain every concrete command, edge case, failure mode, and rejected-alternative rationale.

### Phase 4: Rebuild Indexes, Log, and Validate

1. **Update Indexes**: Rewrite `knowledge/index.md` and root `bundles/index.md` so every concept chapter is linked with its current title, type, tags, and one-line description.
2. **Log Resynthesis**: Prepend one ISO-dated entry in `.agents/bundles/log.md` summarizing the resynthesized chapters, splits, and removals.
3. **Validate**: Verify that all Markdown links resolve, frontmatter schemas and tags are valid, and no active spec under `bundles/specs/` was modified or deleted.

---

## 3.0 CRITICAL RULES

1. **NEVER TOUCH ACTIVE SPECS** — Resynthesis rewrites `knowledge/`, `product/`, `index.md`, and `log.md`; it never deletes or alters active `specs/<flow_id>/` worksheets.
2. **EVIDENCE BEFORE MATERIALIZATION** — Never invent placeholder chapters or empty directories; create a namespace directory only when writing an evidence-backed chapter.
3. **RESOLVE ALL LINKS** — Every relative link in `index.md` and concept chapters must resolve on disk before completion.

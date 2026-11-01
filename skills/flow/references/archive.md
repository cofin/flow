# Flow Archive (`/flow:archive`)

Contract a completed flow (`state: completed`) by synthesizing its durable discoveries, architecture boundaries, domain invariants, patterns, testing recipes, and gotchas into `.agents/bundles/knowledge/**` and `.agents/skills/**`, logging the contraction in `.agents/bundles/log.md`, and removing the completed `.agents/bundles/specs/<flow_id>/` directory.

## Branch-Local Eligibility & Tracking Policy

1. **Branch-Local Eligibility**: Confirm `specs/<flow_id>/spec.md` is `state: completed` (or all tasks in `tasks/*.md` are `completed`/`closed`/`deferred`/`skipped` and verified on the current branch). Archival never requires waiting for a remote PR merge.
2. **Tracking Policy (`shared` vs. `local-only` Stealth Mode)**:
   - Inspect `.agents/bundles/index.md` (`tracking_mode: shared | local-only`).
   - Under `shared` mode, stage the updated `.agents/` files and deleted `specs/<flow_id>/` directory into one atomic `chore(archive): contract <flow_id> into knowledge bundle` commit.
   - Under `local-only` stealth mode (`.agents/` in `.git/info/exclude`), apply the contraction on disk without staging `.agents/` in Git.

## Mandatory Pre-Deletion Knowledge & Skill Synthesis

Never delete `.agents/bundles/specs/<flow_id>/` before synthesizing its durable engineering knowledge:

1. **Audit All Spec Artifacts**: Read `specs/<flow_id>/spec.md`, all `tasks/*.md` (`## Notes & Discoveries`), `learnings.md`, and promoted `research/*.md`.
2. **Execute the `/flow:learn` Synthesis Pass ([`learn.md`](learn.md))**:
   - Promote durable insights into `.agents/bundles/knowledge/` across all applicable namespaces:
     1. `knowledge/domains/<domain>.md` (domain model, glossary terms, invariants)
     2. `knowledge/architecture/<area>.md` (subsystem boundaries, deep-module seams, `5–12` node architecture diagrams)
     3. `knowledge/patterns/<topic>.md` (reusable idioms with `path/to/file::Symbol` anchors in `sources:`)
     4. `knowledge/testing/<topic>.md` & `knowledge/workflow.md` (verification recipes, public-seam TDD rules)
     5. `knowledge/gotchas/<area>.md` & `knowledge/decisions/adr-NNN-<slug>.md` (edge cases, runtime traps, ADRs)
   - Synchronize any affected project-local `.agents/skills/<domain>/` and `.agents/skills/review-<domain>/` (`checklist.md`, `false-positive-suppressions.md`) and `.agents/skills/index.md`.
   - Rewrite updated chapters in place in present tense with `OKF v0.2` frontmatter (`sources: [{ id, resource, title }]` + `[^id]` footnotes, `verified: [{ by, at, commit }]`, and bounded `<= 40`-line `<!-- truth: start -->` blocks), pruning chronological sediment and cache-vs-environment duplication.

## Strict Contraction Write Order

Always execute contraction writes in this exact sequence so no knowledge is ever lost on interruption:

1. **Step 1 — Write Knowledge & Skill Updates First**: Apply all updates to `.agents/bundles/knowledge/**`, `.agents/skills/**`, `knowledge/index.md`, and `.agents/bundles/index.md`.
2. **Step 2 — Prepend Audit Entry to `log.md` Second**: Prepend an ISO-dated `archive` entry to `.agents/bundles/log.md` summarizing the contracted flow (`flow_id`), commit range (`base_commit..head_commit`), and updated knowledge/skill paths.
3. **Step 3 — Delete Completed Spec Directory Last**: Remove `.agents/bundles/specs/<flow_id>/` and update `.agents/bundles/specs/index.md` (if present).
4. **Step 4 — Post-Archive Verification**: Verify that all relative Markdown links in `.agents/bundles/index.md`, `knowledge/index.md`, and `.agents/skills/index.md` resolve on disk and no dangling references to `specs/<flow_id>/` remain.

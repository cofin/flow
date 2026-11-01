# Flow Archive (`/flow:archive`)

Contract a completed flow (`state: completed`) by synthesizing its durable discoveries, architecture boundaries, domain invariants, patterns, testing recipes, and gotchas into `.agents/bundles/knowledge/**` and `.agents/skills/**`, logging the contraction in `.agents/bundles/log.md`, and removing the completed `.agents/bundles/specs/<flow_id>/` directory.

## Mandatory Pre-Deletion Knowledge & Skill Contraction

Never delete `.agents/bundles/specs/<flow_id>/` before synthesizing its durable engineering knowledge:

1. **Audit All Spec Artifacts**: Read `specs/<flow_id>/spec.md`, all `tasks/*.md` (`## Notes & Discoveries`), `learnings.md`, and promoted `research/*.md`.
2. **Execute the `/flow:learn` Synthesis Pass ([`learn.md`](learn.md))**:
   - Promote durable insights into `.agents/bundles/knowledge/` across all applicable namespaces:
     - `knowledge/domains/<domain>.md` (domain model, vocabulary, invariants)
     - `knowledge/architecture/<area>.md` (subsystem boundaries, public seams, dataflow)
     - `knowledge/patterns/<topic>.md` (reusable idioms with `path/to/file::Symbol` anchors in `sources:`)
     - `knowledge/testing/<topic>.md` & `knowledge/workflow.md` (verification recipes, SUT rules)
     - `knowledge/gotchas/<area>.md` & `knowledge/decisions/adr-NNN-<slug>.md` (edge cases, runtime traps, ADRs)
   - Synchronize any affected project-local `.agents/skills/<domain>/` and `.agents/skills/review-<domain>/` (`checklist.md`, `false-positive-suppressions.md`) and `.agents/skills/index.md`.
   - Rewrite updated chapters in place in present tense with `OKF v0.2` frontmatter (`sources: [{ id, resource, title }]` + `[^id]` footnotes and `verified: [{ by, at, commit }]`).

## Contraction & Cleanup Procedure

1. **Verify Eligibility**: Confirm `specs/<flow_id>/spec.md` is `state: completed` (or all tasks in `tasks/*.md` are `completed`/`closed`/`deferred`/`skipped` and verified on the current branch).
2. **Write Knowledge & Skill Updates First**: Apply all updates to `.agents/bundles/knowledge/**`, `.agents/skills/**`, `knowledge/index.md`, and `.agents/bundles/index.md`.
3. **Append Audit Entry to `log.md`**: Prepend an ISO-dated `archive` entry to `.agents/bundles/log.md` summarizing the contracted flow, commit range, and updated knowledge chapters.
4. **Delete Completed Spec Directory Last**: Remove `.agents/bundles/specs/<flow_id>/` and update `.agents/bundles/specs/index.md` (if present).
5. **Verify Links & Commit** (when `.agents/` is tracked under `shared` policy): Verify all Markdown links in `.agents/bundles/index.md` and `knowledge/index.md` resolve on disk, and create one `chore(archive): contract <flow_id> into knowledge bundle` commit.

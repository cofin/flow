# Flow Archive (`/flow:archive`)

Archive a completed single-chapter or multi-chapter flow (`state: completed`).
First verify that durable discoveries, architecture boundaries, domain invariants, patterns, testing recipes, and gotchas from every chapter are captured in `.agents/bundles/knowledge/**` and `.agents/skills/**`.
Then log the archive in `.agents/bundles/log.md` and remove `.agents/bundles/specs/<flow_id>/`.

## Eligibility, Completion Check & Tracking Policy

1. **Completion Check**: Run `/flow:validate` on `<flow_id>` (`--require-completed`) before touching `specs/<flow_id>/`.
   - Confirm `specs/<flow_id>/spec.md` is `state: completed` and zero chapters or tasks remain `planned`, `active`, `pending`, `open`, `in_progress`, or `blocked`.
   - Confirm any `deferred` item carries `deferred_by: "user"` and `deferred_reason`.
   - Confirm every completed task commit SHA modified at least one path in `files:` or `tests:`, and every completed chapter carries a valid `last_reviewed_commit` on the current branch.
   - Archival is branch-local and never waits for a remote PR merge (`hooks/pre-tool-guard.{sh,ps1}` blocks premature `rm` of incomplete spec directories).
2. **Tracking Policy & Worktree Routing (`shared` vs. `local-only` Stealth Mode)**:
   - Inspect `.agents/bundles/index.md` (`tracking_mode: shared | local-only`) and `<hook_context>` worktree routing.
   - Under `shared` mode, stage the updated `.agents/` files and deleted `specs/<flow_id>/` directory into one signed `chore(archive): archive <flow_id> into knowledge bundle` commit.
   - Under `local-only` stealth mode (`.agents/` in `.git/info/exclude`), update knowledge and remove `specs/<flow_id>/` inside the primary checkout's `$MAIN_WORKTREE/.agents/` bundle without staging `.agents/` in Git.

## Pre-Deletion Knowledge & Skill Capture

Never delete `.agents/bundles/specs/<flow_id>/` before capturing its durable engineering knowledge:

1. **Audit All Spec & Chapter Artifacts**: Inspect `specs/<flow_id>/spec.md`, `chapters/<ch_id>/spec.md` (when `has_chapters: true`), all `tasks/*.md` (`## Notes & Discoveries`), and promoted `research/*.md`. Chapter closeout handles most updates; `/flow:archive` performs the final cross-chapter pass.
2. **Run Parallel Domain Synthesis ([`learn.md`](learn.md))**:
   - When updating `>= 2` domains, fan out **1 isolated synthesis subagent per domain** (`type_name="self"` on Google Antigravity) across:
     1. `knowledge/domains/<domain>.md` (domain model, glossary terms, invariants)
     2. `knowledge/architecture/<area>.md` (subsystem boundaries, deep module interfaces, `5–12` node architecture diagrams)
     3. `knowledge/patterns/<topic>.md` (reusable idioms with `path/to/file::Symbol` anchors in `sources:`)
     4. `knowledge/testing/<topic>.md` & `knowledge/workflow.md` (verification recipes, public interface TDD rules)
     5. `knowledge/gotchas/<area>.md` & `knowledge/decisions/adr-NNN-<slug>.md` (edge cases, runtime traps, ADRs)
   - Update affected `.agents/skills/<domain>/`, `.agents/skills/review-<domain>/` (`checklist.md`, `false-positive-suppressions.md`), and `.agents/skills/index.md`.
   - Rewrite updated chapters in place in present tense with `OKF v0.2` frontmatter (`status: stable`, `sources:` + `[^id]:` footnotes, `verified: [{ by, at, commit }]`, `<= 40`-line `<!-- truth: start -->` truth blocks, zero standalone `---` body rules).

## Archive Write Order

Always execute archive writes in this exact sequence so no knowledge is lost on interruption:

1. **Write Knowledge & Skill Updates First**: Apply all updates to `.agents/bundles/knowledge/**`, `.agents/skills/**`, frontmatter-free `knowledge/index.md` / `knowledge/<ns>/index.md`, and root `.agents/bundles/index.md`.
2. **Prepend Audit Entry to `log.md` Second**: Prepend an ISO-dated `archive` entry to `.agents/bundles/log.md` listing `flow_id`, chapter count, commit range (`base_commit..head_commit`), and updated knowledge/skill paths.
3. **Delete Completed Spec Directory Last**: Remove `.agents/bundles/specs/<flow_id>/` (including `chapters/` and promoted `research/`) and update frontmatter-free `.agents/bundles/specs/index.md`.
4. **Post-Archive Verification**: Verify that all relative Markdown links in `.agents/bundles/index.md`, `knowledge/index.md`, `specs/index.md`, and `.agents/skills/index.md` resolve on disk and no dangling references to `specs/<flow_id>/` remain.

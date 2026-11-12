# Flow Archive (`/flow:archive`)

Contract a completed single-chapter or multi-chapter flow (`state: completed`) by verifying that all durable discoveries, architecture boundaries, domain invariants, patterns, testing recipes, and gotchas across every chapter have been synthesized into `.agents/bundles/knowledge/**` and `.agents/skills/**`, logging the contraction in `.agents/bundles/log.md`, and removing the completed `.agents/bundles/specs/<flow_id>/` directory.

## Branch-Local Eligibility, Anti-Skip Gate, & Worktree Tracking Policy

1. **Deterministic Anti-Skip & Completion Eligibility**: Run `/flow:validate` on `<flow_id>` (`--require-completed`) before touching `specs/<flow_id>/`: confirm `specs/<flow_id>/spec.md` is `state: completed`, zero chapters or tasks remain `planned`/`active`/`pending`/`open`/`in_progress`/`blocked`, any `deferred` item carries `deferred_by: "user"` + `deferred_reason`, every completed task commit SHA modified at least one path in `files:` or `tests:`, and every completed chapter carries a valid `last_reviewed_commit` on the current branch. Archival never requires waiting for a remote PR merge (`hooks/pre-tool-guard.{sh,ps1}` blocks premature `rm` of incomplete spec directories).
2. **Tracking Policy & Linked Git Worktree Routing (`shared` vs. `local-only` Stealth Mode)**:
   - Inspect `.agents/bundles/index.md` (`tracking_mode: shared | local-only`) and `<hook_context>` worktree routing.
   - Under `shared` mode, stage the updated `.agents/` files and deleted `specs/<flow_id>/` directory in the active checkout/worktree into one atomic signed `chore(archive): contract <flow_id> into knowledge bundle` commit.
   - Under `local-only` stealth mode (`.agents/` in `.git/info/exclude`), apply the contraction and `specs/<flow_id>/` removal directly inside the primary checkout's `$MAIN_WORKTREE/.agents/` bundle (which linked worktrees symlink to) without staging `.agents/` in Git.

## Subagent-Sharded Pre-Deletion Knowledge & Skill Synthesis

Never delete `.agents/bundles/specs/<flow_id>/` before synthesizing its durable engineering knowledge:

1. **Audit All Spec & Chapter Artifacts**: Inspect `specs/<flow_id>/spec.md`, `chapters/<ch_id>/spec.md` (when `has_chapters: true`), all `tasks/*.md` (`## Notes & Discoveries`), and promoted `research/*.md`. (Most chapter-level synthesis already landed during each chapter's closeout sync; `/flow:archive` performs the final cross-chapter synthesis and cleanup.)
2. **Execute the Subagent-Sharded `/flow:learn` Synthesis Pass ([`learn.md`](learn.md))**:
   - When synthesizing across `>= 2` domains, fan out **1 isolated synthesis subagent per domain** (`type_name="self"` on Google Antigravity) across:
     1. `knowledge/domains/<domain>.md` (domain model, glossary terms, invariants)
     2. `knowledge/architecture/<area>.md` (subsystem boundaries, deep-module seams, `5–12` node architecture diagrams)
     3. `knowledge/patterns/<topic>.md` (reusable idioms with `path/to/file::Symbol` anchors in `sources:`)
     4. `knowledge/testing/<topic>.md` & `knowledge/workflow.md` (verification recipes, public-seam TDD rules)
     5. `knowledge/gotchas/<area>.md` & `knowledge/decisions/adr-NNN-<slug>.md` (edge cases, runtime traps, ADRs)
   - Synchronize any affected project-local `.agents/skills/<domain>/` and `.agents/skills/review-<domain>/` (`checklist.md`, `false-positive-suppressions.md`) and `.agents/skills/index.md`.
   - Rewrite updated chapters in place in present tense with `OKF v0.2` frontmatter (`status: stable`, `sources: [{ id, resource, title }]` + `[^id]:` footnotes, `verified: [{ by, at, commit }]`, bounded `<= 40`-line `<!-- truth: start -->` blocks, and zero standalone `---` body rules), pruning chronological sediment and cache-vs-environment duplication.

## Strict Contraction Write Order

Always execute contraction writes in this exact sequence so no knowledge is ever lost on interruption:

1. **Step 1 — Write Knowledge & Skill Updates First**: Apply all updates to `.agents/bundles/knowledge/**`, `.agents/skills/**`, frontmatter-free `knowledge/index.md` / `knowledge/<ns>/index.md`, and root `.agents/bundles/index.md`.
2. **Step 2 — Prepend Audit Entry to `log.md` Second**: Prepend an ISO-dated `archive` entry to `.agents/bundles/log.md` summarizing the contracted flow (`flow_id`), chapter count, commit range (`base_commit..head_commit`), and updated knowledge/skill paths.
3. **Step 3 — Delete Completed Spec Directory Last**: Remove `.agents/bundles/specs/<flow_id>/` (including `chapters/` and promoted `research/`) and update frontmatter-free `.agents/bundles/specs/index.md`.
4. **Step 4 — Post-Archive Verification**: Verify that all relative Markdown links in `.agents/bundles/index.md`, `knowledge/index.md`, `specs/index.md`, and `.agents/skills/index.md` resolve on disk and no dangling references to `specs/<flow_id>/` remain.

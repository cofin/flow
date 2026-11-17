# Flow Status (`/flow:status`)

Read-only status inspection across root `.agents/bundles/specs/*/spec.md`, `chapters/index.md`, `chapters/<ch_id>/spec.md`, and `tasks/*.md`.
It reconstructs full-plan chapter progress, active chapter task state, documentation/OKF progress, and review stamps from Markdown and Git history ([`state.md`](state.md)) without mutating files.

<!-- flow-status-contract: start -->
```yaml
operation: status
writes: none
ready_order: [priority, created_at, id]
```
<!-- flow-status-contract: end -->

## Workflow

1. **Resolve Bundle Root & Git State**: Read `.agents/setup-state.json` (default `.agents/bundles/`) and inspect `git status --short -b` and `git log -n 5 --oneline`.
2. **Scan Root Specs, Chapters, & Task Worksheets**:
   - Read every `.agents/bundles/specs/<flow_id>/spec.md`.
   - When `has_chapters: true` (or `chapters/` exists), read `chapters/index.md`, each `chapters/<ch_id>/spec.md`, and the active chapter's `tasks/*.md` frontmatter.
   - Compute chapter progress (`k/N chapters completed`, `current_chapter`, remaining chapters tagged `[empirical_dependent]` where `planning_status: empirical_dependent`, `last_reviewed_chapter`, and `last_reviewed_commit`).
   - Compute task counts (`completed`/`closed`, `in_progress`, `pending`/`open`, `blocked`, `deferred`/`skipped`) and `[k/N files documented]` from `## 3. Documentation & OKF Knowledge Plan`.
   - Check for drift across `tasks/*.md` frontmatter (`state`, `commit`), owning `spec.md` checklist markers (`[ ]`, `[~]`, `[x] [<sha>]`, `[!]`, `[-]`), `chapters/index.md`, `chapters/ch*/`, missing `last_reviewed_commit` stamps, and `git log`.
3. **Report Status Summary & Next Action**:
   - Present a scannable table (`Flow ID | State | Chapters (k/N) | Active Chapter & Task Progress | Docs [k/N] | Last Reviewed | Remaining Plan / Blockers`).
   - Example: `Chapters: 2/6 completed | Active: ch03-session-store [1/4 tasks] | Remaining: ch04, ch05 [empirical_dependent], ch06`.
   - Recommend the next command: `/flow:implement <flow_id>`, `/flow:revise <flow_id> <chapter_id>`, `/flow:review <flow_id> <chapter_id>`, `/flow:learn sync` to sync drift, or `/flow:finish <flow_id>`.

# Flow Status (`/flow:status`)

Read-only status inspection across root `.agents/bundles/specs/*/spec.md`, `chapters/index.md`, `chapters/<ch_id>/spec.md`, and `tasks/*.md`. Reconstructs full-plan chapter progress, active chapter task state, documentation/OKF progress, and review stamps directly from Markdown and Git history ([`state.md`](state.md)) without mutating any files.

<!-- flow-status-contract: start -->
```yaml
operation: status
writes: none
ready_order: [priority, created_at, id]
```
<!-- flow-status-contract: end -->

## Workflow

1. **Resolve Bundle Root & Git State**: Read `.agents/setup-state.json` (default `.agents/bundles/`) and inspect `git status --short -b` and `git log -n 5 --oneline`.
2. **Scan Root Specs, Chapters, & Task Blueprints**:
   - Read every `.agents/bundles/specs/<flow_id>/spec.md`. When `has_chapters: true` (or `chapters/` exists), read `chapters/index.md`, each `chapters/<ch_id>/spec.md`, and the active chapter's `tasks/*.md` frontmatter (plus `tasks/*.md` on single-chapter specs).
   - Compute chapter progress (`k/N chapters completed`, `current_chapter`, remaining chapters annotated with `[empirical_dependent]` where `planning_status: empirical_dependent`, `last_reviewed_chapter`, and `last_reviewed_commit`), task counts (`completed`/`closed`, `in_progress`, `pending`/`open`, `blocked`, `deferred`/`skipped`), and `[k/N files documented]` from `## 3. Documentation & OKF Knowledge Plan`.
   - Detect any drift across `tasks/*.md` frontmatter (`state`, `commit`), owning `spec.md` checklist markers (`[ ]`, `[~]`, `[x] [<sha>]`, `[!]`, `[-]`), `chapters/index.md` vs. `chapters/ch*/` directories, completed chapters missing a fresh `last_reviewed_commit`, and `git log`.
3. **Report Full-Plan Dashboard & Next Action Recommendation**:
   - Present a scannable status summary (`Flow ID | State | Chapters (k/N) | Active Chapter & Task Progress | Docs [k/N] | Last Reviewed | Remaining Plan / Blockers`), e.g. `Chapters: 2/6 completed | Active: ch03-session-store [1/4 tasks] | Remaining: ch04, ch05 [empirical_dependent], ch06`.
   - Recommend the exact next command (`/flow:implement <flow_id>`, `/flow:revise <flow_id> <chapter_id>` for `blocked` or `empirical_dependent` chapters, `/flow:review <flow_id> <chapter_id>` if a chapter awaits review stamp, `/flow:learn sync` to reconcile drift, or `/flow:finish <flow_id>`).

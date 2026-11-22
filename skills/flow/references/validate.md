# Flow Validate (`/flow:validate`)

Validate `.agents/bundles/`, `.agents/skills/`, `.agents/agents/`, and single-chapter or multi-chapter specs against `OKF v0.2`, present-tense hygiene, and the Flow state contract ([`state.md`](state.md)).

## Validation Checklist

### 1. Bundle Root, Policy & Reserved Files

- `.agents/bundles/index.md` exists and declares `okf_version: "0.2"` and `bundle:`.
- `.agents/bundles/log.md`, `product/product.md`, `product/product-guidelines.md`, `product/tech-stack.md`, `knowledge/index.md`, and `knowledge/workflow.md` exist.
- Subdirectory `index.md` files (`product/index.md`, `knowledge/index.md`, `knowledge/<ns>/index.md`, `research/index.md`, `specs/index.md`, `specs/<flow_id>/chapters/index.md`) and `log.md` carry **zero YAML frontmatter**.

### 2. OKF Frontmatter & Current-State Hygiene

- Every non-reserved `.md` file under `.agents/bundles/` begins with YAML frontmatter containing non-empty `type:`, `title:`, and `description:`.
- Document maturity uses `status: draft | stable | deprecated`; workflow execution state uses `state:`.
- When `planning_quality` is set on `spec.md`, it is `standard` or `degraded` (and `degraded` requires a non-empty `planning_degraded_reason`).
- `tags:` holds `1-8` lowercase hyphenated tags free of state or status words.
- Every `product/**`, `knowledge/**`, and `spec.md` file contains a `<= 40`-line `<!-- truth: start --> ... <!-- truth: end -->` truth block.
- Knowledge chapters (`knowledge/**`) and specs (`spec.md`) carry `sources: [{ id, resource, title }]` with matching `[^id]:` body footnotes whose local paths exist on disk.
- Bundle Markdown bodies (outside fenced code blocks) contain zero standalone `---` horizontal rules, zero `Revision History` / `Changelog` / `Change History` headings, and zero struck-through checklist remnants (`- [ ] ~~...~~`).

### 3. Project Skills, Subagents & Worktrees

- Every `.agents/skills/<name>/SKILL.md` is `< 24,000` bytes (`<= 200` lines recommended), starts its `description:` with `"Use when "` (`<= 500` chars), and is indexed in `.agents/skills/index.md`.
- Every `.agents/agents/<name>.md` uses YAML list `disallowedTools` (when read-only), `model: inherit`, `mainAgent: false`, `subagent: true`, `commandExecutionPolicy: sandbox`, and top-level H1 (`# `) headings (`# Role & Identity`, `# Responsibilities`, `# Verification & Constraints`, `# Output Contract`).
- In linked `git worktree` checkouts, `.venv` and `node_modules` symlinks (when present in the primary checkout) are unbroken.
- `local-only` stealth mode checkouts resolve `.agents` to the primary checkout without split-brain local shadows.

### 4. Chapters, Completion & Worksheet Consistency

- When `specs/<flow_id>/chapters/` exists:
  - Frontmatter-free `chapters/index.md` exists, root `specs/<flow_id>/tasks/*.md` is absent, and chapter directories match `^ch\d{2}-[a-z0-9-]+$` (no upper cap on chapter count).
  - Disk `chapters/ch*/` directories, `chapters/index.md` links, and root `specs/<flow_id>/spec.md` `chapters:` + checklist entries match **1:1**.
  - Every `chapters/<ch_id>/spec.md` declares `planning_status: complete | empirical_dependent` (`empirical_dependent` requires non-empty `replan_trigger` and `depends_on_chapters`) and holds `1..N` `tasks/*.md` worksheets.
  - A `completed` chapter has zero open tasks, a valid hex `last_reviewed_commit` covering all chapter task commits, and `- [x]` in root `spec.md`.
  - Root `specs/<flow_id>/spec.md` cannot be `state: completed` while any chapter in `chapters:` is `planned`, `active`, or `blocked`; while chapters remain open, `current_chapter` points to an open chapter.
- Single-chapter `specs/<flow_id>/tasks/` holds `1..N` task worksheets, and a `completed` single-chapter `spec.md` cannot have `0` or open task worksheets.
- Any chapter or task in `state: deferred` or `state: skipped` declares `deferred_by: "user"` and a non-empty `deferred_reason`.
- Every `tasks/<id>-<slug>.md` (`type: Task`) contains all required headings for its `worksheet_format` (`full`: `## Objective & Scope Boundary`, `## Bounded Read Manifest`, `## Symbol & Signature Contracts`, `## Edge Cases & Error Semantics`, `## Public-Seam Test Blueprint`, `## Verification`, `## Acceptance Criteria`, `## Notes & Discoveries`; `compact`: `## Objective & Scope Boundary`, `## Bounded Read Manifest`, `## Contracts & Edge Cases`, `## Test Matrix`, `## Verification`, `## Acceptance Criteria`).
- Every task worksheet has valid `read_set` list and non-negative `estimated_loc` types and matches its owning `spec.md` checklist marker (`[ ]`, `[~]`, `[x] [<sha>]`, `[!]`, `[-]`).
- All relative Markdown links across `.agents/bundles/**/*.md` resolve to existing files on disk.

### 5. Brownfield Migration & Layout Check

- No legacy `.agents/specs/`, `.agents/tracks/`, `.agents/transactions/`, or copied global Flow lifecycle skills (`flow`, `flow-setup`, `flow-planning`, `flow-execution`, `flow-dispatch`, `flow-learn`, `flow-completion`, `flow-docs`, `okf`, `debloat`, `multi-harness-plugins`) exist inside `.agents/skills/`.

### 6. Commit Proof & Interactive Auto-Fix

- Verify that `[x] [<sha>]` task commits and `last_reviewed_commit` stamps satisfy `workflow_preferences.sha_tracking` (`strict` by default, with `git patch-id --stable` and rewritten-`HEAD` tolerance; `advisory` or `off` for squash-merge repos).
- Verify that every `completed` task commit touches at least one non-ignored declared path in `files:` or `tests:` (excluding paths matched by `git check-ignore`, such as `.agents/` under `local-only` stealth mode).
- When validation finds repairable drift (missing `index.md` links, out-of-sync checklist markers, frontmatter on subdirectory `index.md`, or unmigrated legacy directories), offer an interactive prompt to auto-fix via `/flow:learn sync` or `/flow:cleanup`.

# Flow Validate (`/flow:validate`)

Validate `.agents/bundles/`, `.agents/skills/`, `.agents/agents/`, and single-chapter or multi-chapter specifications against `OKF v0.2`, present-tense full-plan hygiene, and the Flow state contract ([`state.md`](state.md)).

## Validation Checklist

### 1. Bundle Root, Tracking Policy & Frontmatter-Free Reserved Files

- `.agents/bundles/index.md` exists and declares `okf_version: "0.2"` and `bundle:`.
- `.agents/bundles/log.md`, `product/product.md`, `product/product-guidelines.md`, `product/tech-stack.md`, `knowledge/index.md`, and `knowledge/workflow.md` exist.
- Subdirectory `index.md` files (`product/index.md`, `knowledge/index.md`, `knowledge/<ns>/index.md`, `research/index.md`, `specs/index.md`, `specs/<flow_id>/chapters/index.md`) and `log.md` carry **zero YAML frontmatter**.

### 2. OKF v0.2 Concept Frontmatter, Degraded-Plan Disclosure, & Zero-History Hygiene

- Every non-reserved `.md` file under `.agents/bundles/` begins with YAML frontmatter containing non-empty `type:`, `title:`, and `description:`.
- Document maturity uses `status: draft | stable | deprecated` only; workflow execution state uses `state:`; `planning_quality` (when set on `spec.md`) is `standard` or `degraded` (requiring a non-empty `planning_degraded_reason` whenever `degraded`); `tags:` holds `1–8` lowercase hyphenated tags free of state/status words.
- Every `product/**`, `knowledge/**`, and `spec.md` file contains a bounded `<= 40`-line `<!-- truth: start --> ... <!-- truth: end -->` block.
- Knowledge chapters (`knowledge/**`) and specifications (`spec.md`) carry `sources: [{ id, resource, title }]` with matching `[^id]:` body footnotes whose local repository paths exist on disk.
- Bundle Markdown bodies (outside fenced code blocks) contain **zero standalone `---` horizontal rules**, **zero `Revision History` / `Changelog` / `Change History` headings**, and **zero struck-through checklist remnants (`- [ ] ~~...~~`)**.

### 3. Project-Local Skills, Subagents, & Linked Git Worktrees

- Every `.agents/skills/<name>/SKILL.md` is `< 24,000` bytes (`<= 200` lines recommended), starts its `description:` with `"Use when "` (`<= 500` chars), and is indexed in `.agents/skills/index.md`.
- Every `.agents/agents/<name>.md` uses YAML list `disallowedTools` (when read-only), `model: inherit`, `mainAgent: false`, `subagent: true`, `commandExecutionPolicy: sandbox`, and top-level H1 (`# `) section headings (`# Role & Identity`, `# Responsibilities`, `# Verification & Constraints`, `# Output Contract`).
- In linked `git worktree` checkouts, `.venv` and `node_modules` symlinks (when present in the primary checkout) are unbroken, and `local-only` stealth checkouts resolve `.agents` cleanly to the primary checkout without split-brain local shadows.

### 4. Multi-Chapter, Anti-Skip, Review-Stamp, & Task Blueprint Consistency

- When `specs/<flow_id>/chapters/` exists:
  - Frontmatter-free `chapters/index.md` exists, root `specs/<flow_id>/tasks/*.md` is absent (never mix flat tasks with `chapters/`), and chapter directories match `^ch\d{2}-[a-z0-9-]+$` (with zero upper cap on chapter count).
  - Disk `chapters/ch*/` directories, `chapters/index.md` links, and root `specs/<flow_id>/spec.md` `chapters:` + checklist entries match **1:1**.
  - Every `chapters/<ch_id>/spec.md` declares `planning_status: complete | empirical_dependent` (requiring non-empty `replan_trigger` and `depends_on_chapters` when `empirical_dependent`), has `1–4` `tasks/*.md` blueprints, and when `state: completed` has zero open tasks and carries a valid hex `last_reviewed_commit` covering all chapter task commits (`- [x]` in root `spec.md`).
  - Root `specs/<flow_id>/spec.md` cannot be `state: completed` while any chapter in `chapters:` is `planned`, `active`, or `blocked`; while chapters remain open, `current_chapter` points to a non-`completed` chapter.
- Single-chapter `specs/<flow_id>/tasks/` contains `1–4` task blueprints (`> 4` tasks belong in `chapters/`), and a `completed` single-chapter `spec.md` cannot have `0` or open task worksheets.
- Any chapter or task in `state: deferred` or `state: skipped` declares `deferred_by: "user"` and a non-empty `deferred_reason`.
- Every `tasks/<id>-<slug>.md` (`type: Task`) contains all required blueprint headings for its `blueprint_tier` (`full`: `Objective & Scope Boundary`, `Bounded Read Manifest`, `Symbol & Signature Contracts`, `Edge Cases & Error Semantics`, `Public-Seam Test Blueprint`, `Verification`, `Acceptance Criteria`, `Notes & Discoveries`; `compact` for `estimated_loc <= 60` and `read_set <= 3`: `Objective & Scope Boundary`, `Bounded Read Manifest`, `Verification`, `Acceptance Criteria`), `read_set <= 6` files, `estimated_loc <= 250`, and matches its owning `spec.md` checklist marker (`[ ]`, `[~]`, `[x] [<sha>]`, `[!]`, `[-]`).
- All relative Markdown links across `.agents/bundles/**/*.md` resolve to existing files on disk.

### 5. Brownfield Migration & Anti-Sprawl Integrity

- No legacy `.agents/specs/`, `.agents/tracks/`, `.agents/transactions/`, `.agents/skills/flow-memory-keeper/`, or copied global Flow lifecycle skills (`flow`, `flow-setup`, `flow-planning`, `flow-execution`, `flow-learn`, `flow-completion`, `flow-docs`, `okf`, `debloat`, `multi-harness-plugins`) exist inside project-local `.agents/skills/`.

### 6. Git Commit Ownership Proof & Interactive Auto-Fix (`structured-choice-v1`)

- Verify that `[x] [<sha>]` task commits and `last_reviewed_commit` stamps in active specs satisfy the configured `workflow_preferences.sha_tracking` mode (`strict` by default, with `git patch-id --stable` and rewritten-`HEAD` tolerance; `advisory` or `off` for pure squash-merge repositories), and that every `completed` task commit touches at least one non-ignored declared path in `files:` or `tests:` (excluding paths matched by `git check-ignore`, such as `.agents/` under `local-only` stealth tracking).
- When validation finds repairable drift (missing `index.md` links, out-of-sync checklist markers, frontmatter on subdirectory `index.md`, or unmigrated legacy directories), present an interactive `structured-choice-v1` prompt offering to auto-fix the drift via `/flow:learn sync` or `/flow:cleanup`.

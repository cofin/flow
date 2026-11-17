# Flow Learn (`/flow:learn`, `refresh`, `sync`, `docs`)

`/flow:learn [scope]` aligns the codebase, Git history, `.agents/bundles/knowledge/**`, `.agents/bundles/product/**`, active or completed `.agents/bundles/specs/**`, user docs (`docs/`), and `.agents/skills/` plus `.agents/agents/`.

It combines four operations into one workflow that can run **at any point**:

- **`refresh`**: Cross-machine (`git pull`) and cross-harness catch-up.
- **`sync`**: Projecting `tasks/*.md`, `chapters/<ch_id>/spec.md`, and Git commits into `chapters/index.md`, root `spec.md` checklists, and `## 6. Current State & Remaining Plan Snapshot` in present tense.
- **`knowledge`**: Parallel OKF v0.2 knowledge updates across namespaces, domain glossary sharpening, and `.agents/skills/` updates.
- **`docs`**: Updating user-facing docs (`README.md`, `docs/`) to match current code via [`../../flow-docs/SKILL.md`](../../flow-docs/SKILL.md).

## Phase 1: Catch-Up & Drift Assessment

1. **Worktree Resolution & Spec/Task Sync (`refresh` + `sync`)**:
   - Inspect `<hook_context>`, `git status --short -b`, and `git log --oneline -n 20`.
   - In linked `git worktree` checkouts, verify `.venv` and `node_modules` symlinks (`uv run --no-sync`) and confirm `shared` (worktree `.agents/`) vs. `local-only` (`$MAIN_WORKTREE/.agents/`) routing.
   - When sandbox isolation blocks writes to `$MAIN_WORKTREE/.agents/`, use `/flow:learn sync --from-main` (seed `.agents/` from primary) or `/flow:learn sync --to-main` (merge new `specs/<flow_id>/` and index/log entries back without overwriting).
   - Compare every `.agents/bundles/specs/<flow_id>/spec.md`, `chapters/index.md`, `chapters/<ch_id>/spec.md`, and `tasks/*.md` against Git history and the working tree:
     - **Committed elsewhere, task still open**: If a commit in `HEAD` history implements the task or cites its ID while `state` is `pending`/`open`/`in_progress`, set `state: completed` and `commit: <sha>`.
     - **Task closed, commit missing**: If a `completed`/`closed` task points to a SHA absent from `HEAD` history, flag the conflict in the status summary instead of guessing.
     - **Stale cross-harness claims**: If `state: in_progress` (or `open` with non-null `claimed_by`) came from a prior session and no dirty files match `files:`/`tests:`, clear `claimed_by: null`, `claimed_at: null`, and reset `state: pending`.
     - **Present-Tense Checklist & Snapshot Sync**: Project `tasks/*.md` and `chapters/<ch_id>/spec.md` states into owning `spec.md` markers (`[ ]`, `[~]`, `[x] [<sha>]`, `[!]`, `[-]`), `chapters/index.md`, `current_chapter`, `current_task`, `[k/N files documented]`, and `## 6. Current State & Remaining Plan Snapshot`.
     - **Chapter Parity & Review Check**: Confirm 1:1 parity across `chapters/ch*/`, `chapters/index.md`, and root `spec.md`, and flag any completed chapter lacking a fresh `last_reviewed_commit` for `/flow:review`.
     - **Target Symbol Drift**: Check open `tasks/<id>-<slug>.md` and downstream chapters for drifted `files:` or `path/to/file::Symbol` anchors, and flag them for `/flow:revise <flow_id> [chapter_id]`.
     - **Mid-Flow Discovery Harvest**: Extract confirmed discoveries from `tasks/*.md` (`## Notes & Discoveries`) and promoted `research/*.md` into `knowledge/**`.
2. **Source-to-Knowledge Drift (`sources[].resource` Check)**:
   - Scan every `.agents/bundles/knowledge/**/*.md` chapter's `sources[].resource` paths and `path/to/file::Symbol` references.
   - Flag any knowledge chapter whose cited file was deleted, moved, or modified since its `verified[].commit` / `verified[].at` stamp, or whose `<!-- truth: start -->` claims contradict current code.
   - On multi-domain repos, fan out **1 read-only audit subagent per domain** (`run_workflow` `parallel()` with `type_name="self"` and `agents/researcher.md` on Antigravity; `@researcher` elsewhere) and check `git status --porcelain`.
3. **Manifest & Command Surface Drift**:
   - Compare `pyproject.toml`, `Cargo.toml`, `package.json`, `go.mod`, `Makefile`, and `.github/workflows/*.yml` against `.agents/bundles/product/{product,product-guidelines,tech-stack}.md` and `.agents/bundles/knowledge/workflow.md`.
   - Probe installed host binaries (`uv`, `python3`, `cargo`, `go`, `bun`, `pnpm`, `npm`, `make`, `just`, `pwsh`, `powershell`) so `knowledge/workflow.md` only lists commands that run.
   - When `.agents/setup-state.json` sets `knowledge_catalog.enabled: true` (or `catalog.yaml` exists), compare bundle files against `knowledge_catalog.last_synced_sha256` and report any catalog drift.

## Phase 2: Parallel Domain Knowledge Updates

1. **Fan Out Updates Across Domain Subagents**:
   - When updating `>= 2` knowledge domains, dispatch **1 isolated synthesis subagent per domain** (`type_name="self"` on Antigravity) so each chapter gets thorough present-tense updates:
     - **Domain Model & Invariants (`knowledge/domains/<domain>.md`)**: Sharpen fuzzy or overloaded nouns so code, tests, and specs share one clear term per concept, and document entity lifecycles and invariants.
     - **Architecture & Deep Modules (`knowledge/architecture/<area>.md`)**: Document deep modules, public interfaces, ports/adapters, dependency categories, and `5–12` node architecture diagrams.
     - **Idiomatic Patterns & Anti-Patterns (`knowledge/patterns/<topic>.md`)**: Document reusable patterns anchored to `path/to/file::Symbol`, paired with anti-patterns and `Reason:` notes.
     - **Verification & Testing (`knowledge/testing/<topic>.md` & `knowledge/workflow.md`)**: Document canonical test file mappings, local test doubles vs. external boundary mocks, real-code test rules, and fast inner-loop commands.
     - **Operational Gotchas & ADRs (`knowledge/gotchas/<area>.md` & `knowledge/decisions/adr-NNN-<slug>.md`)**: Document non-obvious footguns and apply the **ADR Filter** (*hard to reverse + surprising without context + genuine trade-off*).
2. **Enforce `OKF v0.2` & Current-State Rules ([`../../flow-docs/references/agent-context.md`](../../flow-docs/references/agent-context.md))**:
   - **Codebase Truth Only**: Delete claims whose files or symbols no longer exist.
   - **Single-Sentence Scope Test**: If a chapter needs more than one sentence in `description:` or exceeds `~200` lines, split it into sub-chapters under `knowledge/<namespace>/<subsystem>/<topic>.md` with a frontmatter-free `index.md`.
   - **Current State Only**: Rewrite drifted sections in place in present tense. Delete chronological narrative (`"added in flow X"`), `Revision History` sections, standalone `---` body rules, and filler prose.
   - **Normative Frontmatter**: Ensure every chapter carries valid YAML frontmatter (`type`, `title`, `description`, `status: stable`, `tags`, `generated`, `verified`, `sources`), a `<= 40`-line `<!-- truth: start -->` truth block, and `[^id]:` footnotes.

## Phase 3: Project Skills, Subagents & Docs Sync

1. **Engineering Domain Skills (`.agents/skills/<domain>/`)**:
   - Keep `SKILL.md` `<= 200` lines (`< 24,000` bytes) with a front-loaded `description:` pointer, a `<= 40`-line `<!-- truth: start -->` truth block, and reference files under `references/*.md`.
2. **Domain Review Skills (`.agents/skills/review-<domain>/`)**:
   - Maintain `SKILL.md`, `references/checklist.md` (`<PREFIX>-01..NN` rules), and `references/false-positive-suppressions.md` (`FP-<PREFIX>-01..NN` intentional patterns with `"DO NOT FLAG"` rationale).
3. **Skill Index & Paired Subagents (`.agents/skills/index.md` & `.agents/agents/`)**:
   - Update `.agents/skills/index.md` mapping `Domain | Prefix | Engineering Skill | Review Skill | Reviewer Subagent | Specialist Subagent | Knowledge Chapters`.
   - Sync paired subagents (`.agents/agents/<domain>-reviewer.md` and `.agents/agents/<domain>-specialist.md`) with H1 (`# `) headers, `mainAgent: false`, `subagent: true`, `model: inherit`, `commandExecutionPolicy: sandbox`, and YAML list `disallowedTools` on reviewers.
   - Remove any copied global Flow skills from `.agents/skills/`.
   - Verify root `AGENTS.md` (`<= 100` lines) links to `.agents/bundles/index.md` and `.agents/skills/index.md` while preserving `<!-- project-customization: start -->` blocks.

## Phase 4: Index Rebuild, Log & Status Summary

1. Rebuild root `.agents/bundles/index.md` (`okf_version: "0.2"`) and frontmatter-free subdirectory `index.md` files (`product/index.md`, `knowledge/index.md`, `knowledge/<ns>/index.md`, `research/index.md`, `specs/index.md`, `specs/<flow_id>/chapters/index.md`), verifying every relative link resolves.
2. Prepend an ISO-dated `synthesize` or `verify` entry to `.agents/bundles/log.md`.
3. Present a scannable **Status Summary**:
   - **Flow & Environment**: Active `flow_id`, `state`, `current_chapter` (`k/N chapters`), `plan_revision`, `branch @ HEAD`, and working tree status.
   - **Catch-Up & Sync**: Commits synced from other machines/sessions, stale claims released, checklists/roadmaps synced, and unreviewed completed chapters flagged.
   - **Knowledge, Docs & Skills**: Drifted sources repaired, `[k/N files documented]` status, new or split `knowledge/**` chapters, and updated `.agents/skills/` and `.agents/agents/`.
   - **Next Exact Step**: The exact chapter/task to run next (`/flow:implement <flow_id>`), review (`/flow:review <flow_id> <ch_id>`), or revise (`/flow:revise <flow_id> <ch_id>`).

# Flow Learn (`/flow:learn`, aliases `resynthesize`, `refresh`, `sync`, `docs`)

`/flow:learn [scope]` performs an anytime, comprehensive project-wide true-up across the codebase, Git history, `.agents/bundles/knowledge/**`, `.agents/bundles/product/**`, active/completed `.agents/bundles/specs/**`, and project-local `.agents/skills/` + `.agents/agents/`.

It combines four operations into a single coherent workflow that can run **at any point**:

- **`refresh`**: Cross-machine (`git pull`) and cross-harness session reorientation.
- **`sync` (`reconcile`)**: Projecting authoritative `tasks/*.md` state and Git commits into `spec.md` checklists and `## 5. Continuity Snapshot`.
- **`resynthesize`**: Deep OKF v0.2 knowledge rewrite across all namespaces, active domain glossary sharpening, and `.agents/skills/` synchronization.
- **`docs`**: Synchronizing user-facing documentation (`README.md`, `docs/`) with current codebase truth via [`../../flow-docs/SKILL.md`](../../flow-docs/SKILL.md).

## Phase 1: Cross-Machine/Harness Reorientation & Drift Assessment

1. **Cross-Machine & Cross-Harness Spec/Task Reorientation (`refresh` + `sync`)**:
   - Inspect `git status --short -b` and `git log --oneline -n 20`.
   - Compare every `.agents/bundles/specs/<flow_id>/spec.md` and its `tasks/*.md` against Git history and the working tree:
     - **Committed on another machine/session, task still open**: If a commit in `HEAD` history implements the task's acceptance criteria or references its task ID while task `state` is `pending`/`open`/`in_progress`, set `state: completed` and bind `commit: <sha>`.
     - **Task closed, commit missing**: If a `completed`/`closed` task points to a SHA absent from `HEAD` history, flag the conflict explicitly in the dashboard rather than guessing.
     - **Stale cross-harness claims**: If `state: in_progress` (or `open` with non-null `claimed_by`) was claimed by a prior harness or another machine's session and no dirty working-tree files match the task's `files:`/`tests:`, clear `claimed_by: null`, `claimed_at: null`, and reset `state: pending` (or re-bind to the current session).
     - **Checklist & Continuity Snapshot Sync (`reconcile`)**: Project authoritative `tasks/*.md` states into `spec.md` checklist markers (`open/pending -> [ ]`, `in_progress -> [~]`, `completed/closed -> [x] [<sha>]`, `blocked -> [!]`, `deferred/skipped -> [-]`), `current_task`, and `## 5. Continuity Snapshot`.
     - **Target Symbol Drift**: Check all open/pending `tasks/<id>-<slug>.md` worksheets for drifted target `files:` or `path/to/file::Symbol` anchors; flag any drifted worksheets for `/flow:revise <flow_id>`.
     - **Mid-Flow Discovery Harvest**: Extract confirmed discoveries from `tasks/*.md` (`## Notes & Discoveries`), `learnings.md`, and promoted `research/*.md` for immediate synthesis into `knowledge/**`.
2. **Source-to-Knowledge Drift (`sources[].resource` Intersection)**:
   - Scan every `.agents/bundles/knowledge/**/*.md` chapter's `sources[].resource` paths and `path/to/file::Symbol` references.
   - Flag any knowledge chapter whose cited file was deleted, moved, or modified since its `verified[].commit` / `verified[].at` stamp, or whose `<!-- truth: start -->` claims contradict current code.
   - When the `run_workflow` tool is available in the active harness (Google Antigravity) and the repository spans multiple domains, fan out `parallel(domains, audit_domain)` using `agent(type_name="researcher", schema=DOMAIN_DRIFT_SCHEMA, model="inherit")` to audit each domain concurrently.
3. **Manifest & Command Surface Drift**:
   - Compare `pyproject.toml`, `Cargo.toml`, `package.json`, `go.mod`, `Makefile`, and `.github/workflows/*.yml` against `.agents/bundles/product/{product,product-guidelines,tech-stack}.md` and `.agents/bundles/knowledge/workflow.md`.
   - Probe installed host binaries (`uv`, `python3`, `cargo`, `go`, `bun`, `pnpm`, `npm`, `make`, `just`, `pwsh`, `powershell`) so `knowledge/workflow.md` only documents commands that execute cleanly.

## Phase 2: Active Domain Modeling & OKF v0.2 Knowledge Resynthesis

1. **Synthesize Across All Knowledge Namespaces**:
   - **Domain Model, Ubiquitous Glossary, & Invariants (`knowledge/domains/<domain>.md`)**:
     - Challenge terms against live code: sharpen fuzzy or overloaded nouns so each domain concept has one unambiguous name across code, tests, and specs.
     - Document entity lifecycles, state transitions, and boundary edge cases.
   - **Architecture & Deep Module Seams (`knowledge/architecture/<area>.md`)**:
     - Document deep modules (small public interfaces hiding substantial implementation), public seams, ports/adapters, dependency categories, and dataflow.
   - **Idiomatic Code Patterns & Anti-Patterns (`knowledge/patterns/<topic>.md`)**:
     - Document reusable patterns anchored to `path/to/file::Symbol`, paired with explicit anti-patterns and `Reason:` explanations.
   - **Verification, Public-Seam TDD, & Testing Matrix (`knowledge/testing/<topic>.md` & `knowledge/workflow.md`)**:
     - Document canonical test file mappings, local-substitutable stand-ins vs. external boundary mocks, SUT integrity rules, and fast inner-loop commands.
   - **Operational Gotchas & ADRs (`knowledge/gotchas/<area>.md` & `knowledge/decisions/adr-NNN-<slug>.md`)**:
     - Document non-obvious footguns and runtime traps.
     - Apply the **ADR Filter**: create or update an ADR in `knowledge/decisions/adr-NNN-<slug>.md` only when a decision is (1) *hard to reverse*, (2) *surprising without context*, and (3) *a genuine trade-off* between viable alternatives.
2. **Enforce `OKF v0.2` Structure & Context Pruning ([`../../flow-docs/references/agent-context.md`](../../flow-docs/references/agent-context.md))**:
   - **Codebase Truth Only**: Delete claims whose files or symbols no longer exist.
   - **Single-Sentence Scope Test**: If a chapter requires more than one crisp sentence in `description:` or exceeds `~200` lines, split it into focused sub-chapters under a nested folder (`knowledge/<namespace>/<subsystem>/<topic>.md`). Never leave a flat catch-all `patterns.md`.
   - **Aggressive Pruning**: Rewrite drifted sections in place in present tense. Delete chronological sediment (`"added in flow X"`), duplicate cache lines that merely restate config files, AI puffery, and model-relative no-ops.
   - **Normative Frontmatter**: Ensure every chapter carries valid YAML frontmatter (`type`, `title`, `description`, `status: stable`, `tags`, `generated: { by, at }`, `verified: [{ by, at, commit }]`, `sources: [{ id, resource, title }]`), a bounded `<= 40`-line `<!-- truth: start -->` block, and `[^id]` footnotes matching `sources[].id`.

## Phase 3: Dynamic Project-Local Skill, Subagent, & Documentation Synchronization

1. **Engineering Domain Skills (`.agents/skills/<domain>/`)**:
   - Keep `SKILL.md` `<= 200` lines (`< 24,000` bytes) with a front-loaded `description:` context pointer, a bounded `<= 40`-line `<!-- truth: start -->` block, and deep reference files under `references/*.md`.
2. **Domain Review Capability Skills (`.agents/skills/review-<domain>/`)**:
   - Maintain `SKILL.md`, `references/checklist.md` (`<PREFIX>-01..NN` rules), and `references/false-positive-suppressions.md` (`FP-<PREFIX>-01..NN` intentional patterns with explicit `"DO NOT FLAG"` rationale).
3. **Skill Index & Paired Subagents (`.agents/skills/index.md` & `.agents/agents/`)**:
   - Update `.agents/skills/index.md` mapping `Domain | Prefix | Engineering Skill | Review Skill | Reviewer Subagent | Specialist Subagent | Knowledge Chapters`.
   - Synchronize paired subagents (`.agents/agents/<domain>-reviewer.md` and `.agents/agents/<domain>-specialist.md`) with H1 (`# `) section headers, `mainAgent: false`, `subagent: true`, `model: inherit`, and YAML list `disallowedTools`.
   - Remove any legacy `.agents/skills/flow-memory-keeper/` or copied global Flow skills.
   - Verify root `AGENTS.md` (`<= 100` lines) links to `.agents/bundles/index.md` and `.agents/skills/index.md` while preserving `<!-- project-customization: start -->` blocks.

## Phase 4: Index Rebuild, `log.md` Audit Entry & Reorientation Dashboard

1. Rebuild `.agents/bundles/index.md`, `product/index.md`, `knowledge/index.md`, `research/index.md`, and `specs/index.md`, verifying that every relative Markdown link resolves on disk.
2. Prepend an ISO-dated `synthesize` / `verify` entry to `.agents/bundles/log.md`.
3. Present a scannable **Project True-Up & Reorientation Dashboard**:
   - **Flow & Environment**: Active `flow_id`, lifecycle `state`, `plan_revision`, `branch @ HEAD`, and working tree status.
   - **Reorientation & Sync**: Commits reconciled from other machines/sessions, stale cross-harness claims released, and checklists synced.
   - **Knowledge & Skill Synthesis**: Drifted sources repaired, new/split `knowledge/**` chapters, and updated `.agents/skills/` & `.agents/agents/`.
   - **Next Exact Step**: The exact task worksheet to resume/claim next (`/flow:implement <flow_id>`) or worksheet flagged for `/flow:revise <flow_id>`.

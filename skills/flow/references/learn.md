# Flow Learn (`/flow:learn`)

`/flow:learn [scope]` (aliases: `resynthesize`, `refresh`, `sync`, `docs`) performs an anytime, comprehensive project-wide true-up across the codebase, Git history, `.agents/bundles/knowledge/**`, `.agents/bundles/product/**`, active/completed `.agents/bundles/specs/**`, and project-local `.agents/skills/` + `.agents/agents/`.

It can be executed **at any point**: mid-flow (to harvest discoveries and detect spec/code drift), post-flow, or standalone on a repository with no active flow.

## Phase 1: Codebase, Git & Spec Drift Assessment (True-Up Audit)

1. **Source-to-Knowledge Drift (`sources[].resource` Intersection)**:
   - Run `git status --short -b` and inspect recent commits (`git log --oneline -n 20`).
   - Scan every `.agents/bundles/knowledge/**/*.md` chapter's `sources[].resource` paths and `path/to/file::Symbol` references.
   - Flag any knowledge chapter whose cited file was deleted, moved, or modified since its `verified[].commit` / `verified[].at` stamp, or whose `<!-- truth: start -->` claims contradict current code.
   - When the `run_workflow` tool is available in the active harness (Google Antigravity) and the repository spans multiple domains, fan out `parallel(domains, audit_domain)` using `agent(type_name="researcher", schema=DOMAIN_DRIFT_SCHEMA, model="inherit")` to audit each domain concurrently.
2. **Manifest & Command Surface Drift**:
   - Compare `pyproject.toml`, `Cargo.toml`, `package.json`, `go.mod`, `Makefile`, and `.github/workflows/*.yml` against `.agents/bundles/product/{product,product-guidelines,tech-stack}.md` and `.agents/bundles/knowledge/workflow.md`.
   - Probe installed host binaries (`uv`, `python3`, `cargo`, `go`, `bun`, `pnpm`, `npm`, `make`, `just`) so `knowledge/workflow.md` only documents commands that execute cleanly.
3. **In-Flight & Completed Spec/Task True-Up**:
   - For every `.agents/bundles/specs/<flow_id>/spec.md`:
     - Reconcile `tasks/*.md` frontmatter (`state`, `commit`) and `spec.md` checklist markers (`[ ]`, `[~]`, `[x] [<sha>]`, `[!]`, `[-]`) against `git log` and working-tree reality per [`state.md`](state.md).
     - Check all open/pending `tasks/<id>-<slug>.md` worksheets for drifted target `files:` or `path/to/file::Symbol` anchors; flag any drifted worksheets for `/flow:revise <flow_id>`.
     - Harvest confirmed mid-flow findings from `tasks/*.md` (`## Notes & Discoveries`), `learnings.md`, and promoted `research/*.md` so durable insights are promoted immediately into `knowledge/**`.

## Phase 2: Comprehensive OKF v0.2 Knowledge Resynthesis (`.agents/bundles/knowledge/`)

1. **Synthesize Across All Five Knowledge Dimensions**:
   - **Domain Model & Invariants (`knowledge/domains/<domain>.md`)**: Ubiquitous terminology, entity lifecycles, and domain constraints.
   - **Architecture & Deep Module Seams (`knowledge/architecture/<area>.md`)**: Subsystem boundaries, narrow public interfaces, dataflow, and concurrency contracts.
   - **Idiomatic Code Patterns (`knowledge/patterns/<topic>.md`)**: Reusable patterns anchored to `path/to/file::Symbol`, paired with explicit anti-patterns.
   - **Verification & Testing Matrix (`knowledge/testing/<topic>.md` & `knowledge/workflow.md`)**: Fixture patterns, SUT integrity rules, and fast inner-loop commands.
   - **Operational Gotchas & ADRs (`knowledge/gotchas/<area>.md` & `knowledge/decisions/adr-NNN-<slug>.md`)**: Non-obvious footguns, runtime traps, and architectural decisions.
2. **Enforce `OKF v0.2` & Knowledge Catalog (`okf-bundle`) Quality**:
   - Rewrite drifted sections in place in present tense (zero historical changelog sediment inside concept docs).
   - Split any chapter exceeding `~200` lines or covering multiple topics into nested subdirectories.
   - Ensure every chapter carries valid YAML frontmatter (`type`, `title`, `description`, `status: stable`, `tags`, `generated: { by, at }`, `verified: [{ by, at, commit }]`, `sources: [{ id, resource, title }]`), a bounded `<= 40`-line `<!-- truth: start -->` block, and `[^id]` footnotes matching `sources[].id`.

## Phase 3: Dynamic Project-Local Skill & Subagent Synchronization (`.agents/skills/` & `.agents/agents/`)

1. **Engineering Domain Skills (`.agents/skills/<domain>/`)**:
   - Keep `SKILL.md` `<= 200` lines (`< 24,000` bytes) with a bounded `<= 40`-line `<!-- truth: start -->` block and deep reference files under `references/*.md`.
2. **Domain Review Capability Skills (`.agents/skills/review-<domain>/`)**:
   - Maintain `SKILL.md`, `references/checklist.md` (`<PREFIX>-01..NN` rules), and `references/false-positive-suppressions.md` (`FP-<PREFIX>-01..NN` intentional patterns with explicit `"DO NOT FLAG"` rationale).
3. **Skill Index & Paired Subagents (`.agents/skills/index.md` & `.agents/agents/`)**:
   - Update `.agents/skills/index.md` mapping `Domain | Prefix | Engineering Skill | Review Skill | Reviewer Subagent | Specialist Subagent | Knowledge Chapters`.
   - Synchronize paired subagents (`.agents/agents/<domain>-reviewer.md` and `.agents/agents/<domain>-specialist.md`) with H1 (`# `) section headers, `mainAgent: false`, `subagent: true`, `model: inherit`, and YAML list `disallowedTools`.
   - Remove any legacy `.agents/skills/flow-memory-keeper/` or copied global Flow skills.
   - Verify root `AGENTS.md` links to `.agents/bundles/index.md` and `.agents/skills/index.md` while preserving `<!-- project-customization: start -->` blocks.

## Phase 4: Index Rebuild, `log.md` Audit Entry & True-Up Report

1. Rebuild `.agents/bundles/index.md`, `product/index.md`, `knowledge/index.md`, `research/index.md`, and `specs/index.md`, verifying that every relative Markdown link resolves on disk.
2. Prepend an ISO-dated `synthesize` / `verify` entry to `.agents/bundles/log.md`.
3. Present a scannable **Project True-Up Summary** listing:
   - Drifted sources repaired and new `knowledge/**` chapters synthesized
   - `.agents/skills/` and `.agents/agents/` updated
   - Active `specs/<flow_id>/` task states reconciled and any worksheets flagged for `/flow:revise`

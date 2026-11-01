# Flow Validate (`/flow:validate`)

Run the 6-phase validator across `.agents/bundles/`, `.agents/skills/`, `.agents/agents/`, and active specifications against `OKF v0.2` and the Flow state contract ([`state.md`](state.md)).

## 6-Phase Validation Checklist

### Phase 1: Bundle Root, Tracking Policy & Reserved Files

- `.agents/bundles/index.md` exists and declares `okf_version: "0.2"` and `bundle:`.
- `.agents/bundles/log.md`, `product/product.md`, `product/product-guidelines.md`, `product/tech-stack.md`, `knowledge/index.md`, and `knowledge/workflow.md` exist.
- Reserved files (`index.md` and `log.md`) do not declare `type:`, `status:`, or `sources:` in frontmatter.

### Phase 2: OKF v0.2 Concept Frontmatter, Truth Blocks & Provenance

- Every non-reserved `.md` file under `.agents/bundles/` begins with YAML frontmatter containing non-empty `type:`, `title:`, and `description:`.
- Document lifecycle uses `status: draft | stable | deprecated`; workflow execution state uses `state:`.
- Every chapter under `product/**` and `knowledge/**` contains a bounded `<= 40`-line `<!-- truth: start --> ... <!-- truth: end -->` block.
- Knowledge chapters under `knowledge/**` carry `sources: [{ id, resource, title }]` with matching `[^id]:` body footnotes whose local repository paths exist on disk.

### Phase 3: Project-Local Skills & Subagents (`.agents/skills/` & `.agents/agents/`)

- Every `.agents/skills/<name>/SKILL.md` is `< 24,000` bytes (`<= 200` lines recommended), starts its `description:` with `"Use when..."`, and is indexed in `.agents/skills/index.md`.
- Every `.agents/agents/<name>.md` uses YAML list `disallowedTools` (when read-only), `model: inherit`, `mainAgent: false`, `subagent: true`, and top-level H1 (`# `) section headings (`# Role & Identity`, `# Responsibilities`, `# Verification & Constraints`, `# Output Contract`).

### Phase 4: Spec-to-Task Worksheet Consistency

- Every `specs/<flow_id>/spec.md` checklist entry has a matching `tasks/<id>-<slug>.md` worksheet whose `state`, `plan_revision`, and `commit` SHA agree with the checklist marker (`[ ]`, `[~]`, `[x] [<sha>]`, `[!]`, `[-]`).
- All relative Markdown links across `index.md`, `knowledge/**`, and `specs/**` resolve to existing files on disk.

### Phase 5: Brownfield Migration & Anti-Sprawl Integrity

- No legacy `.agents/specs/`, `.agents/tracks/`, `.agents/transactions/`, `.agents/skills/flow-memory-keeper/`, or copied global Flow lifecycle skills (`flow`, `flow-setup`, `flow-planning`, `flow-execution`, `flow-learn`, `flow-completion`, `flow-docs`, `okf`, `debloat`, `multi-harness-plugins`) exist inside project-local `.agents/skills/`.

### Phase 6: Git State Check & Interactive Auto-Fix (`structured-choice-v1`)

- Verify that every `[x] [<sha>]` task commit in active specs resolves via `git cat-file -t <sha>`.
- When validation finds repairable drift (missing `index.md` links, out-of-sync checklist markers, missing `<!-- truth: start -->` markers, or unmigrated legacy directories), present an interactive `structured-choice-v1` prompt offering to auto-fix the drift via `/flow:learn sync` or `/flow:cleanup`.

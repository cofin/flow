# Flow Validate (`/flow:validate`)

Validate `.agents/bundles/`, `.agents/skills/`, `.agents/agents/`, and active specifications against `OKF v0.2` and the Flow state contract ([`state.md`](state.md)).

## Validation Checks

1. **Bundle Root & Reserved Files**:
   - `.agents/bundles/index.md` exists and declares `okf_version: "0.2"`.
   - `.agents/bundles/log.md`, `product/product.md`, `product/tech-stack.md`, `knowledge/index.md`, and `knowledge/workflow.md` exist.
2. **OKF v0.2 Concept Frontmatter & Provenance**:
   - Every non-reserved `.md` file (`index.md` and `log.md` are reserved) begins with YAML frontmatter containing a non-empty `type:`.
   - Document lifecycle uses `status: draft | stable | deprecated`; workflow state uses `state:`.
   - Knowledge chapters under `knowledge/**` carry `sources: [{ id, resource, title }]` whose local repository paths exist on disk, and bounded `<= 40`-line `<!-- truth: start -->` blocks.
3. **Project-Local Skills & Subagents (`.agents/skills/` & `.agents/agents/`)**:
   - Every `.agents/skills/<name>/SKILL.md` is `< 24,000` bytes (`<= 200` lines recommended) and indexed in `.agents/skills/index.md`.
   - Every `.agents/agents/<name>.md` uses YAML list `disallowedTools` (when read-only), `model: inherit`, `mainAgent: false`, `subagent: true`, and top-level H1 (`# `) section headings.
   - No legacy `.agents/skills/flow-memory-keeper/` or copied global Flow skills exist in `.agents/skills/`.
4. **Spec & Task Worksheet Consistency**:
   - Every `specs/<flow_id>/spec.md` checklist entry has a matching `tasks/<id>-<slug>.md` worksheet whose `state` and `commit` SHA agree with the checklist marker (`[ ]`, `[~]`, `[x] [<sha>]`, `[!]`, `[-]`).
   - All relative Markdown links across `index.md`, `knowledge/**`, and `specs/**` resolve to existing files.

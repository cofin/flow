---
name: flow-setup
description: "Use when initializing Flow in a repo, configuring .agents, scaffolding OKF knowledge bundles, or creating first project context files."
disable-model-invocation: true
---

# Flow Setup

<!-- lifecycle-ownership: owner=flow-setup; operations=setup -->

## Trigger

Use for `setup` only.

## Workflow

1. **Repository & Stack Detection**: Detect language, framework, canonical commands (`test`, `lint`, `typecheck`), and existing Flow configuration.
2. **Scaffold Hierarchical OKF Layout**: Initialize `.agents/bundles/index.md` (with `okf_version: "0.2"`) and scoped subdirectories under `knowledge/`. Create `product/product.md`, `product/tech-stack.md`, `knowledge/workflow.md`, and `knowledge/patterns.md`.
3. **Project-Local Skills Option**: Ask user whether to scaffold project-tailored Flow skills into `.agents/skills/flow*`.
4. **Validation & State Write**: Verify bundle links and OKF frontmatter compliance, then write `.agents/setup-state.json` with `setup_status: complete`.

## Guardrails

- Preserve existing developer context; never overwrite custom blocks inside `<!-- project-customization: start -->`.
- Preserve Git history and tag immutability.

## Output

Return the resolved layout, generated bundle files, and planning handoff command (`/flow:plan`).

## Validation

Confirm OKF frontmatter validity, directory link integrity, and `.agents/setup-state.json` configuration.

## Example

For a new repository, run setup to detect the Python uv stack, scaffold `.agents/bundles/` with hierarchical chapters, and initialize the setup state.

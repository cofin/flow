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
3. **Standalone Project Skills Option**: Ask whether to install a standalone,
   project-local Flow dependency closure into `.agents/skills/`. This prompt
   defaults to skip and installation requires explicit opt-in. Treat the
   standalone copy as an alternative to the global plugin, not an overlay.
4. **Validation & State Write**: Verify bundle links and OKF frontmatter compliance, then write `.agents/setup-state.json` with `setup_status: complete`.

## Guardrails

- Preserve existing developer context; never overwrite custom blocks inside `<!-- project-customization: start -->`.
- Use the standalone installer for copy, update, conflict, and uninstall
  operations; never hand-copy or delete project skills.
- Preserve Git history and tag immutability.

## Output

Return the resolved layout, generated bundle files, and planning handoff command (`/flow:plan`).

## Validation

Confirm OKF frontmatter validity, directory link integrity, and
`.agents/setup-state.json` configuration. For a standalone install, also
confirm its contained dependency closure and exact managed-file hashes.

## Example

For a new repository, run setup to detect the Python uv stack, scaffold `.agents/bundles/` with hierarchical chapters, and initialize the setup state.

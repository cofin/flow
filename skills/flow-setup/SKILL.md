---
name: flow-setup
description: "Use when initializing Flow in a repo, configuring .agents, scaffolding OKF knowledge bundles, or creating first project context files."
---

# Flow Setup

Use this lifecycle skill for project initialization, installation checks, setup validation, and first context files.

## Workflow

1. Detect project root, existing `.agents/` state, and repo-native commands (setup, lint, test, typecheck, full verification).
2. Scaffold the OKF bundle: `.agents/bundles/index.md` (frontmatter `okf_version: "0.2"`), `.agents/bundles/log.md`, `product/` identity docs, and flat `knowledge/` chapters (workflow.md, patterns.md) from templates, each with a non-empty `type:` frontmatter key.
3. Capture repo-native commands in `knowledge/workflow.md` between `<!-- truth: start -->` and `<!-- truth: end -->` markers so hooks can inject them.
4. Ask the user whether `.agents/bundles/` should be tracked (shared team knowledge) or ignored (private planning), and apply their choice.
5. Re-run setup validation before handing off to planning.

## Guardrails

- Prefer `.git/info/exclude` for local-only ignores.
- Do not edit `.gitignore` unless the user wants shared repository policy.
- Keep setup idempotent; preserve existing user context files and merge rather than overwrite.
- The `.agents/` root is fixed; relocation of bundle directories happens only through `.agents/config.json` (`bundles_dir`, `knowledge_dir`).
- Do not create task databases or external tracker config; task state lives in bundle files.

## Validation

- Confirm `.agents/bundles/index.md` declares `okf_version`, `log.md` exists, and `product/product.md`, `knowledge/workflow.md`, and `knowledge/patterns.md` carry `type:` frontmatter.
- Confirm the session hook resolves context: the priming output lists the project purpose and invariants.
- Run repository validation commands documented in `knowledge/workflow.md` or hook context.

## References Index

- [Setup command details](../flow/references/setup.md)
- [Validate command details](../flow/references/validate.md)
- [Refresh command details](../flow/references/refresh.md)

## Example

User: "Use Flow to set up this repo."

Action: detect the repo root, scaffold `.agents/bundles/` with index, log, and knowledge chapters, record repo-native commands in workflow truths, validate the bundle, then hand off to `flow-planning` for the first flow.

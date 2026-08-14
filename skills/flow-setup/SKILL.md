---
name: flow-setup
description: "Use when initializing Flow in a repo, configuring .agents, scaffolding OKF knowledge bundles, or creating first project context files."
---

# Flow Setup

Use this lifecycle skill for project initialization, installation checks, setup validation, and first context files.

## Workflow

1. Detect project root, existing `.agents/` state, workspace environment, active harness, and repo-native commands. Configure hooks for the active harness only: the Antigravity IDE copies `hooks/hooks-agy.json` to `.agents/hooks.json` (or the `hooks_dir` override from `.agents/config.json`); the Antigravity CLI, Claude Code, Codex, and Cursor load hooks from the installed plugin/extension automatically.
2. Before any brownfield write, inventory every legacy and current authority with ordinary agent file tools and persist the approved source/destination mapping in `.agents/migration-inventory.json`. Record `last_successful_step` and an exact `resume_operation` after each boundary.
3. Scaffold the OKF bundle: `.agents/bundles/index.md` (frontmatter `okf_version: "0.2"`), `.agents/bundles/log.md`, `product/` identity docs, stable `knowledge/workflow.md` and `knowledge/patterns.md` defaults, and project-shaped nested knowledge such as `data-model/`, `app-design/`, `standards/`, or `domains/` when scope requires it. Every chapter has non-empty `type:` frontmatter. Install operational project skills only under `.agents/skills/`.
4. Capture repo-native commands in `knowledge/workflow.md` between `<!-- truth: start -->` and `<!-- truth: end -->` markers so hooks can inject them.
5. Ask the user whether `.agents/bundles/` should be tracked (shared team knowledge) or ignored (private planning), and apply their choice.
6. Keep source artifacts recoverable until approved cleanup, then run every migration and bundle postcondition before setting `setup_status: complete`. A second identical run makes no write and does not change plan identity.

## Guardrails

- Prefer `.git/info/exclude` for local-only ignores.
- Do not edit `.gitignore` unless the user wants shared repository policy.
- Keep setup idempotent; preserve existing user context files and merge rather than overwrite.
- The `.agents/` root is fixed; relocation of bundle directories happens only through `.agents/config.json` (`bundles_dir`, `knowledge_dir`).
- Do not create task databases or external tracker config; task state lives in bundle files.
- Never infer completion from a saved flag. Missing inventory, approval, destination, source/destination count, semantic mapping, or postcondition evidence keeps setup incomplete.
- Never resolve divergent project-skill copies automatically; stop for an explicit user choice. Destructive cleanup always requires fresh approval.
- Never flatten a knowledge tree. Preserve every scope-derived relative path and update its indexes and links when a root moves.

## Validation

- Confirm `.agents/bundles/index.md` declares `okf_version`, `log.md` exists, and `product/product.md`, `knowledge/workflow.md`, and `knowledge/patterns.md` carry `type:` frontmatter.
- Recursively validate every nested knowledge chapter plus its index entries and relative links.
- Confirm the session hook resolves context: the priming output lists the project purpose and invariants.
- Confirm migration postconditions pass, no duplicate authority remains, the report and setup-state resume fields agree, and `.agents/skills/` is the only operational project-skill root.
- Re-run setup against the same inputs and confirm the second pass produces no diff, `plan_revision` change, or `plan_commit` change.
- Run repository validation commands documented in `knowledge/workflow.md` or hook context.

## References Index

- [Setup command details](../flow/references/setup.md)
- [Validate command details](../flow/references/validate.md)
- [Refresh command details](../flow/references/refresh.md)

## Example

User: "Use Flow to set up this repo."

Action: detect the repo root, scaffold `.agents/bundles/` with index, log, and knowledge chapters, record repo-native commands in workflow truths, validate the bundle, then hand off to `flow-planning` for the first flow.

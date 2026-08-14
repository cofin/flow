---
name: flow-setup
description: "Use when initializing Flow in a repo, configuring .agents, scaffolding OKF knowledge bundles, or creating first project context files."
---

# Flow Setup

<!-- lifecycle-ownership: owner=flow-setup; operations=setup -->

## Trigger

Use for `setup` only. Setup's internal postcondition checks are setup phases;
they do not make this skill a second owner of `validate`.

## Workflow

1. Detect the repository, harness, canonical commands, and existing Flow roots.
2. Before a brownfield write, build `.agents/migration-inventory.json` with an
   approved source/destination mapping, `last_successful_step`, and exact
   `resume_operation`.
3. Scaffold `.agents/bundles/` and install operational skills only under
   `.agents/skills/`. Preserve project-shaped nested knowledge and every nested
   relative path, index, and link.
4. Record repository commands in `knowledge/workflow.md` truth markers and ask
   whether bundles are tracked or local-only.
5. Preserve sources until approved cleanup; then run migration and bundle
   postconditions before writing `setup_status: complete`. A second identical run
   makes no write or plan-identity change.

## Guardrails

- Merge user context; never overwrite it or flatten a knowledge tree.
- Divergent project-skill copies require an explicit user choice.
- Destructive cleanup requires fresh approval; never mutate repository tags.

## Output

Return the resolved layout, migration inventory/result, postcondition evidence,
and exact resume action or planning handoff.

## Validation

Recursively validate OKF frontmatter, nested knowledge/index links, inventory
counts and mappings, setup-state agreement, sole `.agents/skills/` authority,
hook context, and idempotence. Use the repository commands captured in
`knowledge/workflow.md`.

## Conditional References

- [Setup procedure](../flow/references/setup.md) — load for setup or migration.
- [State contract](../flow/references/state.md) — load before Flow state writes.
- [Interaction contract](../flow/references/interaction.md) — load before user choices.

## Example

For a brownfield repository, inventory first, preserve nested knowledge, apply
the approved mapping, prove postconditions and idempotence, then hand off to
`flow-planning`.

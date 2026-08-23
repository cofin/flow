# Flow Project Context

Flow is a skill-based toolkit for context-driven development. It has no `flow`
executable; invoke the Flow skill or a `/flow:*` command.

Planning and task state live under `.agents/bundles/specs/<flow_id>/`. Task
worksheets are the authority for task state and commits. Route lifecycle work
through [the Flow router](skills/flow/SKILL.md), and use
[the state contract](skills/flow/references/state.md) for every mutation.

Repository context starts at [.agents/bundles/index.md](.agents/bundles/index.md).
Canonical commands and conventions live in
[workflow.md](.agents/bundles/knowledge/workflow.md) and
[patterns.md](.agents/bundles/knowledge/patterns.md).

Execute one worksheet per invocation, preserve unrelated work, stage exact
paths, and commit locally only after the declared verification passes. Never
create or mutate tags. Pushes and hosted repository writes require fresh,
target-specific user permission.

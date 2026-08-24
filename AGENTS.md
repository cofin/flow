# Flow Project Context

Flow is a toolkit for context-driven development. It has no `flow`
executable; invoke the Flow skill or a `/flow:*` command.

Planning and task state live under `.agents/bundles/specs/<flow_id>/`. Task
worksheets are the authority for task state and commits. Route lifecycle work
through [the Flow router](skills/flow/SKILL.md), and use
[the state contract](skills/flow/references/state.md) for mutations.

Initialize with [the setup guide](skills/flow/references/setup.md), then use its
bundle index, `.agents/bundles/knowledge/workflow.md`, and
recursively relevant `.agents/bundles/knowledge/patterns/**/*.md` chapters.

Execute one worksheet per invocation, preserve unrelated work, stage exact
paths, and commit locally only after the declared verification passes. Never
create or mutate tags. Pushes and hosted repository writes require fresh,
target-specific user permission.

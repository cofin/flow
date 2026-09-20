# Flow Project Context

Flow has no `flow` executable; invoke the Flow skill or a `/flow:*` command.

Planning and task state live under `.agents/bundles/specs/<flow_id>/`. Task
worksheets are the authority for task state and commits. Route lifecycle work
through [the Flow router](skills/flow/SKILL.md), and use
[the state contract](skills/flow/references/state.md) for mutations.

Initialize with [the setup guide](skills/flow/references/setup.md), then use its
bundle index, `.agents/bundles/knowledge/workflow.md`, and
`.agents/bundles/knowledge/patterns/**/*.md` chapters.

Execute one worksheet per invocation, preserve unrelated work, stage exact
paths, and commit locally only after verification passes. Never mutate tags.
Pushes and remote writes require fresh permission. Minimize test churn: run
`make lint` and fast unit tests in inner loops; reserve full suites, cleanup,
and debloat for milestone gates (`checkpoint.phase`, `complete`).
Intermediate progress records `HEAD`; closing requires a clean functional commit.

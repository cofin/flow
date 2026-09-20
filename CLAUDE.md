# Flow for Claude Code

In `.agents/` repos, invoke the Flow skill or `/flow:*`.
Route requests through [the Flow router](skills/flow/SKILL.md).
Planning and task state live under `.agents/bundles/specs/<flow_id>/`;
task worksheets are authoritative. Apply mutations through
[the state contract](skills/flow/references/state.md).
Stage exact paths, never mutate tags, and require
fresh permission before pushes or remote writes.

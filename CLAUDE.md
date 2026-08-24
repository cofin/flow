# Flow for Claude Code

Flow is a skill, not a CLI. In repositories with `.agents/`, invoke the Flow
skill or a `/flow:*` command.

Route requests through [the Flow router](skills/flow/SKILL.md). Planning and
task state live under `.agents/bundles/specs/<flow_id>/`; task worksheets are
authoritative. Apply lifecycle mutations through
[the state contract](skills/flow/references/state.md).

Use `/flow:*` commands for lifecycle requests. Preserve unrelated work, stage
exact paths, never mutate tags, and require fresh user permission before pushes
or hosted repository writes.

# Confidence Tracking

How to track and update confidence as investigation progresses.

## Confidence Levels

| Level | Meaning | Action |
| ----- | ------- | ------ |
| `exploring` | Just started, no hypothesis yet | Gather initial evidence, form hypothesis |
| `low` | Have a hypothesis but weak evidence | Seek confirming/disconfirming evidence |
| `medium` | Evidence supports hypothesis but gaps remain | Fill specific gaps, check edge cases |
| `high` | Strong evidence, minor uncertainties | Verify the uncertainties aren't critical |
| `certain` | Conclusive evidence, ready to act | Synthesize findings and present |

## What to Track at Each Step

Record the following at every investigation step:

- **Current hypothesis** — one sentence stating what you believe is true
- **Evidence for** — specific findings that support the hypothesis
- **Evidence against** — specific findings that contradict or complicate the hypothesis
- **Unexplored areas** — what you haven't checked yet that could change the conclusion
- **Current confidence level and why** — the level plus a one-sentence justification

This tracking prevents circular investigation by making your current state explicit and searchable.

## Escalation Rule

If confidence has not increased after 3 investigation steps, stop and reassess:

1. **Is the hypothesis too broad?** Narrow it to a more specific claim that can be directly tested.
2. **Are you looking in the wrong place?** Try a different angle — different files, different execution path, different search terms.
3. **Do you need a different tool?** Consider whether `flow:tracer` (execution path tracing) or `flow:perspectives` (multi-angle analysis) would unstick the investigation.
4. **Is this genuinely unknowable with available information?** If so, say so explicitly — state what information would be needed to reach a conclusion and why it's unavailable.

## Completion Criteria

Investigation is complete when:

- Confidence is `high` or `certain`
- All `evidence against` items have been explained or incorporated into the hypothesis
- The hypothesis can be stated as a specific, actionable conclusion
- The unexplored areas have been evaluated: either checked, or explicitly ruled out as non-critical

Do not continue investigating once completion criteria are met. Synthesize and present.

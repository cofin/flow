---
name: flow-completion
description: "Use when reviewing, finishing, archiving, reverting, validating, documenting, or cleaning up Flow work after implementation or phase completion."
---

# Flow Completion

<!-- lifecycle-ownership: owner=flow-completion; operations=review,finish,archive,revert,docs,cleanup,validate -->

## Trigger

Use for `review|finish|archive|revert|docs|cleanup|validate`.

<!-- quality-completion-policy: start -->
```yaml
contract: quality-completion-v1
authority: skills/flow/references/review.md
finish_gates: [verification, code_review, quality_review, finish]
archive_gates: [archive_candidate, verification, code_review, quality_review, archive]
runtime_dependency: agent_file_tools_only
evaluator_module: forbidden
```
<!-- quality-completion-policy: end -->

## Workflow

1. Run fresh verification, correctness review, then mandatory read-only quality
   review on the exact candidate range. Route Critical/Important findings
   through revised remediation work and repeat every affected gate.
2. Finish only with exact-range evidence and individually valid post-review
   waivers. Checkpoint the last functional commit; never create an empty one.
3. Archive from a byte-identical disposable candidate: synthesize reusable
   notes into project-shaped knowledge, log once, then delete the tracked spec
   directory after recoverability and review checks.
4. Revert only the selected Flow scope. Docs, cleanup, and validate use their
   own procedure references; validate is owned here, while setup's internal
   postcondition check remains part of setup.

## Guardrails

- No completion/archive without fresh exact-range verification and both reviews.
- Quality review is read-only; waivers never replace dispatch.
- Preserve nested knowledge and unrelated changes; never leave transient
  extracted learnings or push automatically. Never create or mutate Git tags.

## Output

Return the exact range, verification and review results, remediation/waivers,
selected finish outcome, or archive manifest and contraction result.

## Validation

Confirm task metadata and spec views agree, required evidence is fresh, no
unwaived Critical/Important finding remains, knowledge is current-state prose,
and archive removes the reviewed spec directory only.

## Conditional References

- [Review](../flow/references/review.md)
- [Finish](../flow/references/finish.md)
- [Archive](../flow/references/archive.md)
- [Revert](../flow/references/revert.md)
- [Docs](../flow/references/docs.md)
- [Cleanup](../flow/references/cleanup.md)
- [Validate](../flow/references/validate.md)
- [State](../flow/references/state.md)
- [Interaction](../flow/references/interaction.md)
- [Git Notes](../../docs/git-notes.md) — load only for supplementary evidence.

## Example

For finish, verify the exact range, run correctness and quality review, resolve
blocking findings, then present the allowed local outcome.

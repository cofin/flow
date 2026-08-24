---
name: flow-completion
description: "Use when reviewing, finishing, archiving, reverting, validating, documenting, or cleaning up Flow work after implementation or phase completion."
disable-model-invocation: true
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

1. **Two-Axis Review (`/flow:review`)**: Run parallel reviewers evaluating Standards/Smells (Security, Performance, Debloat lenses) and Spec Conformance against `git diff <base>...HEAD`.
2. **Finish Flow (`/flow:finish`)**: Run full test verification suite and record single-paragraph ADRs in `knowledge/decisions/`.
3. **Archive Flow (`/flow:archive`)**: Synthesize discoveries into project-shaped knowledge, append one `log.md` entry, and delete the reviewed completed spec inventory through a journaled archive operation.
4. **Revert or Validate**: Revert designated changes or run repository validation checks.

## Guardrails

- Reviews are read-only; report concrete evidence with file/symbol references.
- Archive leaves a terminal journal outside the bundle and no resident archived spec.
- Preserve Git history. Never create or mutate Git tags.

## Output

Return the review assessment, verification evidence, ADR summaries, or archived flow manifest.

## Validation

Confirm test suites pass cleanly, no blocking review findings remain, and knowledge synthesis is complete.

## Example

For flow completion, run tests, review the diff against `main`, elevate reusable patterns to evidence-backed `knowledge/patterns/<topic>.md` chapters, and archive the spec directory.

<!-- project-customization: start -->
## Custom Completion Checks
<!-- project-customization: end -->

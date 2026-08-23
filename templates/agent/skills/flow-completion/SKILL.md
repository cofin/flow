---
name: flow-completion
description: "Project-tailored Flow completion skill. Use when reviewing, finishing, archiving, reverting, or validating completed flows with repo standards."
---

# Flow Completion (Project-Tailored)

<!-- lifecycle-ownership: owner=flow-completion; operations=review,finish,archive,revert,docs,cleanup,validate -->

## Trigger

Use for `review|finish|archive|revert|docs|cleanup|validate`.

## Two-Axis Review Protocol

Reviewers evaluate changes along two independent axes:

### Axis 1: Code Standards & Smells
- Evaluate diff against repository standards and the 12-point Fowler Code Smell Baseline (*Mysterious Name*, *Duplicated Code*, *Feature Envy*, *Primitive Obsession*, *Speculative Generality*, etc.).
- Run specialized lenses:
  - **Security Lens**: Input validation, secrets handling, auth boundaries.
  - **Performance Lens**: Query efficiency (N+1 queries), hot paths, memory allocation.
  - **Debloat Lens**: Pruning dead branches and redundant wrappers while preserving invariants.

### Axis 2: Spec Conformance
- Evaluate diff against `spec.md` requirements, acceptance criteria, and scope limits.

## Single-Paragraph ADR Standard

Record architectural decisions in `.agents/bundles/knowledge/decisions/` only when:
1. Hard to reverse.
2. Surprising without context.
3. The result of a real trade-off.

Format: `# Title` followed by 1 to 3 concise sentences (Context, Decision, Why).

## Contraction Archive Protocol

1. **Verify Full Suite**: Run aggregate verification commands.
2. **Elevate Knowledge**: Synthesize discoveries from `learnings.md` into `knowledge/patterns.md` and domain chapters.
3. **Log Contraction**: Append a concise date-grouped entry to `log.md`.
4. **Prune Scratch**: Delete ephemeral task files in `.agents/scratch/`.
5. **Delete Reviewed Inventory**: Apply the byte-identical journaled archive request, writing knowledge first, the log second, and deleting the completed spec inventory last. Leave the terminal journal outside the bundle and no resident archived spec.

<!-- project-customization: start -->
## Custom Completion Checks
<!-- project-customization: end -->

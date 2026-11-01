# Agent Context & Instruction Design (`AGENTS.md`, `SKILL.md`, Subagents, & OKF Knowledge)

Principles for authoring high-leverage, low-token agent instructions (`AGENTS.md`, `SKILL.md`, `.agents/agents/*.md`, and `.agents/bundles/knowledge/**/*.md`).

## Context Load vs. Cognitive Load

Every line in an agent instruction system trades off two costs:

- **Context Load**: Tokens that stay loaded in the model's context window on every turn (`AGENTS.md`, skill `description:` frontmatter, and `<!-- truth: start -->` blocks). High context load crowds out working memory and degrades instruction-following across the entire session.
- **Cognitive Load**: What the developer or routing skill must remember to invoke explicitly when a document has no automatic discovery pointer.

### Budgeting Rules

1. **`AGENTS.md` (`<= 100` lines)**: Treat `AGENTS.md` strictly as a map of **context pointers** plus canonical developer commands (`make lint`, `make validate`, `make test`). Never paste full styleguides or multi-page architecture manuals into `AGENTS.md`.
2. **`<!-- truth: start -->` Blocks (`<= 40` lines)**: Session-start hooks extract only bounded truth blocks from `product/product.md`, `product/product-guidelines.md`, `product/tech-stack.md`, `knowledge/workflow.md`, and `knowledge/patterns/*.md`. Keep truth blocks tight (`<= 40` lines of non-negotiable invariants) and place detailed examples below `<!-- truth: end -->`.
3. **`SKILL.md` (`<= 200` lines, `< 24,000` bytes)**: Inline only the universal backbone that every invocation of the skill needs; disclose branch-specific procedures into `references/*.md`.

## Information Hierarchy & Progressive Disclosure

Organize every skill and knowledge bundle across three disclosure levels:

| Level | Location | When to Use |
| --- | --- | --- |
| **In-File Steps** | `SKILL.md` `## Workflow` | The sequential backbone followed on every invocation of the skill. |
| **In-File Reference** | `SKILL.md` tables & `## Guardrails` | Shared schemas, invariants, or decision tables that every branch in `SKILL.md` consults. |
| **Disclosed Reference** | `references/<branch>.md` or `knowledge/<area>/<topic>.md` | Branch-specific procedures, templates, or deep domain catalogs loaded only when the agent takes that branch. |

- **Progressive Disclosure by Branching**: If a skill has distinct operational modes (such as `prd`, `plan`, `revise`, and `research` in `flow-planning`, or `write`, `validate`, and `pr` in `flow-docs`), put each branch's detailed procedure in its own `references/<branch>.md` file and link to it from the branch step.
- **Co-Location**: Keep a concept's definition, rules, and edge cases together under a single heading. Never scatter caveats for a step into a miscellaneous `"Notes"` or `"Tips"` section at the bottom of the file.

## Context Pointers (`description:` & Index Tables)

A skill's `description:` frontmatter (or an `index.md` row) is a **context pointer**: its sole job is to tell the model *when* to load the file.

1. **Front-Load Trigger Words**: Start with `"Use when..."` and name the exact artifacts, commands, or situations that should fire the skill.
2. **One Trigger Per Distinct Branch**: Ensure every major branch inside the skill has a trigger phrase in the pointer so the skill fires for all of its branches.
3. **Cut Identity the Body Already Carries**: Do not waste pointer tokens explaining *how* the skill works internally; save the mechanics for `SKILL.md`.
4. **Model-Invoked vs. User-Invoked (`disable-model-invocation: true`)**:
   - Omit `disable-model-invocation` when the agent or another skill should auto-discover and activate the skill from task context.
   - Set `disable-model-invocation: true` on explicit slash-command stage skills (`flow-setup`, `flow-planning`, `flow-execution`, `flow-learn`, `flow-completion`) that are routed deterministically by the user or [`flow`](../../flow/SKILL.md) router.

## Completion Criteria, Leading Words, & Positive Framing

- **Completion Criteria Drive Legwork**:
  - Weak completion criteria (`"Review the spec and update as needed"`) invite premature completion.
  - Strong completion criteria combine **Clarity** (an explicit checklist of postconditions) and **Demand** (requiring concrete outputs such as `[N/N files documented]`, an `ADOPT` / `CONTEST` / `ESCALATE` Adjudication Ledger, or exit code `0` from `make check`).
- **Use Pretrained Leading Words**:
  - Prefer compact, high-leverage engineering terms that carry dense pretrained meaning—`seam`, `deep module`, `adapter`, `idempotent`, `vertical slice`, `red`, `tight`, `sediment`, `tautological`—over multi-sentence explanations.
- **Frame Instructions Positively**:
  - Negation (`"Don't write tests in separate remediation files"`) forces the model to activate the forbidden pattern first. Lead with the positive target (`"Place all new unit tests inside the canonical module test file tests/<module>/test_<unit>.py"`), then state the boundary concisely.

## Pruning Discipline

Whenever authoring or resynthesizing `AGENTS.md`, `SKILL.md`, or `.agents/bundles/knowledge/**/*.md`, prune four classes of waste:

1. **Duplicate Truth**: If a rule is defined in `skills/flow/references/state.md`, link to `state.md` instead of copying the schema into multiple files.
2. **Stale Environment Cache**: Do not copy full `Makefile` targets, dependency versions, or directory trees into prose unless documenting a non-obvious constraint, unwritten convention, or reason behind a choice. The repository's manifest files are the source of truth for what exists; documentation caches *why* and *how seams fit together*.
3. **Chronological Sediment**: Delete historical migration notes, struck-through requirements, and `"formerly"` callouts from active specs, skills, and knowledge chapters.
4. **Model-Relative No-Ops**: Delete instructions that tell the agent to do what it already does by default (such as `"Use valid syntax"` or `"Be helpful and thorough"`). Every remaining line must steer behavior on a real failure mode.

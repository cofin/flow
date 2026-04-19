---
name: consensus
description: "Auto-activate when evaluating architectural decisions, comparing technology choices, weighing design trade-offs, assessing feature proposals, making build-vs-buy decisions, choosing between competing approaches, when a decision has significant long-term consequences, when multiple teams are affected, or when the cost of reversal is high. Produces a structured recommendation with confidence level (low/medium/high), pro/con analysis, risk assessment, and concrete next steps. Use when: decisions need structured multi-perspective analysis, risk assessment from multiple angles, decisions impact more than one team, decisions span more than a few months, or when the stakes are high enough to warrant deliberate evaluation. Not for routine code review, simple config choices, or styling preferences."
---

# Consensus

Structured decision evaluation through stance rotation — analyze from advocate, critic, and neutral perspectives, then synthesize into a confidence-rated recommendation with concrete next steps.

<workflow>

## Workflow

### Step 1: Select Mode

| Decision Scope | Mode | Reason |
| -------------- | ---- | ------ |
| Bounded, reversible | **Sequential** (default) | All perspectives in one pass — fast |
| Multi-month or irreversible | **Subagent** | Three isolated subagents prevent cross-contamination |
| Perspectives suspiciously aligned | Escalate to **Subagent** | Lack of genuine disagreement signals contamination |

**Use subagent mode when:** the decision impacts more than 3 months of work, multiple teams are affected, or sequential perspectives align too easily (suspiciously low disagreement likely signals contamination — isolated subagents are required to get genuine divergence).

See `references/consensus-strategy.md` for full escalation criteria.

### Step 2: Stance Rotation

Rotate through three perspectives (see `references/stance-rotation.md` for detailed prompts):

1. **Neutral** — state the decision, list all factors (technical, organizational, timeline, risk), note missing information, present assessment without leaning toward a conclusion.
2. **Advocate** — build the strongest case FOR: what problems does it solve, what synergies does it create, how can challenges be overcome? Subject to ethical guardrails — refuse to advocate if fundamentally harmful.
3. **Critic** — rigorous scrutiny: real risks, overlooked complexities, simpler alternatives, flawed assumptions? Subject to ethical guardrails — acknowledge if the proposal is genuinely sound.

In **subagent mode**, dispatch three isolated subagents (one per stance) with identical context. Subagents must NOT see each other's output.

### Step 3: Synthesize

Weigh all three perspectives and produce a recommendation:

1. **Points of agreement** — where all perspectives align (strong signal)
2. **Points of disagreement** — where they diverge and why
3. **Recommendation** — with confidence level: **low** / **medium** / **high**
4. **Would change if** — conditions that would flip the recommendation
5. **Next steps** — concrete actions based on the recommendation

</workflow>

<validation>

### Validation Checkpoint

Before delivering the synthesis, verify:

- [ ] Each perspective contributed at least one unique point not raised by the others
- [ ] The critic identified at least one genuine risk (not manufactured disagreement)
- [ ] The recommendation confidence level is justified by the degree of inter-perspective agreement
- [ ] If all three perspectives agree too easily, escalate to subagent mode

</validation>

<example>

## Example

**Decision:** "Should we migrate from REST to GraphQL?"

| Perspective | Key Finding |
|-------------|-------------|
| Neutral | Current REST API has 47 endpoints; clients use ad-hoc field filtering. GraphQL would reduce over-fetching but adds schema maintenance. |
| Advocate | Mobile clients would cut payload size ~60%. Single endpoint simplifies versioning. Strong ecosystem tooling available. |
| Critic | Team has no GraphQL experience — 2-3 month learning curve. Caching is harder. Existing REST clients need migration path. |

**Synthesis:**

- Agreement: Current API has over-fetching problems worth solving.
- Disagreement: Whether the learning curve cost is justified given timeline.
- Recommendation: **Adopt GraphQL for new endpoints only** (confidence: **medium**).
- Would change if: Team had prior GraphQL experience (→ high confidence, full migration) or deadline is <3 months (→ stay REST).
- Next steps: 1) Prototype one high-traffic endpoint. 2) Measure payload reduction. 3) Decide on full migration after prototype.

</example>

## References

- **[Consensus Strategy](references/consensus-strategy.md)** — Mode selection and escalation criteria
- **[Stance Rotation](references/stance-rotation.md)** — Detailed rotation steps, subagent dispatch, synthesis framework
- **[Stance Prompts](../perspectives/references/stances.md)** — Advocate, critic, neutral prompts with ethical guardrails (from perspectives skill)

<guardrails>
## Guardrails

Add guardrails instructions here.
</guardrails>

---
name: perspectives
description: "Auto-activate when analyzing trade-offs, evaluating decisions, comparing approaches, playing devil's advocate, considering pros and cons, weighing options, assessing risks, reviewing assumptions, stress-testing a conclusion, identifying blind spots, or needing multiple viewpoints on a problem. Use when: any decision needs structured multi-angle analysis, a conclusion feels too comfortable, a proposal has not been challenged yet, or when a single perspective has dominated the analysis. Shared prompt library — produces stance prompts and critical thinking frameworks for use by other skills. Not typically invoked directly — loaded by challenge, consensus, and reviewer skills."
---

# Perspectives

Shared prompt library for structured multi-perspective analysis. Provides stance prompts (advocate, critic, neutral) and critical thinking frameworks used by other Flow skills.

<context>

## Overview

This skill provides the foundation that other skills build on:

- **Stance prompts** — three perspectives (advocate, critic, neutral) each with ethical guardrails that prevent harmful analysis
- **Critical thinking framework** — structured reassessment pattern for evaluating claims and assumptions

Typically loaded by other skills (`challenge`, `consensus`, persona skills) rather than invoked directly. Can be invoked directly when you want raw stance prompts for custom analysis.

## References Index

- **[Stance Prompts](references/stances.md)** — Advocate, critic, and neutral perspective prompts with ethical guardrails
- **[Critical Thinking Framework](references/critical-thinking.md)** — CRITICAL REASSESSMENT pattern and anti-patterns

</context>

<workflow>
## Workflow

1. **Identify the core claim or decision** -- Clearly state the problem or proposal that needs analysis.
2. **Apply the Advocate perspective** -- Identify the benefits, opportunities, and strongest arguments in favor of the proposal.
3. **Apply the Critic perspective** -- Identify the risks, trade-offs, and failure modes. Challenge assumptions and reveal blind spots.
4. **Apply the Neutral perspective** -- Objectively weigh the evidence, consider alternatives, and identify the conditions under which the proposal succeeds or fails.
5. **Synthesize the findings** -- Combine the perspectives into a balanced summary with actionable recommendations and a clear risk assessment.
</workflow>

<guardrails>
## Guardrails

- **Avoid confirmation bias** -- Actively seek evidence that contradicts your preferred conclusion.
- **Ensure diversity of viewpoints** -- Don't just pick the easiest arguments; look for subtle or non-obvious perspectives.
- **Respect ethical and safety constraints** -- Never generate analysis that encourages harmful behavior or violates project security rules.
- **Stay objective in the neutral stance** -- Avoid using biased language or leaning towards one side when synthesizing the results.
- **Explicitly state assumptions** -- Clearly label any unverified facts or assumptions used during the analysis.
</guardrails>

<validation>
## Validation Checkpoint

- [ ] At least three distinct perspectives (Advocate, Critic, Neutral) have been applied
- [ ] Core assumptions have been identified and challenged
- [ ] Potential risks and failure modes are explicitly documented
- [ ] Trade-offs between competing approaches are weighed objectively
- [ ] Final recommendation is based on a synthesis of all perspectives, not just one
- [ ] Analysis avoids loaded language and maintains a professional tone
</validation>

<example>
## Example: Applying Perspectives to a Tech Choice

**Proposal:** Moving from a monolithic database to a distributed microservices architecture.

**Advocate:** "Enables independent scaling of services, improves developer velocity by reducing coupling, and increases fault tolerance through isolation."

**Critic:** "Significantly increases operational complexity (service discovery, distributed tracing), introduces network latency between services, and requires complex distributed transaction management."

**Neutral:** "The transition is beneficial if the current monolith is a bottleneck for deployment frequency or horizontal scaling. However, the team must first invest in robust observability and CI/CD pipelines to manage the added overhead."
</example>

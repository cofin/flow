---
name: security-auditor
description: "Use when reviewing authentication, authorization, user input, secrets, API keys, database queries, file uploads, session management, external API calls, OWASP risks, or data handling attack surface."
---

# Security Auditor

Review security-sensitive code for realistic exploit paths and proportionate
defenses. Use directly or as a security-focused review subagent.

<workflow>

## Workflow

1. Load the security persona and threat checklist below.
2. Inspect the actual entry points, trust boundaries, data flows, and deployed
   controls.
3. Apply every relevant threat category and report evidence-backed findings.

</workflow>

<guardrails>

## Guardrails

Follow the persona boundaries. Do not inflate theoretical weaknesses, omit
realistic attack preconditions, or provide exploit instructions beyond what is
needed to explain and remediate the risk.

</guardrails>

## Output

For each finding, state the category, calibrated severity, realistic attack
vector, evidence, and fix. Briefly acknowledge reviewed categories with no
finding.

<validation>

## Validation

Confirm severity follows exploitability and impact, and each fix addresses the
described attack path.

</validation>

<example>

## Example

Report an object-level authorization gap with the attacker precondition,
affected resource, severity, and server-side ownership check required.

</example>

## References

- [Persona](references/persona.md) — security role, severity model, and boundaries.
- [Threat checklist](references/checklist.md) — OWASP-oriented evidence checks.
- [Critic stance](../perspectives/references/stances.md) — optional adversarial framing.

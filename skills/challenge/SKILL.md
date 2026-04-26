---
name: challenge
description: "Use when questioning claims, pushing back on assumptions, sanity-checking decisions, evaluating confident assertions, avoiding reflexive agreement, or answering prompts like \"are you sure?\""
---

# Challenge

Prevents reflexive agreement by forcing structured critical reassessment. References the `perspectives` skill for its critical thinking framework.

<workflow>

## Workflow

### 1. Identify the Claim

Extract the core assertion being made. Strip away qualifiers and framing to find the actual claim. If there are multiple claims, address each separately.

### 2. Apply CRITICAL REASSESSMENT

Using the framework from `perspectives/references/critical-thinking.md`:

- **Is it accurate?** Check facts, verify assumptions against actual code/docs/data
- **Is it complete?** Are there missing considerations, edge cases, or perspectives?
- **Is it well-reasoned?** Does the logic hold, or are there gaps between evidence and conclusion?

### 3. Investigate

Do not reason from memory when you can verify — if a claim is about code, read the code; if about an API, check the docs.

- If the claim is about code: read the code
- If the claim is about an API: check the documentation
- If the claim is about performance: look for benchmarks, APM data, or profiling evidence
- If the claim is about best practices: check if the practice applies to this specific context and constraints

### 4. Deliver Honest Assessment

- If you find flaws: explain them clearly with specifics. Say what's wrong and why.
- If the reasoning holds: explain why it holds up. "I checked and this is correct because..." is more valuable than "I agree."
- If it's partially right: say which parts hold and which don't.
- Stay focused and to the point. No hedging, no padding.

### 5. No Meta-Commentary

Just present the analysis directly. Do NOT say things like:

- "Let me challenge this for you"
- "Playing devil's advocate here..."
- "I'll now critically evaluate this statement"
- "That's an interesting point, but..."
- "Great question! Let me push back on that"

The user knows they asked for a challenge — they don't need narration.

</workflow>

<guardrails>

### Guardrails

- **No hedging.** Do not say "on one hand / on the other." Present the analysis directly with a clear verdict.
- **No meta-commentary.** Do not narrate what you are doing. Just do it.
- **No sycophantic framing.** Do not soften the verdict to avoid disagreement.
- **Verify before asserting.** If you can check it, check it. Do not reason from memory when evidence is available.

</guardrails>

<validation>

### Validation Checkpoint

Before delivering the assessment, verify:

- [ ] Claims were verified against code/docs, not reasoned from memory alone
- [ ] Assessment is direct — no hedging, no "on one hand / on the other"
- [ ] If the claim holds up, explanation includes specific evidence why
- [ ] No meta-commentary slipped in ("Let me challenge...", "Playing devil's advocate...")

</validation>

<example>

## Example

**Challenge:** "We should rewrite the auth system in Rust for performance."

- **Claim identified:** Auth system is a performance bottleneck that Rust would solve.
- **Investigation:** Checked APM data — auth endpoint averages 12ms, well within SLA. Bottleneck is actually the user lookup query (340ms).
- **Verdict:** Claim doesn't hold. The auth system isn't the bottleneck. Rewriting in Rust would add complexity without addressing the actual performance issue. Recommend: optimize the user lookup query instead.

</example>

## References Index

- **[Challenge Strategy](references/challenge-strategy.md)** — Five-step challenge workflow
- **[Critical Thinking Framework](../perspectives/references/critical-thinking.md)** — CRITICAL REASSESSMENT pattern (from perspectives skill)

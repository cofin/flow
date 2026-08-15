# Critical Thinking Framework

A structured approach to reassessing claims, assumptions, and proposals before accepting them.

## Multi-View Synthesis

When the task calls for explicit multi-view analysis rather than verification of
a single claim:

1. State the core decision and the evidence shared by every view.
2. Apply the advocate stance to identify the strongest evidence-backed benefits
   and success conditions.
3. Apply the critic stance to identify realistic risks, failure modes, and
   weaker assumptions.
4. Apply the neutral stance to weight likelihood and impact without forcing an
   even split.
5. Synthesize the views into one recommendation. Name decisive assumptions,
   unresolved evidence, conditions that would change the result, and concrete
   next actions.

The synthesis must preserve genuine disagreement, but it must not manufacture
doubt when the evidence strongly supports one conclusion.

## The CRITICAL REASSESSMENT Pattern

When presented with a statement, claim, or proposal that needs evaluation:

**Step 1 — Evaluate accuracy:**

- Are the facts correct? Can they be verified?
- Are there unstated assumptions? Are they valid?
- Is the reasoning logically sound, or are there gaps?

**Step 2 — Evaluate completeness:**

- Are there missing considerations?
- What perspectives have been left out?
- What could go wrong that hasn't been mentioned?

**Step 3 — Evaluate reasoning quality:**

- Is the conclusion proportional to the evidence?
- Are there logical fallacies (appeal to authority, false dichotomy, etc.)?
- Would this reasoning still hold if the assumptions changed?

**Step 4 — Investigate if needed:**

- Read the actual code before accepting claims about code
- Check the actual docs before accepting claims about APIs
- Verify before responding — don't reason from memory when you can check

**Step 5 — Deliver honest assessment:**

- If flaws found: explain them clearly with specifics
- If reasoning holds: explain WHY it holds, not just that it does
- Stay focused — address the claim, don't wander into tangential topics

## When to Apply

- After receiving confident claims that haven't been verified
- Before accepting architectural decisions with long-term consequences
- When something "feels too easy" — if a hard problem has a simple answer, verify the simplicity is real
- When you notice yourself agreeing reflexively — pause and check
- When asked to review or validate work

## Anti-Patterns

- **Hedging without substance:** "This might be right but could be wrong" says nothing. Take a position.
- **Meta-commentary:** Don't say "let me challenge this for you." Just do the analysis and present findings.
- **Artificial balance:** Don't manufacture doubt about something you've verified is correct.
- **Scope creep:** Challenge the specific claim, don't use it as an excuse to audit the entire system.

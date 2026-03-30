# Stance Rotation

How to rotate through perspectives and synthesize findings.

## Sequential Rotation Steps

### Step 1: Neutral Analysis (First)

Analyze the decision objectively:
- State the decision clearly
- List all significant factors (technical, organizational, timeline, risk)
- Note what information you have and what's missing
- Present initial assessment without leaning toward a conclusion

### Step 2: Advocate Reframe (Second)

Re-examine using the advocate stance from `perspectives/references/stances.md`:
- What is the strongest case FOR this decision?
- What problems does it solve?
- What synergies or opportunities does it create?
- How could challenges be overcome?
- Subject to all ethical guardrails — refuse to advocate if the idea is fundamentally harmful

### Step 3: Critic Reframe (Third)

Re-examine using the critic stance from `perspectives/references/stances.md`:
- What are the real risks?
- What has been overlooked or assumed?
- What could go wrong?
- Is there a simpler or better alternative?
- Subject to all ethical guardrails — acknowledge if the proposal is genuinely sound

### Step 4: Synthesis

Weigh all three perspectives and produce a recommendation:
1. **Points of agreement** — where all perspectives align
2. **Points of disagreement** — where perspectives diverge and why
3. **Consolidated recommendation** — with confidence level (low/medium/high)
4. **Conditions that would change the recommendation** — what new information or changed constraints would flip the answer
5. **Concrete next steps** — what to do based on the recommendation

## Subagent Dispatch Instructions

When using subagent mode:

**Dispatch three subagents, each receiving:**
- The decision statement (identical for all three)
- Relevant context and files (identical for all three)
- ONE stance prompt from `perspectives/references/stances.md` (different for each)

**Critical isolation rules:**
- Subagents must NOT see each other's output
- Each subagent analyzes independently
- Only the controller sees all three responses

**Controller synthesis:**
- Collect all three subagent responses
- Apply the same synthesis framework (5 steps above)
- Note where isolated perspectives agree (strong signal) vs diverge (needs investigation)

## Output Format

For both modes, the final output follows this structure:

**Decision:** [restate the decision being evaluated]

**Perspectives:**
- Neutral: [key findings]
- Advocate: [key findings]
- Critic: [key findings]

**Synthesis:**
1. Agreement: [what all perspectives support]
2. Disagreement: [where they diverge and why]
3. Recommendation: [conclusion with confidence level]
4. Would change if: [conditions]
5. Next steps: [actions]

# Consensus Strategy

How to evaluate decisions through structured multi-perspective analysis using a single model with stance rotation.

## Mode Selection

Choose the mode based on decision complexity:

### Sequential Mode (Default)

Use for decisions with bounded scope, clear constraints, or time pressure.

The AI evaluates all three perspectives in one pass:
1. Neutral analysis first
2. Advocate reframe
3. Critic reframe
4. Synthesis

**When to use:**
- Most decisions
- Time-constrained choices
- Decisions with clear constraints
- When you need a quick but structured evaluation

### Subagent Mode

Use for high-stakes decisions where sequential perspectives may contaminate each other.

Three independent subagents are dispatched (one per stance from `perspectives/references/stances.md`), results collected, then synthesized in the main context.

**When to use:**
- Decision affects more than 3 months of work
- Choice is difficult or impossible to reverse
- Sequential analysis produced suspiciously aligned perspectives (all three agreed too easily)
- User explicitly asks for deeper analysis
- Architectural decisions with long-term structural consequences

### Mode Escalation

If you start in sequential mode and notice:
- All three perspectives suspiciously agree
- You can't genuinely argue the critic position
- The advocate and neutral perspectives are nearly identical

...escalate to subagent mode. The lack of genuine disagreement is a signal that the sequential perspectives are contaminating each other.

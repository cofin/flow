
# Flow Discipline Rules

Consolidated enforcement rules for TDD, debugging, and verification. These iron laws apply across all flow commands. For detailed education and examples, see the referenced superpowers skills.

## TDD Iron Law

```text
NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST
```

Write code before the test? Delete it. Start over.

**No exceptions:**

- Don't keep it as "reference"
- Don't "adapt" it while writing tests
- Delete means delete

**Violating the letter of the rules is violating the spirit of the rules.**

### Red-Green-Refactor

1. **RED** — Write one minimal failing test. Run it. Confirm it fails for the right reason (feature missing, not typo).
2. **GREEN** — Write simplest code to pass. No extras. Run tests, confirm all pass.
3. **REFACTOR** — Clean up while green. Remove duplication, improve names. Run tests again.
4. **REPEAT** — Next failing test for next behavior.

### TDD Rationalizations

| Excuse | Reality |
|--------|---------|
| "Too simple to test" | Simple code breaks. Test takes 30 seconds. |
| "I'll test after" | Tests passing immediately prove nothing. |
| "Already manually tested" | Ad-hoc is not systematic. No record, can't re-run. |
| "Deleting X hours is wasteful" | Sunk cost fallacy. Keeping unverified code is technical debt. |
| "TDD will slow me down" | TDD is faster than debugging. |
| "Need to explore first" | Fine. Throw away exploration, start with TDD. |

### TDD Red Flags — STOP and Start Over

- Code written before test
- Test passes immediately (testing existing behavior)
- Can't explain why test failed
- Rationalizing "just this once"
- "Keep as reference" or "adapt existing code"

**Full reference:** `superpowers:test-driven-development`

---

## Debugging Iron Law

```text
NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST
```

If you haven't completed Phase 1, you cannot propose fixes.

### The Beads-First Investigation Mandate

**CRITICAL:** Every investigation finding, root cause discovery, and hypothesis test MUST be recorded in Beads as a note on the active task.

1. **Investigate**: Trace data flow, read errors, reproduce.
2. **Note**: `bd note <id> "Root cause: [Description]. Found in [file:line]."`
3. **Commit**: Decisions stored in Beads survive context compaction and session resets. Markdown is for the final "Learnings" summary.

### Four-Phase Protocol

1. **Root Cause Investigation** — Read error messages completely. Reproduce consistently. Check recent changes. Trace data flow to source.
2. **Pattern Analysis** — Find working examples. Compare against references. Identify every difference.
3. **Hypothesis Testing** — Form single hypothesis. Test with smallest possible change. One variable at a time.
4. **Implementation** — Create failing test reproducing bug. Implement single fix. Verify fix.

### Escalation Rule

If 3+ fixes have failed: **STOP**. Question the architecture. Each fix revealing new problems in different places = wrong pattern, not wrong fix. Discuss with user before attempting more.

### Debugging Rationalizations

| Excuse | Reality |
|--------|---------|
| "Issue is simple, don't need process" | Simple issues have root causes too. |
| "Emergency, no time" | Systematic is FASTER than thrashing. |
| "Just try this first" | First fix sets the pattern. Do it right. |
| "I see the problem, let me fix it" | Seeing symptoms is not understanding root cause. |

### Debugging Red Flags — STOP

- "Quick fix for now, investigate later"
- "Just try changing X and see"
- Proposing solutions before tracing data flow
- Adding multiple changes at once
- "One more fix attempt" after 2+ failures

**Full reference:** `superpowers:systematic-debugging`

---

## Verification Iron Law

```text
NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE
```

If you haven't run the verification command in this response, you cannot claim it passes.

### The Gate Function

```text
BEFORE claiming any status:
1. IDENTIFY — What command proves this claim?
2. RUN — Execute the command (fresh, complete)
3. READ — Full output, check exit code
4. VERIFY — Does output confirm the claim?
5. CLAIM — Only then state the result WITH evidence
```

### Verification Requirements

| Claim | Requires | Not Sufficient |
|-------|----------|----------------|
| Tests pass | Test output: 0 failures | "Should pass", previous run |
| Coverage met | Coverage report | Extrapolation |
| Build succeeds | Build exit 0 | Linter passing |
| Bug fixed | Original symptom gone | Code changed, assumed fixed |
| Phase complete | Requirements checklist verified | Tests passing alone |

### Verification Red Flags — STOP

- Using "should", "probably", "seems to"
- Expressing satisfaction before verification ("Done!", "Perfect!")
- About to commit/push without verification
- Trusting agent success reports without independent check

**Full reference:** `superpowers:verification-before-completion`

---

## Beads Mode Iron Law

```text
NO `bd` INVOCATIONS WHEN BEADS IS DISABLED OR MISSING
```

The SessionStart hook (`hooks/detect-env.sh`) emits one of three Beads-backend signals into the agent context:

| Hook signal | Action |
|---|---|
| `Beads Backend: Official (bd)` | Proceed normally — `bd` is the source of truth. |
| `Beads Backend: Missing (None)` | Skip every `bd` invocation. Treat `spec.md` markers as fallback source of truth. |
| `Beads Backend: Disabled via plugin config (useBeads=false)` | Skip every `bd` invocation. Treat `spec.md` markers as fallback source of truth. |

**Never halt for missing Beads.** Degrade gracefully: read state from `spec.md` markers (`[ ]`, `[~]`, `[x]`, `[!]`, `[-]`), record progress by editing those markers directly, skip notes/learnings that would otherwise go into Beads, and skip `/flow:sync` (it's a no-op without a backend).

**Why this exists:** The plugin manifest exposes a `useBeads` userConfig toggle and the host can also lack `bd` entirely. Before this rule, every flow command shelled out to `bd` unconditionally — toggling `useBeads=false` only suppressed SessionStart context while every command still emitted "command not found" or stored garbage.

---

## Critical Thinking Iron Law

```text
NO PROPOSALS OR CLAIMS WITHOUT CRITICAL REASSESSMENT FIRST
```

Before accepting a claim (your own or others), proposing a solution, or making a technical decision, you **MUST** run it through the **CRITICAL REASSESSMENT** pattern.

**No exceptions:**

- Even if it "seems obvious"
- Even if it's "the only way"
- Even if you've done it before

### The CRITICAL REASSESSMENT Pattern

1. **EVALUATE ACCURACY** — Verify facts. Identify unstated assumptions. Check for logical gaps.
2. **EVALUATE COMPLETENESS** — Look for missing considerations, omitted perspectives, and failure modes.
3. **EVALUATE REASONING QUALITY** — Check if conclusions are proportional to evidence. Identify logical fallacies.
4. **INVESTIGATE IF NEEDED** — Read actual code and docs. **Never reason from memory.**
5. **DELIVER HONEST ASSESSMENT** — Provide specific flaws or explain *why* reasoning holds. Avoid hedging and meta-commentary.

### Critical Thinking Rationalizations

| Excuse | Reality |
|--------|---------|
| "I've done this 100 times" | This codebase or context might be different. Verify. |
| "Reviewer knows better" | Reviewers are human (or AI). They can be wrong. |
| "It's just a simple change" | Simple changes have side effects. |
| "Don't want to be negative" | Honesty > performance. |

### Critical Thinking Red Flags — STOP

- Hedging: "This might be right but could be wrong"
- Reflexive agreement: "You're absolutely right!"
- Proposing solutions without investigating the actual code first
- Meta-commentary: "Let me challenge this for you" (just do the analysis)
- Manufacture of 50/50 doubt (no artificial balance)

**Full reference:** `superpowers:perspectives:critical-thinking`

---

## Code Review Discipline

### Requesting Review

At phase completion or before merge:

1. Get git range (base SHA to HEAD)
2. Dispatch code review subagent with: what was implemented, spec requirements, git range
3. Act on feedback: fix Critical immediately, fix Important before proceeding, note Minor for later

### Receiving Review

- **No performative agreement** ("You're absolutely right!", "Great point!")
- **Verify** suggestions against codebase before implementing (follow **Critical Thinking Iron Law**)
- **Push back** with technical reasoning if reviewer is wrong
- **YAGNI check:** if reviewer suggests adding unused features, question the need
- **Clarify** all unclear items BEFORE implementing any

**Full reference:** `superpowers:requesting-code-review`, `superpowers:receiving-code-review`

---

## Subagent Orchestration

When executing parallel tasks or dispatching implementation work:

### Model Selection

- **Mechanical tasks** (1-2 files, clear spec) → fast model
- **Integration tasks** (multi-file, coordination) → standard model
- **Review/architecture tasks** → most capable model

### Two-Stage Review

After each task completion:

1. **Spec compliance review** — Does implementation match requirements? Nothing missing, nothing extra?
2. **Code quality review** — Is implementation well-built? Clean, tested, maintainable?

Spec compliance MUST pass before code quality review begins.

**Full reference:** `superpowers:subagent-driven-development`

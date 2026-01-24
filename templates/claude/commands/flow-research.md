---
description: Conduct pre-PRD research including codebase analysis and documentation lookup
argument-hint: <topic>
allowed-tools: Read, Glob, Grep, Bash, WebSearch, mcp__context7__resolve-library-id, mcp__context7__query-docs
---

# Flow Research

Conducting research for: **$ARGUMENTS**

## Phase 0: Setup Check

Using the **Universal File Resolution Protocol**, verify:
- **Product Definition** (`.agent/product.md`)
- **Tech Stack** (`.agent/tech-stack.md`)
- **Workflow** (`.agent/workflow.md`)

If ANY missing: "Flow not set up. Run `/flow-setup` first." → HALT

---

## Phase 1: Research Initialization

### 1.1 Define Research Topic

**If `$ARGUMENTS` provided:** Use as research topic.
**If empty:** Ask user for topic.

### 1.2 Classify Research Type

Determine type:
- **New Feature:** Patterns, libraries, implementation approaches
- **Bug Investigation:** Root cause, reproduction steps
- **Integration:** External systems, APIs, protocols
- **Refactoring:** Current architecture, improvement patterns
- **Performance:** Profiling, benchmarking, optimization

### 1.3 Announce Research Plan

> "I will conduct research on: '[Topic]' (Type: [Type])
>
> My research will cover:
> 1. Codebase Analysis - Existing patterns and architecture
> 2. Library Documentation - Relevant API docs
> 3. Prior Art - Similar implementations
> 4. Risk Assessment - Challenges and mitigations
>
> This research will be referenced when creating the PRD."

---

## Phase 2: Codebase Exploration

### 2.1 Architecture Discovery

1. **Map Relevant Areas:**
   - Use Glob/Grep to identify related files
   - Analyze directory structure
   - Identify entry points and key abstractions

2. **Pattern Recognition:**
   - Document coding patterns in similar areas
   - Note naming conventions, file organization
   - Identify reusable utilities/helpers

3. **Dependency Analysis:**
   - Map internal module dependencies
   - Document external dependencies
   - Note version constraints

### 2.2 Codebase Summary

```markdown
## Codebase Analysis

### Relevant Modules
- [Module]: [Description]

### Existing Patterns
- [Pattern to follow]

### Reusable Components
- [Utility/helper]

### Constraints
- [Limitations discovered]
```

---

## Phase 3: External Documentation Research

### 3.1 Library Documentation Lookup

1. Identify libraries from Tech Stack relevant to topic
2. Use Context7 or web search for current documentation
3. Focus on APIs, patterns, best practices
4. Note deprecations and migration guides

### 3.2 Document Findings

```markdown
## Library Documentation

### [Library Name] (version X.X)
**Relevant APIs:**
- [API]: [Description and usage]

**Best Practices:**
- [Practice]

**Gotchas:**
- [Pitfall to avoid]
```

---

## Phase 4: Prior Art Research

### 4.1 Search for Prior Art

1. **Internal:**
   - Git history for similar implementations
   - Existing ADRs or design docs
   - Related closed PRs/issues

2. **External:**
   - Common patterns for this problem type
   - Reference implementations
   - Industry standards

### 4.2 Document Findings

```markdown
## Prior Art

### Internal References
- [Existing related work]

### External Patterns
- [Pattern]: [Description]

### Recommended Approach
[Summary and rationale]
```

---

## Phase 5: Risk Assessment

### 5.1 Risk Analysis

1. **Technical Risks:**
   - Complexity hotspots
   - Test coverage gaps
   - Performance concerns
   - Security considerations

2. **Integration Risks:**
   - Breaking change potential
   - Backward compatibility
   - Migration requirements

3. **Recovery Planning:**
   - Rollback strategy
   - Checkpoint opportunities
   - Affected dependencies

### 5.2 Risk Documentation

```markdown
## Risk Assessment

### Technical Risks
| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| [Risk] | High/Med/Low | High/Med/Low | [Strategy] |

### Recovery Strategy
**Rollback Plan:** [How to revert]
**Checkpoints:** [Where to create safe points]
```

---

## Phase 6: Research Synthesis

### 6.1 Create Research Document

1. **Generate Research ID:** `research_{YYYYMMDD}_{shortname}`

2. **Create Research Directory:**
   ```bash
   mkdir -p .agent/research/{research_id}
   ```

3. **Write Research Document:** `.agent/research/{research_id}/research.md`
   - Executive Summary (3-5 bullets)
   - Codebase Analysis
   - Library Documentation
   - Prior Art
   - Risk Assessment
   - Recommended Approach
   - Open Questions

4. **Create Metadata:** `.agent/research/{research_id}/metadata.json`

### 6.2 Present Summary

> "Research complete. Executive summary:
>
> [3-5 bullet points]
>
> **Full research:** `.agent/research/{research_id}/research.md`
>
> **Next step:** Run `/flow-prd` to create a PRD based on this research."

### 6.3 Offer Options

> "Would you like to:
> A) Create PRD based on this research
> B) Research additional areas
> C) Review full research document
> D) End research session"

---

## Quality Gates

Before completion, verify:
- [ ] Codebase analysis covers relevant modules
- [ ] At least 2 libraries documented (if applicable)
- [ ] At least 3 risks identified
- [ ] Recovery strategy defined
- [ ] Recommended approach stated with rationale

---

## Critical Rules

1. **THOROUGH EXPLORATION** - Analyze codebase before external research
2. **CURRENT DOCS** - Use Context7 for up-to-date library documentation
3. **RISK FOCUSED** - Always include recovery planning
4. **ACTIONABLE OUTPUT** - Research should directly inform PRD creation

---
description: Conduct pre-PRD research
argument-hint: <topic>
allowed-tools: Read, Glob, Grep, Bash, WebSearch
---

# Flow Research

Conducting research for: **$ARGUMENTS**

## Phase 0: Setup Check

Using the **Universal File Resolution Protocol**, verify:
- **Product Definition** (`.agents/product.md`)
- **Tech Stack** (`.agents/tech-stack.md`)
- **Workflow** (`.agents/workflow.md`)

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

### 2.1 Structured Research Tasks

**CRITICAL: Research is task-based, not sequential thoughts.**

Create explicit research tasks with status tracking:

```markdown
## Research Tasks

### Task 1: Map Entry Points
**Status**: Complete
**Sources Analyzed**: src/routes/, src/handlers/
**Findings**: [Key discoveries]

### Task 2: Analyze Existing Patterns
**Status**: In Progress
**Sources Analyzed**: patterns.md, src/services/
```

### 2.2 Codebase Analysis with File References

**CRITICAL: Always include file:line references.**

1. **Map Relevant Areas:**
   - Use Glob/Grep to identify related files
   - For each finding, note exact file path and line number
   - Example: `src/services/auth.py:45` - AuthService class definition

2. **Pattern Recognition:**
   - Document coding patterns with specific examples
   - Reference where patterns are used: `src/handlers/base.py:78`

3. **Dependency Trace:**
   - Map import chains with file references
   - Document the data flow through components

### 2.3 Codebase Analysis Report

```markdown
## Codebase Analysis

### Key Locations
| File | Lines | Purpose |
|------|-------|---------|
| `src/services/auth.py` | 45-120 | Authentication service |
| `src/handlers/base.py` | 78-95 | Base error handling |

### Current Implementation Walkthrough
1. Request enters at `src/routes/api.py:23`
2. Middleware processes at `src/middleware/auth.py:15`
3. Handler invoked at `src/handlers/user.py:42`

### Existing Patterns
| Pattern | Location | Usage |
|---------|----------|-------|
| DI with Dishka | `src/di/container.py` | All services |
| Custom exceptions | `src/errors.py:10-50` | Error handling |

### Observations
- **Strength:** [with file reference]
- **Concern:** [with file reference]

### Constraints Discovered
- [Limitation with specific code reference]
```

---

## Phase 3: External Documentation Research

### 3.1 Library Documentation Lookup

1. Identify libraries from Tech Stack relevant to topic
2. Use web search for current documentation
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

1. **Generate Research ID:** `research_{shortname}`

2. **Create Research Directory:**
   ```bash
   mkdir -p .agents/research/{research_id}
   ```

3. **Write Research Document:** `.agents/research/{research_id}/research.md`

   ```markdown
   # Research: [Topic]

   **Workspace**: `.agents/research/{research_id}/`
   **Status**: Complete
   **Type**: [New Feature|Bug|Integration|Refactoring|Performance]

   ## Executive Summary
   - [Key finding 1]
   - [Key finding 2]
   - [Key finding 3]

   ## Research Tasks Summary
   | Task | Status | Key Findings |
   |------|--------|--------------|
   | Codebase Analysis | Complete | [summary] |
   | Library Docs | Complete | [summary] |
   | Prior Art | Complete | [summary] |

   ## Codebase Analysis
   [Detailed findings with file:line references]

   ## Library Documentation
   [Detailed findings with version info]

   ## Prior Art
   [Internal and external references]

   ## Risk Assessment
   [Table of risks with mitigations]

   ## Recommended Approach
   [Summary and rationale]

   ## Open Questions
   - [Question 1]
   - [Question 2]

   ## Research Outputs
   **This research informs:**
   - PRD: `.agents/specs/{prd_id}/prd.md` (when created)
   - Flow: `.agents/specs/{flow_id}/` (when created)
   ```

4. **Create Metadata:** `.agents/research/{research_id}/metadata.json`
   ```json
   {
     "research_id": "{research_id}",
     "topic": "{topic}",
     "type": "{type}",
     "created_at": "ISO timestamp",
     "libraries_researched": ["lib1", "lib2"],
     "files_analyzed": ["path1", "path2"],
     "linked_prd": null,
     "linked_flow": null
   }
   ```

### 6.2 Present Summary

> "Research complete. Executive summary:
>
> [3-5 bullet points]
>
> **Full research:** `.agents/research/{research_id}/research.md`
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
2. **CURRENT DOCS** - Use current, authoritative library documentation
3. **RISK FOCUSED** - Always include recovery planning
4. **ACTIONABLE OUTPUT** - Research should directly inform PRD creation

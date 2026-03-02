# Flow Think MCP Usage Guide

Complete usage documentation for the `flow_think` structured reasoning tool.

## Table of Contents

1. [Overview](#overview)
2. [Tool Schema Reference](#tool-schema-reference)
3. [Purpose Types](#purpose-types)
4. [Confidence Tracking](#confidence-tracking)
5. [Branching and Revisions](#branching-and-revisions)
6. [Beads Integration](#beads-integration)
7. [Best Practices](#best-practices)
8. [Common Patterns](#common-patterns)
9. [Anti-Patterns](#anti-patterns)

---

## Overview

The `flow_think` tool enables structured reasoning for complex problem-solving. It captures multi-step thinking processes with context tracking, confidence scoring, hypothesis verification, and optional Beads integration for cross-session memory.

**When to use flow_think:**

- Multi-step debugging requiring systematic investigation
- Architecture decisions needing documented rationale
- Complex implementation tasks with dependency tracking
- Problems requiring hypothesis testing and verification
- Any task where you need to track and revise earlier thinking

---

## Tool Schema Reference

### Required Fields

Every call to `flow_think` must include these fields:

| Field | Type | Description |
|-------|------|-------------|
| `step_number` | integer (>= 1) | Sequential step number. Start at 1, increment for each step. |
| `estimated_total` | integer (>= 1) | Current estimate of total steps. Adjust as you learn more. |
| `purpose` | string | Category of this step. See [Purpose Types](#purpose-types). |
| `context` | string | What is already known. Include findings from previous steps. |
| `thought` | string | Your current reasoning process. Explain what you are thinking. |
| `outcome` | string | Result or learning from this step. What did you accomplish? |
| `next_action` | string or object | What you will do next. See [Next Action](#next-action-format). |
| `rationale` | string | Why you chose this next action. Explain your reasoning. |

### Optional Fields

#### Completion

| Field | Type | Description |
|-------|------|-------------|
| `is_final_step` | boolean | Set `true` to explicitly mark reasoning complete. |

#### Confidence Tracking

| Field | Type | Description |
|-------|------|-------------|
| `confidence` | number (0-1) | Your confidence in this step. See [Confidence Tracking](#confidence-tracking). |
| `uncertainty_notes` | string | Specific doubts or assumptions you are making. |

#### Revision Support

| Field | Type | Description |
|-------|------|-------------|
| `revises_step` | integer | Step number you are revising or correcting. |
| `revision_reason` | string | Why you are revising the earlier step. |

#### Branching

| Field | Type | Description |
|-------|------|-------------|
| `branch_from` | integer | Step number to branch from for alternative exploration. |
| `branch_id` | string | Unique branch identifier. Auto-generated if not provided. |
| `branch_name` | string | Human-readable branch name (e.g., "Alternative A: Use caching"). |

#### Hypothesis Testing

| Field | Type | Description |
|-------|------|-------------|
| `hypothesis` | string | Current hypothesis being tested. State clearly. |
| `verification_status` | enum | Status: `pending`, `confirmed`, or `refuted`. |

#### Tool Integration

| Field | Type | Description |
|-------|------|-------------|
| `tools_used` | string[] | Tools used during this step for tracking. |
| `external_context` | object | External data or tool outputs relevant to this step. |
| `dependencies` | integer[] | Step numbers this step depends on. |

#### Session Support

| Field | Type | Description |
|-------|------|-------------|
| `session_id` | string | Group related reasoning chains. Sessions expire after timeout. |

#### Flow Integration

| Field | Type | Description |
|-------|------|-------------|
| `flow_id` | string | Current Flow context from `.agent/specs/`. |
| `beads_task_id` | string | Linked Beads task ID for sync. |
| `files_referenced` | string[] | Files examined during this step (absolute paths). |
| `patterns_discovered` | string[] | Patterns discovered for learnings capture. |

### Next Action Format

The `next_action` field accepts two formats:

**Simple string:**
```json
"next_action": "Read the configuration file to understand settings"
```

**Structured object:**
```json
"next_action": {
  "tool": "Read",
  "action": "Read the config file to check database settings",
  "parameters": { "file_path": "/app/config.json" },
  "expectedOutput": "Database connection configuration"
}
```

The structured format is recommended when you know the specific tool you will use next.

---

## Purpose Types

Purpose types categorize each reasoning step. Use these standard types:

| Purpose | When to Use | Example |
|---------|-------------|---------|
| `planning` | Breaking down tasks, outlining approach | "Identify files to modify for this feature" |
| `research` | Gathering information, investigating | "Search codebase for similar implementations" |
| `implement` | Writing code, making changes (TDD) | "Write failing test for new validation" |
| `debug` | Troubleshooting errors, root cause analysis | "Trace authentication flow to find bug" |
| `analysis` | Examining code or architecture | "Evaluate performance implications of approach" |
| `validation` | Verifying hypothesis or implementation | "Confirm fix resolves the reported issue" |
| `decision` | Choosing between options | "Compare caching strategies A vs B" |
| `exploration` | Trying different approaches | "Test alternative API design" |
| `reflection` | Reviewing progress, extracting patterns | "Document learnings from this implementation" |

**Custom purposes are allowed** - use descriptive strings when standard types do not fit.

---

## Confidence Tracking

Confidence values (0-1 scale) help identify when reasoning needs more support.

### Confidence Levels

| Range | Level | Meaning |
|-------|-------|---------|
| 0.95+ | Very High | Comprehensive understanding, ready to proceed |
| 0.80-0.94 | High | Strong evidence supports this conclusion |
| 0.50-0.79 | Medium | Some evidence, may need verification |
| 0.30-0.49 | Low | Limited evidence, assumptions being made |
| < 0.30 | Critical | High uncertainty, stop and gather information |

### Warning Thresholds

The server generates warnings when confidence drops below the configured threshold (default: 0.5):

- **Warning** (< 0.5): "You may want to verify assumptions before proceeding"
- **Critical** (< 0.2): "Consider gathering more information or breaking the problem into smaller parts"

### Confidence Guidelines

**Set high confidence (0.8+) when:**
- You have examined the relevant code directly
- Tests confirm your understanding
- Multiple evidence sources agree

**Set medium confidence (0.5-0.8) when:**
- Working from documentation or logs
- Making reasonable inferences
- Some uncertainty remains

**Set low confidence (< 0.5) when:**
- Guessing based on limited information
- Working with unfamiliar codebase
- Multiple plausible explanations exist

### Example with Confidence

```json
{
  "step_number": 2,
  "estimated_total": 4,
  "purpose": "debug",
  "context": "Found timeout error in logs",
  "thought": "The timeout suggests either network issues or slow database query",
  "outcome": "Need to check both possibilities",
  "next_action": "Check database query performance",
  "rationale": "Database is more likely based on error timing",
  "confidence": 0.6,
  "uncertainty_notes": "Could also be network - should check if DB proves OK"
}
```

---

## Branching and Revisions

### Branching for Alternative Exploration

Create a branch when you want to explore an alternative approach without abandoning your current path:

```json
{
  "step_number": 5,
  "estimated_total": 8,
  "purpose": "exploration",
  "context": "Current approach uses polling, considering websockets",
  "thought": "Websockets might reduce server load significantly",
  "outcome": "Will prototype websocket approach to compare",
  "next_action": "Implement websocket handler",
  "rationale": "Need data to make informed decision",
  "branch_from": 3,
  "branch_name": "Alternative: Websocket approach",
  "confidence": 0.5
}
```

**Branch depth limit:** Default is 5 levels deep (configurable via `FLOW_MCP_MAX_BRANCH_DEPTH`).

### Revising Earlier Steps

When new information invalidates earlier reasoning, use revisions:

```json
{
  "step_number": 6,
  "estimated_total": 7,
  "purpose": "validation",
  "context": "Testing revealed the bug is in auth middleware, not session handling",
  "thought": "My step 3 hypothesis was wrong - the issue is earlier in the pipeline",
  "outcome": "Identified correct root cause in auth token validation",
  "next_action": "Fix token validation logic",
  "rationale": "Evidence now clearly points to auth middleware",
  "revises_step": 3,
  "revision_reason": "New evidence shows auth middleware is the actual cause",
  "confidence": 0.9
}
```

**Note:** The original step is automatically marked as revised with a reference to the revision.

---

## Beads Integration

Flow Think integrates with Beads for persistent cross-session memory.

### Enabling Beads Sync

Beads sync is enabled by default. Configure via environment:

```bash
FLOW_MCP_BEADS_SYNC=true  # Enable (default)
FLOW_MCP_BEADS_SYNC=false # Disable
```

### Linking to Beads Tasks

Use `beads_task_id` to link reasoning to a Beads issue:

```json
{
  "step_number": 1,
  "estimated_total": 5,
  "purpose": "planning",
  "context": "Starting implementation of user authentication",
  "thought": "Will break this into auth flow, session handling, and tests",
  "outcome": "Defined implementation phases",
  "next_action": "Implement auth flow",
  "rationale": "Auth flow is the core dependency",
  "beads_task_id": "auth-feature-123",
  "flow_id": "user-auth_20260131"
}
```

### Session-Epic Mapping

Register a session with a Beads epic for automatic syncing:

```json
{
  "step_number": 1,
  "session_id": "debug-session-001",
  "beads_task_id": "epic-456"
}
```

All subsequent steps in this session automatically sync to the epic.

### Cross-Session Restoration

Restore reasoning context from a previous session via Beads:

1. Register session with epic ID
2. The server can restore steps from the epic's notes
3. Provides context summary for continuing work

### What Gets Synced

Each step synced to Beads includes:
- Step number and purpose
- Context, thought, outcome
- Next action and rationale
- Confidence and uncertainty notes
- Hypothesis and verification status
- Files referenced and patterns discovered
- Branch and revision information

---

## Best Practices

### 1. Start with Planning

Always begin with a planning step to outline your approach:

```json
{
  "step_number": 1,
  "estimated_total": 4,
  "purpose": "planning",
  "context": "Bug report: users can't save settings after update",
  "thought": "Will need to trace the save flow from UI to database",
  "outcome": "Identified investigation path: UI -> API -> Service -> DB",
  "next_action": "Search for save handler in settings module",
  "rationale": "Start at the entry point and trace forward"
}
```

### 2. Adjust Estimates Dynamically

Update `estimated_total` as you learn more about the problem:

```json
{
  "step_number": 3,
  "estimated_total": 7,
  "purpose": "research",
  "context": "Found the issue is more complex than expected...",
  "thought": "...",
  "outcome": "...",
  "next_action": "...",
  "rationale": "..."
}
```

### 3. Track Hypotheses Explicitly

Use hypothesis fields for systematic debugging:

```json
{
  "step_number": 4,
  "estimated_total": 6,
  "purpose": "debug",
  "context": "Error occurs only on POST requests",
  "thought": "CSRF token might be missing or invalid",
  "outcome": "Will verify CSRF token handling",
  "next_action": "Check CSRF token in request headers",
  "rationale": "POST-specific issues often relate to CSRF",
  "hypothesis": "CSRF token is missing from AJAX requests",
  "verification_status": "pending",
  "confidence": 0.7
}
```

Then update when verified:

```json
{
  "step_number": 5,
  "estimated_total": 6,
  "purpose": "validation",
  "context": "Checked request headers",
  "thought": "Confirmed CSRF token is missing",
  "outcome": "Root cause identified",
  "next_action": "Add CSRF token to AJAX requests",
  "rationale": "Fix is straightforward",
  "hypothesis": "CSRF token is missing from AJAX requests",
  "verification_status": "confirmed",
  "confidence": 0.95
}
```

### 4. Document Files and Patterns

Track what you examined and what you learned:

```json
{
  "step_number": 6,
  "estimated_total": 7,
  "purpose": "analysis",
  "context": "Reviewing related code",
  "thought": "...",
  "outcome": "...",
  "next_action": "...",
  "rationale": "...",
  "files_referenced": [
    "/app/src/services/auth.ts",
    "/app/src/middleware/csrf.ts"
  ],
  "patterns_discovered": [
    "CSRF tokens must be refreshed after session change",
    "All AJAX POST requests need X-CSRF-Token header"
  ]
}
```

### 5. Use Sessions for Complex Work

Group related reasoning chains with session IDs:

```json
{
  "step_number": 1,
  "estimated_total": 10,
  "purpose": "planning",
  "context": "...",
  "thought": "...",
  "outcome": "...",
  "next_action": "...",
  "rationale": "...",
  "session_id": "feature-auth-implementation",
  "beads_task_id": "auth-epic-001"
}
```

### 6. Mark Final Steps Explicitly

Always set `is_final_step` when reasoning is complete:

```json
{
  "step_number": 7,
  "estimated_total": 7,
  "purpose": "reflection",
  "context": "Implementation complete and tested",
  "thought": "Reviewing what was learned",
  "outcome": "Feature working, tests passing",
  "next_action": "None - task complete",
  "rationale": "All objectives achieved",
  "is_final_step": true,
  "patterns_discovered": ["Key learnings from this investigation"]
}
```

---

## Common Patterns

### Pattern 1: Systematic Debugging

```
Step 1: planning - Outline investigation approach
Step 2: research - Gather logs and error messages
Step 3: debug - Form initial hypothesis
Step 4: validation - Test hypothesis
Step 5: debug - Refine or revise based on results
Step 6: implement - Apply fix
Step 7: validation - Verify fix works
Step 8: reflection - Document learnings
```

### Pattern 2: Architecture Decision

```
Step 1: planning - Define decision criteria
Step 2: research - Gather options and constraints
Step 3: analysis - Evaluate option A
Step 4: analysis - Evaluate option B (branch)
Step 5: decision - Compare and choose
Step 6: reflection - Document decision rationale
```

### Pattern 3: TDD Implementation

```
Step 1: planning - Outline feature requirements
Step 2: implement - Write failing test
Step 3: implement - Write minimal passing code
Step 4: implement - Refactor while green
Step 5: validation - Verify coverage
Step 6: reflection - Extract patterns
```

### Pattern 4: Root Cause Analysis

```
Step 1: research - Collect symptoms and evidence
Step 2: analysis - Identify potential causes
Step 3: debug - Test most likely cause (hypothesis)
Step 4: debug - Test alternative if refuted (branch)
Step 5: validation - Confirm root cause
Step 6: implement - Apply fix
Step 7: validation - Verify resolution
```

---

## Anti-Patterns

### Anti-Pattern 1: Skipping Context

**Bad:**
```json
{
  "context": "Working on bug",
  "thought": "Checking the code"
}
```

**Good:**
```json
{
  "context": "User reported 500 error on /api/settings POST. Previous steps found the endpoint handler exists and authentication works correctly.",
  "thought": "The error might be in request body validation since auth passes but handler fails"
}
```

### Anti-Pattern 2: Vague Next Actions

**Bad:**
```json
{
  "next_action": "Continue investigating",
  "rationale": "To find the bug"
}
```

**Good:**
```json
{
  "next_action": {
    "tool": "Grep",
    "action": "Search for ValidationError in settings service",
    "expectedOutput": "Lines showing validation logic"
  },
  "rationale": "Validation errors match the 500 response pattern we're seeing"
}
```

### Anti-Pattern 3: Ignoring Low Confidence

**Bad:** Proceeding with 0.3 confidence without noting uncertainties.

**Good:**
```json
{
  "confidence": 0.3,
  "uncertainty_notes": "Haven't verified database state. Assuming config is valid. Need to check logs if this doesn't work."
}
```

### Anti-Pattern 4: Never Revising

If you discover earlier reasoning was wrong, **use revisions**. Do not pretend the old thinking was correct.

### Anti-Pattern 5: Too Many Steps Without Completion

If you reach step 15 and `estimated_total` keeps growing, stop and reflect. Consider:
- Breaking into sub-problems
- Re-evaluating the approach
- Using branching to explore alternatives

### Anti-Pattern 6: Not Using Beads for Multi-Session Work

If work spans multiple sessions, **always use Beads integration**. Without it, context is lost between sessions.

---

## Configuration Reference

Environment variables for customization:

| Variable | Default | Description |
|----------|---------|-------------|
| `FLOW_MCP_OUTPUT_FORMAT` | console | Output format: `console`, `json`, `markdown` |
| `FLOW_MCP_MAX_HISTORY` | 100 | Maximum steps retained in memory (1-10000) |
| `FLOW_MCP_SESSION_TIMEOUT` | 60 | Session timeout in minutes (1-1440) |
| `FLOW_MCP_MAX_BRANCH_DEPTH` | 5 | Maximum branching depth (1-20) |
| `FLOW_MCP_BEADS_SYNC` | true | Enable Beads integration |
| `FLOW_MCP_LOW_CONFIDENCE` | 0.5 | Warning threshold for low confidence |

---

## Response Format

The tool returns JSON responses with these fields:

```json
{
  "status": "flow_think_in_progress",
  "step_number": 3,
  "estimated_total": 5,
  "completed": false,
  "total_steps_recorded": 3,
  "next_action": "Search for validation logic",
  "confidence": 0.75,
  "hypothesis": {
    "text": "Validation is rejecting the request",
    "status": "pending"
  }
}
```

**Status values:**
- `flow_think_in_progress` - More steps expected
- `flow_think_complete` - Chain finished (`is_final_step` or completion phrase detected)

**Completion phrases** that auto-complete chains:
- "final conclusion"
- "in conclusion"
- "reasoning complete"
- "analysis complete"
- "task complete"
- "investigation complete"

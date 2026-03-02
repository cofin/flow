# Planning Example: PRD Decomposition

This example demonstrates using `flow_think` to decompose a Product Requirements Document (PRD) into actionable implementation tasks.

## Scenario

A PRD specifies a new user authentication system with OAuth support. The planning process breaks this into phases and tasks.

---

## Step 1: Understanding Requirements

```json
{
  "step_number": 1,
  "estimated_total": 6,
  "purpose": "planning",
  "context": "Received PRD for user authentication system. Requirements include: email/password login, OAuth (Google, GitHub), session management, and password reset flow.",
  "thought": "This is a multi-phase feature. I need to identify dependencies and create a logical ordering. OAuth depends on basic auth infrastructure. Password reset depends on email service integration.",
  "outcome": "Identified three major phases: (1) Core auth infrastructure, (2) OAuth providers, (3) Supporting features (reset, session management)",
  "next_action": {
    "tool": "Read",
    "action": "Review existing codebase for auth patterns",
    "parameters": { "path": "src/auth" },
    "expectedOutput": "Current authentication structure and patterns"
  },
  "rationale": "Must understand existing patterns before planning implementation to ensure consistency"
}
```

### Expected Response

```json
{
  "status": "flow_think_in_progress",
  "step_number": 1,
  "estimated_total": 6,
  "completed": false,
  "total_steps_recorded": 1,
  "next_action": {
    "tool": "Read",
    "action": "Review existing codebase for auth patterns",
    "parameters": { "path": "src/auth" },
    "expectedOutput": "Current authentication structure and patterns"
  }
}
```

---

## Step 2: Architecture Analysis

```json
{
  "step_number": 2,
  "estimated_total": 6,
  "purpose": "analysis",
  "context": "Reviewed existing auth structure. Found: UserService, TokenManager, SessionStore. Uses JWT for tokens. No current OAuth support.",
  "thought": "Current architecture uses a clean service pattern. OAuth can be added as a new OAuthProvider interface with specific implementations. Session management already exists but needs extension for OAuth tokens.",
  "outcome": "Architecture allows extension. Will add: OAuthProvider interface, GoogleOAuthProvider, GitHubOAuthProvider, extend SessionStore for OAuth tokens",
  "next_action": "Define Phase 1 tasks for core infrastructure",
  "rationale": "Phase 1 establishes the foundation that OAuth providers will depend on",
  "confidence": 0.85,
  "files_referenced": ["src/auth/user-service.ts", "src/auth/token-manager.ts", "src/auth/session-store.ts"]
}
```

---

## Step 3: Phase 1 Task Breakdown

```json
{
  "step_number": 3,
  "estimated_total": 6,
  "purpose": "planning",
  "context": "Architecture analysis complete. Phase 1 focuses on core email/password authentication.",
  "thought": "Phase 1 needs: user model updates, password hashing, login endpoint, registration endpoint, session creation. TDD approach requires tests first.",
  "outcome": "Phase 1 tasks defined:\n1.1. Add password_hash field to User model\n1.2. Implement password hashing service (bcrypt)\n1.3. Create POST /auth/register endpoint\n1.4. Create POST /auth/login endpoint\n1.5. Add session creation on successful login\n1.6. Write integration tests for auth flow",
  "next_action": "Define Phase 2 tasks for OAuth integration",
  "rationale": "Phase 2 builds on Phase 1 infrastructure",
  "confidence": 0.9
}
```

---

## Step 4: Phase 2 Task Breakdown

```json
{
  "step_number": 4,
  "estimated_total": 6,
  "purpose": "planning",
  "context": "Phase 1 tasks defined. Phase 2 adds OAuth provider support.",
  "thought": "OAuth requires: provider interface, callback handling, token exchange, user creation/linking. Google and GitHub have different scopes but similar flows. Can create abstract base class.",
  "outcome": "Phase 2 tasks defined:\n2.1. Create OAuthProvider interface\n2.2. Implement OAuth callback route\n2.3. Add GoogleOAuthProvider\n2.4. Add GitHubOAuthProvider\n2.5. Implement user linking (OAuth to existing account)\n2.6. Add OAuth-specific session handling\n2.7. Integration tests for OAuth flows",
  "next_action": "Define Phase 3 tasks for supporting features",
  "rationale": "Phase 3 contains features that depend on both Phase 1 and 2",
  "confidence": 0.85
}
```

---

## Step 5: Phase 3 Task Breakdown

```json
{
  "step_number": 5,
  "estimated_total": 6,
  "purpose": "planning",
  "context": "Phases 1 and 2 defined. Phase 3 adds supporting features: password reset, session management UI.",
  "thought": "Password reset requires email service integration. Session management needs list/revoke endpoints. These are independent and can be parallelized.",
  "outcome": "Phase 3 tasks defined:\n3.1. Implement email service abstraction\n3.2. Create password reset token generation\n3.3. Add POST /auth/forgot-password endpoint\n3.4. Add POST /auth/reset-password endpoint\n3.5. Create GET /auth/sessions endpoint\n3.6. Add DELETE /auth/sessions/:id endpoint\n3.7. E2E tests for reset and session management",
  "next_action": "Create final implementation plan document",
  "rationale": "Consolidate all phases into structured plan.md for execution",
  "confidence": 0.9
}
```

---

## Step 6: Finalize Plan

```json
{
  "step_number": 6,
  "estimated_total": 6,
  "purpose": "planning",
  "context": "All phases defined with task breakdowns. Ready to create implementation plan.",
  "thought": "Plan needs: phase ordering, task dependencies, estimated effort, and acceptance criteria. TDD workflow means tests are included in each phase.",
  "outcome": "Implementation plan complete:\n- Phase 1: Core Auth (6 tasks, ~2 days)\n- Phase 2: OAuth (7 tasks, ~3 days)\n- Phase 3: Supporting (7 tasks, ~2 days)\nTotal: 20 tasks, ~7 days estimated",
  "next_action": {
    "tool": "Write",
    "action": "Create plan.md with structured task list",
    "parameters": { "path": ".agent/specs/auth-system/plan.md" },
    "expectedOutput": "Structured plan document ready for implementation"
  },
  "rationale": "Plan document enables tracking and execution of implementation",
  "is_final_step": true,
  "confidence": 0.95,
  "patterns_discovered": [
    "OAuth providers share common interface pattern",
    "Phase dependencies enable parallel execution within phases",
    "TDD integration tests should be last task per phase"
  ]
}
```

### Expected Response

```json
{
  "status": "flow_think_complete",
  "step_number": 6,
  "estimated_total": 6,
  "completed": true,
  "total_steps_recorded": 6,
  "next_action": {
    "tool": "Write",
    "action": "Create plan.md with structured task list",
    "parameters": { "path": ".agent/specs/auth-system/plan.md" },
    "expectedOutput": "Structured plan document ready for implementation"
  },
  "confidence": 0.95
}
```

---

## Tips for Planning with flow_think

1. **Start with requirements understanding** - First step should analyze and categorize requirements
2. **Identify dependencies early** - Look for what depends on what to order phases correctly
3. **Use confidence scoring** - Higher confidence as plan solidifies
4. **Track files examined** - Use `files_referenced` to document which files informed decisions
5. **Capture patterns** - Use `patterns_discovered` for reusable insights
6. **End with actionable output** - Final step should produce concrete deliverable

## Common Planning Patterns

### Breaking Down Large Features

```json
{
  "purpose": "planning",
  "thought": "Feature is too large for single phase. Decomposing into: infrastructure, core functionality, edge cases, polish"
}
```

### Identifying Technical Debt

```json
{
  "purpose": "analysis",
  "thought": "Existing code lacks proper separation of concerns. Plan should include refactoring task before new features.",
  "patterns_discovered": ["Existing service combines auth and session logic - should separate"]
}
```

### Estimating Effort

```json
{
  "purpose": "planning",
  "thought": "Based on similar past work and codebase complexity, estimating 2-3 hours per task. Buffer 20% for unknowns.",
  "confidence": 0.7,
  "uncertainty_notes": "OAuth complexity depends on existing session implementation"
}
```

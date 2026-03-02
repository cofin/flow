# Implementation Example: TDD Cycle

This example demonstrates using `flow_think` to track a Test-Driven Development implementation cycle.

## Scenario

Implementing a rate limiter service following TDD methodology: write failing test, implement to pass, refactor while green.

---

## Step 1: Understand Requirements

```json
{
  "step_number": 1,
  "estimated_total": 8,
  "purpose": "planning",
  "context": "Task: Implement rate limiter with sliding window algorithm. Requirements:\n- Limit: 100 requests per minute per user\n- Sliding window for smooth limiting\n- Redis-backed for distributed deployment\n- Return retry-after header when limited",
  "thought": "Before writing tests, need to understand the interface. Rate limiter should: check if request allowed, track request, return limit status with metadata.",
  "outcome": "Interface defined:\n- isAllowed(userId): Promise<RateLimitResult>\n- RateLimitResult: { allowed: boolean, remaining: number, resetAt: Date, retryAfter?: number }",
  "next_action": {
    "tool": "Read",
    "action": "Check existing service patterns",
    "parameters": { "path": "src/services" },
    "expectedOutput": "Service structure and patterns to follow"
  },
  "rationale": "Ensure new service follows existing patterns",
  "confidence": 0.9
}
```

---

## Step 2: Write First Failing Test (Red)

```json
{
  "step_number": 2,
  "estimated_total": 8,
  "purpose": "implement",
  "context": "Interface defined. Starting TDD cycle with simplest test case: allow request under limit.",
  "thought": "First test: Given fresh user, when checking rate limit, should allow request and show 99 remaining.",
  "outcome": "Test written:\n```typescript\ndescribe('RateLimiter', () => {\n  it('should allow request under limit', async () => {\n    const limiter = new RateLimiter(mockRedis);\n    const result = await limiter.isAllowed('user-123');\n    expect(result.allowed).toBe(true);\n    expect(result.remaining).toBe(99);\n  });\n});\n```\nTest fails: RateLimiter class doesn't exist.",
  "next_action": "Implement minimal code to pass test",
  "rationale": "TDD: Write just enough code to make test pass",
  "confidence": 0.95,
  "tools_used": ["Write", "Bash"],
  "files_referenced": ["src/services/rate-limiter.test.ts"]
}
```

---

## Step 3: Make Test Pass (Green)

```json
{
  "step_number": 3,
  "estimated_total": 8,
  "purpose": "implement",
  "context": "Test failing. Need to implement RateLimiter class.",
  "thought": "Implementing minimal code:\n1. Create RateLimiter class\n2. Implement isAllowed that returns hardcoded success\n3. Wire up Redis connection (won't use yet)",
  "outcome": "Implementation:\n```typescript\nexport class RateLimiter {\n  constructor(private redis: Redis) {}\n  \n  async isAllowed(userId: string): Promise<RateLimitResult> {\n    return {\n      allowed: true,\n      remaining: 99,\n      resetAt: new Date(Date.now() + 60000)\n    };\n  }\n}\n```\nTest passes.",
  "next_action": "Write test for limit exceeded scenario",
  "rationale": "Need to test the blocking case next",
  "confidence": 0.9,
  "tools_used": ["Write", "Bash"],
  "files_referenced": ["src/services/rate-limiter.ts"]
}
```

---

## Step 4: Add Limit Exceeded Test (Red)

```json
{
  "step_number": 4,
  "estimated_total": 8,
  "purpose": "implement",
  "context": "Happy path passes. Now testing the limit enforcement.",
  "thought": "Need to test: after 100 requests, 101st should be blocked with retry-after. Will mock Redis to simulate full bucket.",
  "outcome": "Test added:\n```typescript\nit('should block request when limit exceeded', async () => {\n  mockRedis.zcount.mockResolvedValue(100);\n  \n  const result = await limiter.isAllowed('user-123');\n  \n  expect(result.allowed).toBe(false);\n  expect(result.remaining).toBe(0);\n  expect(result.retryAfter).toBeGreaterThan(0);\n});\n```\nTest fails: Always returns allowed.",
  "next_action": "Implement sliding window logic with Redis",
  "rationale": "Real implementation requires Redis sorted set for sliding window",
  "confidence": 0.85,
  "tools_used": ["Write", "Bash"],
  "files_referenced": ["src/services/rate-limiter.test.ts"]
}
```

---

## Step 5: Implement Sliding Window (Green)

```json
{
  "step_number": 5,
  "estimated_total": 8,
  "purpose": "implement",
  "context": "Need actual sliding window implementation using Redis sorted sets.",
  "thought": "Sliding window algorithm:\n1. Remove entries older than window (60s)\n2. Count entries in window\n3. If count >= limit, deny\n4. Otherwise, add new entry and allow",
  "outcome": "Implementation:\n```typescript\nasync isAllowed(userId: string): Promise<RateLimitResult> {\n  const key = `ratelimit:${userId}`;\n  const now = Date.now();\n  const windowStart = now - 60000;\n  \n  // Remove old entries\n  await this.redis.zremrangebyscore(key, 0, windowStart);\n  \n  // Count current window\n  const count = await this.redis.zcount(key, windowStart, now);\n  \n  if (count >= this.limit) {\n    const oldest = await this.redis.zrange(key, 0, 0, 'WITHSCORES');\n    const retryAfter = Math.ceil((oldest[1] + 60000 - now) / 1000);\n    return { allowed: false, remaining: 0, resetAt: new Date(oldest[1] + 60000), retryAfter };\n  }\n  \n  // Add new entry\n  await this.redis.zadd(key, now, `${now}`);\n  await this.redis.expire(key, 61);\n  \n  return { allowed: true, remaining: this.limit - count - 1, resetAt: new Date(now + 60000) };\n}\n```\nAll tests pass.",
  "next_action": "Refactor for cleaner code",
  "rationale": "TDD cycle: Tests green, now safe to refactor",
  "confidence": 0.85,
  "tools_used": ["Write", "Bash"],
  "files_referenced": ["src/services/rate-limiter.ts"],
  "patterns_discovered": [
    "Sorted sets ideal for sliding window - O(log n) operations",
    "Always set TTL slightly longer than window to handle edge cases"
  ]
}
```

---

## Step 6: Refactor (Green)

```json
{
  "step_number": 6,
  "estimated_total": 8,
  "purpose": "implement",
  "context": "Tests passing. Code works but could be cleaner. Time to refactor.",
  "thought": "Refactoring opportunities:\n1. Extract window cleanup to separate method\n2. Add configuration for limit/window\n3. Use pipeline for atomic operations\n4. Add proper error handling",
  "outcome": "Refactored implementation:\n```typescript\nexport class RateLimiter {\n  constructor(\n    private redis: Redis,\n    private config: RateLimitConfig = { limit: 100, windowMs: 60000 }\n  ) {}\n  \n  async isAllowed(userId: string): Promise<RateLimitResult> {\n    const key = this.getKey(userId);\n    const now = Date.now();\n    \n    const [, count] = await this.redis.pipeline()\n      .zremrangebyscore(key, 0, now - this.config.windowMs)\n      .zcount(key, '-inf', '+inf')\n      .exec();\n    \n    if (count >= this.config.limit) {\n      return this.buildDeniedResult(key, now);\n    }\n    \n    return this.buildAllowedResult(key, now, count);\n  }\n  \n  private getKey(userId: string): string {\n    return `ratelimit:${userId}`;\n  }\n  // ... helper methods\n}\n```\nTests still passing.",
  "next_action": "Add edge case tests",
  "rationale": "Need to ensure boundary conditions are handled",
  "confidence": 0.9,
  "tools_used": ["Write", "Bash"],
  "files_referenced": ["src/services/rate-limiter.ts"]
}
```

---

## Step 7: Edge Case Tests

```json
{
  "step_number": 7,
  "estimated_total": 8,
  "purpose": "validation",
  "context": "Core logic refactored. Adding edge case tests for robustness.",
  "thought": "Edge cases to test:\n1. Exactly at limit (100th request)\n2. Redis connection failure\n3. Concurrent requests\n4. Clock skew handling",
  "outcome": "Edge case tests added:\n```typescript\nit('should allow exactly at limit', async () => {\n  mockRedis.zcount.mockResolvedValue(99);\n  const result = await limiter.isAllowed('user-123');\n  expect(result.allowed).toBe(true);\n  expect(result.remaining).toBe(0);\n});\n\nit('should handle Redis errors gracefully', async () => {\n  mockRedis.pipeline.mockImplementation(() => {\n    throw new Error('Connection refused');\n  });\n  \n  await expect(limiter.isAllowed('user-123'))\n    .rejects.toThrow('Rate limiter unavailable');\n});\n```\nAll tests pass including edge cases.",
  "next_action": "Write integration test with real Redis",
  "rationale": "Unit tests mock Redis - need integration test for confidence",
  "confidence": 0.9,
  "tools_used": ["Write", "Bash"],
  "files_referenced": ["src/services/rate-limiter.test.ts"]
}
```

---

## Step 8: Integration Test and Completion

```json
{
  "step_number": 8,
  "estimated_total": 8,
  "purpose": "validation",
  "context": "Unit tests complete. Running integration test with real Redis.",
  "thought": "Integration test validates:\n1. Real Redis operations work as expected\n2. Sliding window actually slides\n3. Concurrent requests handled correctly\n4. Performance acceptable (<5ms per check)",
  "outcome": "Integration test results:\n- All scenarios pass\n- P99 latency: 2.3ms\n- Concurrent test (100 parallel): No race conditions\n- Sliding window verified with time manipulation\n\nCoverage: 94% (missing error paths that require Redis failure)",
  "next_action": "Commit implementation with conventional commit message",
  "rationale": "Implementation complete and tested - ready to commit",
  "is_final_step": true,
  "confidence": 0.95,
  "tools_used": ["Bash"],
  "files_referenced": [
    "src/services/rate-limiter.ts",
    "src/services/rate-limiter.test.ts",
    "src/services/rate-limiter.integration.test.ts"
  ],
  "patterns_discovered": [
    "Pipeline operations are atomic in Redis - use for complex operations",
    "Always set key expiry slightly longer than window",
    "Mock at boundary (Redis client) for unit tests, real Redis for integration"
  ]
}
```

### Expected Response

```json
{
  "status": "flow_think_complete",
  "step_number": 8,
  "estimated_total": 8,
  "completed": true,
  "total_steps_recorded": 8,
  "next_action": "Commit implementation with conventional commit message",
  "confidence": 0.95
}
```

---

## Tips for Implementation with flow_think

1. **Follow TDD rhythm** - Alternate between Red (failing test) and Green (passing) states
2. **Track files modified** - Use `files_referenced` to document which files change each step
3. **Record tools used** - Write for code, Bash for tests - track the workflow
4. **Capture patterns** - TDD surfaces patterns; record them in `patterns_discovered`
5. **Refactor only when green** - Only refactor after tests pass
6. **Keep steps small** - One test or one small change per step

## Implementation Patterns

### Revising Earlier Implementation

```json
{
  "step_number": 6,
  "purpose": "implement",
  "revises_step": 3,
  "revision_reason": "Step 3 implementation had race condition in concurrent scenarios",
  "thought": "Adding mutex to prevent concurrent bucket updates for same user",
  "confidence": 0.8
}
```

### Handling Unexpected Test Failure

```json
{
  "step_number": 5,
  "purpose": "debug",
  "thought": "Test unexpectedly failing. Expected 99 remaining, got 98. Investigating...",
  "outcome": "Found off-by-one error in count calculation",
  "confidence": 0.7,
  "uncertainty_notes": "May be related to when entry is added vs when count happens"
}
```

### Parallel Task Implementation

```json
{
  "step_number": 4,
  "purpose": "implement",
  "thought": "These three tests are independent. Writing them in parallel.",
  "tools_used": ["Write"],
  "files_referenced": [
    "src/services/rate-limiter.test.ts",
    "src/services/rate-limiter.edge.test.ts",
    "src/services/rate-limiter.performance.test.ts"
  ],
  "confidence": 0.9
}
```

### Coverage Gap Identified

```json
{
  "step_number": 7,
  "purpose": "validation",
  "thought": "Coverage report shows untested error path in line 45-52",
  "outcome": "Added test for Redis timeout scenario",
  "external_context": {
    "coverage_before": "87%",
    "coverage_after": "94%",
    "untested_lines": [45, 46, 47, 48, 49, 50, 51, 52]
  },
  "confidence": 0.9
}
```

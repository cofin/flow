# Debug Example: Root Cause Analysis

This example demonstrates using `flow_think` to systematically debug an issue and identify root cause.

## Scenario

Users report intermittent "session expired" errors during checkout. The issue happens randomly and is hard to reproduce. We'll use structured debugging to find the root cause.

---

## Step 1: Gather Initial Evidence

```json
{
  "step_number": 1,
  "estimated_total": 6,
  "purpose": "debug",
  "context": "Bug report: Users get 'session expired' error during checkout. Happens ~5% of requests. No pattern in user type or browser. Started after last deployment (v2.4.1).",
  "thought": "Need to establish timeline and gather data. First, check what changed in v2.4.1. Also need to examine logs around failed requests.",
  "outcome": "Initial data gathered:\n- v2.4.1 changes: Updated Redis client, added session caching layer\n- Error logs show SessionNotFoundError at checkout/payment step\n- Errors cluster around 3am and 3pm UTC (redis maintenance windows?)",
  "next_action": {
    "tool": "Grep",
    "action": "Search for session handling in checkout flow",
    "parameters": { "pattern": "session|getSession|validateSession", "path": "src/checkout" },
    "expectedOutput": "Session usage points in checkout"
  },
  "rationale": "Need to understand how sessions are used in checkout to identify failure points",
  "hypothesis": "Session caching layer introduced in v2.4.1 has a bug",
  "verification_status": "pending",
  "confidence": 0.4
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
    "tool": "Grep",
    "action": "Search for session handling in checkout flow",
    "parameters": { "pattern": "session|getSession|validateSession", "path": "src/checkout" },
    "expectedOutput": "Session usage points in checkout"
  },
  "hypothesis": {
    "text": "Session caching layer introduced in v2.4.1 has a bug",
    "status": "pending"
  },
  "confidence": 0.4,
  "warnings": [{
    "level": "warning",
    "message": "Low confidence (0.4) - gather more evidence"
  }]
}
```

---

## Step 2: Trace the Error Path

```json
{
  "step_number": 2,
  "estimated_total": 6,
  "purpose": "debug",
  "context": "Found session usage in checkout:\n- checkout/cart.ts: getSession() on cart load\n- checkout/payment.ts: validateSession() before payment\n- checkout/confirm.ts: getSession() for order creation\n\nPayment step is where errors occur.",
  "thought": "The validateSession() in payment.ts is the failure point. Looking at the implementation:\n```typescript\nasync validateSession(sessionId: string) {\n  const cached = await this.cache.get(sessionId);\n  if (cached) return cached;\n  \n  const session = await this.redis.get(sessionId);\n  if (!session) throw new SessionNotFoundError();\n  \n  await this.cache.set(sessionId, session, TTL);\n  return session;\n}\n```\nCache-aside pattern. If cache miss AND redis miss, error thrown.",
  "outcome": "Identified potential race condition: If cache expires but Redis entry still exists, and there's a slight delay, user could get error. But this doesn't explain the 5% rate.",
  "next_action": {
    "tool": "Read",
    "action": "Check cache configuration and TTL settings",
    "parameters": { "path": "src/services/session-cache.ts" },
    "expectedOutput": "Cache configuration including TTL"
  },
  "rationale": "TTL mismatch between cache and Redis could cause the issue",
  "hypothesis": "Cache TTL is shorter than Redis session TTL causing premature cache eviction",
  "verification_status": "pending",
  "confidence": 0.6,
  "tools_used": ["Grep", "Read"]
}
```

---

## Step 3: Analyze TTL Configuration

```json
{
  "step_number": 3,
  "estimated_total": 6,
  "purpose": "debug",
  "context": "Examined cache configuration:\n- Session Redis TTL: 30 minutes\n- Cache TTL: 5 minutes\n- Cache is in-memory (node process local)\n\nWait - cache is process-local, not shared!",
  "thought": "CRITICAL FINDING: The cache is in-memory and not shared between pods. In Kubernetes, requests can hit different pods. If user's first request hits Pod A (which caches session), next request hits Pod B (no cache), Pod B checks Redis directly.\n\nBut this still shouldn't cause errors unless... checking if Redis read is failing.",
  "outcome": "Hypothesis refined: It's not cache vs Redis TTL. It's that Pod B might be reading from Redis replica that hasn't synced yet. Our Redis uses read replicas.",
  "next_action": {
    "tool": "Read",
    "action": "Check Redis connection configuration",
    "parameters": { "path": "config/redis.ts" },
    "expectedOutput": "Redis connection settings, especially replica config"
  },
  "rationale": "Redis replica lag could explain intermittent 'not found' errors",
  "hypothesis": "Redis replica lag causes session read to fail before replication completes",
  "verification_status": "pending",
  "confidence": 0.75,
  "revises_step": 2,
  "revision_reason": "Local cache isn't the issue - it's Redis replication lag"
}
```

---

## Step 4: Confirm Redis Configuration

```json
{
  "step_number": 4,
  "estimated_total": 6,
  "purpose": "validation",
  "context": "Redis configuration found:\n```typescript\nexport const redisConfig = {\n  master: { host: 'redis-master', port: 6379 },\n  replicas: [\n    { host: 'redis-replica-1', port: 6379 },\n    { host: 'redis-replica-2', port: 6379 }\n  ],\n  readFrom: 'replica',  // <-- READS GO TO REPLICAS\n  replicaLag: 100  // ms tolerance\n};\n```\n\nSessions are WRITTEN to master but READ from replicas!",
  "thought": "Found it! Session creation writes to master. validateSession reads from replica. With async replication, there's a window where session exists on master but not yet on replica.\n\nThis explains:\n- 5% rate (depends on replication lag timing)\n- Clustering around 3am/3pm (higher load = more lag)\n- Started in v2.4.1 (that's when 'readFrom: replica' was added)",
  "outcome": "ROOT CAUSE IDENTIFIED:\n1. Session created (writes to master)\n2. User proceeds quickly to payment\n3. validateSession reads from replica\n4. Replica hasn't received write yet\n5. Session not found -> error",
  "next_action": "Verify hypothesis by checking replication lag metrics",
  "rationale": "Need to confirm timing matches error occurrence",
  "hypothesis": "Redis replica lag causes session read to fail before replication completes",
  "verification_status": "pending",
  "confidence": 0.9,
  "tools_used": ["Read"],
  "patterns_discovered": [
    "Write-then-read-immediately pattern breaks with async replication",
    "Read replicas require careful consideration of consistency requirements"
  ]
}
```

---

## Step 5: Verify with Metrics

```json
{
  "step_number": 5,
  "estimated_total": 6,
  "purpose": "validation",
  "context": "Checking Prometheus metrics for Redis replication lag vs error occurrence.",
  "thought": "Correlation analysis:\n- redis_replication_lag_seconds p99: 150ms normally, spikes to 500ms at 3am/3pm\n- Session errors correlate exactly with lag spikes\n- User time from session creation to payment: median 2s, p5 is 200ms (fast users hit the bug)",
  "outcome": "Hypothesis CONFIRMED:\n- Fast checkout users (200ms) hit replication window\n- During high-lag periods, more users affected\n- Direct correlation between lag spikes and error rate",
  "next_action": "Design and implement fix",
  "rationale": "Root cause confirmed, need to implement solution",
  "hypothesis": "Redis replica lag causes session read to fail before replication completes",
  "verification_status": "confirmed",
  "confidence": 0.95,
  "tools_used": ["Bash"],
  "external_context": {
    "redis_lag_p99_normal": "150ms",
    "redis_lag_p99_peak": "500ms",
    "user_checkout_time_p5": "200ms",
    "error_correlation": 0.94
  }
}
```

---

## Step 6: Implement Fix

```json
{
  "step_number": 6,
  "estimated_total": 6,
  "purpose": "implement",
  "context": "Root cause confirmed. Need to fix without sacrificing read scaling benefits of replicas.",
  "thought": "Solution options:\n1. Read from master for session validation (defeats replica purpose)\n2. Add session ID to request context after creation (client-side, but needs client change)\n3. Use 'read-your-writes' consistency with session ID routing\n4. Add retry with master fallback on not-found\n\nOption 4 is least invasive and handles edge case properly.",
  "outcome": "Fix implemented:\n```typescript\nasync validateSession(sessionId: string) {\n  // Try replica first (fast path)\n  let session = await this.redis.replica.get(sessionId);\n  \n  // Fallback to master if not found (handles replication lag)\n  if (!session) {\n    session = await this.redis.master.get(sessionId);\n  }\n  \n  if (!session) throw new SessionNotFoundError();\n  return session;\n}\n```\n\nTest added to verify retry behavior. Deployed to staging.",
  "next_action": "Monitor staging for 24h, then deploy to production",
  "rationale": "Verify fix works in realistic environment before production",
  "is_final_step": true,
  "confidence": 0.95,
  "tools_used": ["Write", "Bash"],
  "files_referenced": [
    "src/services/session-service.ts",
    "src/services/session-service.test.ts"
  ],
  "patterns_discovered": [
    "Always consider replication lag for write-then-read patterns",
    "Master fallback provides consistency without sacrificing replica benefits",
    "Fast users are most likely to hit race conditions"
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
  "next_action": "Monitor staging for 24h, then deploy to production",
  "confidence": 0.95,
  "hypothesis": {
    "text": "Redis replica lag causes session read to fail before replication completes",
    "status": "confirmed"
  }
}
```

---

## Tips for Debugging with flow_think

1. **Form hypotheses early** - Even with low confidence, having a hypothesis focuses investigation
2. **Track verification status** - Move from pending -> confirmed/refuted as evidence accumulates
3. **Use revises_step** - When hypothesis changes, link back to the step being revised
4. **Capture external context** - Store metrics, logs, and data points for reference
5. **Build confidence incrementally** - Start low (0.3-0.4), increase as evidence confirms
6. **Record patterns** - Debugging surfaces systemic issues; capture them for prevention

## Debugging Patterns

### Refuting a Hypothesis

```json
{
  "step_number": 4,
  "purpose": "debug",
  "thought": "Hypothesis was wrong. Data shows no correlation between cache TTL and errors.",
  "hypothesis": "Cache TTL mismatch causing session loss",
  "verification_status": "refuted",
  "outcome": "Cache TTL is not the issue. Need new hypothesis.",
  "confidence": 0.3,
  "next_action": "Re-examine the error pattern with fresh perspective"
}
```

### Branching to Explore Alternative Cause

```json
{
  "step_number": 3,
  "purpose": "exploration",
  "branch_from": 2,
  "branch_id": "network-issue",
  "branch_name": "Investigate network connectivity",
  "thought": "While investigating cache, noticed some requests have high latency. Could be network issue instead.",
  "confidence": 0.4
}
```

### Escalating Urgency

```json
{
  "step_number": 5,
  "purpose": "debug",
  "thought": "Error rate increasing from 5% to 15%. Need to expedite investigation.",
  "outcome": "Identified temporary mitigation: route all session reads to master",
  "confidence": 0.7,
  "uncertainty_notes": "Mitigation will increase master load - monitor closely"
}
```

### Documenting Dead Ends

```json
{
  "step_number": 4,
  "purpose": "debug",
  "thought": "Investigated memory pressure hypothesis. Checked pod metrics - memory stable at 60%.",
  "outcome": "RULED OUT: Memory pressure is not causing the issue",
  "hypothesis": "Memory pressure causing session eviction",
  "verification_status": "refuted",
  "confidence": 0.9,
  "next_action": "Return to replication hypothesis"
}
```

### Capturing Root Cause Summary

```json
{
  "step_number": 6,
  "purpose": "reflection",
  "is_final_step": true,
  "outcome": "ROOT CAUSE SUMMARY:\n\nProblem: 5% of checkout sessions fail with 'session expired'\n\nCause: Redis read-replica lag during high-load periods\n\nTimeline:\n1. User creates session (written to master)\n2. User quickly proceeds to payment (<200ms)\n3. Payment validates session (reads from replica)\n4. Replica hasn't received write -> error\n\nFix: Master fallback on replica miss\n\nPrevention: Add replication lag monitoring alert",
  "patterns_discovered": [
    "Write-then-read patterns need consistency consideration",
    "P5 latency users reveal race conditions",
    "Load testing should include replication delay simulation"
  ]
}
```

## Debugging Checklist

Use this checklist structure in your debugging steps:

- [ ] Establish timeline (when did it start?)
- [ ] Quantify impact (how many users/requests?)
- [ ] Identify changes (what deployed recently?)
- [ ] Gather logs and metrics
- [ ] Form initial hypothesis
- [ ] Design verification test
- [ ] Confirm or refute hypothesis
- [ ] Implement and verify fix
- [ ] Document root cause and prevention

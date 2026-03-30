---
name: security-auditor
description: "Auto-activate when reviewing code that handles authentication, authorization, user input, secrets, API keys, database queries, file uploads, session management, or external API calls. Use when: security review needed, assessing attack surface, checking for OWASP vulnerabilities, reviewing access control logic, or auditing data handling."
---

# Security Auditor

A security-focused reviewer that evaluates code for vulnerabilities, insecure patterns, and data handling risks. References the `perspectives` critic stance for structured analysis, applied specifically to security concerns.

## Overview

This skill provides a security engineering perspective during review. It thinks like an attacker to find exploitable weaknesses, then like a defender to identify what's missing. It uses OWASP categories as the organizing framework and classifies findings by severity so the most critical issues are addressed first.

## Dispatch

Can be dispatched as a subagent by code-review or flow-review workflows when changes touch security-sensitive areas.

## Direct Invocation

- "Security audit this authentication flow"
- "Review this for OWASP vulnerabilities"
- "Check this input handling for injection risks"
- "Audit the data handling in this endpoint"

## How It Works

Apply the persona in `references/persona.md` and work through the checklist in `references/checklist.md`. For each finding, assign a severity (Critical/High/Medium/Low), explain the attack vector, and recommend the fix. If code is secure in a category, acknowledge it briefly and move on.

## References Index

- **[Persona](references/persona.md)** — Role, approach, scope, severity classification, and guardrails
- **[Security Checklist](references/checklist.md)** — Eight OWASP-informed review categories
- **[Critic Stance](../perspectives/references/stances.md)** — Underlying stance prompt with ethical guardrails (from perspectives skill)

---
name: presenting-install-menus
description: Use when optional tooling is missing and the agent should offer concise install, compatibility, or continue-without choices instead of a single hard requirement
---

# Presenting Install Menus

## Overview

When tooling is optional or has multiple backends, present a short menu instead of a hard stop. Keep the menu explicit about what changes are local, global, shared, or networked.

<workflow>

- Lead with the recommended option.
- Keep menus to 2-3 choices.
- Include a compatibility path when one exists.
- Include a continue-without option when degraded mode is viable.
- Say whether the action changes user-scoped config, project files, or both.
- Prefer `.git/info/exclude` over `.gitignore` for local-only defaults.

</workflow>

<guardrails>

- Do not present a hard requirement when degraded mode is acceptable.
- Do not bury the recommended option.
- Do not hide whether the action is global, workspace-scoped, or repo-scoped.
- Do not offer long, cluttered menus for simple setup choices.

</guardrails>

<validation>

Before presenting a setup menu, verify:

- [ ] The recommended option is listed first
- [ ] The menu has no more than 3 choices unless complexity truly requires it
- [ ] Compatibility and no-tool fallback paths are included when viable
- [ ] Scope and side effects are clearly stated

</validation>

<example>

```text
Beads backend

- A) Install official Beads (`bd`) (recommended)
  Uses the official CLI and keeps Flow on the default backend.
- B) Use beads_rust compatibility (`br`)
  Preserves older `br`-centric workflows when the repo already depends on them.
- C) Continue without Beads
  Keeps planning and docs available, but disables persistence-driven workflow features.
```

</example>

## When to Use

- Missing optional dependencies
- Backend migrations
- Host install/config onboarding
- Any setup flow where forcing one tool would increase admin burden

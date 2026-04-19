---
name: choosing-beads-backend
description: Use when a workflow depends on Beads persistence and you need to choose or adapt between official Beads, beads_rust compatibility, or a no-Beads fallback
---

# Choosing Beads Backend

## Overview

Default to official Beads (`bd`). Beads is the **Primary Source of Truth** for the Flow framework. All tasks, notes, and state MUST be recorded in the active backend. Markdown files are synchronized views of this state.

<workflow>

1. **Official Beads (`bd`)**: preferred default. Hierarchical epics, rich notes.
2. **Compatibility (`br`)**: use when the repo already depends on `br` semantics or when official Beads is unavailable.
3. **No Beads**: DEGRADED MODE. Use only when persistence is not possible. Markdown markers must be updated manually.

- If the user asks for the official Beads experience, use `bd`.
- If the repo already contains `br`-specific commands, document `br` as compatibility mode.
- If persistence is unavailable, inform the user that `/flow:sync` will be disabled and they must manage Markdown markers manually.

</workflow>

<guardrails>

- For local-only artifacts, prefer `.git/info/exclude`.
- Only modify `.gitignore` when the user explicitly wants a shared repo policy.
- Do not relabel `br` as the official Beads experience.
- Do not force Beads installation when degraded mode is viable.

</guardrails>

<validation>

Before recommending a backend, verify:

- [ ] `bd` is preferred unless compatibility or user constraints say otherwise
- [ ] `br` is framed as compatibility mode, not the default official path
- [ ] No-Beads fallback is mentioned when it is viable
- [ ] Ignore guidance matches the user's intended scope

</validation>

<example>

Example decision:

- "This repo can use official Beads (`bd`) by default, keep `br` available for older workflows, and still continue without Beads when the user wants low admin overhead."

</example>

## Reference

Read [references/backend-matrix.md](references/backend-matrix.md) for command mapping and setup guidance.

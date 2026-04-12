# Platform Alignment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Align Flow's host integration guidance around current official platform workflows, make official Beads (`bd`) the default backend, keep `br` and no-Beads fallbacks available, and minimize admin churn with `.git/info/exclude`-first local ignores.

**Architecture:** Introduce a small set of generic reusable skills for platform integration, Beads backend selection, and install-menu UX. Then update Flow's public docs, installer, and core workflow guidance to reference the new defaults while preserving host-specific differences where the platforms genuinely differ.

**Tech Stack:** Markdown, JSON, shell, JavaScript

---

## Design Summary

- Prefer official host install/update paths where they exist:
  - Claude Code: git-based marketplace install and update
  - Gemini CLI: native extension install and update from GitHub
  - Codex CLI: plugin manifest + marketplace mental model, with local-linked install guidance
  - OpenCode: local plugin files / project skills guidance instead of undocumented git URL config
  - Antigravity: workspace-local `.agents` guidance first, global fallback second
- Prefer official Beads (`bd`) as the default Flow backend.
- Keep `br` as a documented compatibility backend.
- Keep a no-Beads degraded mode for planning/docs-only workflows.
- Default local-only ignore behavior to `.git/info/exclude`.
- Only recommend `.gitignore` changes when the user explicitly wants shared repo policy.

### Task 1: Add reusable generic skills

**Files:**
- Create: `.agents/specs/platform-alignment/spec.md`
- Create: `.agents/specs/platform-alignment/metadata.json`
- Create: `.agents/specs/platform-alignment/learnings.md`
- Create: `skills/integrating-agent-platforms/SKILL.md`
- Create: `skills/integrating-agent-platforms/references/host-matrix.md`
- Create: `skills/choosing-beads-backend/SKILL.md`
- Create: `skills/choosing-beads-backend/references/backend-matrix.md`
- Create: `skills/presenting-install-menus/SKILL.md`

- [ ] Document the approved architecture and task breakdown in the Flow spec directory.
- [ ] Add a generic host-integration skill that captures install, update, cache, and local-vs-shared guidance across Claude, Gemini, Codex, OpenCode, and Antigravity.
- [ ] Add a generic Beads-backend skill that defines the default order: `bd`, `br`, `none`.
- [ ] Add a generic install-menu skill that standardizes concise menu-driven prompts for missing optional tooling.

### Task 2: Update public host-install guidance

**Files:**
- Modify: `README.md`
- Modify: `.opencode/INSTALL.md`
- Modify: `gemini-extension.json`

- [ ] Rewrite README install guidance to prefer official platform flows and describe update behavior explicitly.
- [ ] Replace the outdated OpenCode `opencode.json` git-url guidance with local plugin / skills guidance that matches current docs.
- [ ] Keep Gemini on a GitHub-backed extension lifecycle and reserve `link` for local development.
- [ ] Update the Gemini extension manifest to use `GEMINI.md` as the extension context file and keep AGENTS loading through the repo workflow rather than only the extension root.

### Task 3: Update Flow backend defaults

**Files:**
- Modify: `AGENTS.md`
- Modify: `skills/flow/SKILL.md`
- Modify: `skills/flow/references/setup.md`
- Modify: `skills/flow/references/implement.md`
- Modify: `templates/agent/workflow.md`

- [ ] Rewrite the Beads sections around backend modes: `bd` preferred, `br` compatibility, `none` degraded.
- [ ] Replace `.gitignore`-first local-ignore guidance with `.git/info/exclude`-first guidance.
- [ ] Add explicit cross-references to the new generic skills so Flow stops duplicating stale platform/backend rules.

### Task 4: Update installer behavior and UX

**Files:**
- Modify: `tools/install.sh`
- Modify: `.opencode/plugins/flow.js`
- Modify: `hooks/session-start`
- Modify: `hooks/pre-commit`

- [ ] Update installer messaging to explain install source, refresh behavior, and backend choices per host.
- [ ] Prefer non-interactive host-native install/update flows when available.
- [ ] Offer a menu for Beads backend selection that prioritizes `bd`, allows `br`, and supports continue-without-Beads.
- [ ] Avoid changing repo-wide ignore files in installer/setup defaults.
- [ ] Make hook behavior degrade safely when `bd` is present but `br`-specific sync is unavailable.

### Task 5: Verify documentation and behavioral consistency

**Files:**
- Test: `README.md`
- Test: `AGENTS.md`
- Test: `tools/install.sh`
- Test: `skills/integrating-agent-platforms/SKILL.md`
- Test: `skills/choosing-beads-backend/SKILL.md`
- Test: `skills/presenting-install-menus/SKILL.md`

- [ ] Run targeted searches for stale `br`-first install language in the touched files.
- [ ] Run shell syntax validation for `tools/install.sh`.
- [ ] Verify the new skills are concise, generic, and consistent with the actual repo behavior.


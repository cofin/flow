
# Flow Setup

Initialize a project for context-driven development backed by OKF v0.2 knowledge bundles under `.agents/bundles/`.

Use `presenting-install-menus` for concise install prompts.

## Phase 0: Environment Detection

**PROTOCOL: Before starting, check if the environment has already been detected via hooks.**

1. **Check Hook Context:** Look for Flow project context (`## Project Purpose`, `## Core Project Invariants`) in your `<hook_context>`. If present, the bundle already resolves.
2. **Manual Check (Fallback only):** Only if the hook context is missing or incomplete:

```bash
if [ -f ".agents/setup-state.json" ]; then
  cat .agents/setup-state.json
fi
```

**Treat setup as completed if** `setup_status` is `"complete"`.

**If setup is complete:** offer Align (recommended), Re-setup, or Exit — as in the `/flow:setup` command.

**If state exists with incomplete step:** Offer to resume from last successful step.

**If no state exists:** Continue with full setup.

---

## Phase 0.1: Alignment Mode

**PROTOCOL: Validate existing setup and update to latest best practices.**

### 0.1.1 Legacy Layout Migration

Scan for legacy locations: `specs/` or `.agents/specs/` spec trees, flat context files (`.agents/product.md`, `.agents/tech-stack.md`, `.agents/workflow.md`, `.agents/patterns.md`, `.agents/knowledge/`, `.agents/code-styleguides/`), and legacy task-tracker artifacts (`.agents/beads.json`, `.beads/`, `metadata.json`).

Offer migration into `.agents/bundles/`: specs to `bundles/specs/<flow_id>/spec.md` with OKF frontmatter (`type: Spec`, `flow_id`, `title`, `state`, timestamps; map legacy status in_progress→active, completed→completed, else planned), flat context files into the matching `knowledge/` chapter with `type:` frontmatter, styleguides into `knowledge/` (as `<topic>-style.md` chapters). Delete migrated `metadata.json` files and, after user confirmation, legacy tracker config — task state now lives in the bundle files. Do not create `flows.md` or `metadata.json` files.

### 0.1.1b Remove Legacy Tracker Machinery

Offer each removal explicitly: delete `.git/hooks/pre-commit` when it contains tracker sync logic; delete `.beads/` and `.agents/beads.json` after confirmation; note the legacy `bd` binary is no longer used and may be uninstalled.

### 0.1.1c Scrub Tracker Instructions from Context Files

Scan `AGENTS.md`/`CLAUDE.md`/`GEMINI.md`, `.claude/settings.local.json` (`Bash(bd:*)` allowlist entries), `opencode.json`, and `.cursor/rules/*.mdc` for tracker-era instructions or legacy `.agents/specs/` paths. Show each proposed edit; replace with bundle equivalents or remove on approval (merge, back up, never clobber).

### 0.1.2 Learnings Ingestion

Validate existing `learnings.md` files against the current codebase and merge confirmed patterns into `.agents/bundles/knowledge/patterns.md`.

### 0.1.3 Core Artifacts Check

Check for `product/product.md` and `product/tech-stack.md`. Ensure they exist, carry `type: Guide` frontmatter, and contain `<!-- truth: start -->` and `<!-- truth: end -->` markers. Keep each truth block focused (≤ 40 lines) — the session hook extracts a bounded excerpt, so broader wraps are silently truncated.

### 0.1.4 Workflow Revalidation & Sync

**PROTOCOL: Synchronize the workflow chapter with the latest template while preserving local "truth" markers.**

1. Read the existing `knowledge/workflow.md`.
2. Extract content between `<!-- truth: start -->` and `<!-- truth: end -->`.
3. Replace the rest of the file with the latest `templates/agent/workflow.md`.
4. If markers are missing, offer to add them based on existing "Essential Commands" and "Guiding Principles".
5. Inspect the repo's real command surfaces (`Makefile`, `package.json`, etc.) to propose canonical command updates.

### 0.1.4b Knowledge Resynthesis

Migration is complete only after RE-synthesis: rewrite migrated chapters as coherent current-state documentation — merge duplicates across old flat files and knowledge chapters, resolve contradictions against the actual codebase, drop stale notes, no dated entries or flow attributions (history lives in `log.md`). Present restructured chapters for approval.

### 0.1.4c Spec Review Against the Codebase

For each migrated `planned`/`active` spec, verify task `state` values against source reality (`files:` exist, `tests:` pass, behavior implemented); propose corrections and reconcile the checklist.

### 0.1.5 Bundle Integrity Check

Confirm `.agents/bundles/index.md` declares `okf_version: "0.2"`, `log.md` exists, every non-reserved bundle markdown file has a non-empty `type:`, and no task file stores workflow state in `status:` (move such values to `state:`).

### 0.1.6 Policy & Context Validation

**PROTOCOL: Ensure planning policies and harness-specific context/settings files are present for every detected harness.**

- **Antigravity:** Confirm Flow is installed through Antigravity's native plugin and skills surfaces. Do not create project-local legacy extension files.
- **Claude Code:** Check for `CLAUDE.md` in the project root. If missing, offer to create it from the latest template to provide project context and rules. Also run **Phase 7.5.1** (re-merge Flow-recommended `.claude/settings.local.json` keys without clobbering user entries).
- **OpenCode:** Run **Phase 7.5.2** (re-merge Flow-recommended `opencode.json` keys).
- **Codex CLI:** Announce the trust-prompt recommendation from **Phase 7.5.3**. Do not write to `~/.codex/config.toml`.

Each prompt remains opt-in (Yes/Skip). Reruns are idempotent - every Phase 7.5 step deduplicates and merges.

### 0.1.7 Alignment Summary

Provide a clear summary of all updates performed, including bundle integrity, workflow sync status, spec migration counts, policy/context updates, and validation results.

**After alignment, HALT (don't continue to full setup).**

---

## Phase 1: Project Detection

Detect brownfield vs greenfield (existing code, build files, `.agents/` presence). The Flow root is always `.agents/` with bundles at `.agents/bundles/`; relocations go through `.agents/config.json` (`bundles_dir`, `knowledge_dir`) only when the user asks for a nonstandard layout.

---

## Phase 2: Context Gathering (Interactive)

Ask the user ONE AT A TIME, as in the `/flow:setup` command:

- **Product definition** → `product/product.md` (`type: Guide`, truth markers around the summary)
- **Product guidelines** → `product/product-guidelines.md` (`type: Guide`)
- **Tech stack** (detect first, confirm) → `product/tech-stack.md` (`type: Guide`, truth markers around the core list)
- **Workflow preferences** (coverage target, commit format, CI, canonical commands, bundle tracking policy) → `knowledge/workflow.md` from `templates/agent/workflow.md` with the repo's real commands merged in. Do not leave generic placeholders when canonical commands already exist.

---

## Phase 3: Style & Convention Chapters

Offer styleguides from `templates/styleguides/` for detected languages; copy selected into `knowledge/` (as `<topic>-style.md` chapters) as `type: Pattern` chapters alongside `patterns.md`.

---

## Phase 4: Create the Bundle Skeleton

Create:

- `.agents/bundles/index.md` - Bundle root index (`okf_version: "0.2"`)
- `.agents/bundles/log.md` - Dated change log with a creation entry
- `.agents/bundles/knowledge/patterns.md` - Patterns template (`type: Pattern`)
- `.agents/bundles/skills/flow-memory-keeper/SKILL.md` - Project-local memory/refinement skill

```bash
mkdir -p .agents/bundles/{specs,product,knowledge,research} .agents/bundles/skills/flow-memory-keeper
```

Copy `templates/agent/skills/flow-memory-keeper/SKILL.md` into `.agents/bundles/skills/flow-memory-keeper/SKILL.md`.

---

## Phase 5: Git Configuration

**PROTOCOL: Ask whether the knowledge bundle is shared (tracked) or private (local-only). Prefer `.git/info/exclude` for local-only entries; touch `.gitignore` only for explicit shared policy.**

- **Shared** (recommended for teams): track `.agents/bundles/` (and `.agents/config.json`); exclude the rest of `.agents/` locally.
- **Local-only:** append `.agents/` to `.git/info/exclude`.

Always APPEND, never overwrite. Never force-add ignored Flow files.

---

## Phase 7.5: Harness Policy Bootstrap (Cross-Harness)

**PROTOCOL: Detect installed agentic harnesses and OFFER (opt-in) to merge Flow-recommended settings into each harness's policy file.**

### 7.5.0 Harness Detection

```bash
detected=()
command -v claude   >/dev/null 2>&1 || [ -d "$HOME/.claude" ]                && detected+=("claude")
command -v opencode >/dev/null 2>&1 || [ -d "$HOME/.config/opencode" ]       && detected+=("opencode")
command -v codex    >/dev/null 2>&1 || [ -d "$HOME/.codex" ]                 && detected+=("codex")
command -v antigravity >/dev/null 2>&1 || [ -d "$HOME/.gemini/antigravity-cli" ] && detected+=("antigravity")
```

For each detected harness, run the matching subsection. **Skip Codex auto-write** — Codex's first-session trust prompt covers this case; just announce the recommendation.

### 7.5.1 Claude Code

> **Configure Claude Code for this Flow project?**
>
> Adds `plansDirectory` (so Plan Mode artifacts land in `.agents/bundles/specs/`) and a workflow-derived `permissions.allow` allowlist to `.claude/settings.local.json` (gitignored — per-developer).
>
> - **A) Yes** (recommended)
> - **B) Skip**

If A, MERGE into `.claude/settings.local.json` (NEVER clobber). Use `jq` when available.

**Computed allow entries** = read-only base ∪ workflow-derived:

- **Read-only base (always included):** `Read`, `Grep`, `Glob`, `LS`, `WebFetch`, `WebSearch`, `Bash(git status)`, `Bash(git diff:*)`, `Bash(git log:*)`, `Bash(ls:*)`, `Bash(cat:*)`, `Bash(grep:*)`, `Bash(rg:*)`, `Bash(wc:*)`, `Bash(find:*)`
- **Workflow-derived (from `knowledge/workflow.md`):** parse the "Essential Commands" section. For each canonical command (e.g. `make lint`, `make test`, `make check`, `bun test`, `bun run build:*`, `uv run pytest`, `npx vitest`, `cargo test`), add `Bash(<first-token>:*)`. Deduplicate against base.

**Merge recipe (jq):**

```bash
mkdir -p .claude
[ -f .claude/settings.local.json ] || echo '{}' > .claude/settings.local.json
cp .claude/settings.local.json .claude/settings.local.json.bak

new_allow_json='[ "Read","Grep","Glob","LS","WebFetch","WebSearch","Bash(git status)","Bash(git diff:*)","Bash(git log:*)","Bash(ls:*)","Bash(cat:*)","Bash(grep:*)","Bash(rg:*)","Bash(wc:*)","Bash(find:*)" /* + workflow-derived entries */ ]'

jq --argjson new "$new_allow_json" '
  .plansDirectory //= ".agents/bundles/specs" |
  .permissions = ((.permissions // {}) + {
    allow: ((((.permissions.allow) // []) + $new) | unique)
  })
' .claude/settings.local.json > .claude/settings.local.json.tmp \
  && mv .claude/settings.local.json.tmp .claude/settings.local.json
```

> **Critical rules**
>
> - Never overwrite. Always merge.
> - Always back up to `settings.local.json.bak` before touching the file.
> - `.claude/settings.local.json` is gitignored by Claude convention — do NOT add it to `.gitignore` again, and do NOT force-add it.

**Announce:** "Merged Flow-recommended Claude settings into `.claude/settings.local.json` (backed up previous version)."

### 7.5.2 OpenCode

> **Configure OpenCode for this Flow project?**
>
> Adds a `permission` block with sensible defaults and points OpenCode's `instructions` at Flow's truth files. Merges into `opencode.json` at the project root.
>
> - **A) Yes** (recommended)
> - **B) Skip**

If A, MERGE into `opencode.json`:

```bash
[ -f opencode.json ] || echo '{}' > opencode.json
cp opencode.json opencode.json.bak

jq '
  .permission = ((.permission // {}) + {edit: "ask", bash: "ask"}) |
  .instructions = (((.instructions // []) + ["AGENTS.md", ".agents/bundles/product/product.md", ".agents/bundles/product/tech-stack.md"]) | unique)
' opencode.json > opencode.json.tmp && mv opencode.json.tmp opencode.json
```

> **Critical rules**
>
> - Never overwrite existing `permission` keys (only add missing).
> - Deduplicate `instructions` with `unique` so reruns are idempotent.
> - `opencode.json` may be committed (team policy) or local-only (`.git/info/exclude`). Honor the user's existing ignore decision; do not change it.

**Announce:** "Merged Flow-recommended OpenCode settings into `opencode.json` (backed up previous version)."

### 7.5.3 Codex CLI

Codex configuration lives in the global `~/.codex/config.toml` (per-user, not per-project). Codex prompts for project trust on first session, so Flow does NOT auto-write here.

**Announce:** "Codex CLI detected. On your first Codex session in this project, accept the trust prompt to mark this directory `trusted`. Flow does not modify your global `~/.codex/config.toml`."

### 7.5.4 Antigravity

If running under Antigravity, prefer the native plugin and skills install flow. The workspace hook config installs at `.agents/hooks.json`; subagents install at `.agents/agents/`. Flow should not write legacy extension policy files.

---

## Phase 8: First Flow (Optional)

> **Would you like to create your first flow?**
> Describe what you want to build.

If yes, invoke `flow-prd` with description.

---

## Phase 9: Save State

Save setup state to `.agents/setup-state.json`:

```json
{
  "setup_status": "complete",
  "last_successful_step": "complete",
  "project_type": "brownfield|greenfield",
  "workflow_revision": "flow-template-v2",
  "timestamp": "ISO timestamp"
}
```

---

## Final Summary

```text
Flow Setup Complete

Bundle: .agents/bundles/ (OKF v0.2)

Created:
- index.md, log.md
- product/product.md
- product/product-guidelines.md
- product/tech-stack.md
- knowledge/workflow.md
- knowledge/patterns.md (+ style chapters)
- skills/flow-memory-keeper/SKILL.md
- specs/

Next Steps:
1. Run `flow-prd "description"` to create your first flow
2. Run `flow-implement {flow_id}` to start coding
```

---

## Critical Rules

1. **BUNDLE FIRST** - All context and task state lives in `.agents/bundles/` OKF files; no task database or CLI
2. **TYPED FRONTMATTER** - Every non-reserved bundle markdown file gets a non-empty `type:` key
3. **FIXED ROOT** - `.agents/` is the root; relocations go through `.agents/config.json` only
4. **ONE QUESTION AT A TIME** - Don't overwhelm the user
5. **DETECT FIRST** - Auto-detect tech stack before asking
6. **LOCAL EXCLUDES FIRST** - Prefer `.git/info/exclude` before `.gitignore`
7. **SAVE STATE** - Enable resume if interrupted
8. **NO FORCE-ADD** - If a Flow file is ignored, do not force-add it to a commit
9. **REVALIDATE EXISTING INSTALLS** - Existing installs must be offered workflow refresh/update, not just syntax checks
10. **PREFER REPO-NATIVE COMMANDS** - Capture and reuse canonical commands like `make lint`, `make test`, `make check`, `just check`, or equivalent wrappers

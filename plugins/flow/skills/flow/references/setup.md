
# Flow Setup

Initialize a project for context-driven development with Beads integration.

Use `presenting-install-menus` for concise install prompts.

## Phase 0: Environment Detection

**PROTOCOL: Before starting, check if the environment has already been detected via hooks.**

1. **Check Hook Context:** Look for `## Flow Environment Context` in your `<hook_context>`.
    - If **Flow Root** is present, use that as the authoritative root directory.
    - If **Beads Backend** is present and NOT `Missing`, note the active backend.
2. **Manual Check (Fallback only):** Only if the hook context is missing or incomplete, perform the following:

Resolve the configured Flow root first:

```bash
if [ -f ".agents/setup-state.json" ]; then
  cat .agents/setup-state.json
elif [ -f "specs/setup-state.json" ]; then
  cat specs/setup-state.json
fi
```

**Treat setup as completed if either of these is true:**

- `setup_status` is `"complete"`
- legacy `last_successful_step` is `"complete"` or `"3.3_initial_prd_generated"`

**If setup is complete:**

> **Existing Flow setup detected. What would you like to do?**
>
> - **A) Align** (recommended) - Validate and update to latest best practices
> - **B) Re-setup** - Start fresh (preserves existing specs)
> - **C) Exit** - Keep current setup

**If A (Align) selected:** Jump to **Phase 0.1: Alignment Mode**

**If B (Re-setup) selected:** Continue to Phase 1 (will skip existing files unless changed)

**If C (Exit) selected:** Announce "Setup unchanged." and HALT

**If state exists with incomplete step:** Offer to resume from last successful step.

**If no state exists:** Continue to Phase 1.

---

## Phase 0.1: Alignment Mode

**PROTOCOL: Validate existing setup and update to latest best practices.**

### 0.1.1 Beads Validation

```bash
command -v bd >/dev/null 2>&1 && echo "BD_OK" || echo "BEADS_MISSING"
```

Use official Beads (`bd`). Allow no-Beads degraded mode when the user wants less administrative overhead.

### 0.1.2 Legacy Specs Migration

Scan for legacy spec locations and offer migration to the current root. Update the registry and Beads backend accordingly.

### 0.1.3 Learnings Ingestion

Validate existing `learnings.md` files against the current codebase and merge confirmed patterns into `patterns.md`.

### 0.1.4 Core Artifacts Check

Check for `product.md` and `tech-stack.md`. Ensure they exist and contain `<!-- truth: start -->` and `<!-- truth: end -->` markers. Keep each truth block focused (≤ 40 lines) — the session-start hook caps extracted output at 40 lines per block, so broader wraps are silently truncated.

### 0.1.5 Workflow Revalidation & Sync

**PROTOCOL: Synchronize workflow.md with the latest template while preserving local "truth" markers.**

1. Read the existing `workflow.md`.
2. Extract content between `<!-- truth: start -->` and `<!-- truth: end -->`.
3. Replace the rest of the file with the latest `templates/agent/workflow.md`.
4. If markers are missing, offer to add them based on existing "Essential Commands" and "Guiding Principles".
5. Inspect the repo's real command surfaces (`Makefile`, `package.json`, etc.) to propose canonical command updates.

### 0.1.6 Knowledge Base Check

Check for missing `.agents/knowledge/` directory and ensure `knowledge/index.md` exists.

### 0.1.7 Policy & Context Validation

**PROTOCOL: Ensure Plan Mode policies and host-specific context/settings files are present for every detected host.**

- **Gemini CLI:** Check for `.gemini/policies/flow-overrides.toml`. If missing or outdated, offer to create it to allow common development tools in Plan Mode.
- **Claude Code:** Check for `CLAUDE.md` in the project root. If missing, offer to create it from the latest template to provide project context and rules. Also run **Phase 7.5.1** (re-merge Flow-recommended `.claude/settings.local.json` keys without clobbering user entries).
- **OpenCode:** Run **Phase 7.5.2** (re-merge Flow-recommended `opencode.json` keys).
- **Codex CLI:** Announce the trust-prompt recommendation from **Phase 7.5.3**. Do not write to `~/.codex/config.toml`.

Each prompt remains opt-in (Yes/Skip), matching the existing Gemini pattern. Reruns are idempotent — every Phase 7.5 step deduplicates and merges.

### 0.1.8 Configuration Validation

Check and update:

- `<root_directory>/beads.json` - Ensure valid configuration
- `<root_directory>/setup-state.json` - Update `workflow_revision` and status

### 0.1.9 Alignment Summary

Provide a clear summary of all updates performed, including Beads version, workflow sync status, spec migration counts, policy/context updates, and configuration validation results.

**After alignment, HALT (don't continue to full setup).**

---

## Phase 1: Beads Installation Check

**CRITICAL:** Prefer official Beads, but do not force unnecessary admin work.

```bash
if command -v bd >/dev/null 2>&1; then
  echo "BD_OK"
else
  echo "BEADS_MISSING"
fi
```

If no backend is found, ask user:

> **Beads backend**
>
> - **A) Install official Beads (`bd`)** (recommended)
> - **B) Continue without Beads** (degraded mode)

If installed, verify the backend version is current.

---

## Phase 1.5: Configure Root Directory

**PROTOCOL: Ask user where to store Flow specification files.**

> **Where would you like to store Flow specification files?**
>
> - **A) `.agents/`** (Recommended - hidden from project root)
> - **B) `specs/`** (Visible at project root)
> - **C) Custom path** (Type your own)

**Store Configuration:** Based on user's choice, set `root_directory` variable.

- Default to `.agents/` if A selected
- Use `specs/` if B selected
- Use custom path if C selected

**Create Directory:**

```bash
mkdir -p <root_directory>
```

**All subsequent file paths use `<root_directory>` instead of hardcoded `.agents/`.**

---

## Phase 2: Project Detection

Detect if this is a brownfield (existing) or greenfield (new) project:

1. Check for existing code: `src/`, `lib/`, `app/`, `packages/`
2. Check for build files: `package.json`, `pyproject.toml`, `Cargo.toml`, `go.mod`
3. Check for existing `<root_directory>` directory

**Output**: "Detected: [Brownfield|Greenfield] project"

---

## Phase 3: Context Gathering (Interactive)

Ask the user these questions ONE AT A TIME:

### 3.1 Product Definition

> **What is this project?**
> Describe your product in 2-3 sentences. Include:
>
> - What problem it solves
> - Who it's for
> - Key differentiator

Write response to `<root_directory>/product.md`

### 3.2 Product Guidelines

> **What are your brand/style guidelines?**
> Include:
>
> - Tone of voice
> - Visual style preferences
> - Any constraints or requirements

Write response to `<root_directory>/product-guidelines.md`

### 3.3 Tech Stack

> **What technologies are you using?**
> Include:
>
> - Languages (Python, TypeScript, Rust, etc.)
> - Frameworks (Litestar, React, etc.)
> - Database (PostgreSQL, SQLite, etc.)
> - Package manager (uv, npm, bun, cargo)

Detect from existing files if possible, then confirm with user.

Write response to `<root_directory>/tech-stack.md`

### 3.4 Workflow Preferences

> **What are your development preferences?**
>
> - Test coverage target? (default: 80%)
> - Commit message format? (default: conventional commits)
> - CI integration? (GitHub Actions, GitLab CI, etc.)
> - Canonical repo commands for setup, lint, test, typecheck, and full verification?
> - Local-only or shared ignore policy for Flow artifacts?

Before asking, inspect the repo's real command surfaces and copy the workflow template with those commands merged into it. Do not leave generic placeholders when canonical commands already exist.

---

## Phase 4: Code Styleguides

Based on detected languages, offer relevant styleguides:

1. List detected languages
2. Show available styleguides from `templates/styleguides/`
3. Ask user which to include
4. Copy selected to `<root_directory>/code-styleguides/`

---

## Phase 5: Beads Initialization

**CRITICAL: Configure for local-only use by default.**

Derive a slugged prefix from the repo name:

```bash
repo_slug="$(basename "$(git rev-parse --show-toplevel 2>/dev/null || pwd)" | tr '[:upper:]' '[:lower:]' | tr -cs 'a-z0-9' '-' | sed 's/^-//; s/-$//')"
```

Official default:

```bash
bd init --non-interactive --stealth --prefix "$repo_slug" --skip-agents
bd config set no-git-ops true
bd config set export.auto false
bd config set export.git-add false
```

Flow owns the host instruction files, so Beads setup must skip its generated agent files.
The config commands keep Beads local-only by default: no automatic export, no auto-staging, and no git operations in `bd prime` output.

Opt the project into the bd v2.0 JSON envelope so `bd --json` stops printing the deprecation notice on every command. Append the Viper key idempotently to `.beads/config.yaml`:

```bash
mkdir -p .beads
if [ ! -f .beads/config.yaml ] || ! grep -q '^json-envelope:' .beads/config.yaml; then
  printf 'json-envelope: true\n' >> .beads/config.yaml
fi
```

bd 1.x reads the toggle only from `BD_JSON_ENVELOPE`; flow's hooks export that during sessions. Writing the YAML key now records the intent in version-controllable form so the project is ready when beads wires the toggle through Viper.

Or prompt user:

> **Beads mode:**
>
> - **Local-only** (recommended) - Add ignores to `.git/info/exclude`
> - **Team** - Commit to repo for team sharing

Create `<root_directory>/beads.json` with local-only configuration from `templates/agent/beads.json`, including `syncPolicy.allowDoltPush: false`.

---

## Phase 6: Create Supporting Files

Create:

- `<root_directory>/index.md` - File resolution index
- `<root_directory>/flows.md` - Empty flow registry
- `<root_directory>/patterns.md` - Empty patterns template
- `<root_directory>/knowledge/index.md` - Knowledge base index (from template)
- `<root_directory>/skills/flow-memory-keeper/SKILL.md` - Project-local memory/refinement skill

```bash
mkdir -p <root_directory>/knowledge <root_directory>/skills/flow-memory-keeper
```

Copy `knowledge/index.md` from the Flow templates (`templates/agent/knowledge/index.md`).
Copy `templates/agent/skills/flow-memory-keeper/SKILL.md` into `<root_directory>/skills/flow-memory-keeper/SKILL.md`.

---

## Phase 7: Local Ignore Configuration (Optional)

**PROTOCOL: Prefer `.git/info/exclude` for local-only defaults.**

### 7.1 Local Exclude Configuration

> **Would you like to keep Flow artifacts local-only?**
>
> - **A) Yes** (recommended) - Use `.git/info/exclude`
> - **B) Shared** - Update `.gitignore` for the whole repo

**If A selected:**

1. Check if `.git/info/exclude` already has the entries:

    ```bash
    [ -f ".git/info/exclude" ] && grep -q "<root_directory>" .git/info/exclude && echo "ALREADY_EXISTS" || echo "NEEDS_UPDATE"
    ```

2. **CRITICAL: APPEND only, never overwrite:**

    ```bash
    printf '\n# Flow specification files (local-only)\n<root_directory>/\n.beads/\n' >> .git/info/exclude
    ```

---

## Phase 7.5: Host Policy Bootstrap (Cross-Host)

**PROTOCOL: Detect installed agentic hosts and OFFER (opt-in) to merge Flow-recommended settings into each host's policy file. Mirrors what `commands/flow/setup.toml` already does for Gemini, but for Claude Code and OpenCode.**

### 7.5.0 Host Detection

```bash
detected=()
command -v claude   >/dev/null 2>&1 || [ -d "$HOME/.claude" ]                && detected+=("claude")
command -v opencode >/dev/null 2>&1 || [ -d "$HOME/.config/opencode" ]       && detected+=("opencode")
command -v codex    >/dev/null 2>&1 || [ -d "$HOME/.codex" ]                 && detected+=("codex")
# Gemini is handled by commands/flow/setup.toml Phase 3.4 — do not duplicate here.
```

For each detected host, run the matching subsection. **Skip Codex auto-write** — Codex's first-session trust prompt covers this case; just announce the recommendation.

### 7.5.1 Claude Code

> **Configure Claude Code for this Flow project?**
>
> Adds `plansDirectory` (so Plan Mode artifacts land in `<root_directory>/specs/`) and a workflow-derived `permissions.allow` allowlist to `.claude/settings.local.json` (gitignored — per-developer).
>
> - **A) Yes** (recommended)
> - **B) Skip**

If A, MERGE into `.claude/settings.local.json` (NEVER clobber). Use `jq` when available.

**Computed allow entries** = read-only base ∪ workflow-derived:

- **Read-only base (always included):** `Read`, `Grep`, `Glob`, `LS`, `WebFetch`, `WebSearch`, `Bash(bd:*)`, `Bash(git status)`, `Bash(git diff:*)`, `Bash(git log:*)`, `Bash(ls:*)`, `Bash(cat:*)`, `Bash(grep:*)`, `Bash(rg:*)`, `Bash(wc:*)`, `Bash(find:*)`
- **Workflow-derived (from `<root_directory>/workflow.md`):** parse the "Essential Commands" section. For each canonical command (e.g. `make lint`, `make test`, `make check`, `bun test`, `bun run build:*`, `uv run pytest`, `npx vitest`, `cargo test`), add `Bash(<first-token>:*)`. Deduplicate against base.

**Merge recipe (jq):**

```bash
mkdir -p .claude
[ -f .claude/settings.local.json ] || echo '{}' > .claude/settings.local.json
cp .claude/settings.local.json .claude/settings.local.json.bak

new_allow_json='[ "Read","Grep","Glob","LS","WebFetch","WebSearch","Bash(bd:*)","Bash(git status)","Bash(git diff:*)","Bash(git log:*)","Bash(ls:*)","Bash(cat:*)","Bash(grep:*)","Bash(rg:*)","Bash(wc:*)","Bash(find:*)" /* + workflow-derived entries */ ]'

jq --argjson new "$new_allow_json" '
  .plansDirectory //= "<root_directory>/specs" |
  .permissions = ((.permissions // {}) + {
    allow: ((((.permissions.allow) // []) + $new) | unique)
  })
' .claude/settings.local.json > .claude/settings.local.json.tmp \
  && mv .claude/settings.local.json.tmp .claude/settings.local.json
```

If `jq` is unavailable, use a Python helper:

```bash
python3 - <<'PY'
import json, pathlib
p = pathlib.Path(".claude/settings.local.json")
data = json.loads(p.read_text()) if p.exists() else {}
data.setdefault("plansDirectory", "<root_directory>/specs")
perms = data.setdefault("permissions", {})
existing = set(perms.get("allow", []))
new = [...]  # base + workflow-derived
perms["allow"] = sorted(existing | set(new))
p.write_text(json.dumps(data, indent=2) + "\n")
PY
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

# Use ${root_directory} in shell expansion; below shows .agents.
jq '
  .permission = ((.permission // {}) + {edit: "ask", bash: "ask"}) |
  .instructions = (((.instructions // []) + ["AGENTS.md", "<root_directory>/product.md", "<root_directory>/tech-stack.md"]) | unique)
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

### 7.5.4 Gemini CLI

If running under Gemini, defer to `commands/flow/setup.toml` Phase 3.4 (writes `.gemini/policies/flow-overrides.toml` and configures `.geminiignore`). Do not duplicate Gemini writes from this skill phase.

---

## Phase 8: First Flow (Optional)

> **Would you like to create your first flow?**
> Describe what you want to build.

If yes, invoke `flow-prd` with description.

---

## Phase 9: Save State

Save setup state to `<root_directory>/setup-state.json`. Store `root_directory` **without a trailing slash** (e.g. `.agents`, not `.agents/`) — the session-start hook concatenates paths from this value, and a trailing slash produces `.agents//product.md`:

```json
{
  "setup_status": "complete",
  "last_successful_step": "complete",
  "project_type": "brownfield|greenfield",
  "root_directory": ".agents",
  "workflow_revision": "flow-template-v1",
  "timestamp": "ISO timestamp"
}
```

---

## Final Summary

```text
Flow Setup Complete

Directory: <root_directory>

Created:
- product.md
- product-guidelines.md
- tech-stack.md
- workflow.md
- beads.json
- index.md
- flows.md
- patterns.md
- knowledge/index.md
- code-styleguides/

Next Steps:
1. Load the active backend state (`bd`) or continue in no-Beads mode
2. Run `flow-prd "description"` to create your first flow
3. Run `flow-implement {flow_id}` to start coding
```

---

## Phase 8: Install Git Hooks

**PROTOCOL: Install pre-commit hook to automate Beads sync.**

Copy the `pre-commit` hook to the `.git/hooks/` directory to ensure Bead states remain synchronized before any commit:

```bash
if [ -f ~/.flow/hooks/pre-commit ]; then
  cp ~/.flow/hooks/pre-commit .git/hooks/pre-commit
  chmod +x .git/hooks/pre-commit
elif [ -f ~/.gemini/extensions/flow/tools/scripts/hooks/pre-commit ]; then
  cp ~/.gemini/extensions/flow/tools/scripts/hooks/pre-commit .git/hooks/pre-commit
  chmod +x .git/hooks/pre-commit
fi
```

Review official Beads git/LLM hook support before relying on Flow-specific hooks long-term. Prefer upstream Beads or host-native hooks when they already cover the lifecycle cleanly.

---

## Critical Rules

1. **BEADS MODE FIRST** - Use `bd`, allow no-Beads when admin overhead should stay low
2. **CLI CHECK** - Ensure the chosen backend is installed and available
3. **ROOT DIRECTORY PROMPT** - Ask user where to store files
4. **LOCAL DEFAULT** - Configure Beads for local-only use
5. **ONE QUESTION AT A TIME** - Don't overwhelm the user
6. **DETECT FIRST** - Auto-detect tech stack before asking
7. **LOCAL EXCLUDES FIRST** - Prefer `.git/info/exclude` before `.gitignore`
8. **SAVE STATE** - Enable resume if interrupted
9. **NO FORCE-ADD** - If a Flow file is ignored, do not force-add it to a commit
10. **REVALIDATE EXISTING INSTALLS** - Existing installs must be offered workflow refresh/update, not just syntax checks
11. **PREFER REPO-NATIVE COMMANDS** - Capture and reuse canonical commands like `make lint`, `make test`, `make check`, `just check`, or equivalent wrappers

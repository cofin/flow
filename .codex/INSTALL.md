# Installing Flow for Codex

Flow ships as a native Codex plugin via marketplace.

## Prerequisites

- Codex CLI 0.117.0+ (with marketplace support; verify with `codex --version`)
- [Beads CLI](https://github.com/steveyegge/beads) (or [`beads_rust`](https://github.com/Dicklesworthstone/beads_rust) for compatibility)

## Install

```bash
codex plugin marketplace add cofin/flow
```

In a Codex session, run `/plugins` and enable Flow.

## Update

```bash
codex plugin marketplace upgrade flow-marketplace
```

## Uninstall

```bash
codex plugin marketplace remove flow-marketplace
```

## Usage

Codex plugins do not currently expose plugin-defined `/flow:*` slash commands. Use Flow through natural-language requests:

```
Use Flow to set up this project
Use Flow to create a PRD for user authentication
Use Flow to implement the current flow with TDD
```

The Flow skill responds to all `/flow:*` intents (`setup`, `prd`, `plan`, `implement`, `sync`, `status`, `refresh`, `research`, `docs`, etc.).

## Recommended Codex settings

In `~/.codex/config.toml`, set plan-mode reasoning effort high (Codex has no plugin-author hook for an artifact-directory equivalent to Gemini's `plan.directory`):

```toml
plan_mode_reasoning_effort = "high"
```

---

<details>
<summary>Manual / repo-scoped install (legacy)</summary>

Use this only if your environment can't reach `cofin/flow` via the native marketplace command (private fork, air-gapped network, team policy).

### Repo-scoped (team)

1. Clone Flow into your project:

   ```bash
   git clone https://github.com/cofin/flow.git plugins/flow
   ```

2. Create `.agents/plugins/marketplace.json` at the repo root:

   ```json
   {
     "name": "local-plugins",
     "interface": { "displayName": "Project Plugins" },
     "plugins": [
       {
         "name": "flow",
         "source": { "source": "local", "path": "./plugins/flow" },
         "policy": { "installation": "AVAILABLE" },
         "category": "Development"
       }
     ]
   }
   ```

3. Restart Codex. Run `/plugins` to verify Flow appears.

### Personal

1. Clone Flow:

   ```bash
   git clone https://github.com/cofin/flow.git ~/.codex/plugins/flow
   ```

2. Create `~/.agents/plugins/marketplace.json`:

   ```json
   {
     "name": "personal-plugins",
     "interface": { "displayName": "Personal Plugins" },
     "plugins": [
       {
         "name": "flow",
         "source": { "source": "local", "path": "~/.codex/plugins/flow" },
         "policy": { "installation": "AVAILABLE" },
         "category": "Development"
       }
     ]
   }
   ```

3. Restart Codex. Run `/plugins` to verify Flow appears.

### Updating a manual install

```bash
cd ~/.codex/plugins/flow && git pull
```

</details>

<details>
<summary>Migrating from pre-marketplace symlink installs</summary>

If you previously installed Flow via symlinks under `~/.codex/prompts/` or `~/.codex/skills/`, remove the old artifacts before running the marketplace install:

```bash
rm -f ~/.codex/prompts/flow-*.md
rm -rf ~/.codex/skills/flow ~/.codex/skills/beads
sed -i '/^# Flow Framework/,$d' ~/.codex/AGENTS.md 2>/dev/null
```

</details>

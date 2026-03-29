# Installing Flow for Codex

Enable Flow skills and commands in Codex via the native plugin system.

## Prerequisites

- Codex CLI 0.117.0+ (with plugin support)
- [Beads CLI](https://github.com/Dicklesworthstone/beads_rust)

## Installation

### Option 1: Plugin Install (Recommended)

Tell Codex:

> Fetch and follow instructions from https://raw.githubusercontent.com/cofin/flow/refs/heads/main/.codex/INSTALL.md

Codex will clone the repo, register the plugin, and make all Flow skills and commands available.

### Option 2: Repo-Scoped (Team)

1. Clone Flow into your project:

   ```bash
   git clone https://github.com/cofin/flow.git plugins/flow
   ```

2. Create marketplace entry at `.agents/plugins/marketplace.json`:

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

### Option 3: Personal

1. Clone Flow:

   ```bash
   git clone https://github.com/cofin/flow.git ~/.codex/plugins/flow
   ```

2. Create marketplace entry at `~/.agents/plugins/marketplace.json`:

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

## Migrating from Legacy Install

If you previously installed Flow via symlinks (`~/.codex/prompts/`, `~/.codex/skills/`), remove the old artifacts:

```bash
rm -f ~/.codex/prompts/flow-*.md
rm -rf ~/.codex/skills/flow ~/.codex/skills/beads
# Remove Flow section from AGENTS.md if present
sed -i '/^# Flow Framework/,$d' ~/.codex/AGENTS.md 2>/dev/null
```

## Updating

```bash
cd ~/.codex/plugins/flow && git pull
```

## Uninstalling

Remove the plugin directory and marketplace entry:

```bash
rm -rf ~/.codex/plugins/flow
```

## Usage

Flow skills and commands are available via Codex's native skill system:

```
/flow:setup    — Initialize project
/flow:prd      — Create feature roadmap
/flow:plan     — Plan single flow
/flow:implement — Execute tasks (TDD)
/flow:sync     — Sync Beads to spec
/flow:status   — Show progress
/flow:refresh  — Refresh context from codebase
```

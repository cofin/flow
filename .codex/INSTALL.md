# Installing Flow for Codex

Enable Flow skills and commands in Codex via native discovery and instruction following.

## Prerequisites

- Git
- [Beads CLI](https://github.com/Dicklesworthstone/beads_rust)

## Installation

1. **Clone the Flow repository:**

   ```bash
   git clone https://github.com/cofin/flow.git ~/.codex/flow
   ```

2. **Create the skills symlink:**

   ```bash
   mkdir -p ~/.agents/skills
   ln -s ~/.codex/flow/skills ~/.agents/skills/flow
   ```

3. **Install Flow commands/prompts:**

   ```bash
   mkdir -p ~/.codex/prompts
   ln -s ~/.codex/flow/templates/codex/prompts/* ~/.codex/prompts/
   ```

4. **Add Flow context to your AGENTS.md:**

   ```bash
   cat ~/.codex/flow/templates/codex/AGENTS.md >> ~/.codex/AGENTS.md
   ```

5. **Restart Codex** to discover the skills and prompts.

## Updating

```bash
cd ~/.codex/flow && git pull
```

## Uninstalling

```bash
rm ~/.agents/skills/flow
rm ~/.codex/prompts/flow-*
```

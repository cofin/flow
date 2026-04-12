# Backend Matrix

## Official Beads (`bd`)

- Preferred install:
  - `brew install beads`
  - `curl -fsSL https://raw.githubusercontent.com/steveyegge/beads/main/scripts/install.sh | bash`
- Preferred setup:
  - `repo_slug="$(basename "$(git rev-parse --show-toplevel 2>/dev/null || pwd)" | tr '[:upper:]' '[:lower:]' | tr -cs 'a-z0-9' '-' | sed 's/^-//; s/-$//')"`
  - `bd init --stealth --prefix "$repo_slug"`
  - `bd setup <host>` when the host supports official Beads integration
- Preferred session pattern:
  - `bd prime`
  - `bd ready --json`
  - `bd update ... --claim`
  - `bd close ...`

## beads_rust Compatibility (`br`)

- Preferred install:
  - `curl -fsSL https://raw.githubusercontent.com/Dicklesworthstone/beads_rust/main/install.sh | bash`
- Preferred setup:
  - `repo_slug="$(basename "$(git rev-parse --show-toplevel 2>/dev/null || pwd)" | tr '[:upper:]' '[:lower:]' | tr -cs 'a-z0-9' '-' | sed 's/^-//; s/-$//')"`
  - `br init --prefix "$repo_slug"`
- Typical session pattern:
  - `br status`
  - `br ready`
  - `br update <id> --status in_progress`
  - `br close <id> --reason "commit: <sha>"`
  - `br sync --flush-only`

## No-Beads Fallback

- Keep Flow usable for:
  - specs
  - plans
  - research
  - docs
- Disable or soften claims about:
  - cross-session persistence
  - dependency-aware ready queues
  - automatic Beads sync
- Use git history and `.agents/specs/` artifacts as the lightweight fallback state.

## Local-Only Ignore Default

- Prefer:

```bash
printf '\n# Flow local-only artifacts\n.beads/\n.agents/\n' >> .git/info/exclude
```

- Use `.gitignore` only when the user wants the ignore policy committed for the whole team.

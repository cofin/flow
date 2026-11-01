# Single-File Validator Template

Replace sprawling multi-script `tools/` directories with a single zero-dependency Python stdlib `tools/validate.py` script paired with a clean `Makefile`.

## What `tools/validate.py` Should Audit

1. **Manifest Version Synchronization**:
   Verify that `pyproject.toml`, `package.json`, `plugin.json`, `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `.codex-plugin/plugin.json`, `.cursor-plugin/plugin.json`, and `.agents/plugins/marketplace.json` all exist and declare the exact same semantic version string.
2. **Harness Manifest Schemas**:
   - Root `plugin.json` contains only allowed Antigravity keys (`$schema`, `name`, `displayName`, `version`, `description`, `contextFileName`, `excludeTools`, `skills`, `agents`, `rules`, `mcpServers`, `apps`).
   - `.agents/plugins/marketplace.json` points `plugins[0].source.path` to `"./"` (no duplicate `plugins/<name>/` mirror).
   - `package.json` points `"main"` to `".opencode/plugins/<name>.js"`.
3. **Hook & Runtime Checks**:
   - `hooks.json`, `hooks/hooks-claude.json`, and `hooks/hooks-cursor.json` exist, parse as valid JSON, and reference `hooks/session-start.sh`.
   - Executing `sh hooks/session-start.sh --harness agy|claude|cursor` returns exit code `0` and valid JSON matching each harness's expected output keys (`injectSteps`, `hookSpecificOutput`, `additional_context`).
4. **Skill Inventory, Frontmatter, & `24 KB` Size Cap**:
   - Every `skills/<name>/SKILL.md` is `< 24,000` bytes, declares `name: <name>` and `description: Use when ...` (`<= 500` chars), contains the required structural sections (`Workflow`, `Guardrails`, `Validation`, `Example`), and has zero broken relative Markdown links.
5. **Subagent Parity (`agents/*.md` & `.codex/agents/*.toml`)**:
   - Every `agents/<name>.md` has a matching `.codex/agents/<name>.toml`.
   - Every `agents/<name>.md` declares `model: inherit`, `mainAgent: false`, `subagent: true`, `commandExecutionPolicy`, `skills:` as a YAML list, and top-level `# ` H1 section headers (`# Role & Identity`, `# Responsibilities`, `# Verification & Constraints`, `# Output Contract`).
   - Read-only reviewer subagents declare `readonly: true` and `disallowedTools` as a YAML list containing `Edit`, `Write`, `MultiEdit`, and `NotebookEdit`.
6. **Anti-Sprawl Guardrails**:
   - Assert that retired duplicate paths (`plugins/<name>`, `commands`, `CLAUDE.md`, `.github/agents`, `.opencode/agents`, `skills/*/agents/openai.yaml`) do not exist.
7. **OKF v0.2 Bundle Validation (`--bundle <path>`)**:
   - When `--bundle <path>` is passed (or when `.agents/bundles/` is present), validate `index.md` (`okf_version: "0.2"`), reserved `index.md`/`log.md` frontmatter keys, `generated`/`verified` provenance blocks, `sources` footnote resolution (`[^id]`), and `specs/<flow_id>/spec.md` + `tasks/*.md` frontmatter.

## Minimal `Makefile` Pattern

```makefile
MARKDOWN_GLOBS := "skills/**/*.md" "agents/*.md" "rules/*.md" "templates/**/*.md" "AGENTS.md" "README.md"

lint:
    npx --yes markdownlint-cli2 $(MARKDOWN_GLOBS)
    uv run ruff check tools/ tests/
    uv run ruff format --check tools/ tests/
    uv run mypy tools/ tests/
    uv run pyright tools/ tests/

validate:
    uv run python tools/validate.py

test:
    uv run pytest

check:
    $(MAKE) lint
    $(MAKE) validate
    $(MAKE) test
```

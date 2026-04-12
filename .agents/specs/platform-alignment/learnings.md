# Platform Alignment Learnings

## [2026-04-12 00:00] - Initial design

- **Learning:** Host integration guidance had drifted because platform rules were duplicated across README, installer, Flow docs, and OpenCode-specific files.
- **Pattern:** Platform install/update/caching behavior should live in generic skills first, then Flow should reference those skills instead of restating every platform detail.
- **Gotcha:** Local-only ignore defaults should prefer `.git/info/exclude` to reduce repo churn.

## [2026-04-12 11:45] - Ignore and Terraform defaults

- **Learning:** `.geminiignore` is more reliable when it inherits the repo's `.gitignore` baseline and then explicitly re-includes agent context such as `.agents/`, `AGENTS.md`, `GEMINI.md`, and `CLAUDE.md`.
- **Pattern:** If a setup artifact is ignored by git, Flow should leave it unstaged and never use `git add -f` to force it into a commit.
- **Pattern:** Brownfield Terraform should default to `infra/terraform/` with separate directories and state per environment/root instead of CLI workspaces for environment separation.

## [2026-04-12 12:05] - User frustration as knowledge signal

- **Learning:** When the user has to repeat a correction or sounds frustrated that something obvious was forgotten, that is not just conversational feedback; it is evidence of a missing workflow default.
- **Pattern:** Repeated user corrections or frustration should be captured in `learnings.md`, elevated into `.agents/patterns.md`, and reflected in `.agents/skills/flow-memory-keeper/SKILL.md` so the same miss becomes less likely in future iterations.

# Pull Requests, Commits, & Changelogs

Standards for authoring clean pull requests, signed Git commits, release changelogs, GitHub issues, and inline code reviews.

## Pull Request Titles & Bodies

### 1. Title Format

Use conventional commit syntax:

```text
<type>(<scope>): <concise summary>
```

Examples:

- `feat(skills): add flow-learn and flow-docs skills`
- `fix(hooks): resolve workspace path from stdin in Antigravity sessionStart`
- `refactor(validate): consolidate manifest and OKF checks into single script`

### 2. Body Structure (`## Summary` + `## Key Changes` Only)

Keep PR descriptions focused on *what* changed and *why*, grouped cleanly by module or adapter:

```markdown
## Summary

Consolidate multi-harness plugin manifests into a single root layout, replace the write-ahead state journal with direct Markdown and Git tracking, and add `flow-learn` and `flow-docs`.

## Key Changes

### Harness Manifests & Hooks
- **Added**: Native `.cursor-plugin/plugin.json` manifest and pure POSIX `sh` `hooks/session-start.sh` entrypoint.
- **Changed**: Pointed `.agents/plugins/marketplace.json` to `./` and upgraded `.opencode/plugins/flow.js` to OpenCode V2.
- **Removed**: Duplicate `plugins/flow/` mirror, `commands/` wrappers, and root `CLAUDE.md`.

### Skills & Lifecycle References
- **Added**: `flow-learn` (`/flow:learn`), `flow-docs` (`/flow:docs`), and `multi-harness-plugins`.
- **Changed**: Simplified `skills/flow/references/state.md` to track task state directly in `tasks/*.md` frontmatter and `spec.md` checklists.
```

### 3. What Never Belongs in a PR Body

- **No `## Verification` section** or pasted terminal test outputs.
- **No `## Merge Danger`, `**Door:**`, `**Blast Radius:**`, or ASCII diff-sketch file/call trees.**
- **No multi-PR stack navigation tables.**
- **No internal audit or workflow ceremony** (finding counts, severity tallies, task IDs like `TASK-1.2` or `ORA-001`, `[ai-review-remediation:...]`, or subagent mechanics).
- **No internal product/CLI names, local workstation paths, or customer names.**

## Git Commits & Branch Discipline

- **Signed Commits**: Always commit with `git commit -S` (ensure `commit.gpgsign` is `true`).
- **Exact Path Staging**: Stage explicit file paths (`git add <path1> <path2>`); never run blind `git add -A` or `git add .` when untracked or unrelated files exist.
- **Incremental Branch Pushes**: When updating or restacking PR branches, push each branch after `make lint` passes rather than batch-pushing multiple branches at once.
- **Never Merge on the User's Behalf**: Push the branch, report the clickable PR link (`[#123](https://github.com/<owner>/<repo>/pull/123)`), and let the user review and merge.

## Changelogs (`docs/changelog.rst` / `CHANGELOG.md`)

- **Omit Redundant Version Bump Lines**: The release section header already states the version number; never add a bullet saying "Bump version to X.Y.Z".
- **Document User-Visible Impact**: Group entries under `Added`, `Changed`, `Fixed`, and `Removed` with exact class/function names and PR links.
- **Include CI Action Bumps**: Record GitHub Actions dependency updates under `Changed:`.

## GitHub Issues & Teammate PR Reviews

- **Clickable PR & Issue Links**: Always format any PR `#` or Issue `#` in chat responses as a clickable Markdown link to its GitHub URL.
- **Authorship Guardrail**: Never edit PR bodies or close PRs not authored by the user, and always prompt for confirmation before commenting on, reviewing, or pushing to any PR or issue authored by someone else.
- **Creating GitHub Issues**: Describe the high-level feature or product ask rather than low-level implementation details. Split multi-area requests into separate focused issues, and attach the target milestone, assignee, `type/*` + `area/*` labels, and native GitHub `IssueType` (`Feature` or `Bug`).
- **Reviewing a Teammate's PR**:
  - Never push commits directly to the author's PR branch.
  - Post line-anchored inline PR review comments with GitHub `suggestion` blocks targeting exact `path` and `line`/`start_line` in the diff rather than a single monolithic comment.
  - When replying to multiple review comments on your own PR, reply to each comment individually (linking to the comment and listing the exact files/changes made) rather than posting a single consolidated reply.
  - Keep all review comments calm, constructive, and matter-of-fact (no `!`).

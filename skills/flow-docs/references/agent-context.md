# Agent Context & Cross-Harness Configuration

Standards for authoring low-token agent instructions (`AGENTS.md`, `.agents/skills/*/SKILL.md`, `.agents/agents/*.md`, `.codex/agents/*.toml`, `.agents/rules/*.md`, `.agents/bundles/knowledge/**/*.md`, and local MCP configs) across Google Antigravity, Claude Code, Codex CLI, Cursor, OpenCode V2, and VS Code.

## Project-Local Discovery Matrix (`.agents/` & Repo Configs)

See the canonical cross-harness discovery table (`AGENTS.md`, skills, subagents, hooks, and MCP config paths) in [`multi-harness-plugins`](../../multi-harness-plugins/SKILL.md#project-local-discovery-matrix-agents--repo-local-configs).

### Universal Project Rules

- **Single `AGENTS.md` Baseline**: Never place a `CLAUDE.md` file alongside `AGENTS.md` unless `CLAUDE.md` explicitly imports `@AGENTS.md`. Claude Code suppresses `AGENTS.md` when `CLAUDE.md` exists, while Cursor loads both and duplicates prompt tokens.
- **Project MCP Naming Limits**: Keep MCP server keys (`<= 12` chars) and tool names (`<= 30` chars) short (`^[a-zA-Z0-9_-]+$`) so combined tool names stay well under Cursor's `59`-character limit and Google Antigravity's `64`-character limit (`mcp_<plugin>_<server>_<tool>`). In `.agents/mcp_config.json`, always keep `command` as a bare executable name (`"uv"`, `"node"`, `"sh"`) and pass paths inside `args` or `cwd`.

## Context Load vs. Cognitive Load

Every line in an agent instruction system trades off two costs:

- **Context Load**: Tokens that stay loaded in the model's context window on every turn (`AGENTS.md`, skill `description:` frontmatter, and `<!-- truth: start -->` blocks). High context load crowds out working memory and degrades instruction-following across the session.
- **Cognitive Load**: What the developer or routing skill must remember to invoke explicitly when a document has no automatic discovery pointer.

### Budgeting Rules

1. **`AGENTS.md` (`<= 100` lines)**: Treat `AGENTS.md` as a map of **context pointers** plus canonical developer commands (build, lint, typecheck, and test checks). Never paste full styleguides or multi-page architecture manuals into `AGENTS.md`.
2. **`<!-- truth: start -->` Blocks (`<= 40` lines)**: Session-start priming extracts only bounded truth blocks from `product/product.md`, `product/product-guidelines.md`, `product/tech-stack.md`, `knowledge/workflow.md`, and `knowledge/patterns/*.md`. Keep truth blocks tight (`<= 40` lines of non-negotiable invariants) and place detailed examples below `<!-- truth: end -->`.
3. **`SKILL.md` (`<= 200` lines, `< 24,000` bytes)**: Google Antigravity truncates `SKILL.md` files past `24,000` bytes, silently dropping `Guardrails` and `Validation` sections at the bottom of oversized files. Inline only the universal backbone in `SKILL.md` and disclose branch-specific procedures into `references/*.md`.

## Information Hierarchy & Progressive Disclosure

Organize every skill and knowledge bundle across three disclosure levels:

| Level | Location | When to Use |
| --- | --- | --- |
| **In-File Steps** | `SKILL.md` `## Workflow` | The sequential backbone followed on every invocation of the skill. |
| **In-File Reference** | `SKILL.md` tables & `## Guardrails` | Shared schemas, invariants, or decision tables that every branch in `SKILL.md` consults. |
| **Disclosed Reference** | `references/<branch>.md` or `knowledge/<area>/<topic>.md` | Branch-specific procedures, checklists, or deep domain catalogs loaded only when the agent takes that branch. |

- **Progressive Disclosure by Branching**: When a skill has distinct modes (such as migrations, query builders, and pooling in a database skill), place each branch's procedure in `references/<branch>.md`. Link to it from the branch step.
- **Co-Location**: Keep a concept's definition, rules, and edge cases together under a single heading. Never scatter caveats for a step into a miscellaneous `"Notes"` or `"Tips"` section at the bottom of the file.

## Context Pointers (`description:` & Index Tables)

A skill's `description:` frontmatter (or an `index.md` row) is a **context pointer**: its sole job is to tell the model *when* to load the file.

1. **Front-Load Trigger Words**: Start with `"Use when..."` (`<= 500` characters) and name the exact files, modules, commands, or situations that should fire the skill.
2. **One Trigger Per Distinct Branch**: Ensure every major branch inside the skill has a trigger phrase in the pointer so the skill fires for all of its branches.
3. **Cut Identity the Body Already Carries**: Do not waste pointer tokens explaining *how* the skill works internally; save the mechanics for `SKILL.md`.
4. **Model-Invoked vs. User-Invoked (`disable-model-invocation: true`)**:
   - Omit `disable-model-invocation` on domain and review skills (`.agents/skills/<domain>/`, `.agents/skills/review-<domain>/`) so the agent auto-discovers and activates them from task context.
   - Set `disable-model-invocation: true` on explicit slash-command workflows that should only run when directly invoked by the user.

## Universal Subagent Format (`.agents/agents/<name>.md`)

Format project-local Markdown subagents so they parse cleanly across all supported harnesses:

```yaml
---
name: api-reviewer
description: "Review API routes, DTO schemas, and public-interface tests for contract compliance."
model: inherit
mainAgent: false
subagent: true
readonly: true
commandExecutionPolicy: sandbox
skills:
  - api
  - review-api
disallowedTools:
  - Write
  - Edit
  - MultiEdit
  - NotebookEdit
  - write_file
  - edit_file
---
```

- **Top-Level H1 (`# `) Headings**: Google Antigravity splits subagent Markdown bodies into system-prompt sections only on top-level H1 (`# Header`) lines (`##` headings collapse into a single fallback section). Use `# Role & Identity`, `# Responsibilities`, `# Verification & Constraints`, and `# Output Contract`, with `###` for subsections.
- **`mainAgent: false` + `subagent: true` & Sandboxed Verification**: Keeps specialized reviewers out of the primary agent dropdown while keeping them invokable via subagent tools and `run_workflow`. Pair `commandExecutionPolicy: sandbox` with `readonly: true` and `disallowedTools` so read-only reviewers can run `git diff`. On Google Antigravity, invoke subagents with `type_name="self"` pointing at `agents/<role>.md` or `.agents/agents/<name>.md` so read, shell, search, and MCP tools stay available.
- **Cross-Harness `Stop` Checks**: Pair `SessionStart` priming with `Stop` hooks (`hooks/stop-check.{sh,ps1}` and OpenCode `ctx.session.hook("context", ...)`). They verify checklist parity, `last_reviewed_commit` stamps, and present-tense roadmap sync before ending a turn.
- **YAML List `tools` / `disallowedTools`**: Always format tool lists as YAML arrays (`- Edit`). Never use comma-separated strings (`tools: Read, Grep`), which fail YAML list unmarshaling and silently drop the subagent.
- **Inherit Model**: Always set `model: inherit` for cross-harness compatibility.

## Completion Criteria & Positive Framing

- **Completion Criteria Drive Legwork**:
  - Weak completion criteria (`"Review the module and update docs as needed"`) invite premature completion.
  - Strong completion criteria combine **Clarity** (an explicit checklist of postconditions) and **Demand** (concrete outputs like `[N/N files documented]`, an `ADOPT` / `CONTEST` / `ESCALATE` review summary, or exit code `0` from the check).
- **Use Plain Technical Terms**:
  - Prefer direct engineering terms—`deep module`, `adapter`, `idempotent`, `public interface`, `fast failing test`—over long explanations or coined jargon.
- **Frame Instructions Positively**:
  - Negation (`"Don't write tests in separate remediation files"`) forces the model to activate the forbidden pattern first. Lead with the positive target (`"Place all new unit tests inside the canonical module test file tests/<module>/test_<unit>.py"`), then state the boundary concisely.

## Pruning Discipline

Whenever authoring or refreshing `AGENTS.md`, `SKILL.md`, or `.agents/bundles/knowledge/**/*.md`, prune four classes of waste:

1. **Duplicate Truth**: If an invariant or schema is defined in a canonical architecture or pattern chapter, link to that chapter instead of copying the schema into multiple files.
2. **Stale Environment Cache**: Do not copy full `Makefile` targets, dependency versions, or directory trees into prose unless documenting a non-obvious constraint or reason behind a choice. Manifest files are the source of truth; docs explain *why* and how modules connect.
3. **Stale History**: Delete historical migration notes, struck-through requirements, and `"formerly"` callouts from active specs, skills, and knowledge chapters.
4. **Model-Relative No-Ops**: Delete instructions that tell the agent to do what it already does by default (such as `"Use valid syntax"` or `"Be helpful and thorough"`). Every remaining line must steer behavior on a real failure mode.

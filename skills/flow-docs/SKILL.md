---
name: flow-docs
description: "Use when writing or auditing technical documentation, READMEs, user guides, design docs, agent instructions, pull requests, commit messages, or changelogs. Don't use for planning implementation specs (use flow-planning) or syncing task state against Git (use flow-learn)."
---

# Documentation, Agent Instructions, & Pull Requests

<!-- lifecycle-ownership: owner=flow-docs; operations=docs,pr -->

Write clear, accurate technical documentation, user guides, agent instruction files (`AGENTS.md`, `SKILL.md`, OKF knowledge chapters), commit messages, changelogs, and pull requests.

## Operational Modes (`/flow:docs [mode]`)

- `write` — Author or update READMEs, user guides, module docs, or agent skills using file-checklist source coverage (`[k/N files documented]`).
- `validate` — Audit documentation and `.agents/bundles/` for first-time reader clarity, primary-source `path/to/file::Symbol` accuracy, broken links, and stale history.
- `capture` — Distill validated architectural and operational patterns from code and completed flows into `.agents/bundles/knowledge/` and user-facing `docs/`.
- `sync` — Sync documentation claims and examples against live repository signatures and configuration.
- `pr` — Draft or update pull request titles, `## Summary` + `## Key Changes` bodies, signed commits, and release changelogs.

## Core Writing Rules

- **Pass the First-Time Reader Test.** Every document must be understandable on the first read by an engineer or isolated agent with no prior chat history. Lead with purpose, public interface, concrete examples, and invariants.
- **Read source before writing (`[k/N files documented]`).** List the in-scope files first, read every file completely, and anchor claims to `path/to/file::Symbol`. Never guess behavior from filenames or function names.
- **State rules plainly with a one-line `Reason:`.** Write direct, present-tense sentences. When documenting a constraint or design choice, state the rule followed by `Reason: <why>`.
- **Eliminate AI slop, buzzwords, and stale history.**
  - Never use promotional adjectives (`seamless`, `robust`, `comprehensive`, `pivotal`, `delve`, `leverage`, `blazingly fast`), decorative adverbs (`seamlessly`, `effortlessly`, `obviously`), negative parallelisms (`"not just X, but Y"`), or formulaic transitions (`"Moreover"`, `"Furthermore"`).
  - Never use artificial numbered buzzword labels or inflated metaphors (`"engineering lawbooks"`, `"causal waterfall"`, `"zero-tolerance"`). Name components and headings semantically so counts never break when items change.
  - Never leave stale history (`"Added in v2"`, `"Previously we used X"`) inside current-state documentation or specs. History belongs in `CHANGELOG.md` and `.agents/bundles/log.md`.
- **Never leak internal workflow ceremony or private paths.** Keep PRs, commits, changelogs, tests, and docs free of finding counts, task IDs (`PROJ-123`, `test_task_1_2_*`), workflow internals, `## Verification` command logs, `## Merge Danger` blocks, ASCII trees, or local paths.
- **Keep reader-facing design docs prospective and concise.** Omit commit SHAs, UUIDs, hash codes, source line numbers, private helper names, and mechanical inventory counts from PRDs and design docs. Keep documentation tables at 5 columns or fewer, one value per cell, without horizontal rules (`---`) inside bundle bodies. Move traceability matrices into `.agents/bundles/knowledge/` or a companion index.

## Reference Guides

| Area | Reference File | Key Topics |
| --- | --- | --- |
| Technical Prose & Documentation | [`references/prose-and-documentation.md`](references/prose-and-documentation.md) | First-time reader standard, file-checklist coverage (`[k/N files documented]`), component scaling templates, guide structure, diagram rules, validation report |
| Agent Context, `.agents/`, & Harness Config | [`references/agent-context.md`](references/agent-context.md) | Cross-harness `.agents/` discovery (skills, subagents, rules, hooks, MCP configs), context load vs. cognitive load, information hierarchy, context pointers, progressive disclosure, completion criteria, positive framing, pruning discipline |
| Pull Requests, Commits, & Changelogs | [`references/prs-commits-and-changelogs.md`](references/prs-commits-and-changelogs.md) | `<type>(<scope>): <summary>` titles, `## Summary` + `## Key Changes` PR bodies, signed commits, changelog conventions, inline PR reviews, GitHub issues |

## Workflow

1. **Select Target & Reference**:
   - For **READMEs, user guides, module/API docs, or doc audits**, load [`references/prose-and-documentation.md`](references/prose-and-documentation.md).
   - For **`AGENTS.md`, `SKILL.md`, subagents, or `.agents/bundles/knowledge/` chapters**, load [`references/agent-context.md`](references/agent-context.md).
   - For **PRs, commits, changelogs, or code review comments**, load [`references/prs-commits-and-changelogs.md`](references/prs-commits-and-changelogs.md).
2. **Build Checklist & Parallelize Authoring**:
   - List every file in scope (`[0/N files documented]`) and read each implementation file before drafting prose.
   - When documenting or syncing `>= 2` domains, subsystems, or chapters (`/flow:docs write | capture | sync`), fan out isolated per-domain documentation subagents so each file gets runnable, code-verified examples rather than a compressed summary.
3. **Draft in Present Tense**:
   - Keep user guides focused on a single concept (`<= 200` lines), leading with a runnable example and expected output.
   - Keep living specs (`specs/<flow_id>/spec.md`, `chapters/index.md`, `chapters/<ch_id>/spec.md`), `.agents/bundles/knowledge/**` chapters, and user `docs/` in present tense. State current verified reality, remaining chapters, and the full plan with zero `Revision History` sections.
   - Keep `SKILL.md` files `<= 200` lines (`< 24,000` bytes), `<!-- truth: start -->` blocks `<= 40` lines, and bundle bodies free of standalone `---` horizontal rules, disclosing deep reference material into `references/*.md`.
4. **Verify & Prune**:
   - Strip puffery, stale history, duplicate cache lines, and workflow ceremony, then verify all links and examples (`make lint`).

## Guardrails

- **Conceptual Diagrams Only in `docs/`**: Keep Mermaid diagrams in user-facing `docs/` and `README.md` conceptual (`4-6` nodes focused on the user mental model). Place detailed module/implementation diagrams in `.agents/bundles/knowledge/architecture/`.
- **Single Source of Truth**: Link to canonical rules rather than duplicating them across files.
- **Calm, Matter-of-Fact Tone**: Never use exclamation marks (`!`) or dismissive language in documentation, PR bodies, or code reviews.

## Validation

- Confirm every checklist item is covered (`[N/N files documented]`) and every technical claim cites a verified source (`path/to/file::Symbol`).
- Confirm PR bodies contain only `## Summary` and `## Key Changes` and every PR `#` or Issue `#` in chat is a clickable Markdown link.
- Confirm all relative Markdown links resolve on disk and `make lint` exits `0`.

## Example

Invoke `/flow:docs write` to document a module with `[4/4 files documented]` coverage tracking, `/flow:docs validate` to audit `.agents/bundles/` and `docs/` for stale symbols or prose bloat, or `/flow:docs pr` when preparing a pull request in `/flow:finish`.

```bash
flow git validate-pr-body --title "feat(auth): add PKCE exchange" --from pr.md
```

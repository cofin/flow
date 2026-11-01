---
name: flow-docs
description: Use when writing or auditing technical documentation, READMEs, user guides, architecture docs, agent instructions (AGENTS.md, SKILL.md, OKF chapters), pull requests, commit messages, or changelogs.
---

# Documentation, Prose, Agent Instructions, & Pull Requests (`flow-docs`)

Write clear, accurate, zero-bloat technical documentation, user guides, agent instruction files (`AGENTS.md`, `SKILL.md`, OKF knowledge chapters), commit messages, changelogs, and pull requests.

## Operational Modes (`/flow:docs [mode]`)

- `write` — Author or update READMEs, user guides, module documentation, or agent skills using manifest-driven source coverage (`[k/N files documented]`).
- `validate` — Audit documentation and `.agents/bundles/` for Goldfish comprehension, primary-source `path/to/file::Symbol` accuracy, broken links, and prose sediment.
- `capture` — Distill validated architectural and operational patterns from code and completed flows into `.agents/bundles/knowledge/` and user-facing `docs/`.
- `sync` — Reconcile documentation claims and examples against live repository signatures and configuration.
- `pr` — Draft or update pull request titles, `## Summary` + `## Key Changes` bodies, signed commits, and release changelogs.

## Core Writing & Anti-Bloat Rules

- **Pass the Goldfish Comprehension Test.** Every document must be understandable on the first read by a fresh engineer or zero-context agent ("Goldfish") with zero prior session history. Lead with purpose, public interface, concrete examples, and invariants.
- **Read source before writing (`[k/N files documented]`).** Enumerate the in-scope files first, read every file completely, and anchor claims to `path/to/file::Symbol`. Never guess behavior from filenames or function names.
- **State rules plainly with a one-line `Reason:`.** Write direct, present-tense sentences. When documenting a constraint or design choice, state the rule followed by `Reason: <why>`.
- **Eliminate AI slop, buzzwords, and chronological sediment.**
  - Never use promotional adjectives (`seamless`, `robust`, `comprehensive`, `pivotal`, `delve`, `leverage`, `blazingly fast`), decorative adverbs (`seamlessly`, `effortlessly`, `obviously`), negative parallelisms (`"not just X, but Y"`), formulaic transitions (`"Moreover"`, `"Furthermore"`), or superficial participle tails (`"...ensuring reliability"`).
  - Never use artificial count-prefixed labels (`"3-Layer Sizing"`, `"5-Tier Hierarchy"`, `"4-Stage Pipeline"`, `"7 guidelines"`) or inflated metaphors (`"engineering lawbooks"`, `"causal waterfall"`, `"zero-tolerance"`). Name components and headings semantically so counts never break when items change.
  - Never leave chronological sediment (`"Added in v2"`, `"Previously we used X"`) inside current-state documentation or specs. History belongs in `CHANGELOG.md` and `.agents/bundles/log.md`.
- **Never leak internal workflow ceremony or private paths.** Keep PRs, commits, changelogs, tests, and docs free of finding counts, task/finding IDs (`ORA-001`, `test_task_1_2_*`), workflow mechanics (`checkpoint.phase`, subagent names), `## Verification` command logs, `## Merge Danger` blocks, ASCII file/call trees, or local workstation paths.

## Reference Guides

| Area | Reference File | Key Topics |
| --- | --- | --- |
| Technical Prose & Documentation | [`references/prose-and-documentation.md`](references/prose-and-documentation.md) | Goldfish comprehension standard, manifest-driven `docgen` workflow (`[k/N files documented]`), component scaling templates, guide structure, diagram rules, validation report |
| Writing for Agents (`AGENTS.md`, `SKILL.md`, OKF) | [`references/writing-for-agents.md`](references/writing-for-agents.md) | Context load vs. cognitive load, 3-rung information hierarchy, context pointers, progressive disclosure by branch, co-location, completion criteria, leading words, positive framing, pruning caches/sediment/no-ops |
| Pull Requests, Commits, & Changelogs | [`references/prs-commits-and-changelogs.md`](references/prs-commits-and-changelogs.md) | `<type>(<scope>): <summary>` titles, `## Summary` + `## Key Changes` PR bodies, signed commits, changelog conventions, inline PR reviews, GitHub issues |

## Workflow

1. **Select Target & Reference**:
   - For **READMEs, user guides, module/API docs, or doc audits**, load [`references/prose-and-documentation.md`](references/prose-and-documentation.md).
   - For **`AGENTS.md`, `SKILL.md`, subagents, or `.agents/bundles/knowledge/` chapters**, load [`references/writing-for-agents.md`](references/writing-for-agents.md).
   - For **PRs, commits, changelogs, or code review comments**, load [`references/prs-commits-and-changelogs.md`](references/prs-commits-and-changelogs.md).
2. **Build Manifest & Inspect Primary Sources**:
   - List every file in scope (`[0/N files documented]`) and read each implementation file before drafting prose.
3. **Draft to Match Target Length & Hierarchy**:
   - Keep user guides focused on a single concept (`<= 200` lines), leading with a runnable example and expected output.
   - Keep `SKILL.md` files `<= 200` lines (`< 24,000` bytes) and `<!-- truth: start -->` blocks `<= 40` lines, disclosing deep reference material into `references/*.md`.
4. **Verify & Prune**:
   - Strip puffery, chronological sediment, duplicate cache lines, and workflow ceremony, then verify all links and examples (`make lint`).

## Guardrails

- **Conceptual Diagrams Only in `docs/`**: Keep Mermaid diagrams in user-facing `docs/` and `README.md` conceptual (`4–6` nodes focused on the user mental model). Place detailed module/implementation diagrams in `.agents/bundles/knowledge/architecture/`.
- **Single Source of Truth**: Link to canonical rules rather than duplicating them across files.
- **Calm, Matter-of-Fact Tone**: Never use exclamation marks (`!`) or dismissive language in documentation, PR bodies, or code reviews.

## Validation

- Confirm every manifest item is covered (`[N/N files documented]`) and every technical claim cites a verified source (`path/to/file::Symbol`).
- Confirm PR bodies contain only `## Summary` and `## Key Changes` and every PR `#` or Issue `#` in chat is a clickable Markdown link.
- Confirm all relative Markdown links resolve on disk and `make lint` exits `0`.

## Example

Invoke `/flow:docs write` to document a module with `[4/4 files documented]` coverage tracking, `/flow:docs validate` to audit `.agents/bundles/` and `docs/` for stale symbols or prose bloat, or `/flow:docs pr` when preparing a pull request in `/flow:finish`.

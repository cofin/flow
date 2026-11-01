---
name: flow-docs
description: Use when writing or updating pull requests, commit messages, changelogs, user guides, tutorials, API reference documentation, docstrings, or READMEs.
---

# Documentation, Guides, & Pull Request Writing (`flow-docs`)

Write clear, direct documentation, user guides, API reference pages, changelogs, commit messages, and pull requests without AI slop, buzzwords, or leaked workflow ceremony.

## Plain-Language & Anti-Slop Rules

- **Use plain, direct language.** State what a feature or change does in clear sentences. When documenting a rule or design choice, state the rule and a one-line `Reason:`.
- **Never use count-prefixed buzzwords or AI metaphors.** Avoid artificial numbered labels ("3-Layer Sizing", "5-Tier Hierarchy", "4-Stage Pipeline", "7 guidelines") and inflated metaphors ("engineering lawbooks", "causal waterfall", "zero-tolerance", "canonical invariants"). Name components and sections by what they do so headings and filenames never break when items change.
- **Never leak internal workflow or audit ceremony.** Keep PR descriptions, commit messages, changelogs, tests, and user docs free of:
  - Finding counts, severity tallies, task or finding IDs (`ORA-001`, `test_task_1_2_*`), or internal review script names.
  - Multi-PR stack navigation tables or agent workflow mechanics (`worksheet`, `checkpoint.phase`, subagent names).
  - `## Verification` command logs, `## Merge Danger`, `**Door:**`, `**Blast Radius:**`, or ASCII file/call trees in PR bodies.
- **Never leak private paths or internal identifiers.** Never include local workstation paths, `scratch/` directories, private corporate tool names or shortlinks, or customer engagement names/IDs in repository files, commits, or PRs.
- **Keep tone calm and matter-of-fact.** Never use exclamation marks (`!`) or dismissive phrasing in PRs, code reviews, comments, or documentation.

## Quick Reference

| Area | Reference File | Key Topics |
| --- | --- | --- |
| Pull Requests, Commits, & Changelogs | [`references/prs-commits-and-changelogs.md`](references/prs-commits-and-changelogs.md) | `<type>(<scope>): <summary>` PR titles, `## Summary` + `## Key Changes` PR bodies, signed commits, changelog conventions, inline PR reviews, GitHub issues |
| User Guides & API Reference Docs | [`references/guides-and-api-docs.md`](references/guides-and-api-docs.md) | Zensical Free (`zensical.toml`), `mkdocstrings-python` (Griffe), page budgets (`<= 12` viewports, `<= 120 KB` HTML), runnable `docs/examples/`, `TypedDict` / `msgspec.Struct` docstrings |

## Workflow

1. **Identify the Target Artifact**:
   - **Pull Request, Commit, or Changelog**: Follow [`references/prs-commits-and-changelogs.md`](references/prs-commits-and-changelogs.md).
   - **User Guide, Tutorial, README, or API Reference**: Follow [`references/guides-and-api-docs.md`](references/guides-and-api-docs.md).
2. **Draft with Reader-First Structure**:
   - For **PRs**: Write a `<type>(<scope>): <concise summary>` title, a 1–3 sentence `## Summary`, and `## Key Changes` grouped by module or area and change type.
   - For **Guides**: Start with a runnable example from `docs/examples/` (`--8<--`), show expected output, walk through the key lines, and end with a 3-bullet recap.
   - For **API Reference Pages**: Curate symbols under `2–5` `##` category headings with `inherited_members = false`, `show_bases = true`, and `<= 14` right-sidebar TOC items.
3. **Run Anti-Slop & Hygiene Checks**:
   - Strip any internal task IDs, workflow terminology, `## Verification` blocks, or inline `#` code comments.
   - Verify that all code examples, links, and formatting checks (`make lint`) pass.

## Guardrails

- **No `## Verification` or ASCII Trees in PRs**: Never include test execution logs, `## Verification` sections, `## Merge Danger` blocks, or ASCII diff sketches in pull request bodies.
- **No Unverified Inline Code Snippets**: Prefer standalone runnable modules under `docs/examples/` tested by `pytest` (with zero inline `#` comments and no leaked test fixtures like `tmp_path` or `monkeypatch`).
- **Conceptual Diagrams Only in `docs/`**: Keep Mermaid diagrams in user-facing `docs/` conceptual (`4–6` nodes focused on the user mental model). Place implementation-level architecture diagrams in `.agents/bundles/knowledge/`.
- **Tabbed Package Installation Blocks**: In Python documentation (`docs/`), format installation commands with linked `pymdownx.tabbed` blocks (`=== "uv"`, `=== "pip"`, `=== "pdm"`, `=== "poetry"`).

## Validation

- Confirm PR titles match `<type>(<scope>): <concise summary>` and PR bodies contain only `## Summary` and `## Key Changes`.
- Confirm every PR `#` or Issue `#` referenced in chat responses is formatted as a clickable Markdown link to its GitHub URL.
- Confirm documentation pages respect reading budgets (`<= 200` Markdown lines for guides; `<= 120 KB` HTML and `<= 14` TOC items for API reference pages).

## Example

Invoke `/flow:docs` (or activate `flow-docs`) when preparing a pull request in `/flow:finish`, updating `docs/` and `README.md` during `/flow:learn`, or building Zensical / `mkdocstrings` documentation.

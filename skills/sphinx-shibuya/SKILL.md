---
name: sphinx-shibuya
description: Sphinx documentation authoring with the Shibuya theme, including doc structure, toctrees, and Shibuya-compatible extensions (docsearch, iconify, tabs, togglebutton, sphinx-design grids/cards). Use when editing or reimagining docs/ in projects that use Shibuya or when adding Sphinx extensions and site structure.
---

# Sphinx + Shibuya Docs Workflow

## Overview

Use this skill to design or rework Sphinx documentation that uses the Shibuya theme. Focus on clean structure, short pages, and Shibuya-friendly directives.

## Workflow

### 1) Discover current structure

- Read `docs/conf.py` for enabled extensions and theme config.
- Scan `docs/index.rst` and top-level section indexes for current toctree structure.
- Locate custom extensions in `tools/sphinx_ext/` and reuse them before adding new ones.
- Prefer `docs/examples/` + `literalinclude` patterns for code snippets.

### 2) Structure for short pages

- Split long guides into per-topic pages using a section `index.rst` with a hidden toctree.
- Keep each page scoped to one concept or workflow; link out to examples and reference pages.
- Prefer list tables or grid cards for navigation hubs.

Example Shibuya grid card hub (use with sphinx-design):

```rst
.. grid:: 1 1 2 4
   :gutter: 2
   :padding: 0

   .. grid-item-card:: Litestar
      :link: frameworks/litestar
      :link-type: doc

      .. image:: /_static/logos/litestar.svg
         :width: 72
         :align: center
         :alt: Litestar
```

### 3) Shibuya-compatible extensions to consider

Use only what the docs actually need, but favor these Shibuya-friendly extensions:

- `sphinx_design` for grids, cards, and layout components.
- `sphinx_iconify` for icon usage.
- `sphinx_docsearch` for Algolia DocSearch UI.
- `sphinx_tabs.tabs` for tabbed content.
- `sphinx_togglebutton` for collapsible sections.
- `sphinx_datatables` for data tables where sorting/searching helps.
- `sphinx_copybutton`, `sphinx_paramlinks`, `sphinxcontrib.mermaid` as needed.

### 4) Code samples

- Use `literalinclude` with `# start-example` / `# end-example` markers.
- Keep examples short and runnable with `pytest` where possible.
- Prefer language-specific highlights (`:language: python`, `:language: sql`).

### 5) Validation

- Run `make docs` and address warnings.
- If auto-generated API docs are present, keep them excluded from the main toctree unless explicitly linked.

## Project conventions (SQLSpec)

- Prefer examples in `docs/examples/` and reference them with `literalinclude`.
- Keep pages short, avoid heavy emoji usage, and favor neutral tone.
- Use custom directives from `tools/sphinx_ext/` when available (e.g., playground/changelog helpers).

## Official References

- https://shibuya.lepture.com/
- https://shibuya.lepture.com/changelog/
- https://www.sphinx-doc.org/en/master/
- https://sphinx-design.readthedocs.io/en/latest/
- https://sphinx-docsearch.readthedocs.io/
- https://sharm294.github.io/sphinx-datatables/

## Shared Styleguide Baseline

- Use shared styleguides for generic language/framework rules to reduce duplication in this skill.
- [General Principles](https://github.com/cofin/flow/blob/main/templates/styleguides/general.md)
- Keep this skill focused on tool-specific workflows, edge cases, and integration details.

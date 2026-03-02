---
name: sphinx-shibuya
description: Sphinx documentation authoring with the Shibuya theme, including doc structure, toctrees, and Shibuya-compatible extensions (docsearch, iconify, tabs, togglebutton, sphinx-design grids/cards). Use when editing or reimagining docs/ in projects that use Shibuya or when adding Sphinx extensions and site structure.
---

# Sphinx + Shibuya Docs Workflow

## Overview

Use this skill to design or rework Sphinx docs that use the Shibuya theme.
Prioritize official Sphinx + Shibuya guidance, clear IA, and short focused pages.

## Workflow

### 1) Discover current docs setup

- Read `docs/conf.py` for enabled extensions and theme config.
- Scan `docs/index.rst` and section `index.rst` files for current `toctree` layout.
- Locate custom extensions in `tools/sphinx_ext/` and reuse them before adding new ones.
- Prefer `literalinclude` from real files over large inline code blocks.

Learn more:
- https://www.sphinx-doc.org/en/master/usage/configuration.html
- https://www.sphinx-doc.org/en/master/usage/restructuredtext/directives.html#toctree

### 2) Structure for short, navigable pages

- Split long guides into per-topic pages using a section `index.rst` with a hidden toctree.
- Keep each page scoped to one concept or workflow; link out to examples and reference pages.
- Use Shibuya-friendly hubs (cards/grids) when it improves navigation.

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

Learn more:
- https://www.sphinx-doc.org/en/master/usage/restructuredtext/directives.html#toctree
- https://shibuya.lepture.com/extensions/sphinx-design/

### 3) Choose extensions from Shibuya-supported docs first

Use only what the docs need. Prefer extensions with explicit Shibuya integration docs:

- `sphinx_design` for cards/grids and layout blocks.
- `sphinx_tabs.tabs` for tabbed content.
- `sphinx_togglebutton` for collapsible sections.
- `sphinx_copybutton` for copy buttons on code blocks.
- `sphinx_docsearch` for Algolia DocSearch.
- `sphinx_iconify` for icon roles.
- `sphinx_datatables` only when interactive tables are needed.

Learn more:
- https://shibuya.lepture.com/contributing/roadmap/
- https://shibuya.lepture.com/extensions/sphinx-design/
- https://shibuya.lepture.com/extensions/sphinx-tabs/
- https://shibuya.lepture.com/extensions/sphinx-togglebutton/
- https://shibuya.lepture.com/extensions/docsearch/
- https://shibuya.lepture.com/extensions/sphinx-iconify/
- https://sphinx-copybutton.readthedocs.io/en/latest/

### 4) Code samples

- Use `literalinclude` with `:start-after:` / `:end-before:` markers from source files.
- Keep examples short and realistic.
- Set explicit language highlighting where useful.

Learn more:
- https://www.sphinx-doc.org/en/master/usage/restructuredtext/directives.html#literalinclude

### 5) Validation

- Run `make docs` and address warnings.
- If auto-generated API docs are present, keep them excluded from the main toctree unless explicitly linked.

Learn more:
- https://www.sphinx-doc.org/en/master/usage/builders/index.html

## Official References

- https://shibuya.lepture.com/
- https://shibuya.lepture.com/stability/
- https://shibuya.lepture.com/changelog/
- https://www.sphinx-doc.org/en/master/

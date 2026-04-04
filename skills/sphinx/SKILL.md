---
name: sphinx
description: "Auto-activate for conf.py (Sphinx), .rst files, docs/source/. Produces Sphinx documentation sites with RST, autodoc, themes (Shibuya/Immaterial), and CI/CD integration. Use when: editing conf.py, reStructuredText (.rst), autodoc, readthedocs builds, Shibuya theme, Wasm extensions, VHS terminal recordings, or any Sphinx project setup. Not for MkDocs, Docusaurus, or Mintlify documentation sites."
---

# Sphinx Skill

Expert knowledge for maintaining and expanding Sphinx documentation workspaces.

## Quick Reference

### conf.py Setup

```python
# docs/conf.py
project = "MyProject"
copyright = "2025, My Org"
author = "My Org"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx_copybutton",
    "sphinx_design",
]

# Theme (choose one)
html_theme = "shibuya"  # or "sphinx_immaterial"
html_static_path = ["_static"]

# Autodoc
autodoc_member_order = "bysource"
autodoc_typehints = "description"
autodoc_class_signature = "separated"

# Intersphinx (cross-project links)
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "sqlalchemy": ("https://docs.sqlalchemy.org/en/20/", None),
}
```

### Key RST Patterns

```rst
.. Title and sections (heading hierarchy)
==========
Page Title
==========

Section
-------

Subsection
^^^^^^^^^^

.. Cross-references
:ref:`label-name`
:doc:`other-page`
:func:`mymodule.myfunction`

.. Autodoc directives
.. automodule:: mypackage.module
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: mypackage.MyClass
   :members:
   :special-members: __init__

.. Code blocks
.. code-block:: python

   def hello():
       print("world")

.. Include from file with markers
.. literalinclude:: ../../examples/demo.py
   :language: python
   :start-after: # start-example
   :end-before: # end-example

.. Admonitions
.. note::
   Important information here.

.. warning::
   Dangerous operation ahead.
```

### Autodoc Configuration

- `autodoc_member_order = "bysource"` -- preserves source order (not alphabetical).
- `autodoc_typehints = "description"` -- puts type hints in parameter descriptions, not signatures.
- `napoleon` extension -- enables Google-style and NumPy-style docstrings.
- `intersphinx` -- links to external project docs (Python stdlib, SQLAlchemy, etc.) without duplicating content.

<workflow>

## Workflow

### Step 1: Project Structure

Set up the docs directory with `conf.py`, `index.rst`, and section directories. Use a hidden toctree in `index.rst` for navigation.

```text
docs/
├── conf.py
├── index.rst
├── getting-started/
│   ├── index.rst
│   └── installation.rst
├── api/
│   ├── index.rst
│   └── modules.rst
├── _static/
└── _templates/
```

### Step 2: Configure Extensions

Enable `autodoc`, `intersphinx`, `napoleon`, `viewcode`, and theme-specific extensions. Pin Sphinx and extension versions in `pyproject.toml`.

### Step 3: Write Content

Split long guides into per-topic pages. Keep each page scoped to one concept. Use `literalinclude` with markers for code examples. Prefer `sphinx_design` grids and cards for navigation hubs.

### Step 4: Build and Test

```bash
# Local build
sphinx-build -b html docs/ docs/_build/html -W --keep-going

# Watch mode (with sphinx-autobuild)
sphinx-autobuild docs/ docs/_build/html
```

### Step 5: CI/CD Integration

Add a GitHub Actions workflow that builds docs on every PR. Fail the build on warnings (`-W` flag). Deploy to GitHub Pages or ReadTheDocs on merge to main.

</workflow>

<guardrails>

## Guardrails

- **Pin Sphinx version** -- specify `sphinx>=8.0,<9` in `pyproject.toml` to prevent surprise breaking changes. Pin extension versions too.
- **Use intersphinx for cross-project links** -- never hardcode URLs to external docs. Use `:func:`, `:class:`, `:doc:` roles with intersphinx mappings.
- **Test builds in CI** -- run `sphinx-build -W` (warnings as errors) in CI. Catch broken references, missing modules, and RST syntax errors before merge.
- **`autodoc_typehints = "description"`** -- keeps signatures readable; type info appears in parameter docs.
- **One concept per page** -- split long guides into focused pages linked via toctree. Readers find content faster.
- **`literalinclude` over inline code** -- keeps examples runnable and testable. Use `start-after`/`end-before` markers.

</guardrails>

<validation>

### Validation Checkpoint

Before delivering Sphinx configurations, verify:

- [ ] Sphinx and extension versions are pinned in pyproject.toml
- [ ] `intersphinx_mapping` is configured for all external references
- [ ] `sphinx-build -W` completes without warnings
- [ ] Autodoc picks up all public modules/classes
- [ ] Cross-references (`:ref:`, `:doc:`, `:func:`) resolve correctly
- [ ] CI workflow builds docs and fails on warnings

</validation>

<example>

## Example

**Task:** Minimal conf.py and RST page with autodoc.

**`docs/conf.py`:**

```python
project = "Acme"
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx_copybutton",
    "sphinx_design",
]

html_theme = "shibuya"

autodoc_member_order = "bysource"
autodoc_typehints = "description"

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
}
```

**`docs/index.rst`:**

```rst
=====
Acme
=====

Welcome to Acme's documentation.

.. toctree::
   :hidden:
   :maxdepth: 2

   getting-started/index
   api/index
```

**`docs/api/index.rst`:**

```rst
=============
API Reference
=============

.. automodule:: acme.core
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: acme.client.AcmeClient
   :members:
   :special-members: __init__
```

</example>

---

## References Index

For detailed guides on specific themes and extensions, refer to the following documents:

### Themes

- **[Sphinx Immaterial Theme](references/immaterial-theme.md)** -- Configuration for the Material Design theme.
- **[Shibuya Theme](references/shibuya.md)** -- Configuration for the Shibuya theme.

### Extensions & Demos

- **[Wasm Playground](references/wasm-playground.md)** -- Integrating interactive Wasm playgrounds.
- **[VHS Terminal Recordings](references/vhs-demos.md)** -- Guidelines for creating and embedding VHS recordings.

### Infrastructure

- **[CI/CD Pipelines](references/ci-cd.md)** -- GitHub Actions workflows for building and deploying documentation.

---

## Official References

- <https://www.sphinx-doc.org/>
- <https://sphinx-immaterial.readthedocs.io/>
- <https://shibuya.lepture.com/>

## Shared Styleguide Baseline

- Use shared styleguides for generic language/framework rules to reduce duplication in this skill.
- [General Principles](https://github.com/cofin/flow/blob/main/templates/styleguides/general.md)
- [Python](https://github.com/cofin/flow/blob/main/templates/styleguides/languages/python.md)
- Keep this skill focused on tool-specific workflows, edge cases, and integration details.

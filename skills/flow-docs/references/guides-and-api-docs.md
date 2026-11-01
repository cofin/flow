# User Guides, Tutorials, & API Reference Documentation

Architecture and writing standards for technical documentation, user guides, READMEs, and static AST API references.

## Core Documentation Principles

- **Keep reading columns scannable (`68–75ch` / `46rem`) with persistent left and right sidebars.** Reason: uncapped prose width and hidden `"On this page"` outlines make technical pages hard to scan.
- **Cap guide pages at `<= 12` viewports (`~80–200` Markdown lines, one concept per page).** Reason: focused pages load quickly and match reader task intent.
- **Cap API Reference pages at `<= 120 KB` HTML and `<= 14` right-sidebar TOC items.** Reason: monolithic module dumps with dozens of classes and hundreds of inherited methods bury primary constructors.
- **Use Zensical Free (`zensical >= 0.0.71`) + `mkdocstrings-python` (Griffe static AST) for Python documentation sites.** Reason: Griffe extracts API signatures and docstrings statically in seconds without compiling native extensions or importing heavy runtime dependencies.
- **Set `inherited_members = false` and `show_bases = true` on leaf classes.** Reason: base methods belong once on the base class Reference page and link from subclasses via `show_bases`.
- **Execute standalone `docs/examples/**/*.py` modules in `pytest` and embed them via `--8<--`.** Reason: inline Markdown code blocks rot silently, whereas standalone modules checked by `ruff`, `mypy`, `pyright`, and `pytest` stay runnable.

## Information Architecture

Organize documentation navigation into task-oriented top-level tabs rather than raw directory trees:

| Tab | Purpose | Budget |
| --- | --- | --- |
| `Learn` | Quickstart, First Steps, Core Concepts, and Production Recipes | `<= 12` viewports (`~80–200` lines) per page |
| `Databases` / `Adapters` | Central Capability Matrix (`index.md`) + 1-page setup and configuration guide per driver/adapter | `<= 10` viewports (`~80–140` lines) per adapter |
| `Integrations` | Framework and ecosystem guides combining setup, DI, and lifecycle usage | `<= 12` viewports per integration |
| `Reference` | Curated `mkdocstrings` pages grouped by domain with explicit `members` lists | `<= 120 KB` HTML and `<= 14` TOC items per page |
| `Project` | Contributor Guide, Architecture Overview, Releases, and Changelog | Standard prose measure |

## Progressive Tutorial Structure

Structure every `Learn` or feature guide page in four concise parts:

1. **Complete Runnable Example First**: Embed a verified script from `docs/examples/<area>/<topic>.py` via `pymdownx.snippets` (`--8<-- "docs/examples/..."`) with `hl_lines` highlighting the focal lines.
2. **Expected Output**: Show the exact terminal output or return payload immediately beneath the snippet.
3. **Walkthrough**: Explain the highlighted lines in 3–5 short paragraphs without restating obvious syntax.
4. **Recap**: Close with a 3-bullet summary and links to the next guide or API Reference page.

### Rules for `docs/examples/` Modules

- Give every example module a top-level docstring, a `main()` entry point, `__all__ = ("main",)`, and **zero inline `#` comments**.
- Never leak `pytest` fixtures (`tmp_path`, `monkeypatch`) into `docs/examples/**/*.py`; use `tempfile.TemporaryDirectory()` inside `main()` when temporary files are needed.

## Python Docstrings & Griffe Rendering

- **Google-Style Docstrings**: Use Google-style sections (`Args:`, `Returns:`, `Raises:`, `Examples:`) on public classes, methods, and functions.
- **Inline Field Docstrings on `TypedDict` and `msgspec.Struct`**: Document every public field with a PEP 257 string literal immediately below the field definition (and omit duplicate class-level `Attributes:` blocks) so Griffe renders structured parameter tables.
- **No Docstrings on `@overload` Stubs**: Write the docstring once on the implementation function; docstrings on `@overload` signatures override the implementation docstring in Griffe.
- **No Compiler or Internal Leaks**: Never mention mypyc workarounds, C-extension internals, or internal task IDs in public docstrings.

## Diagrams & Installation Blocks in `docs/`

- **Conceptual Mermaid Diagrams (`4–6` Nodes)**: Keep Mermaid diagrams in user-facing `docs/` and `README.md` high-level and focused on the user's mental model. Place detailed implementation-level diagrams in `.agents/bundles/knowledge/`.
- **Tabbed Installation Commands**: Format Python package installation instructions using linked `pymdownx.tabbed` tabs:

  ````markdown
  === "uv"

      ```bash
      uv add <package>
      ```

  === "pip"

      ```bash
      pip install <package>
      ```

  === "pdm"

      ```bash
      pdm add <package>
      ```

  === "poetry"

      ```bash
      poetry add <package>
      ```
  ````

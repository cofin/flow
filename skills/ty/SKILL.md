---
name: ty
description: "Auto-activate for ty commands, ty.toml. Usage of `ty`, a zero-config, high-performance type checker from Astral. Use when: running fast static analysis on Python codebases where `ty` is installed."
---

# Ty Skill

## Overview

`ty` is a new, high-performance static type checker from Astral (creators of `uv` and `ruff`). It aims to be zero-config and significantly faster than existing options.

**Status**: Preview / Emerging.

## Usage

### 1. Installation

Ensure `ty` is installed in your project or environment. It is NOT bundled with Python by default.

```bash
uv add --dev ty
```

### 2. Running Checks

```bash
uvx ty check
```

## When to Use

- **Greenfield Projects**: Great for starting with strict typing from day one without config fatigue.
- **Large Codebases**: When `mypy` or `pyright` performance becomes a bottleneck.

## Integration

- **VS Code**: Use the `ty` extension if available, or configure generic LSP.
- **CI**: Add `uvx ty check` to your CI pipeline.

> [!IMPORTANT]
> Since `ty` is emerging software, always verify its installation before running it in scripts.
>
> ```bash
> if command -v ty &> /dev/null; then
>     ty check
> fi
> ```

## Official References

- <https://docs.astral.sh/ty/>
- <https://docs.astral.sh/ty/installation/>
- <https://docs.astral.sh/ty/type-checking/>
- <https://docs.astral.sh/ty/editors/>
- <https://docs.astral.sh/ty/reference/cli/>
- <https://github.com/astral-sh/ty/releases>

## Shared Styleguide Baseline

- Use shared styleguides for generic language/framework rules to reduce duplication in this skill.
- [General Principles](https://github.com/cofin/flow/blob/main/templates/styleguides/general.md)
- [Python](https://github.com/cofin/flow/blob/main/templates/styleguides/languages/python.md)
- Keep this skill focused on tool-specific workflows, edge cases, and integration details.

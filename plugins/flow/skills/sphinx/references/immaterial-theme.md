
# Sphinx Immaterial Theme Workflow

## Overview

Use this skill to configure and optimize the `sphinx-immaterial` theme for documentation projects. It provides a modern, responsive interface with rich navigation, search, and code annotation features.

## Theme Selection: Immaterial vs Shibuya

When choosing between `sphinx-immaterial` and `sphinx-shibuya`:

| Feature/Aspect | Sphinx Immaterial | Sphinx Shibuya |
| :--- | :--- | :--- |
| **Aesthetic** | Google Material Design (dense, card-like) | Minimalist, clean layout |
| **Ideal For** | API-heavy docs, dense references, dark mode | Reading-focused guides, structured tutorials |
| **Best Feature** | Sticky TOC, Code annotations, Rich Search | Multi-level sidebar, elegant typography |

Choose **Immaterial** if you want absolute feature density and interactive elements (like annotations) that make documenting technical systems highly scannable.

## Configuration (`docs/conf.py`)

### 1. Dependencies

Ensure your environment configuration (e.g., `pyproject.toml`) includes:

```toml
[project.optional-dependencies]
docs = [
    "sphinx>=8.0.0",
    "sphinx-immaterial>=0.13.0",
    "myst-parser>=4.0.0",
    "sphinx-copybutton>=0.5.0",
    "sphinx-design>=0.6.0",
]
```

### 2. Theme Setup

```python
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "sphinx.ext.napoleon",
    "myst_parser",
    "sphinx_copybutton",
    "sphinx_design",
    "sphinx_immaterial",
]

html_theme = "sphinx_immaterial"
html_static_path = ["_static"]
html_css_files = ["custom.css"]

html_theme_options = {
    "icon": {
        "repo": "fontawesome/brands/github",
        "logo": "material/database", # Adjust as workspace requires
    },
    "palette": [
        {
            "media": "(prefers-color-scheme: light)",
            "scheme": "default",
            "primary": "light-green",
            "accent": "light-blue",
            "toggle": {
                "icon": "material/lightbulb",
                "name": "Switch to dark mode",
            },
        },
        {
            "media": "(prefers-color-scheme: dark)",
            "scheme": "slate",
            "primary": "light-green",
            "accent": "light-blue",
            "toggle": {
                "icon": "material/lightbulb-outline",
                "name": "Switch to light mode",
            },
        },
    ],
    "features": [
        "content.action.edit",
        "content.action.view",
        "content.code.annotate",
        "content.code.copy",
        "navigation.expand",
        "navigation.footer",
        "navigation.instant",
        "navigation.sections",
        "navigation.tabs",
        "navigation.tabs.sticky",
        "navigation.top",
        "navigation.tracking",
        "search.highlight",
        "search.share",
        "toc.follow",
        "toc.sticky",
    ],
}
```

### 3. Custom Admonitions

Add custom directive nodes in `conf.py` to style specific system alerts:

```python
sphinx_immaterial_custom_admonitions = [
    {
        "name": "system-note",
        "title": "System Note",
        "icon": "material/cogs",
        "color": (11, 87, 208), # RGB tuple for theme borders
        "classes": ["info"],
    },
]
```

## Custom CSS Enhancements (`_static/custom.css`)

Apply these baselines to lift visual hierarchy:

```css
:root {
  --md-tooltip-width: 600px;
}

/* Hovering cards from sphinx-design */
.sd-card {
  border-radius: 1rem;
  transition: box-shadow 0.2s ease, transform 0.2s ease;
}

.sd-card:hover {
  box-shadow: 0 4px 16px rgb(0 0 0 / 12%);
  transform: translateY(-2px);
}

/* Code block container aesthetics */
.code-block-caption {
  margin-bottom: 0.5rem;
  font-weight: 600;
}

pre > code {
  border-radius: 0.4rem;
}
```

## Best Practices

- **MyST extensions**: Activate `colon_fence`, `attrs_block`, and `deflist` in `conf.py` for rich Markdown rendering that doesn't rely on crude tables.
- **Navigation density**: Immaterial benefits from deep hierarchies; do not be afraid to nest toctrees, as the expandable sidebar handles them well.
- **Feature Toggles**: Start with all navigation features enabled, then strip down if layout is crowded for your specific page flow.

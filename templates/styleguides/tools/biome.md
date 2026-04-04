# Biome Style Guide

Biome is the standard JS/TS linter and formatter, replacing ESLint and Prettier.

## Configuration

Standard `biome.json`:

```json
{
  "$schema": "https://biomejs.dev/schemas/2.5.0/schema.json",
  "vcs": {
    "enabled": true,
    "clientKind": "git",
    "useIgnoreFile": true
  },
  "formatter": {
    "enabled": true,
    "indentStyle": "space",
    "indentWidth": 2,
    "lineWidth": 180,
    "lineEnding": "lf"
  },
  "linter": {
    "enabled": true,
    "rules": {
      "recommended": true,
      "suspicious": {
        "noExplicitAny": "off"
      },
      "complexity": {
        "noForEach": "off"
      }
    }
  },
  "javascript": {
    "formatter": {
      "quoteStyle": "double",
      "semicolons": "asNeeded"
    }
  }
}
```

## Key Settings

| Setting | Value | Rationale |
|---------|-------|-----------|
| `indentStyle` | `space` | Consistent across editors |
| `indentWidth` | `2` | Standard for JS/TS ecosystem |
| `lineWidth` | `180` | Match Python line-length for fullstack consistency |
| `quoteStyle` | `double` | Consistent with JSON, HTML attributes |
| `semicolons` | `asNeeded` | Cleaner code, ASI-safe |

## Overrides for Generated Code

```json
{
  "overrides": [
    {
      "includes": ["src/js/api/**/*", "src/js/routes/**/*"],
      "linter": {
        "rules": {
          "style": {
            "noDefaultExport": "off"
          }
        }
      }
    }
  ]
}
```

## Integration with Package Scripts

```json
{
  "scripts": {
    "lint": "biome check --write .",
    "format": "biome format --write .",
    "check": "biome check --write --files-ignore-unknown=true --no-errors-on-unmatched ."
  }
}
```

## Anti-Patterns

- **Don't use ESLint + Prettier** — Biome replaces both with faster Rust-based tooling
- **Don't mix formatting tools** — use Biome exclusively for JS/TS, Ruff for Python
- **Don't disable recommended rules broadly** — override per-file with `overrides`

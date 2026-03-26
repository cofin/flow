# Biome Configuration

Standard configuration for Biome linter and formatter.

## Core Settings

### Formatter

- **Enabled**: `true`
- **Indent Width**: `2`
- **Line Width**: `180`
- **Indent Style**: `space`
- **Line Ending**: `lf`

### Javascript Formatter

- **Quote Style**: `"double"`
- **JSX Quote Style**: `"double"`
- **Semicolons**: `"asNeeded"`

### Linter

- **Enabled**: `true`
- **Recommended**: `true`

---

## Linter Rules (Adjustments)

| Group | Rule | Status | Rationale |
|-------|------|--------|-----------|
| `suspicious` | `noExplicitAny` | `off` | Flexibility in type definitions |
| `suspicious` | `noUnknownAtRules` | `off` | CSS custom rules support |
| `complexity` | `noForEach` | `off` | Standard JS iteration |
| `a11y` | `noSvgWithoutTitle` | `off` | Icon libraries often omit titles |
| `nursery` | `useSortedClasses` | `warn` | Tailwind/CSS class sorting |

---

## Setup with UV

To run Biome inside a project environment:

```bash
# Run linter
uv run biome lint src/

# Run formatter check
uv run biome format src/

# Apply fixes
uv run biome check --apply src/
```

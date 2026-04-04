---
name: biome
description: "Auto-activate for biome.json, biome.jsonc. Expert knowledge for Biome toolchain (Linter, Formatter). Use when configuring workspace styles, troubleshooting linter errors, or setting up ignores/overrides for frontend projects. Produces Biome linter/formatter configurations with workspace overrides. Not for ESLint, Prettier, or non-JS/TS toolchains."
---

# Biome Skill

## Overview

Expert knowledge for Biome, an extremely fast toolchain for web projects (replaces ESLint and Prettier).

---

<workflow>

## References Index

For detailed guides on configurations and overrides:

- **[Standard Configuration](references/config.md)**
  - Formatter, linter rules, and JS style setups.
- **[Linter Overrides](references/overrides.md)**
  - Overrides for UI components (ShadCN), routing files, and generated code modules.

</workflow>

---

<example>

## Example Configuration

Minimal `biome.json` with workspace overrides:

```json
{
  "$schema": "https://biomejs.dev/schemas/1.9.4/schema.json",
  "organizeImports": { "enabled": true },
  "formatter": {
    "indentStyle": "space",
    "indentWidth": 2,
    "lineWidth": 100
  },
  "linter": {
    "enabled": true,
    "rules": { "recommended": true }
  },
  "overrides": [
    {
      "include": ["**/*.generated.ts"],
      "linter": { "enabled": false }
    }
  ]
}
```

</example>

---

## Official References

- <https://biomejs.dev/>
- <https://biomejs.dev/linter/rules/>
- <https://biomejs.dev/formatter/>

## Shared Styleguide Baseline

- Use shared styleguides for generic language/framework rules to reduce duplication in this skill.
- [General Principles](https://github.com/cofin/flow/blob/main/templates/styleguides/general.md)
- [Biome](https://github.com/cofin/flow/blob/main/templates/styleguides/tools/biome.md)
- Keep this skill focused on tool-specific workflows, edge cases, and integration details.

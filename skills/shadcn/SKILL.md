---
name: shadcn
description: Expert knowledge for Shadcn/ui component library. Use when building UI with Radix primitives, dialogs, forms, data tables, or command palettes.
---

# Shadcn/ui Skill (Current, Concise)

Use this skill when the task involves shadcn/ui setup, component generation, theming, or composition patterns.

## What is true right now

- shadcn/ui is code you copy into your app. It is not a runtime UI package you install once and import globally.
- The current CLI is `shadcn` via `shadcn@latest` (not legacy `shadcn-ui` commands).
- `components.json` is CLI config and is required for CLI-driven `add`; it is optional if you only copy/paste manually.
- Data table is intentionally a build-your-own guide using `@tanstack/react-table`, not a single drop-in component.
- Forms docs now emphasize `Field`-based composition with React Hook Form and accessibility attributes.
- shadcn now supports both Radix and Base UI primitives in docs/examples.

## Preferred workflow

1. Start from official install/create docs for the target framework.
2. Initialize project config if needed.
3. Add only the components required for the feature.
4. Keep generated component APIs intact (`variant`, `size`, `asChild`) and compose around them.
5. For forms/tables, follow official guide patterns instead of inventing custom abstractions first.

## CLI quick commands

Use the project package manager consistently.

```bash
# Scaffold a new app
pnpm dlx shadcn@latest create

# Initialize shadcn in an existing app
pnpm dlx shadcn@latest init

# Add components
pnpm dlx shadcn@latest add button dialog form table
```

## Integration guardrails

- Prefer CSS variables theming (`components.json` -> `tailwind.cssVariables: true`) unless project standards say otherwise.
- Use `@/components/ui/*` and `@/lib/utils` aliases consistently with project config.
- Validate accessibility in composed controls (`aria-invalid`, labels, descriptions, error text) when integrating forms.
- Treat docs/changelog as the source of truth when command syntax or component patterns conflict with old snippets.

## Official learn more

- Installation: https://ui.shadcn.com/docs/installation
- CLI: https://ui.shadcn.com/docs/cli
- components.json: https://ui.shadcn.com/docs/components-json
- Theming: https://ui.shadcn.com/docs/theming
- React Hook Form guide: https://ui.shadcn.com/docs/forms/react-hook-form
- Data Table guide: https://ui.shadcn.com/docs/components/data-table
- Monorepo support: https://ui.shadcn.com/docs/monorepo
- Changelog: https://ui.shadcn.com/docs/changelog
- Radix UI primitives: https://www.radix-ui.com/primitives/docs/overview/introduction
- Tailwind CSS install/docs: https://tailwindcss.com/docs/installation

## Shared styleguide baseline

- [General Principles](https://github.com/cofin/flow/blob/main/templates/styleguides/general.md)
- [Tailwind and Shadcn](https://github.com/cofin/flow/blob/main/templates/styleguides/frameworks/tailwind.md)
- [React](https://github.com/cofin/flow/blob/main/templates/styleguides/frameworks/react.md)

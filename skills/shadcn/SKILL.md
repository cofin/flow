---
name: shadcn
description: "Auto-activate for components.json (shadcn config), cn() utility. Tailwind component expertise for shadcn/ui. Use when: using cn() utility, Radix primitives, shadcn add, copy-paste components, component CLI, dialogs, forms, data tables, or command palettes. Not for Material UI, Chakra UI, or other component libraries."
---

# Shadcn/ui Component Library

<workflow>

## Official shadcn/ui Skills (Highly Recommended)

For component discovery, CLI mastery, and pattern enforcement, we highly recommend installing the official shadcn/ui agent skills:

- **shadcn**: Official skill for adding components and ensuring proper composition.

**Installation:**

```bash
npx skills add shadcn/ui
```

## Supplemental Patterns

The patterns below provide additional context for Flow-specific copy-paste workflows and SPA navigation.

## Overview

Shadcn/ui provides copy-paste components built on Radix UI primitives and Tailwind CSS. Components are added to your project via CLI, not installed as a dependency.

```bash
# Add components
bunx --bun shadcn@latest add button card dialog form table
```

---

## References Index

For detailed guides and code examples, refer to the following documents in `references/`:

- **[Best Practices](references/best_practices.md)**
  - TanStack Router & React Router integration, accessibility, and agent guidance.
- **[Core Components](references/components.md)**
  - Button, Input, Card, Select, Checkbox, Switch, and `cn()` utility.
- **[Dialogs & Overlays](references/dialogs.md)**
  - Dialogs, Sheets, Drawer, Popover, and AlertDialog.
- **[Forms](references/forms.md)**
  - Integration with `react-hook-form` and `zod`.
- **[Tables](references/tables.md)**
  - Data Table pattern with TanStack Table.
- **[Shadcn Docs](references/shadcn-docs.md)**
  - Official shadcn/ui documentation overview, CLI, theming, and registry.

---

## SPA Integration Notes

When using shadcn/ui components within a Single Page Application (SPA), ensure navigation does not cause full page reloads. Use `asChild` to pass the routing `Link` child directly.

<example>

```tsx
import { Link } from '@tanstack/react-router'
import { Button } from "@/components/ui/button"

<Button asChild>
  <Link to="/settings">Go to Settings</Link>
</Button>
```

</example>

</workflow>

---

## Official References

- <https://ui.shadcn.com/>
- <https://ui.shadcn.com/docs/components>
- <https://ui.shadcn.com/docs/forms/tanstack-form>

- **[Shadcn Docs](references/shadcn-docs.md)**
  - Official Shadcn/ui documentation reference.

## Shared Styleguide Baseline

- Use shared styleguides for generic language/framework rules to reduce duplication in this skill.
- [General Principles](https://github.com/cofin/flow/blob/main/templates/styleguides/general.md)
- [Tailwind](https://github.com/cofin/flow/blob/main/templates/styleguides/frameworks/tailwind.md)
- [TypeScript](https://github.com/cofin/flow/blob/main/templates/styleguides/languages/typescript.md)
- Keep this skill focused on tool-specific workflows, edge cases, and integration details.

<guardrails>
## Guardrails

- **Use `asChild` for Routing:** When integrating with SPA routers (e.g., TanStack Router, React Router), always use the `asChild` prop on shadcn components to pass the routing `Link` as a child. This prevents invalid nested links and ensures proper event handling.
- **Prefer Semantic Colors:** Use shadcn's semantic color variables (e.g., `text-primary`, `bg-secondary`) instead of hardcoded hex codes or arbitrary Tailwind colors. This ensures the application remains themable and supports dark mode out of the box.
- **Avoid Hardcoded Values:** Never use arbitrary padding, margin, or font sizes. Stick to the Tailwind utility classes provided by the shadcn configuration to maintain design consistency.
- **Keep Components Atomic:** Refactor shadcn components only for global application consistency. Avoid making a component "do too much"; use composition instead.
</guardrails>

<validation>
## Validation

- **Check Component Accessibility:** Verify that all shadcn/ui components used in the application maintain their ARIA attributes and keyboard navigation capabilities, especially after custom styling.
- **Verify CLI Version:** Ensure that `shadcn@latest` is used for adding new components to benefit from the latest bug fixes, accessibility improvements, and registry updates.
- **Confirm `cn()` Utility Usage:** Audit component code to ensure the `cn()` utility is used for all class merging, especially when combining base component styles with variant-specific classes or user-provided props.
- **Audit Semantic Theming:** Check that custom styles do not bypass the CSS variable-based theming system (e.g., using `text-red-500` instead of a variable defined in the theme).
</validation>

---
name: shadcn-tools
description: "Use when editing shadcn/ui code, components.json, cn() utility, Radix primitives, shadcn add workflows, dialogs, forms, data tables, command palettes, or Tailwind component composition."
---

# shadcn/ui (Flow Tools)

<workflow>

## 🚀 Official shadcn/ui Skills (Highly Recommended)

For component discovery, CLI mastery, and pattern enforcement, we highly recommend installing the official shadcn/ui agent skills:

- **shadcn**: Official skill for adding components and ensuring proper composition.

**Installation:**

```bash
npx skills add shadcn/ui
```

## Supplemental Patterns

The patterns below provide additional context for Flow-specific copy-paste workflows and SPA navigation.

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

<guardrails>
## Guardrails

- **Use `asChild` for Routing:** When integrating with SPA routers (e.g., TanStack Router, React Router), always use the `asChild` prop on shadcn components to pass the routing `Link` as a child. This prevents invalid nested links and ensures proper event handling.
- **Prefer Semantic Colors:** Use shadcn's semantic color variables (e.g., `text-primary`, `bg-secondary`) instead of hardcoded hex codes or arbitrary Tailwind colors. This ensures the application remains themable and supports dark mode out of the box.
- **Avoid Hardcoded Values:** Never use arbitrary padding, margin, or font sizes. Stick to the Tailwind utility classes provided by the shadcn configuration to maintain design consistency.
- **Keep Components Atomic:** Refactor shadcn components only for global application consistency. Avoid making a component "do too much"; use composition instead.
</guardrails>

<validation>
## Validation

- **Confirm `cn()` Utility Usage:** Audit component code to ensure the `cn()` utility is used for all class merging, especially when combining base component styles with variant-specific classes or user-provided props.
- **Audit Semantic Theming:** Check that custom styles do not bypass the CSS variable-based theming system (e.g., using `text-red-500` instead of a variable defined in the theme).
</validation>

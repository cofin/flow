---
name: shadcn
description: Expert knowledge for Shadcn/ui component library. Use when building UI with Radix primitives, dialogs, forms, data tables, or command palettes.
---

# Shadcn/ui Component Library

## Overview

Shadcn/ui provides copy-paste components built on Radix UI primitives and Tailwind CSS. Components are added to your project via CLI, not installed as a dependency.

```bash
# Add components
bunx --bun shadcn@latest add button card dialog form table
```

---

## References Index

For detailed guides and code examples, refer to the following documents in `references/`:

- **[Best Practices 2026](references/best_practices_2026.md)**
  - TanStack Router & React Router integration, accessibility, and agent guidance.
- **[Core Components](references/components.md)**
  - Button, Input, Card, Select, Checkbox, Switch, and `cn()` utility.
- **[Dialogs & Overlays](references/dialogs.md)**
  - Dialogs, Sheets, Drawer, Popover, and AlertDialog.
- **[Forms](references/forms.md)**
  - Integration with `react-hook-form` and `zod`.
- **[Tables](references/tables.md)**
  - Data Table pattern with TanStack Table.

---

## SPA Integration Notes

When using shadcn/ui components within a Single Page Application (SPA), ensure navigation does not cause full page reloads. Use `asChild` to pass the routing `Link` child directly.

```tsx
import { Link } from '@tanstack/react-router'
import { Button } from "@/components/ui/button"

<Button asChild>
  <Link to="/settings">Go to Settings</Link>
</Button>
```

---

## Official References

- https://ui.shadcn.com/
- https://ui.shadcn.com/docs/components
- https://ui.shadcn.com/docs/forms/tanstack-form

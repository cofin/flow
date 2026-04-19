# ShadCN/ui Best Practices 2026

## Core Principles

### 1. Full Code Ownership

- **Copy, Don't Install**: Components are added to your source tree (`src/components/ui/`). Modify them freely to fit your design system.
- **Avoid Over-Styling**: Keep local styles minimal. Handle full-page layout in parent containers.

### 2. Accessibility (Radix Primitives)

- **`asChild` Prop**: Crucial for SPA routing. Passes navigation behavior to children (e.g., `Link`) without breaking button semantics.
- **Interactive Safeguards**: Never wrap fully interactive components inside button tags. Let Radix handle ARIA attributes.

---

## Routing Integrations

### 1. TanStack Router (File-Based)

- **Wrapper Components**: Standard `Sheet` and `Dialog` can cause portal animation overlaps or trigger strict route rendering loops. Wrap them in route-aware contexts if animations get stuck.
- **Component Placement**: Avoid putting temporary or dialog components directly in route files. Place them in `./routes/-components/` or `./features/` to prevent TanStack Router from creating routes for them.
- **Type-Safe Links**:

  ```tsx
  import { Link } from '@tanstack/react-router'
  import { Button } from "@/components/ui/button"

  <Button asChild>
    <Link to="/dashboard" search={{ filter: 'active' }}>Dashboard</Link>
  </Button>
  ```

### 2. React Router

- **Standard Support**: Official and mature integration.
- **Layout Composition**: Verify that floating overlays (Portals) resolve correctly inside nested `<Outlet />` structures.

---

## Agent & LLM Best Practices

When generating UI code using assistants:

1. **Layout Separation**: Generate components that take styling props for outer margin/padding, rather than baking absolute layouts into the component itself.
2. **Guard Standard Defaults**: Do not change standard Radix hooks inside generated items unless specifically requested.
3. **Type Safety**: Always type inputs securely, especially when integrating with heavy validators like Zod or custom search parameters.

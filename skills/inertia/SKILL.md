---
name: inertia
description: Expert knowledge for Inertia.js with any backend. Use when building SPAs with server-side routing, handling Inertia responses, or managing page components.
---

# Inertia.js Skill

## Quick Reference

Inertia bridges server-side routing and client-side page rendering:

1. First visit returns full HTML + page payload.
2. Inertia visits send `X-Inertia` and receive JSON page payloads.
3. The client adapter swaps page components without a full reload.

### Client setup (React)

```tsx
import { createInertiaApp } from "@inertiajs/react";
import { createRoot } from "react-dom/client";

createInertiaApp({
  resolve: (name) => {
    const pages = import.meta.glob("./Pages/**/*.tsx", { eager: true });
    return pages[`./Pages/${name}.tsx`];
  },
  setup({ el, App, props }) {
    createRoot(el).render(<App {...props} />);
  },
});
```

### Client setup (Vue 3)

```ts
import { createApp, h } from "vue";
import { createInertiaApp } from "@inertiajs/vue3";

createInertiaApp({
  resolve: (name) => {
    const pages = import.meta.glob("./Pages/**/*.vue", { eager: true });
    return pages[`./Pages/${name}.vue`];
  },
  setup({ el, App, props, plugin }) {
    createApp({ render: () => h(App, props) }).use(plugin).mount(el);
  },
});
```

### Forms and visits

```tsx
import { useForm, router } from "@inertiajs/react";

const form = useForm({ name: "", email: "" });
form.post("/users");

router.reload({ only: ["users"] });
router.reload({ preserveScroll: true });
```

### Shared props in pages/layouts

```tsx
import { usePage } from "@inertiajs/react";

const page = usePage();
const user = page.props.auth?.user;
```

## Key v2 capabilities to use intentionally

- `Deferred props`: load non-critical data after initial render.
- `Merging props`: append/prepend/update paginated or incremental data.
- `Partial reloads`: request only specific props with `only`.
- `History encryption`: protect sensitive history state in supported server adapters.
- `Remembering state`: persist local state/form data in browser history.

## Litestar-Vite notes (if using Litestar backend)

Use current Litestar-Vite Inertia patterns:

```python
from typing import Any
from litestar import Request, get
from litestar_vite.inertia import InertiaResponse, share, defer

@get("/dashboard", component="Dashboard")
async def dashboard(request: Request) -> dict[str, Any]:
    share(request, "auth", {"user": request.user})
    return {
        "stats": defer("stats", get_dashboard_stats),
    }

@get("/account")
async def account() -> InertiaResponse:
    return InertiaResponse(
        content={"ssn": "..."},
        encrypt_history=True,
    )
```

For Precognition on Litestar-Vite, enable it in `InertiaConfig` and use `@precognition` on handlers that should short-circuit on validation requests.

## Where to learn more (official docs)

- Inertia docs home: https://inertiajs.com/
- Inertia client setup: https://inertiajs.com/docs/v2/installation/client-side-setup
- Inertia forms: https://inertiajs.com/forms
- Inertia partial reloads: https://inertiajs.com/partial-reloads
- Inertia deferred props: https://inertiajs.com/deferred-props
- Inertia merging props: https://inertiajs.com/merging-props
- Inertia shared data: https://inertiajs.com/shared-data
- Inertia history encryption: https://inertiajs.com/history-encryption
- Inertia v2 upgrade guide: https://inertiajs.com/docs/v2/getting-started/upgrade-guide
- Inertia releases: https://github.com/inertiajs/inertia/releases
- Litestar-Vite Inertia docs: https://litestar-org.github.io/litestar-vite/inertia/
- Litestar-Vite Inertia responses: https://litestar-org.github.io/litestar-vite/inertia/responses.html

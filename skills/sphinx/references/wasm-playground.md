
# Sphinx Wasm Playground Workflow

## Overview

Use this skill to add interactive WebAssembly (Wasm) playgrounds to Sphinx documentation workflows. It involves creating custom Docutils directive nodes that render HTML templates linked to browser-based execution runtimes like Pyodide.

## Implementation Strategy

The standard pattern utilizes a **custom Sphinx extension** residing in `tools/sphinx_ext/` combined with an HTML template.

### 1. Custom Directive (`tools/sphinx_ext/playground.py`)

Create a directive class that generates rendered nodes containing script contexts:

```python
"""Sphinx directive for Pyodide execution."""
from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import uuid4

from docutils import nodes
from docutils.parsers.rst import Directive
from jinja2 import Environment, FileSystemLoader, select_autoescape

TEMPLATE_NAME = "playground_template.html"

class WasmPlayground(Directive):
    """Embed a Wasm-powered playground in the docs."""
    has_content = False

    def run(self) -> list[nodes.Node]:
        playground_id = uuid4().hex
        env = Environment(
            loader=FileSystemLoader(Path(__file__).parent),
            autoescape=select_autoescape(["html", "xml"])
        )
        template = env.get_template(TEMPLATE_NAME)
        # Pass identifier or pre-seeded script contents back to layout
        rendered = template.render(id=playground_id)
        return [nodes.raw(text=rendered, format="html")]

def setup(app: Any) -> dict[str, Any]:
    app.add_directive("wasm-playground", WasmPlayground)
    return {"version": "1.0", "parallel_read_safe": True, "parallel_write_safe": True}
```

### 2. HTML Integration (`tools/sphinx_ext/playground_template.html`)

Ensure that your template incorporates essential script calls that interface well with standard template assets:

```html
<div id="playground-{{ id }}" class="playground-root">
  <!-- Structure for Code Editor and Output Area -->
</div>

<script>
  // Logic to wire Pyodide runtime triggers on demand
  // or load iframe sandboxes.
</script>
```

### 3. Configuration (`conf.py`)

Hook the extension into your build cycle:

```python
import sys
from pathlib import Path

# Ensure Sphinx can find local extensions
sys.path.insert(0, str(Path("../").resolve()))

extensions = [
    # ... other extensions
    "tools.sphinx_ext.playground",
]
```

## Integration best practices

-   **Sandboxed execution**: Favor loading heavy Wasm environments (like Pyodide libraries) in `<iframe>` wrappers or lazy-triggering them only when users click "Run" to minimize landing page load overhead.
-   **Dynamic Seeding**: Modify the directive layout so that users can place code inside directive bodies using standard block containers.
-   **Environment Cleanup**: Ensure execution variables do not bleed between multiple playground triggers sitting on alternative tabs.

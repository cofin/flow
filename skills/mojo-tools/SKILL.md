---
name: mojo-tools
description: "Flow-specific supplemental patterns for Mojo. Auto-activate for .mojo files, .🔥 files. Mojo development patterns for high-performance computing: SIMD, zero-copy Python interop, GIL-free parallelism, C FFI, and Hatch build integration. Use when: writing Mojo code, .mojo files, SIMD kernels, Python-Mojo hybrid projects, hatch-mojo build hooks, or packaging Mojo extensions into wheels. Produces high-performance Mojo code with SIMD kernels, Python interop, and Hatch build integration. Not for pure Python performance work or C extensions (see python/cpp)."
---

# Mojo (Flow Tools)

<workflow>

## 🚀 Official Modular Skills (Highly Recommended)

For comprehensive support for modern Mojo syntax, project initialization, and GPU programming, we highly recommend installing the official Modular agent skills:

- **mojo-syntax**: Overcomes agent misconceptions and ensures correct modern syntax.
- **new-modular-project**: Wizard for initializing Mojo/MAX projects with Pixi and UV.
- **mojo-python-interop**: Expert guidance for zero-copy Python interaction.
- **mojo-gpu-fundamentals**: Patterns for high-performance accelerator programming.

**Installation:**

```bash
npx skills add modular/skills
```

## Supplemental Patterns

The patterns below focus on project integration and build hooks.

### Hatch-Mojo Build Hook

The `hatch-mojo` plugin allows seamless compilation of Mojo source files during the standard Python build process.

**Key Configuration (`pyproject.toml`):**

```toml
[tool.hatch.build.targets.wheel.hooks.mojo]
# Configuration for mojo compilation
```

</workflow>

<guardrails>
## Guardrails

- **Explicitly define memory ownership** -- Use `owned`, `borrowed`, and `inout` to manage data flow and avoid unnecessary copies.
- **Use `SIMD` for performance-critical logic** -- Mojo excels at vectorization; always consider SIMD when processing large arrays.
- **Verify data alignment** -- Ensure pointers are aligned for the target architecture, especially when using SIMD operations.
</guardrails>

<validation>
## Validation Checkpoint

- [ ] Explicit ownership markers are correctly applied to arguments
- [ ] SIMD vectorization is implemented where applicable
- [ ] Memory safety is verified through ownership and borrowing checks
</validation>

<example>
## Hatch-Mojo Build Hook Example

```toml
[tool.hatch.build.targets.wheel.hooks.mojo]
dependencies = ["hatch-mojo"]
path = "src/my_extension.mojo"
```

</example>

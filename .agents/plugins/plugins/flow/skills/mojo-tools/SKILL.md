---
name: mojo-tools
description: "Use when editing Mojo code, .mojo files, fire emoji files, SIMD kernels, Python-Mojo interop, GIL-free parallelism, C FFI, hatch-mojo build hooks, or packaging Mojo extensions."
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

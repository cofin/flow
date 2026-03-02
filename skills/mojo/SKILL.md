---
name: mojo
description: "Current Mojo + Python interoperability guidance (Mojo ↔ Python calls, FFI, packaging handoff points, and official docs). Use when building or reviewing hybrid Python/Mojo code."
---

# Mojo + Python Interop (Current)

## Scope

- Use this skill for Mojo/Python boundary design and implementation.
- Focus areas:
- Calling Python from Mojo.
- Calling Mojo from Python.
- Native extension/module boundaries.
- C FFI used by interop layers.

## Current State (Important)

- Mojo language/tooling is still evolving; always verify behavior in current docs/changelog before coding.
- Python interoperability in Modular docs is available via:
- Mojo calling Python (`PythonObject`, Python module imports, method calls).
- Python calling Mojo (Mojo-built Python modules / extensions).

## Core Rules

### 1) Prefer official interop APIs, not ad-hoc pointer tricks

- Avoid undocumented pointer extraction patterns unless required for a proven low-level case.
- Prefer documented Python interop APIs first, then FFI only when needed.

### 2) Treat zero-copy as opt-in and API-specific

- Do not assume all Mojo↔Python data exchange is zero-copy.
- State ownership/lifetime explicitly whenever raw pointers or borrowed memory are involved.

### 3) Keep wrappers thin

- Put compute-heavy logic in Mojo.
- Keep Python boundary functions focused on conversion/validation and dispatch.

### 4) Be explicit about unstable behavior

- If guidance depends on toolchain version, cite the relevant changelog/manual page in code review notes or docs.

## Canonical Interop Patterns

### Mojo calling Python

Use documented Python interop surface:

```mojo
from python import Python

fn mean_via_numpy(x: PythonObject) raises -> PythonObject:
    let np = Python.import_module("numpy")
    return np.mean(x)
```

Guidelines:
- Use `raises` where Python exceptions can propagate.
- Convert/check types at boundaries; avoid implicit assumptions about Python object shape.

### Python calling Mojo

Use Mojo-supported Python module/extension workflows from official docs and examples.

Guidelines:
- Keep exported symbols minimal and stable.
- Treat module init/export APIs as version-sensitive; check docs for current signatures and helpers.
- Avoid copying legacy snippets blindly from old blog posts or stale repos.

## FFI in Interop Layers

- Use the current stdlib FFI docs (`ffi`) as source of truth for:
- `external_call` for link-time known symbols.
- Dynamic library loading handles/functions for runtime-loaded symbols.
- For C interop:
- Use exact-width numeric types where ABI matters.
- Document `UnsafePointer` safety assumptions inline.
- Validate callback lifetime and thread-safety assumptions explicitly.

## Build/Test Notes (Current)

- Use the current Mojo tooling docs for compile/build commands.
- Do not prescribe removed commands. Example: `mojo test` was removed (see changelog), so use current testing guidance from docs.
- For Python package integration, use the documented packaging path for your stack and pin tool versions where reproducibility matters.

## Environment Guidance

- Do not hard-ban environment managers in this skill.
- If project policy requires one tool (`uv`, `pixi`, etc.), follow project-local policy; otherwise default to project conventions already present in the repo.

## Review Checklist for Mojo↔Python PRs

- Interop API usage matches current official docs.
- Boundary functions are typed and failure paths are explicit.
- Ownership/lifetime of shared memory is documented.
- No stale commands or deprecated APIs in examples.
- Every non-obvious interop choice has an official doc link in PR notes.

## Where to Learn More (Official)

- Mojo docs home: https://docs.modular.com/mojo/
- Mojo changelog: https://docs.modular.com/mojo/changelog/
- Python interop manual (Mojo + Python): https://docs.modular.com/mojo/manual/python/
- Calling Mojo from Python: https://docs.modular.com/mojo/manual/python/mojo-from-python/
- Calling Python from Mojo: https://docs.modular.com/mojo/manual/python/python-from-mojo/
- Mojo FFI manual/API entry points:
- https://docs.modular.com/mojo/manual/c-ffi/
- https://docs.modular.com/mojo/stdlib/ffi/
- Modular coding-assistant guidance (official agent context): https://docs.modular.com/max/coding-assistants/

## Optional LLM Context Files (Modular Docs)

- https://docs.modular.com/llms-mojo.txt
- https://docs.modular.com/llms-mojo-python.txt
- https://docs.modular.com/llms-mojo-kernel.txt
- https://docs.modular.com/llms-max.txt
- https://docs.modular.com/llms.txt

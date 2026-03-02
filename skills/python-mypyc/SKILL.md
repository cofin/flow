---
name: python-mypyc
description: Practical mypyc guide for compiling typed Python to C extensions with current constraints, performance tips, and official references.
---

# mypyc Skill

## Overview

mypyc compiles typed Python modules into CPython C extensions for speedups (often strongest in typed, object-heavy code). It ships with `mypy` and is used to compile `mypy` itself.

## Use It When

- You already have solid type coverage in hot modules.
- Profiling shows Python interpreter overhead in those modules.
- You can accept C-extension build/distribution requirements.

## Core Guidance (Current)

### 1. Favor precise, non-`Any` types in hot paths

- mypyc generates better native ops when types are concrete.
- Add explicit annotations at boundaries to avoid `Any` propagation from untyped libs.

### 2. Understand native classes

- Classes in compiled modules are native by default (with exceptions).
- Native classes are already slot-like in behavior; `__slots__` is not a universal requirement.
- Only single inheritance is supported for native classes, except traits via `mypy_extensions.trait`.
- Dataclasses/attrs are supported with partial native support, typically less efficient than plain native classes.

### 3. Expect runtime type enforcement

- mypyc enforces many annotations at runtime and can raise `TypeError` where interpreted Python would not.
- `cast(...)` can become runtime checks in compiled code.

### 4. Plan around Python-compat differences

- Compiled functions/classes/module attributes are more static/immutable.
- Some features are unsupported or limited (for example nested classes and conditional class/function definitions).
- Compiled extensions are imported modules, not script entrypoints.

## Build and Workflow

1. Type-check first (`mypy`) and tighten untyped areas in performance-critical code.
2. Compile targeted modules first (do not compile everything blindly).
3. Re-profile compiled vs interpreted behavior before expanding scope.

Minimal official build entrypoint example uses `setuptools` + `mypyc.build.mypycify` (see Getting Started docs).

## Common Pitfalls

- Treating mypyc as a drop-in speedup without type cleanup.
- Heavy dynamic patterns (runtime mutation, unsupported decorators/metaclasses) in compiled modules.
- Assuming CPython runtime behavior is identical in all edge cases.

## Official Learn More

- Docs home: https://mypyc.readthedocs.io/en/stable/
- Getting started: https://mypyc.readthedocs.io/en/stable/getting_started.html
- Performance tips: https://mypyc.readthedocs.io/en/stable/performance_tips_and_tricks.html
- Native classes: https://mypyc.readthedocs.io/en/stable/native_classes.html
- Differences from Python: https://mypyc.readthedocs.io/en/stable/differences_from_python.html
- Type annotations and optimization model: https://mypyc.readthedocs.io/en/stable/using_type_annotations.html
- mypy repository (`mypyc` source lives there): https://github.com/python/mypy/tree/master/mypyc

## Shared Styleguide Baseline

- Use shared styleguides for generic language/framework rules to reduce duplication in this skill.
- [General Principles](https://github.com/cofin/flow/blob/main/templates/styleguides/general.md)
- [Python](https://github.com/cofin/flow/blob/main/templates/styleguides/languages/python.md)
- Keep this skill focused on tool-specific workflows, edge cases, and integration details.

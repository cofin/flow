---
name: pyapp
description: "Auto-activate for pyapp build config. Build air-gapped, multi-architecture standalone Python executables using PyApp and uv. Use when: bundling Python runtimes for network-isolated environments, patching PyApp defaults, or compiling single-binary assets."
---

# PyApp Standalone Binaries

Enable building self-contained, air-gapped, multi-architecture standalone executables for any Python application using **PyApp** and **uv**.

---

## Overview

Standard `pyapp` installation bootstraps the environment on first run, which usually requires internet access. For **air-gapped** or **network-isolated** environments, you must embed the entire Python distribution and its dependencies ahead of time.

This skill documents the **Bundle-Patch-Compile** workflow:

1. **Bundle**: Download a standalone Python build, install dependencies into its `site-packages`, and repackage.
2. **Patch**: Modify the PyApp source code to enforce custom install locations or isolation defaults.
3. **Compile**: Compile the patched PyApp binary with the bundled distribution embedded.

---

## Architecture & Philosophy

### The Packaged Distribution

Instead of installing at runtime, we build a **hybrid distribution**:

* A basic standalone Python distribution (e.g., from `python-build-standalone`).
* Pre-populated `site-packages` via `uv pip install --target`.
* This avoids running any package managers on first execution.

---

## Configuration

### 1. Standard Settings

In your `pyproject.toml`, configure the Hatch target or custom builder to use specific variables.

```toml
[tool.hatch.build.targets.binary]
scripts = ["myapp"]
pyapp-version = "v0.29.0"

[tool.hatch.build.targets.binary.env]
PYAPP_DISTRIBUTION_EMBED = "1"
PYAPP_FULL_ISOLATION = "1"
PYAPP_ALLOW_UPDATES = "1"
```

---

## Step-by-Step Workflow

### Phase 1: Bundling (Prep the Runtime)

To enable fully offline operations, follow these steps using an automation script (see `scripts/bundler.py`):

1. **Download Standalone Python**: Acquire a compatible `install_only_stripped` version for the Target Rust arch (e.g., `x86_64-unknown-linux-gnu`).
2. **Install Deps Off-Target**: Use `uv pip install` with specific cross-compilation flags:
    * `--target <extracted_python_site_packages>`
    * `--python-platform <uv_supported_platform>`
    * `--upgrade`
3. **Repackage**: Compress the resulting layout back into a `.tar.gz`.

### Phase 2: PyApp Patching (Enforce Paths)

By default, PyApp stores user data in standard local data folders. If you require strict isolation (e.g., `~/.myapp`), you can **patch the PyApp source code** just before `cargo build`:

```python
# Conceptual example of patching src/app.rs
import re
content = app_rs.read_text()
pattern = re.compile(r"platform_dirs\(\)\s*\.data_local_dir\(\)...")
replacement = "std::path::PathBuf::from(\"~/.myapp\")"
app_rs.write_text(pattern.sub(replacement, content))
```

### Phase 3: Compiling

To maintain maximum glibc backward-compatibility (e.g., supporting RHEL 7+ / manylinux2014 baseline):

* Use **Zig** as the linker trigger: `cargo zigbuild --release --target <target>.2.17`

---

## CI/CD Integration

Ensure your GitHub Action includes:

1. An upstream build step creating target-agnostic `.whl` files.
2. A cross-target build matrix (`x86_64-linux-gnu`, `aarch64-linux-gnu`, `aarch64-apple-darwin`, etc.).
3. Zig setup steps for robust glibc pin targeting.

> [!TIP]
> Always test inside a non-networked container:
> `docker run --network none -v $(pwd):/app ubuntu:20.04 /app/myapp-binary --help`

---

## Provided Resources

* **Bundler Template**: `scripts/bundler.py` (in this skill directory)
* **CI Matrix Action Example**: `examples/release-action.yml` (in this skill directory)

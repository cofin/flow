# hatch-mojo Usage Guide

`hatch-mojo` is a Hatch build hook that compiles `.mojo` sources during Python package builds.

This guide is based on your current library implementation in `/home/cody/code/c/hatch-mojo` (`v0.1.5`).

## 1. Prerequisites

1. Install Mojo toolchain and ensure `mojo` is runnable.
2. Use a Hatch/Hatchling build backend project (`pyproject.toml`).
3. Add `hatch-mojo` as a build dependency.

## 2. Install

```bash
uv add hatch-mojo
```

## 3. Minimal `pyproject.toml` setup

```toml
[build-system]
build-backend = "hatchling.build"
requires = ["hatchling", "hatch-mojo"]

[tool.hatch.build.targets.wheel.hooks.mojo]
targets = ["wheel"]

[[tool.hatch.build.targets.wheel.hooks.mojo.jobs]]
name = "core"
input = "src/mo/my_pkg/core.mojo"
emit = "python-extension"
module = "my_pkg._core"
include-dirs = ["src/mo"]
```

Build:

```bash
hatch build -t wheel
```

## 4. Global hook options

```toml
[tool.hatch.build.targets.wheel.hooks.mojo]
mojo-bin = "/opt/mojo/bin/mojo"    # or use HATCH_MOJO_BIN env var
parallel = true
fail-fast = true
clean-before-build = false
clean-after-build = false
skip-editable = true
build-dir = "build/mojo"
targets = ["wheel"]
include = ["src/mo/**/*.mojo"]
exclude = ["**/experimental*.mojo"]
bundle-libs = true
```

## 5. Profiles and multiple jobs

Profiles reduce duplication across compile jobs.

```toml
[tool.hatch.build.targets.wheel.hooks.mojo.profiles.default]
include-dirs = ["src/mo"]
flags = ["-I", "vendor/include"]

[[tool.hatch.build.targets.wheel.hooks.mojo.jobs]]
name = "core"
profiles = ["default"]
input = "src/mo/my_pkg/core.mojo"
emit = "python-extension"
module = "my_pkg._core"

[[tool.hatch.build.targets.wheel.hooks.mojo.jobs]]
name = "cli"
profiles = ["default"]
input = "src/mo/my_pkg/cli.mojo"
emit = "executable"
install = { kind = "scripts", path = "my-cli" }
depends-on = ["core"]
```

For non-Python artifacts (`shared-lib`, `static-lib`, `object`, `executable`), set `install = { kind, path }`.

## 6. Runtime library bundling (`bundle-libs`)

Set:

```toml
[tool.hatch.build.targets.wheel.hooks.mojo]
bundle-libs = true
```

What it does:

1. Bundles Mojo runtime libs into the wheel.
2. Linux: updates RPATH (requires `patchelf`).
3. macOS: rewrites dylib references (`install_name_tool`).
4. Adds `NOTICE.mojo-runtime`; copies SDK license if present.

## 7. cibuildwheel notes

### Linux (manylinux)

If your Mojo SDK requires a newer glibc/libstdc++ baseline, use retagging flow:

```toml
[tool.cibuildwheel.linux]
repair-wheel-command = "python -m wheel tags --remove --platform-tag manylinux_2_34_x86_64 {wheel} && mv {wheel} {dest_dir}"
```

### macOS

Use standard `delocate`:

```toml
[tool.cibuildwheel.macos]
repair-wheel-command = "delocate-wheel -w {dest_dir} {wheel}"
```

If needed, pass `DYLD_LIBRARY_PATH` inline in the repair command (SIP may strip it from environment inheritance).

## 8. Common errors

1. `mojo executable not found`
Solution: set `mojo-bin`, export `HATCH_MOJO_BIN`, or add `mojo` to `PATH`.

2. `No build jobs resolved`
Solution: verify `input` paths, `include`/`exclude` globs, and target matching.

3. Non-Python output missing from wheel
Solution: add `install = { kind, path }` on non-extension jobs.

4. Python extension not importable
Solution: verify `module` matches final package import path (e.g., `my_pkg._core`).

## 9. Deployment

### Publishing to PyPI
Use `uv publish` for publishing completed wheels. 2026 standards prefer OIDC authentication.

---

## 10. CI/CD Actions

Example GitHub Actions workflow utilizing `cibuildwheel` to compile multi-platform wheels support:

```yaml
name: Build Wheels
on: [push, pull_request]

jobs:
  build_wheels:
    name: Build wheels on ${{ matrix.os }}
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest]

    steps:
      - uses: actions/checkout@v4

      - name: Install Mojo
        run: |
          curl -s https://get.modular.com | sh -
          modular install mojo
          echo "$HOME/.modular/pkg/packages.modular.com_mojo/bin" >> $GITHUB_PATH

      - name: Build and test wheels
        uses: pypa/cibuildwheel@v2.22
        env:
          CIBW_BEFORE_BUILD: "pip install hatchling hatch-mojo"
          # Apply platform-conditional repair commands from section 7
```

## 11. Where to learn more

1. Library repo: `https://github.com/cofin/hatch-mojo`
2. Project README: `/home/cody/code/c/hatch-mojo/README.md`
3. Hatch build hooks: `https://hatch.pypa.io/`
4. Mojo docs: `https://docs.modular.com/mojo/`
5. cibuildwheel docs: `https://cibuildwheel.pypa.io/`

---
name: duckdb-extension
description: Build, debug, test, and ship DuckDB C++ extensions using current DuckDB extension best practices. Use when working on extension repos with files like `extension_config.cmake`, `CMakeLists.txt`, `src/*.cpp`, `test/*.test`, and GitHub Actions pipelines for distribution.
---

# DuckDB Extension Development

## Overview

Use this skill to implement and maintain DuckDB extensions with a predictable workflow: configure/build, run DuckDB SQL tests, keep extension metadata/versioning aligned, and ship binaries through CI.

## Workflow

1. Confirm extension wiring.
2. Build with the repo's supported flow.
3. Run unit/integration SQL tests.
4. Validate extension packaging/distribution config.
5. Prepare release artifacts and compatibility notes.

## 1) Confirm wiring first

Check these files before changing code:

1. `extension_config.cmake` to ensure `duckdb_extension_load(<name> ...)` is correct.
2. `CMakeLists.txt` to verify sources, include paths, and third-party link logic.
3. `Makefile` and CI makefiles for canonical build/test targets.
4. `test/unit_tests/*.test` and `test/integration_tests/*.test` for expected behavior.

## 2) Follow DuckDB extension build conventions

Prefer the extension-template/extension-ci-tools pattern:

1. Keep extension metadata in `extension_config.cmake`.
2. Use CMake for both loadable and static extension targets where needed.
3. Keep platform-specific dependency resolution explicit.
4. Avoid one-off local scripts for core build orchestration when existing make/CI targets already define behavior.

## 3) Testing best practices

1. Run fast unit tests first (no external DB dependency).
2. Run integration tests in containerized environments for external systems.
3. Keep SQL logic tests close to DuckDB's `sqllogictest` style and isolate regressions with focused files.
4. When adding pushdown/type behavior, add direct tests for predicate/projection/type mapping, not only broad end-to-end tests.

## 4) Local evaluation checklist for `duckdb-oracle`

For `/home/cody/code/other/duckdb-oracle`:

1. Build wiring looks correct: `extension_config.cmake` loads `oracle`.
2. CMake integrates OCI detection and links OCI/OpenSSL in both static/loadable targets.
3. Build/test ergonomics are good: `Makefile` has `release`, `test`, `integration`, `tidy-check`, `configure_ci`.
4. Release process is documented in `docs/RELEASE.md` with tag-driven GitHub Actions flow.
5. Improvement opportunity: document signed-extension path and long-term upgrade strategy against DuckDB release cadence in one place.

## DuckDB best-practice guardrails

1. Keep extension changes aligned to the targeted DuckDB branch/version matrix.
2. Prefer reproducible CI/container builds over host-specific assumptions.
3. Keep compatibility notes explicit for each DuckDB version line.
4. Test both functional correctness and extension loading/install experience.

## Learn more (official)

1. DuckDB extension template: https://github.com/duckdb/extension-template
2. DuckDB extension distribution overview: https://duckdb.org/docs/stable/extensions/extension_distribution
3. Community extensions: https://duckdb.org/community_extensions/list_of_extensions
4. Extension CI tools: https://github.com/duckdb/extension-ci-tools
5. C API extension loading reference: https://duckdb.org/docs/stable/clients/c/api.html

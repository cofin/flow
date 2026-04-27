# DuckDB Extension Development

## Overview

Use this reference to implement and maintain DuckDB extensions with a predictable workflow: configure/build, run DuckDB SQL tests, keep extension metadata/versioning aligned, and ship binaries through CI.

## Workflow

1. Confirm extension wiring.
2. Build with the repo's supported flow.
3. Run unit/integration SQL tests.
4. Validate extension packaging/distribution config.
5. Prepare release artifacts and compatibility notes.

---

## 1) Confirm Wiring First

Check these files before changing code:

1. `extension_config.cmake` to ensure `duckdb_extension_load(<name> ...)` is correct.
2. `CMakeLists.txt` to verify sources, include paths, and third-party link logic.
3. `Makefile` and CI makefiles for canonical build/test targets.
4. `test/unit_tests/*.test` and `test/integration_tests/*.test` for expected behavior.

---

## 2) Follow DuckDB Extension Build Conventions

Prefer the extension-template/extension-ci-tools pattern:

1. Keep extension metadata in `extension_config.cmake`.
2. Use CMake for both loadable and static extension targets where needed.
3. Keep platform-specific dependency resolution explicit.
4. Avoid one-off local scripts for core build orchestration when existing make/CI targets already define behavior.

### extension_config.cmake

```cmake
duckdb_extension_load(my_extension
    SOURCE_DIR ${CMAKE_CURRENT_LIST_DIR}
    LOAD_TESTS
)
```

### CMakeLists.txt Pattern

```cmake
cmake_minimum_required(VERSION 3.12)
set(EXTENSION_NAME my_extension)
project(${EXTENSION_NAME})

include_directories(src/include)

set(EXTENSION_SOURCES
    src/my_extension.cpp
    src/my_functions.cpp
)

build_static_extension(${EXTENSION_NAME} ${EXTENSION_SOURCES})
build_loadable_extension(${EXTENSION_NAME} " " ${EXTENSION_SOURCES})
```

---

## 3) Testing Best Practices

1. Run fast unit tests first (no external DB dependency).
2. Run integration tests in containerized environments for external systems.
3. Keep SQL logic tests close to DuckDB's `sqllogictest` style and isolate regressions with focused files.
4. When adding pushdown/type behavior, add direct tests for predicate/projection/type mapping, not only broad end-to-end tests.

### SQL Logic Test Pattern

```text
# test/sql/my_extension/basic.test

# name: test/sql/my_extension/basic.test
# description: Test basic my_extension functionality

require my_extension

statement ok
SELECT my_function('hello');

query I
SELECT my_function('world');
----
expected_result
```

---

## 4) Local Evaluation Checklist

When evaluating a DuckDB extension project:

1. Build wiring looks correct: `extension_config.cmake` loads the extension name.
2. CMake integrates external dependency detection and links required libraries in both static/loadable targets.
3. Build/test ergonomics are good: `Makefile` has `release`, `test`, `integration`, `tidy-check`, `configure_ci`.
4. Release process is documented (e.g., `docs/RELEASE.md`) with tag-driven GitHub Actions flow.
5. Consider documenting signed-extension path and long-term upgrade strategy against DuckDB release cadence.

---

## 5) Distribution and CI

### GitHub Actions Pattern

- Use `duckdb/extension-ci-tools` for standardized CI workflows.
- Tag-driven releases produce platform-specific binaries.
- Test across the DuckDB version matrix supported by the extension.

### Installing Extensions

```sql
-- From community repository
INSTALL my_extension FROM community;
LOAD my_extension;

-- From custom repository
SET custom_extension_repository = 'https://my-repo.example.com';
INSTALL my_extension;
```

---

## DuckDB Best-Practice Guardrails

1. Keep extension changes aligned to the targeted DuckDB branch/version matrix.
2. Prefer reproducible CI/container builds over host-specific assumptions.
3. Keep compatibility notes explicit for each DuckDB version line.
4. Test both functional correctness and extension loading/install experience.

---

## Official References

- DuckDB extension template: <https://github.com/duckdb/extension-template>
- Extension distribution overview: <https://duckdb.org/docs/extensions/overview>
- Extension distribution: <https://duckdb.org/docs/stable/extensions/extension_distribution>
- Community extensions: <https://duckdb.org/community_extensions/list_of_extensions>
- Extension CI tools: <https://github.com/duckdb/extension-ci-tools>
- C API extension loading reference: <https://duckdb.org/docs/stable/clients/c/api.html>

---
name: cpp
description: "Auto-activate for .cpp, .hpp, .cc, .hh, .cxx, CMakeLists.txt. Modern C++ development patterns for extensions and backend systems. Produces modern C++ code with proper build systems, resource management, and CI/CD integration. Use when: designing C++ code, setting up CI/CD pipelines, managing builds, or working with resource ownership, APIs, error handling, and concurrency in C++ projects. Not for C code or legacy C++ without modern idioms."
---

# C++ Development

## Overview

Use this skill for modern C++ extension and backend work: safe, maintainable design choices plus a reliable build-and-release pipeline. Covers resource ownership, API boundaries, error handling, concurrency, local builds, git workflow, and CI/CD.

## Quick Reference

### Key Design Principles

| Principle | Rule |
|---|---|
| Resource management | RAII for all resource lifetimes; no raw `new`/`delete` |
| Ownership | `std::unique_ptr` for exclusive, `std::shared_ptr` only when truly shared |
| Error handling | Explicit policy per module (exceptions or error codes); never mix ad hoc |
| Immutability | `const` by default on variables, parameters, and methods |
| API boundaries | Small, stable headers; hide implementation in `.cpp` files |
| Concurrency | Message passing or clear lock ownership; document thread-safety per type |
| Performance | Measure first; avoid allocations in hot loops; keep data cache-friendly |

### CMake Setup Pattern

```cmake
cmake_minimum_required(VERSION 3.20)
project(mylib VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# Library target
add_library(mylib src/mylib.cpp)
target_include_directories(mylib PUBLIC include)

# Tests
option(BUILD_TESTS "Build tests" ON)
if(BUILD_TESTS)
    enable_testing()
    add_subdirectory(tests)
endif()
```

### Build Commands

| Action | Command |
|---|---|
| Configure (debug) | `cmake -B build -DCMAKE_BUILD_TYPE=Debug` |
| Configure (release) | `cmake -B build -DCMAKE_BUILD_TYPE=Release` |
| Build | `cmake --build build -j$(nproc)` |
| Test | `ctest --test-dir build --output-on-failure` |
| Tidy check | `clang-tidy src/*.cpp -- -I include` |
| Sanitizer build | `cmake -B build -DCMAKE_CXX_FLAGS="-fsanitize=address,undefined"` |

<workflow>

## Workflow

### Step 1: Set Up the Build System

Create `CMakeLists.txt` with C++20 standard, `CMAKE_EXPORT_COMPILE_COMMANDS ON` (for tooling), and separate library/executable/test targets.

### Step 2: Design the API

Define public headers in `include/`. Keep headers minimal — forward-declare where possible, use the Pimpl idiom for implementation hiding. Document thread-safety guarantees on public types.

### Step 3: Implement with RAII

Use smart pointers for heap allocations, RAII wrappers for file handles / sockets / locks. Never use raw `new`/`delete`. Prefer value types and references over pointers.

### Step 4: Write Tests

Use a testing framework (GoogleTest, Catch2). Write tests alongside implementation. Focus on behavior and edge cases, not line coverage.

### Step 5: Configure CI

Build matrix across supported OS/arch. Run clang-tidy and sanitizers (ASan, UBSan) in CI. Separate fast unit tests from slower integration tests. Cache dependencies/toolchains.

</workflow>

<guardrails>

## Guardrails

- **No raw `new`/`delete`** — use `std::make_unique` / `std::make_shared`; if you need custom allocation, wrap it in an RAII type
- **Prefer `std::` algorithms** over hand-written loops — `std::ranges::find`, `std::transform`, `std::accumulate` are safer and often faster
- **Use sanitizers in CI** — always run AddressSanitizer and UndefinedBehaviorSanitizer; add ThreadSanitizer for concurrent code
- **Do not throw across C ABI boundaries** — catch exceptions at the boundary and convert to error codes
- **Avoid global mutable state** — it creates hidden dependencies and makes testing and concurrency harder
- **Keep critical sections short** — hold locks for the minimum duration; prefer lock-free designs when measured to be necessary
- **Validate inputs early** — check preconditions at API boundaries and return actionable diagnostics

</guardrails>

<validation>

### Validation Checkpoint

Before delivering code, verify:

- [ ] No raw `new`/`delete` — all allocations use smart pointers or RAII wrappers
- [ ] `CMakeLists.txt` sets C++ standard, exports compile commands, and has test targets
- [ ] Public headers are minimal (forward declarations, no implementation details)
- [ ] Thread-safety guarantees are documented on public types
- [ ] CI configuration includes sanitizers (ASan + UBSan at minimum)
- [ ] Error handling policy is consistent within the module

</validation>

<example>

## Example

CMakeLists.txt and a class demonstrating RAII:

```cmake
# CMakeLists.txt
cmake_minimum_required(VERSION 3.20)
project(sensor_reader VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

add_library(sensor_reader src/sensor_reader.cpp)
target_include_directories(sensor_reader PUBLIC include)
```

```cpp
// include/sensor_reader/sensor_reader.hpp
#pragma once

#include <cstdint>
#include <memory>
#include <span>
#include <string>
#include <string_view>

/// Thread-safety: NOT thread-safe. Each instance must be used from one thread.
class SensorReader {
public:
    /// Opens a connection to the sensor at the given device path.
    /// Throws std::runtime_error if the device cannot be opened.
    explicit SensorReader(std::string_view device_path);

    /// RAII: closes the connection on destruction.
    ~SensorReader();

    // Non-copyable, moveable
    SensorReader(const SensorReader&) = delete;
    SensorReader& operator=(const SensorReader&) = delete;
    SensorReader(SensorReader&&) noexcept;
    SensorReader& operator=(SensorReader&&) noexcept;

    /// Read up to `buffer.size()` bytes. Returns the number of bytes read.
    [[nodiscard]] std::size_t read(std::span<std::uint8_t> buffer) const;

    /// Device path this reader is connected to.
    [[nodiscard]] std::string_view device_path() const noexcept;

private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
};
```

```cpp
// src/sensor_reader.cpp
#include "sensor_reader/sensor_reader.hpp"

#include <fcntl.h>
#include <unistd.h>

#include <stdexcept>
#include <utility>

struct SensorReader::Impl {
    std::string device_path;
    int fd = -1;

    ~Impl() {
        if (fd >= 0) {
            ::close(fd);
        }
    }
};

SensorReader::SensorReader(std::string_view device_path)
    : impl_(std::make_unique<Impl>()) {
    impl_->device_path = std::string(device_path);
    impl_->fd = ::open(impl_->device_path.c_str(), O_RDONLY);
    if (impl_->fd < 0) {
        throw std::runtime_error("Failed to open device: " + impl_->device_path);
    }
}

SensorReader::~SensorReader() = default;
SensorReader::SensorReader(SensorReader&&) noexcept = default;
SensorReader& SensorReader::operator=(SensorReader&&) noexcept = default;

std::size_t SensorReader::read(std::span<std::uint8_t> buffer) const {
    const auto n = ::read(impl_->fd, buffer.data(), buffer.size());
    if (n < 0) {
        throw std::runtime_error("Read failed on device: " + impl_->device_path);
    }
    return static_cast<std::size_t>(n);
}

std::string_view SensorReader::device_path() const noexcept {
    return impl_->device_path;
}
```

</example>

---

## References Index

For detailed guides, refer to the following documents in `references/`:

- **[Design Best Practices](references/design.md)**
  - Modern C++ design and implementation: resource ownership (RAII), API conventions, error handling, performance hygiene, and concurrency.
- **[Build & CI Workflow](references/ci_workflow.md)**
  - Local developer workflow, git branching strategy, CI pipeline design, release and compatibility flow.

---

## Official References

1. C++ Core Guidelines: <https://isocpp.github.io/CppCoreGuidelines/CppCoreGuidelines>
2. C++ reference (language/library): <https://en.cppreference.com/>
3. CMake docs: <https://cmake.org/cmake/help/latest/>
4. Clang-Tidy checks: <https://clang.llvm.org/extra/clang-tidy/>
5. GitHub Actions docs: <https://docs.github.com/actions>
6. GitHub Actions security hardening: <https://docs.github.com/actions/security-guides/security-hardening-for-github-actions>
7. Conventional Commits: <https://www.conventionalcommits.org/>
8. SemVer: <https://semver.org/>

## Shared Styleguide Baseline

- Use shared styleguides for generic language/framework rules to reduce duplication in this skill.
- [General Principles](https://github.com/cofin/flow/blob/main/templates/styleguides/general.md)
- Keep this skill focused on tool-specific workflows, edge cases, and integration details.

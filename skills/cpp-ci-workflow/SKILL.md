---
name: cpp-ci-workflow
description: Define and execute a dependable C++ build + git + CI workflow for extension projects. Use when setting up or improving build targets, branch/PR policy, release tagging, and multi-platform CI pipelines for C++ repositories.
---

# C++ Build, Git, and CI Workflow

## Overview

Use this skill to keep C++ project delivery predictable: clean local build/test commands, disciplined git flow, and CI pipelines that match release requirements.

## Local developer workflow

1. Keep canonical make/cmake targets documented (`release`, `debug`, `test`, `integration`, `tidy-check`).
2. Make environment setup explicit (`configure_ci`-style target for dependencies/toolchains).
3. Use fast local checks before pushing.
4. Keep integration tests reproducible via containers.

## Git workflow

1. Branch from `main` with short-lived feature/fix branches.
2. Keep commits atomic and scoped (code, tests, docs).
3. Require green CI before merge.
4. Use semantic version tags for release automation (`vX.Y.Z`, optional prerelease suffix).
5. Keep changelog/release notes synced to tagged artifacts.

## CI pipeline design

1. Build matrix should match supported OS/arch/release targets.
2. Separate smoke/unit checks from heavier integration jobs.
3. Cache dependencies/toolchains, but keep cache invalidation clear.
4. Use least-privilege tokens; only elevate when workflow updates require it.
5. Publish artifacts with deterministic naming that encodes extension and DuckDB version.

## Release and compatibility flow

1. Trigger release pipeline from tags.
2. Verify artifacts on release page and smoke-load in target runtime.
3. Track compatibility matrix against upstream DuckDB versions.
4. Keep upgrade automation (e.g., DuckDB version update workflows) documented.

## Review checklist

1. Can a new contributor build and run tests from docs alone?
2. Do CI jobs mirror local commands?
3. Are release steps repeatable and scriptable?
4. Are platform-specific dependencies explicit?
5. Are secrets/tokens minimally scoped?

## Learn more (official)

1. GitHub Actions docs: https://docs.github.com/actions
2. GitHub Actions security hardening: https://docs.github.com/actions/security-guides/security-hardening-for-github-actions
3. CMake docs: https://cmake.org/cmake/help/latest/
4. Conventional Commits (optional policy): https://www.conventionalcommits.org/
5. SemVer: https://semver.org/

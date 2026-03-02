---
name: makefile
description: Concise, modern Makefile patterns with safe defaults, clear help output, and official references.
---

# Makefile Skill

## Overview

Use a consistent `Makefile` shape so common tasks are discoverable and safe.
Prefer:
- Explicit `.PHONY` declarations for task targets.
- Self-documenting `help` output from `##` comments.
- Minimal global side effects.
- Target names that match team workflows (`install`, `lint`, `test`, `clean`, etc.).

## Standard Template

Use this baseline and customize command bodies per project:

```makefile
SHELL := /usr/bin/env bash
.SHELLFLAGS := -eu -o pipefail -c

.DEFAULT_GOAL := help
MAKEFLAGS += --no-print-directory

ifndef VERBOSE
  .SILENT:
endif

.PHONY: help
help: ## Show available targets
	@awk 'BEGIN { FS = ":.*##"; printf "\nUsage:\n  make <target>\n\nTargets:\n" } \
	/^[a-zA-Z0-9_.-]+:.*##/ { printf "  %-18s %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

.PHONY: install
install: ## Install dependencies
	@echo "implement install"

.PHONY: lint
lint: ## Run linters
	@echo "implement lint"

.PHONY: test
test: ## Run tests
	@echo "implement test"

.PHONY: clean
clean: ## Remove local build/test artifacts
	@rm -rf build dist .pytest_cache .ruff_cache .mypy_cache
```

## Current Guidance (Audit Notes)

1. Do not enable `.EXPORT_ALL_VARIABLES` by default.
`GNU make` documents it, but also recommends explicit `export` instead of “export everything” because of unexpected side effects.

2. Use `.ONESHELL` only when needed.
It can improve performance and script readability, but changes failure behavior across recipe lines. If used, pair it with strict `.SHELLFLAGS` and validate recipes.

3. Keep templates tool-agnostic.
Avoid hard-coding ecosystem commands (`uv`, `npm`, `cargo`, etc.) in a “standard” template. Add stack-specific targets in project-local Makefiles.

4. Keep portability explicit.
If you require Bash features (`pipefail`, arrays), declare Bash in `SHELL`. If you need POSIX portability, stay with `/bin/sh` and compatible flags.

## Where to Learn More (Official)

- GNU Make Manual (4.4.1): https://www.gnu.org/software/make/manual/make.html
- GNU `.ONESHELL`: https://www.gnu.org/software/make/manual/html_node/One-Shell.html
- GNU special targets (`.PHONY`, `.EXPORT_ALL_VARIABLES`, `.NOTPARALLEL`, etc.): https://www.gnu.org/software/make/manual/html_node/Special-Targets.html
- GNU choosing shell / `.SHELLFLAGS`: https://www.gnu.org/software/make/manual/html_node/Choosing-the-Shell.html
- GNU recipe execution model: https://www.gnu.org/software/make/manual/html_node/Execution.html
- POSIX Issue 8 index (IEEE 1003.1-2024): https://pubs.opengroup.org/onlinepubs/9799919799/
- POSIX `make` utility (Issue 8): https://pubs.opengroup.org/onlinepubs/9799919799/utilities/make.html

## Shared Styleguide Baseline

- Use shared styleguides for generic language/framework rules to reduce duplication in this skill.
- [General Principles](https://github.com/cofin/flow/blob/main/templates/styleguides/general.md)
- [Bash](https://github.com/cofin/flow/blob/main/templates/styleguides/languages/bash.md)
- Keep this skill focused on tool-specific workflows, edge cases, and integration details.

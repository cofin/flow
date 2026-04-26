---
name: makefile
description: "Use when editing Makefile or GNUmakefile, adding development targets, wiring uv commands, defining .PHONY rules, creating self-documenting help, or fixing Make recipe safety."
---

# Makefile Skill

<workflow>

## Overview

All projects should use a consistent `Makefile` structure to ensure developer familiarity. The standard includes:

- **Configuration**: `.ONESHELL`, `.EXPORT_ALL_VARIABLES`, strict shell flags.
- **Presentation**: Standard colors (`BLUE`, `GREEN`, `RED`, `YELLOW`) and icons (`ℹ`, `✓`, `⚠`, `✖`).
- **Help System**: Self-documenting `help` target parsing `##` comments.
- **Standard Targets**: `install`, `upgrade`, `clean`, `test`, `lint`.

## Standard Template

Copy this template to the root of new projects:

<example>

```makefile
SHELL := /bin/bash
# =============================================================================
# Variables
# =============================================================================

.DEFAULT_GOAL:=help
.ONESHELL:
.EXPORT_ALL_VARIABLES:
MAKEFLAGS += --no-print-directory

# Silence output if VERBOSE is not set
ifndef VERBOSE
.SILENT:
endif

# Define colors and formatting
BLUE := $(shell printf "\033[1;34m")
GREEN := $(shell printf "\033[1;32m")
RED := $(shell printf "\033[1;31m")
YELLOW := $(shell printf "\033[1;33m")
NC := $(shell printf "\033[0m")
INFO := $(shell printf "$(BLUE)ℹ$(NC)")
OK := $(shell printf "$(GREEN)✓$(NC)")
WARN := $(shell printf "$(YELLOW)⚠$(NC)")
ERROR := $(shell printf "$(RED)✖$(NC)")

.PHONY: help
help:                                               ## Display this help text for Makefile
 @awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z0-9_-]+:.*?##/ { printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)


# =============================================================================
# Developer Utils
# =============================================================================

.PHONY: install
install:                                            ## Install dependencies for local development
 @echo "${INFO} Installing dependencies..."
 @uv sync
 @echo "${OK} Installation complete"

.PHONY: upgrade
upgrade:                                            ## Upgrade all dependencies
 @echo "${INFO} Updating dependencies... 🔄"
 @uv lock --upgrade
 @uv run pre-commit autoupdate
 @echo "${OK} Dependencies updated 🔄"

.PHONY: clean
clean:                                              ## Cleanup temporary build artifacts
 @echo "${INFO} Cleaning working directory..."
 @rm -rf .pytest_cache .ruff_cache build/ dist/ .coverage coverage.xml htmlcov/
 @find . -name '*.egg-info' -exec rm -rf {} +
 @find . -name '__pycache__' -exec rm -rf {} +
 @echo "${OK} Working directory cleaned"

.PHONY: destroy
destroy:                                            ## Destroy local environment
 @echo "${INFO} Destroying environment... 🗑️"
 @rm -rf .venv
 @echo "${OK} Environment destroyed"


# =============================================================================
# Quality & Testing
# =============================================================================

.PHONY: lint
lint:                                               ## Run all linting checks
 @echo "${INFO} Running linting... 🔍"
 @uv run pre-commit run --all-files
 @echo "${OK} Linting passed ✨"

.PHONY: test
test:                                               ## Run tests
 @echo "${INFO} Running tests... 🧪"
 @uv run pytest
 @echo "${OK} Tests passed ✨"
```

</example>

## Best Practices

1. **Emojis**: Use emojis consistent with the tool being used:
    - 📦 Packaging/Install
    - 🔄 Updates
    - 🧹 Cleanup
    - 🗑️ Destruction
    - 🔍 Linting/Inspection
    - 🧪 Testing
    - ✨ Success
    - 🚀 Execution/Server
    - 📊 Analytics/Benchmarks
    - 🦀 Rust
    - 🐍 Python

2. **Output**: Always use the `${INFO}`, `${OK}`, `${WARN}`, `${ERROR}` variables to prefix status messages.
3. **Silence**: Use `.SILENT:` (conditioned on `VERBOSE`) to keep the output clean for the user, revealing commands only when debugging.

</workflow>

## Official References

- <https://www.gnu.org/software/make/manual/make.html>
- <https://www.gnu.org/software/make/manual/html_node/One-Shell.html>
- <https://www.gnu.org/software/make/manual/html_node/Special-Targets.html>
- <https://www.gnu.org/software/make/manual/html_node/Phony-Targets.html>
- <https://lists.gnu.org/archive/html/info-gnu/2023-02/msg00011.html>
- <https://pubs.opengroup.org/onlinepubs/9699919799/utilities/make.html>

## Shared Styleguide Baseline

- Use shared styleguides for generic language/framework rules to reduce duplication in this skill.
- [General Principles](https://github.com/cofin/flow/blob/main/templates/styleguides/general.md)
- [Bash](https://github.com/cofin/flow/blob/main/templates/styleguides/languages/bash.md)
- Keep this skill focused on tool-specific workflows, edge cases, and integration details.

<guardrails>
## Guardrails

Add guardrails instructions here.
</guardrails>

<validation>
## Validation

Add validation instructions here.
</validation>

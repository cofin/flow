# Copyright 2026 cofin
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c
# =============================================================================
# Variables
# =============================================================================

.DEFAULT_GOAL:=help
.ONESHELL:
.EXPORT_ALL_VARIABLES:
MAKEFLAGS += --no-print-directory

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

.PHONY: clean
clean:                                              ## Cleanup temporary build artifacts
	@echo "${INFO} Cleaning working directory..."
	@rm -rf dist/
	@echo "${OK} Working directory cleaned"

.PHONY: install-hooks
install-hooks:                                      ## Install git hooks (auto-sync plugins/flow on commit)
	@git config core.hooksPath .githooks
	@chmod +x .githooks/* 2>/dev/null || true
	@echo "${OK} Git hooks installed (core.hooksPath=.githooks)"

.PHONY: lint
lint:                                               ## Lint markdown and refresh generated Codex package files
	@echo "${INFO} Linting and fixing markdown files..."
	@npx markdownlint-cli2 --fix "skills/**/*.md" "commands/**/*.md" "docs/**/*.md" "AGENTS.md" "README.md"
	@echo "${INFO} Refreshing generated Codex package..."
	@uv run --extra dev tools/sync-codex-package.py
	@echo "${OK} Markdown linting passed"

.PHONY: sync-codex-package
sync-codex-package:                                ## Assemble the committed Codex marketplace package at plugins/flow/
	@echo "${INFO} Syncing Codex marketplace package..."
	@uv run --extra dev tools/sync-codex-package.py
	@echo "${OK} Codex marketplace package synced"

.PHONY: codex-package-check
codex-package-check:                               ## Verify plugins/flow/ matches generated Codex package payload
	@echo "${INFO} Checking Codex marketplace package..."
	@uv run --extra dev tools/sync-codex-package.py --check
	@echo "${OK} Codex marketplace package is current"

.PHONY: sync-manifests
sync-manifests:                                    ## Sync version strings across all manifests
	@echo "${INFO} Syncing version strings..."
	@uv run --extra dev tools/sync-manifests.py
	@echo "${OK} Version strings in sync"

.PHONY: check

.PHONY: validate
validate:                                          ## Validate all manifests, skills, commands, and agents
	@echo "${INFO} Running consolidated validation..."
	@uv run --extra dev tools/validate.py
	@echo "${OK} Validation passed"

.PHONY: test
test:                                              ## Run the Python test suite
	@echo "${INFO} Running tests..."
	@uv run --extra dev pytest
	@echo "${OK} Tests passed"

check: lint sync-codex-package codex-package-check validate sync-manifests test ## Run all quality checks (lint + validate + tests)
	@echo "${OK} All checks passed"

.PHONY: build
build:                                              ## Build the package
	@echo "${INFO} Building package... 📦"
	@echo "${OK} Package build complete"

.PHONY: release
release:                                           ## Bump version and create release tag (e.g. make release bump=patch)
	@echo "${INFO} Preparing for release... 📦"
	@make clean
	@uv run --extra dev bump-my-version bump $(bump)
	@make build
	@echo "${OK} Release complete 🎉"

.PHONY: pre-release
pre-release:                                       ## Start/advance a pre-release (e.g. make pre-release version=1.1.0a1)
	@echo "${INFO} Preparing pre-release $(version)... 📦"
	@make clean
	@uv run --extra dev bump-my-version bump --new-version $(version) patch
	@make build
	@echo "${OK} Pre-release $(version) complete 🎉"

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

# Detect Rodete and configure NPM registry for Bun/NPM
ifneq ($(shell grep -s -q "rodete" /etc/os-release && echo "yes"),)
export NPM_CONFIG_REGISTRY=https://registry.npmjs.org
export PIP_INDEX_URL=https://pypi.org/simple
export UV_INDEX_URL=https://pypi.org/simple
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

MARKDOWN_GLOBS := "skills/**/*.md" "agents/*.md" "rules/*.md" "templates/**/*.md" "AGENTS.md" "README.md"

.PHONY: help
help:                                               ## Display this help text for Makefile
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z0-9_-]+:.*?##/ { printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

# =============================================================================
# Developer Utils
# =============================================================================
.PHONY: setup-env
setup-env:                                          ## Configure local environment (e.g. Rodete)
	@./tools/scripts/setup-env.sh

.PHONY: install
install: destroy clean setup-env                    ## Install the project and dependencies for local development
	@echo "${INFO} Starting fresh installation..."
	@uv sync --all-groups
	@echo "${OK} Installation complete!"

.PHONY: upgrade
upgrade: setup-env                                  ## Upgrade all dependencies to the latest stable versions
	@echo "${INFO} Updating all dependencies..."
	@uv lock --upgrade
	@uv sync --all-groups
	@echo "${OK} Dependencies updated"

.PHONY: destroy
destroy:                                            ## Destroy the virtual environment
	@echo "${INFO} Destroying virtual environment..."
	@rm -rf .venv
	@echo "${OK} Virtual environment destroyed"

.PHONY: lock
lock: setup-env                                     ## Rebuild lockfiles from scratch, updating all dependencies
	@echo "${INFO} Rebuilding lockfiles..."
	@uv lock --upgrade
	@echo "${OK} Python lockfiles updated"

.PHONY: clean
clean:                                              ## Cleanup temporary build artifacts
	@echo "${INFO} Cleaning working directory..."
	@rm -rf dist/
	@echo "${OK} Working directory cleaned"

.PHONY: lint
lint:                                               ## Check Markdown and Python sources without changing them
	@npx --yes markdownlint-cli2 $(MARKDOWN_GLOBS)
	@uv run ruff check tools/ tests/
	@uv run ruff format --check tools/ tests/
	@uv run mypy tools/ tests/
	@uv run pyright tools/ tests/
	@echo "${OK} Lint passed"

.PHONY: format
format:                                             ## Fix Markdown and Python formatting explicitly
	@npx --yes markdownlint-cli2 --fix $(MARKDOWN_GLOBS)
	@uv run ruff check --fix tools/ tests/
	@uv run ruff format tools/ tests/
	@echo "${OK} Format complete"

.PHONY: validate
validate:                                           ## Validate all manifests, skills, hooks, subagents, and OKF contracts
	@echo "${INFO} Running consolidated validation..."
	@uv run python tools/validate.py
	@echo "${OK} Validation passed"

.PHONY: test
test:                                               ## Run the Python test suite
	@echo "${INFO} Running tests..."
	@uv run pytest
	@echo "${OK} Tests passed"

.PHONY: check
check: lint validate test                           ## Verify sources, manifests, and tests without fixing them
	@echo "${OK} All checks passed"

.PHONY: build
build:                                              ## Build the package
	@echo "${INFO} Building package..."
	@echo "${OK} Package build complete"

.PHONY: release
release:                                            ## Bump version across all manifests (e.g. make release bump=minor)
	@echo "${INFO} Preparing for release..."
	@make clean
	@uv run bump-my-version bump $(bump)
	@make build
	@echo "${OK} Release complete"

.PHONY: pre-release
pre-release:                                        ## Start/advance a pre-release (e.g. make pre-release version=1.1.0a1)
	@echo "${INFO} Preparing pre-release $(version)..."
	@make clean
	@uv run bump-my-version bump --new-version $(version) patch
	@make build
	@echo "${OK} Pre-release $(version) complete"

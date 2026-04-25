#!/usr/bin/env bash
#
# detect-env.sh - Core logic for Flow environment detection.
#
# This script identifies the project context, beads backend, tooling,
# git status, and project identity to provide priming context for AI agents.
#
# Usage:
#   ./detect-env.sh
#
set -euo pipefail
IFS=$'\n\t'

# --- Configuration ---
readonly DEFAULT_ROOT_DIR=".agents"

# --- Functions ---

# Helper to safely run a command with timeout and return its output
# Usage: safe_run <timeout> <command> [args...]
safe_run() {
    local timeout_val="$1"
    shift
    if command -v timeout >/dev/null 2>&1; then
        timeout "${timeout_val}" "$@" 2>/dev/null || true
    else
        "$@" 2>/dev/null || true
    fi
}

detect_beads() {
    echo "## Flow Environment Context"
    if command -v bd >/dev/null 2>&1; then
        echo "- **Beads Backend**: Official (bd)"
    elif command -v br >/dev/null 2>&1; then
        echo "- **Beads Backend**: Compatibility (br)"
    else
        echo "- **Beads Backend**: Missing (None)"
    fi
}

detect_project_root() {
    local root_dir="${DEFAULT_ROOT_DIR}"
    if [[ -f ".agents/setup-state.json" ]]; then
        local found_root
        found_root=$(grep -o '"root_directory": "[^"]*"' .agents/setup-state.json | cut -d'"' -f4 || true)
        found_root="${found_root%/}"
        if [[ -n "${found_root}" ]]; then
            root_dir="${found_root}"
            echo "- **Flow Root**: ${root_dir}"
        else
            echo "- **Flow Root**: .agents (default, missing in setup-state)"
        fi
    else
        echo "- **Flow Root**: .agents (default)"
    fi
    echo "${root_dir}"
}

check_tooling() {
    local tools=("uv" "bun" "ruff" "make" "railway")
    local available=()
    for tool in "${tools[@]}"; do
        if command -v "${tool}" >/dev/null 2>&1; then
            available+=("${tool}")
        fi
    done

    printf '%s' "- **Tooling**: "
    if [[ ${#available[@]} -eq 0 ]]; then
        echo "None"
    else
        (IFS=' '; echo "${available[*]}")
    fi

}

git_context() {
    local root_dir="$1"
    if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
        local branch
        branch=$(git symbolic-ref --short HEAD 2>/dev/null || echo "unborn")
        echo "- **Git Branch**: ${branch}"
        if git check-ignore -q "${root_dir}/" 2>/dev/null; then
            echo "- **Git Visibility**: ${root_dir}/ is GIT-IGNORED (Use 'cat' or bypass ignore filters)"
        else
            echo "- **Git Visibility**: ${root_dir}/ is Tracked"
        fi
    fi
}

project_identity() {
    local root_dir="$1"
    if [[ -f "${root_dir}/product.md" ]]; then
        echo ""
        echo "### Project Identity"
        if ! extract_truths "${root_dir}/product.md"; then
            grep -m 5 "^[^#<]" "${root_dir}/product.md" | head -n 5 | sed 's/^/  /' || true
        fi
    fi
}

context_index() {
    local root_dir="$1"
    echo ""
    echo "### Project Context Index"
    echo "- **Product Definition**: ${root_dir}/product.md"
    echo "- **Tech Stack**: ${root_dir}/tech-stack.md"
    echo "- **Workflow**: ${root_dir}/workflow.md"
    echo "- **Patterns**: ${root_dir}/patterns.md"
    echo "- **Flow Registry**: ${root_dir}/flows.md"
}

active_work() {
    echo ""
    echo "### Active Work"
    if command -v bd >/dev/null 2>&1; then
        local ready
        ready=$(safe_run 2s bd ready --json)
        if [[ -n "${ready}" ]] && [[ "${ready}" != "[]" ]]; then
            # Attempt to parse and truncate with python if available
            if command -v python3 >/dev/null 2>&1; then
                local truncated
                truncated=$(echo "${ready}" | python3 -c 'import json, sys; d=json.load(sys.stdin); print(json.dumps(d[:3]))' 2>/dev/null || true)
                if [[ -n "${truncated}" ]]; then
                    echo "- **Ready Tasks (Top 3)**: ${truncated}"
                    return
                fi
            fi
            echo "- **Ready Tasks**: ${ready}"
        else
            echo "- **Ready Tasks**: None"
        fi
    elif command -v br >/dev/null 2>&1; then
        local ready
        ready=$(safe_run 2s br ready | head -n 3 || true)
        if [[ -n "${ready}" ]]; then
            echo "- **Ready Tasks (Top 3)**:"
            printf '%s\n' "  ${ready//$'\n'/$'\n'  }"
        else
            echo "- **Ready Tasks**: None"
        fi
    else
        echo "- **Status**: No active backend for task tracking."
    fi
}

extract_truths() {
    local file="$1"
    if [[ -f "${file}" ]]; then
        local truths
        # Extract between truth markers, capped at 40 lines so broadly-wrapped sections cannot flood session context
        truths=$(sed -n '/<!-- truth: start -->/,/<!-- truth: end -->/p' "${file}" | grep -v "<!--" | head -n 40 || true)
        if [[ -n "${truths}" ]]; then
            printf '%s\n' "  ${truths//$'\n'/$'\n'  }"
            return 0
        fi
    fi
    return 1
}

essential_truths() {
    local root_dir="$1"
    echo ""
    echo "### Core Project Truths"

    local tech_stack="${root_dir}/tech-stack.md"
    if [[ -f "${tech_stack}" ]]; then
        echo "- **Tech Stack Summary**:"
        if ! extract_truths "${tech_stack}"; then
            grep -m 10 "^-" "${tech_stack}" | sed 's/^/  /' || true
        fi
    fi

    local workflow="${root_dir}/workflow.md"
    if [[ -f "${workflow}" ]]; then
        echo "- **Canonical Commands**:"
        if ! extract_truths "${workflow}"; then
            grep -A 15 "## Development Commands" "${workflow}" | grep -v "^#" | grep -v "^$" | sed 's/^/  /' || true
        fi
    fi

    local patterns="${root_dir}/patterns.md"
    if [[ -f "${patterns}" ]]; then
        echo "- **Critical Patterns**:"
        if ! extract_truths "${patterns}"; then
            grep -m 10 "^-" "${patterns}" | sed 's/^/  /' || true
        fi
    fi
}

knowledge_inventory() {
    local root_dir="$1"
    if [[ -d "${root_dir}/knowledge" ]] || [[ -f "${root_dir}/patterns.md" ]]; then
        echo ""
        echo "### Knowledge Base"
        if [[ -f "${root_dir}/patterns.md" ]]; then
            echo "- **Consolidated Patterns**: ${root_dir}/patterns.md"
        fi
        if [[ -d "${root_dir}/knowledge" ]]; then
            local chapters
            chapters=$(find "${root_dir}/knowledge" -name "*.md" -exec basename {} \; 2>/dev/null | tr '\n' ' ' || true)
            if [[ -n "${chapters}" ]]; then
                echo "- **Knowledge Chapters**: ${chapters}"
            fi
        fi
    fi
}

flow_mandate() {
    local root_dir="$1"
    echo ""
    echo "### Flow Mandate"
    cat <<EOF
- **Zero-Ambiguity Standard**: All PRDs MUST be Master Roadmaps (Sagas). ALL child plans MUST be 'High-Definition Worksheets' with exact line numbers and code snippets.
- **Synthesis Mandate**: You are responsible for the knowledge lifecycle. Autonomously identify patterns and synthesize learnings into formal guides in \`${root_dir}/knowledge/\`.
- **Cleanup Mandate**: Regularly run \`/flow:cleanup\` to re-assess, reorganize, and optimize the project context. Verify task status against SOURCE CODE.
- **Inherit First**: READ \`patterns.md\` and \`knowledge/\` chapters before planning. Adhere to current state truth.
- **Deep Research First**: Do NOT defer research to implementation. ALL analysis and architectural decisions MUST be completed upfront.
- **Stateless Executor Test**: A plan is only 'Ready' if an agent with ZERO context can implement it 100% correctly based ONLY on the worksheet.
- **TDD Discipline**: Follow the Red-Green-Refactor cycle and verify coverage as outlined in the \`flow\` skill.
- **Sync Requirement**: Run \`/flow:sync\` after any change to Beads state or project structure.
EOF
}

main() {
    detect_beads
    local root_dir
    local root_info
    root_info=$(detect_project_root)
    # Use sed '$d' instead of head -n -1 for macOS portability
    printf '%s\n' "${root_info}" | sed '$d'
    root_dir=$(printf '%s\n' "${root_info}" | tail -n 1)
    # Ensure root_dir is not empty
    if [[ -z "${root_dir}" ]]; then
        root_dir="${DEFAULT_ROOT_DIR}"
    fi

    check_tooling
    git_context "${root_dir}"
    project_identity "${root_dir}"
    context_index "${root_dir}"
    active_work
    essential_truths "${root_dir}"
    knowledge_inventory "${root_dir}"
    flow_mandate "${root_dir}"
}

main "$@"


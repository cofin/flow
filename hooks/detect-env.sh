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
# CLAUDE_PLUGIN_OPTION_* are injected by the Claude Code harness from
# plugin.json userConfig. Other hosts leave these unset, so default-fallback.
readonly DEFAULT_ROOT_DIR="${CLAUDE_PLUGIN_OPTION_AGENTSDIR:-.agents}"
readonly USE_BEADS="${CLAUDE_PLUGIN_OPTION_USEBEADS:-true}"

# Opt into the bd v2.0 JSON envelope so `bd --json` stops emitting the
# deprecation notice into the SessionStart context block. Bridges until
# beads wires this through Viper config; flow's parsers below are
# envelope-aware either way.
export BD_JSON_ENVELOPE=1

# --- Functions ---

# Helper to safely run a command with timeout and return its output
# Usage: safe_run <timeout> <command> [args...]
safe_run() {
    local timeout_val="$1"
    shift
    local timeout_cmd="timeout"
    if ! command -v timeout >/dev/null 2>&1; then
        if command -v gtimeout >/dev/null 2>&1; then
            timeout_cmd="gtimeout"
        else
            timeout_cmd=""
        fi
    fi

    if [[ -n "${timeout_cmd}" ]]; then
        "${timeout_cmd}" "${timeout_val}" "$@" 2>/dev/null || true
    else
        "$@" 2>/dev/null || true
    fi
}

detect_beads() {
    echo "## Flow Environment Context"
    if [[ "${USE_BEADS}" != "true" ]]; then
        echo "- **Beads Backend**: Disabled via plugin config (useBeads=false)"
        return
    fi
    if command -v bd >/dev/null 2>&1; then
        echo "- **Beads Backend**: Official (bd)"
    else
        echo "- **Beads Backend**: Missing (None)"
        if command -v br >/dev/null 2>&1; then
            echo "- **Migration Notice**: Detected legacy \`br\` (beads_rust). Flow no longer supports br. Install official Beads: brew install beads (or https://github.com/gastownhall/beads)."
        fi
    fi
}

check_settings() {
    local settings_files=(".gemini/settings.json" "${HOME}/.gemini/settings.json")
    local conflict=0
    for file in "${settings_files[@]}"; do
        if [[ -f "${file}" ]]; then
            if grep -q '"autoEnter": true' "${file}"; then
                echo "⚠ **Settings Conflict**: 'autoEnter' is enabled in ${file}."
                echo "  - This causes the host to 'guess' your goal and fire research tools, bypassing Flow's PRD process."
                echo "  - **Recommendation**: Set \`\"general.plan.autoEnter\": false\`."
                conflict=1
            fi
        fi
    done
}

detect_project_root() {
    local root_dir="${DEFAULT_ROOT_DIR}"
    local msg=""
    if [[ -f ".agents/setup-state.json" ]]; then
        local found_root
        found_root=$(grep -o '"root_directory": "[^"]*"' .agents/setup-state.json | cut -d'"' -f4 || true)
        found_root="${found_root%/}"
        if [[ -n "${found_root}" ]]; then
            root_dir="${found_root}"
            msg="- **Flow Root**: ${root_dir}"
        else
            msg="- **Flow Root**: ${root_dir} (default, missing in setup-state)"
        fi
    else
        msg="- **Flow Root**: ${root_dir} (default)"
    fi
    # machine-readable path on stdout, message on stderr (or captured separately)
    # Actually, let's just echo the msg and then the path, but ensure main parses it correctly.
    echo "${msg}"
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
    if [[ "${USE_BEADS}" != "true" ]]; then
        echo "- **Status**: Beads disabled via plugin config (useBeads=false)."
        return
    fi
    if command -v bd >/dev/null 2>&1; then
        local ready
        ready=$(safe_run 2s bd ready --json)
        if [[ -n "${ready}" ]] && [[ "${ready}" != "[]" ]]; then
            # Attempt to parse and truncate with python if available
            if command -v python3 >/dev/null 2>&1; then
                local truncated
                truncated=$(echo "${ready}" | python3 -c 'import json, sys
d = json.load(sys.stdin)
if isinstance(d, dict) and "data" in d:
    d = d["data"]
print(json.dumps(d[:3]))' 2>/dev/null || true)
                if [[ -n "${truncated}" ]]; then
                    echo "- **Ready Tasks (Top 3)**: ${truncated}"
                    return
                fi
            fi
            echo "- **Ready Tasks**: ${ready}"
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
- **Sync Requirement**: Follow \`${root_dir}/beads.json\` \`syncPolicy.flowSyncAfterMutation\`; default setup runs \`/flow:sync\` after Beads changes but does not auto-export, auto-stage, or run \`bd dolt push\`.
EOF
}

main() {
    detect_beads
    check_settings
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

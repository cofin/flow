#!/usr/bin/env bash
#
# session-start - Consolidated SessionStart hook for Flow framework.
#
# Supports: Antigravity, Claude Code, OpenCode, Codex CLI, Cursor IDE.
#
set -euo pipefail
IFS=$'\n\t'

# --- Functions ---

get_script_dir() {
    local source="${BASH_SOURCE[0]:-}"
    if [[ -z "${source}" ]]; then
        # Fallback to current script name if BASH_SOURCE is empty
        source="$0"
    fi
    local dir
    while [[ -h "${source}" ]]; do
        dir="$(cd -P "$(dirname "${source}")" && pwd)"
        source="$(readlink "${source}")"
        [[ "${source}" != /* ]] && source="${dir}/${source}"
    done
    cd -P "$(dirname "${source}")" && pwd
}

# Safely escape text for JSON
# Usage: escape_json <text>
escape_json() {
    local input="$1"
    # Use python3 for reliable escaping if available
    if command -v python3 >/dev/null 2>&1; then
        if ! echo "${input}" | python3 -c 'import json, sys; print(json.dumps(sys.stdin.read()))' 2>/dev/null; then
            echo '"Error: JSON escaping failed during python execution."'
        fi
    else
        # Fallback for systems without python3 - more robust sed pattern
        # 1. Escape backslashes
        # 2. Escape double quotes
        # 3. Escape newlines
        # 4. Remove actual newlines
        # 5. Wrap in quotes
        echo "${input}" | sed 's/\\/\\\\/g; s/"/\\"/g; s/$/\\n/' | tr -d '\n' | sed 's/^/"/; s/$/"/'
    fi
}

main() {
    local script_dir
    script_dir=$(get_script_dir || pwd)
    
    # Robust resolution: search for detect-env.sh in script dir, then parent, then current
    local detect_script=""
    local candidates=(
        "${script_dir}/detect-env.sh"
        "${script_dir}/../detect-env.sh"
        "$(pwd)/hooks/detect-env.sh"
    )
    
    for candidate in "${candidates[@]}"; do
        if [[ -x "${candidate}" ]]; then
            detect_script="${candidate}"
            break
        fi
    done
    
    local context=""
    if [[ -n "${detect_script}" ]]; then
        # Capture output, allow failure of the subshell without exiting main script
        if ! context=$("${detect_script}" 2>&1); then
             context="Error: Environment detection script failed with exit code $?. Output: ${context}"
        fi
    else
        # Diagnostic help
        local pwd_val=$(pwd)
        context="Error: Environment detection script not found or not executable. Checked: ${candidates[*]}. PWD: ${pwd_val}, Script Dir: ${script_dir}"
    fi

    local escaped_context
    escaped_context=$(escape_json "${context}")

    # Detect harness. Priority: explicit overrides, then harness-specific plugin-root vars.
    # Codex exports PLUGIN_ROOT (canonical) and CLAUDE_PLUGIN_ROOT (compat alias),
    # so we must check the Codex-specific markers BEFORE the Claude branch to avoid
    # misdetecting Codex as Claude.
    local harness="unknown"
    if [[ -n "${FLOW_HARNESS:-}" ]]; then
        # Explicit override set by a harness hook command (e.g. Codex sets
        # FLOW_HARNESS=codex) is authoritative when the harness exports no plugin-root var.
        harness="${FLOW_HARNESS}"
    elif [[ -n "${ANTIGRAVITY_PLUGIN_ROOT:-}" ]] || [[ -n "${AGY_PLUGIN_ROOT:-}" ]]; then
        harness="antigravity"
    elif [[ -n "${CODEX_PLUGIN_ROOT:-}" ]] || [[ -n "${PLUGIN_ROOT:-}" ]]; then
        harness="codex"
    elif [[ -n "${CLAUDE_PLUGIN_ROOT:-}" ]]; then
        harness="claude"
    elif [[ -n "${OPENCODE_PLUGIN_ROOT:-}" ]] || [[ -n "${FLOW_PLUGIN_ROOT:-}" ]]; then
        harness="opencode"
    elif [[ -n "${CURSOR_PLUGIN_ROOT:-}" ]]; then
        harness="cursor"
    fi

    # Emit harness-appropriate JSON. Antigravity, Claude, OpenCode shell hooks, and
    # Codex all accept the modern hookSpecificOutput shape. Cursor and the unknown
    # fallback retain the legacy snake_case shape for safety.
    case "${harness}" in
        antigravity|claude|opencode|codex)
            cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": ${escaped_context}
  }
}
EOF
            ;;
        cursor|unknown|*)
            printf '{"additional_context": %s}\n' "${escaped_context}"
            ;;
    esac
}

main "$@"

#!/usr/bin/env bash
#
# session-start - Consolidated SessionStart hook for Flow framework.
#
# Supports: Gemini CLI, Claude Code, OpenCode, Codex CLI, Cursor IDE.
#
set -euo pipefail
IFS=$'\n\t'

# --- Functions ---

get_script_dir() {
    local source="${BASH_SOURCE[0]}"
    while [[ -h "${source}" ]]; do
        local dir
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
    
    local detect_script="${script_dir}/detect-env.sh"
    local context=""
    
    if [[ -x "${detect_script}" ]]; then
        # Capture output, allow failure of the subshell without exiting main script
        # We use a subshell and redirect stderr to a variable or log if we wanted to debug
        if ! context=$("${detect_script}" 2>/dev/null); then
             context="Error: Environment detection script failed with exit code $?."
        fi
    else
        context="Error: Environment detection script not found or not executable at ${detect_script}."
    fi

    local escaped_context
    escaped_context=$(escape_json "${context}")

    # Output based on detected host environment
    if [[ -n "${CLAUDE_PLUGIN_ROOT:-}" ]] || [[ -n "${OPENCODE_PLUGIN_ROOT:-}" ]]; then
        # Claude Code / OpenCode schema
        cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": ${escaped_context}
  }
}
EOF
    elif [[ -n "${CODEX_PLUGIN_ROOT:-}" ]]; then
        # Codex CLI schema
        printf '{"additional_context": %s}\n' "${escaped_context}"
    elif [[ -n "${CURSOR_PLUGIN_ROOT:-}" ]]; then
        # Cursor IDE schema
        printf '{"additional_context": %s}\n' "${escaped_context}"
    else
        # Default to Gemini CLI systemMessage schema
        printf '{"systemMessage": %s}\n' "${escaped_context}"
    fi
}

main "$@"


#!/usr/bin/env bash
#
# run-hook.sh - Cross-platform hook runner for Flow plugin.
#
# Usage:
#   run-hook.sh <hook-name>
#
set -euo pipefail
IFS=$'\n\t'

main() {
    local script_dir
    script_dir="$(cd "$(dirname "$0")" && pwd)"
    
    local hook_name="${1:-}"
    if [[ -z "${hook_name}" ]]; then
        printf '{"error": "No hook name provided"}\n' >&2
        exit 1
    fi

    # Try both with and without .sh extension
    local hook_script="${script_dir}/${hook_name}.sh"
    if [[ ! -f "${hook_script}" ]]; then
        hook_script="${script_dir}/${hook_name}"
    fi

    if [[ ! -f "${hook_script}" ]]; then
        printf '{"error": "Hook script not found: %s"}\n' "${hook_name}" >&2
        exit 1
    fi

    if [[ ! -x "${hook_script}" ]]; then
        chmod +x "${hook_script}"
    fi

    exec "${hook_script}"
}

main "$@"


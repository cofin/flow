#!/usr/bin/env bash
# Cross-platform hook runner for Flow plugin
# Called by hooks.json or run-hook.cmd
#
# Usage: run-hook.sh <hook-name>
# Example: run-hook.sh session-start

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
HOOK_NAME="${1:-}"

if [ -z "$HOOK_NAME" ]; then
    echo '{"error": "No hook name provided"}' >&2
    exit 1
fi

HOOK_SCRIPT="${SCRIPT_DIR}/${HOOK_NAME}.sh"

if [ ! -f "$HOOK_SCRIPT" ]; then
    echo "{\"error\": \"Hook script not found: ${HOOK_NAME}.sh\"}" >&2
    exit 1
fi

if [ ! -x "$HOOK_SCRIPT" ]; then
    chmod +x "$HOOK_SCRIPT"
fi

exec "$HOOK_SCRIPT"

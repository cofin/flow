#!/usr/bin/env bash
# Flow Framework - Auto-Sync Pre-Commit Hook

set -e

# Escape hatch
if [ "${SKIP_FLOW_SYNC:-0}" = "1" ]; then
    exit 0
fi

# Only run if Flow is initialized and Beads is present
if [ ! -d ".agent" ] || [ ! -d ".beads" ]; then
    exit 0
fi

# Ensure br is available
if ! command -v br &> /dev/null; then
    echo "[Flow] Beads CLI (br) not found. Skipping auto-sync."
    exit 0
fi

echo "[Flow] Running automatic Beads sync..."

# Force a local beads flush
br sync --flush-only >/dev/null 2>&1 || true

# TODO: write simple node or python sync logic inline if we can't find active flow?
# Since parsing json and markdown is hard in bash alone, we can rely on node or python.

#!/usr/bin/env bash
# Flow Destructive Git Guardrail Hook (POSIX shell, fast, zero dependencies beyond jq)
set -euo pipefail

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.command // .CommandLine // .cmd // empty' 2>/dev/null || echo "")

if [ -z "$COMMAND" ]; then
  exit 0
fi

# Intercept destructive Git commands (force pushes, hard resets, destructive cleans, deleting/mutating tags, force branch deletion)
if echo "$COMMAND" | grep -Eq '\bgit\s+(push\s+(--force|-f)|reset\s+--hard|clean\s+-[a-zA-Z]*f|tag\s+-[a-zA-Z]*d|tag\s+[a-zA-Z0-9_\.-]+|branch\s+-D)\b'; then
  echo "Blocked by Flow Safety Hook: Destructive Git operation detected: $COMMAND" >&2
  echo "Flow enforces append-only Git history and immutable tags. Use atomic commits on the current branch." >&2
  exit 2
fi

exit 0

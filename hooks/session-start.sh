#!/usr/bin/env bash
# Gemini CLI SessionStart Hook Wrapper
# Receives JSON on stdin, returns JSON on stdout

CONTEXT=$("$(dirname "$0")/../tools/hooks/detect-env.sh")

# Extract the context and escape for JSON
# Using a safer approach for multi-line string escaping
ESCAPED_CONTEXT=$(echo "$CONTEXT" | python3 -c 'import json, sys; print(json.dumps(sys.stdin.read()))')

# Return the systemMessage to Gemini CLI
printf '{"systemMessage": %s}\n' "$ESCAPED_CONTEXT"

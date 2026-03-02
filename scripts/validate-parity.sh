#!/usr/bin/env bash

set -euo pipefail

# Required commands
COMMANDS=(
  "setup" "prd" "plan" "sync" "research" "docs" "implement" "status"
  "revert" "validate" "block" "skip" "revise" "archive" "export"
  "handoff" "refresh" "formula" "wisp" "distill"
)

ERRORS=0

echo "Checking OpenCode parity..."
for cmd in "${COMMANDS[@]}"; do
  if ! grep -q "\"flow:$cmd\"" templates/opencode/opencode.json; then
    echo "Missing command flow:$cmd in templates/opencode/opencode.json"
    ERRORS=$((ERRORS + 1))
  fi
  if [ ! -f "templates/opencode/commands/flow-$cmd.md" ]; then
    echo "Missing template templates/opencode/commands/flow-$cmd.md"
    ERRORS=$((ERRORS + 1))
  fi
done

echo "Checking Codex parity..."
for cmd in "${COMMANDS[@]}"; do
  if [ ! -d "templates/codex/skills/flow-$cmd" ]; then
    echo "Missing skill templates/codex/skills/flow-$cmd"
    ERRORS=$((ERRORS + 1))
  fi
done

if [ -d "templates/codex/prompts" ]; then
  echo "Found legacy templates/codex/prompts directory!"
  ERRORS=$((ERRORS + 1))
fi

echo "Checking Gemini parity..."
for cmd in "${COMMANDS[@]}"; do
  if [ ! -f "commands/flow/$cmd.toml" ]; then
    echo "Missing command commands/flow/$cmd.toml"
    ERRORS=$((ERRORS + 1))
  fi
done

echo "Checking for legacy git tag checkpoints..."
if grep -r "git tag checkpoint" templates commands; then
  echo "Found legacy git tag checkpoint references!"
  ERRORS=$((ERRORS + 1))
fi

echo "Checking for legacy parent prd references..."
if grep -r "\.agent/prd/" templates commands; then
  echo "Found legacy .agent/prd/ references!"
  ERRORS=$((ERRORS + 1))
fi

if [ $ERRORS -gt 0 ]; then
  echo "Parity validation failed with $ERRORS errors."
  exit 1
else
  echo "Parity validation passed successfully!"
  exit 0
fi

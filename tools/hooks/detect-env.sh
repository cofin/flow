#!/usr/bin/env bash
# Core logic for environment detection

echo "## Flow Environment Context"

# 1. Beads Backend Detection
if command -v bd >/dev/null 2>&1 && command -v br >/dev/null 2>&1; then
  echo "- **Beads Backend**: Dual (bd + br available)"
elif command -v bd >/dev/null 2>&1; then
  echo "- **Beads Backend**: Official (bd)"
elif command -v br >/dev/null 2>&1; then
  echo "- **Beads Backend**: Compatibility (br)"
else
  echo "- **Beads Backend**: Missing (None)"
fi

# 2. Project Config Detection
if [ -f ".agents/setup-state.json" ]; then
  ROOT_DIR=$(grep -o '"root_directory": "[^"]*"' .agents/setup-state.json | cut -d'"' -f4)
  echo "- **Flow Root**: $ROOT_DIR"
else
  echo "- **Flow Root**: .agents/ (default)"
fi

# 3. Tooling Check
echo -n "- **Tooling**: "
tools=("uv" "bun" "ruff" "make")
available=()
for tool in "${tools[@]}"; do
  if command -v "$tool" >/dev/null 2>&1; then
    available+=("$tool")
  fi
done
if [ ${#available[@]} -eq 0 ]; then
  echo "None"
else
  echo "${available[*]}"
fi

# 4. Git Context
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  BRANCH=$(git rev-parse --abbrev-ref HEAD)
  echo "- **Git Branch**: $BRANCH"
fi

# 5. Flow Mandate (Context Reinforcement)
echo ""
echo "### Flow Mandate"
echo "- **Process First**: Always use Flow skills (\`flow:plan\`, \`flow:prd\`, \`flow:implement\`, \`flow:sync\`) for any multi-step task."
echo "- **Spec Awareness**: Read \`spec.md\` and \`metadata.json\` in the active flow directory before implementing."
echo "- **TDD Discipline**: Follow the Red-Green-Refactor cycle and verify coverage as outlined in the \`flow\` skill."
echo "- **Sync Requirement**: Run \`/flow:sync\` after any change to Beads state or project structure."

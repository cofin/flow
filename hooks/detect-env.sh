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
  if git check-ignore -q .agents/ 2>/dev/null; then
    echo "- **Git Visibility**: .agents/ is GIT-IGNORED (Use 'cat' or bypass ignore filters)"
  else
    echo "- **Git Visibility**: .agents/ is Tracked"
  fi
fi

# 5. Knowledge Inventory
if [ -d ".agents/knowledge" ] || [ -f ".agents/patterns.md" ]; then
  echo "- **Knowledge Base**: Active"
  [ -f ".agents/patterns.md" ] && echo "  - Patterns: .agents/patterns.md"
  if [ -d ".agents/knowledge" ]; then
    CHAPTERS=$(ls .agents/knowledge/*.md 2>/dev/null | xargs -n 1 basename | tr '\n' ' ')
    [ -n "$CHAPTERS" ] && echo "  - Chapters: $CHAPTERS"
  fi
else
  echo "- **Knowledge Base**: Empty"
fi

# 6. Flow Mandate (Context Reinforcement)
echo ""
echo "### Flow Mandate"
echo "- **Zero-Ambiguity Standard**: All PRDs MUST be Master Roadmaps (Sagas). ALL child plans MUST be 'High-Definition Worksheets' with exact line numbers and code snippets."
echo "- **Synthesis Mandate**: You are responsible for the knowledge lifecycle. Autonomously identify patterns and synthesize learnings into formal guides in \`.agents/knowledge/\`."
echo "- **Cleanup Mandate**: Regularly run \`/flow:cleanup\` to re-assess, reorganize, and optimize the project context. Verify task status against SOURCE CODE."
echo "- **Inherit First**: READ \`patterns.md\` and \`knowledge/\` chapters before planning. Adhere to current state truth."
echo "- **Deep Research First**: Do NOT defer research to implementation. ALL analysis and architectural decisions MUST be completed upfront."
echo "- **Stateless Executor Test**: A plan is only 'Ready' if an agent with ZERO context can implement it 100% correctly based ONLY on the worksheet."
echo "- **TDD Discipline**: Follow the Red-Green-Refactor cycle and verify coverage as outlined in the \`flow\` skill."
echo "- **Sync Requirement**: Run \`/flow:sync\` after any change to Beads state or project structure."

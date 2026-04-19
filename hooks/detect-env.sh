#!/usr/bin/env bash
# Core logic for environment detection

echo "## Flow Environment Context"

# 1. Beads Backend Detection
if timeout 2s command -v bd >/dev/null 2>&1; then
  echo "- **Beads Backend**: Official (bd)"
elif timeout 2s command -v br >/dev/null 2>&1; then
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
  ROOT_DIR=".agents"
fi

# 3. Tooling Check
echo -n "- **Tooling**: "
tools=("uv" "bun" "ruff" "make" "railway")
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
  BRANCH=$(git symbolic-ref --short HEAD 2>/dev/null || echo "unborn")
  echo "- **Git Branch**: $BRANCH"
  if git check-ignore -q .agents/ 2>/dev/null; then
    echo "- **Git Visibility**: .agents/ is GIT-IGNORED (Use 'cat' or bypass ignore filters)"
  else
    echo "- **Git Visibility**: .agents/ is Tracked"
  fi
fi

# 5. Project Identity
if [ -f "$ROOT_DIR/product.md" ]; then
  echo ""
  echo "### Project Identity"
  # Extract until first list or first 5 lines of content
  grep -m 5 "^[^#]" "$ROOT_DIR/product.md" | head -n 5 | sed 's/^/  /'
fi

# 6. Context Index
echo ""
echo "### Project Context Index"
echo "- **Product Definition**: $ROOT_DIR/product.md"
echo "- **Tech Stack**: $ROOT_DIR/tech-stack.md"
echo "- **Workflow**: $ROOT_DIR/workflow.md"
echo "- **Patterns**: $ROOT_DIR/patterns.md"
echo "- **Flow Registry**: $ROOT_DIR/flows.md"

# 7. Active Work
echo ""
echo "### Active Work"
if command -v bd >/dev/null 2>&1; then
  READY=$(timeout 2s bd ready --json 2>/dev/null | python3 -c 'import json, sys; d=json.load(sys.stdin); print(json.dumps(d[:3]))' 2>/dev/null)
  if [ -n "$READY" ] && [ "$READY" != "[]" ]; then
    echo "- **Ready Tasks (Top 3)**: $READY"
  else
    echo "- **Ready Tasks**: None"
  fi
elif command -v br >/dev/null 2>&1; then
  READY=$(timeout 2s br ready 2>/dev/null | head -n 3)
  if [ -n "$READY" ]; then
    echo "- **Ready Tasks (Top 3)**:"
    echo "$READY" | sed 's/^/  /'
  else
    echo "- **Ready Tasks**: None"
  fi
else
  echo "- **Status**: No active backend for task tracking."
fi

# 8. Essential Truths (Priming)
echo ""
echo "### Core Project Truths"

extract_truths() {
  local file=$1
  if [ -f "$file" ]; then
    # Try to extract between truth markers first
    local truths=$(sed -n '/<!-- truth: start -->/,/<!-- truth: end -->/p' "$file" | grep -v "<!--")
    if [ -n "$truths" ]; then
      echo "$truths" | sed 's/^/  /'
      return 0
    fi
  fi
  return 1
}

if [ -f "$ROOT_DIR/tech-stack.md" ]; then
  echo "- **Tech Stack Summary**:"
  if ! extract_truths "$ROOT_DIR/tech-stack.md"; then
    grep -m 10 "^-" "$ROOT_DIR/tech-stack.md" | sed 's/^/  /'
  fi
fi

if [ -f "$ROOT_DIR/workflow.md" ]; then
  echo "- **Canonical Commands**:"
  if ! extract_truths "$ROOT_DIR/workflow.md"; then
    grep -A 15 "## Development Commands" "$ROOT_DIR/workflow.md" | grep -v "^#" | grep -v "^$" | sed 's/^/  /'
  fi
fi

if [ -f "$ROOT_DIR/patterns.md" ]; then
  echo "- **Critical Patterns**:"
  if ! extract_truths "$ROOT_DIR/patterns.md"; then
    grep -m 10 "^-" "$ROOT_DIR/patterns.md" | sed 's/^/  /'
  fi
fi

# 9. Knowledge Inventory
if [ -d "$ROOT_DIR/knowledge" ] || [ -f "$ROOT_DIR/patterns.md" ]; then
  echo ""
  echo "### Knowledge Base"
  [ -f "$ROOT_DIR/patterns.md" ] && echo "- **Consolidated Patterns**: $ROOT_DIR/patterns.md"
  if [ -d "$ROOT_DIR/knowledge" ]; then
    CHAPTERS=$(find "$ROOT_DIR/knowledge" -name "*.md" -exec basename {} \; 2>/dev/null | tr '\n' ' ')
    [ -n "$CHAPTERS" ] && echo "- **Knowledge Chapters**: $CHAPTERS"
  fi
fi

# 9. Flow Mandate (Context Reinforcement)
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

exit 0

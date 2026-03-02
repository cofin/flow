import os
import re

descriptions = {
    "setup": "Initialize project with context files, Beads, and first flow",
    "prd": "Analyze goals and generate Master Roadmap (Sagas)",
    "plan": "Create unified spec.md for a single Flow",
    "sync": "Export Beads state to spec.md (source of truth sync)",
    "research": "Conduct pre-PRD research",
    "docs": "Five-phase documentation workflow",
    "implement": "Execute tasks from plan (context-aware)",
    "status": "Display progress overview with Beads status",
    "revert": "Git-aware revert of flows, phases, or tasks",
    "validate": "Validate project integrity and fix issues",
    "block": "Mark task as blocked with reason",
    "skip": "Skip current task with justification",
    "revise": "Update spec/plan when implementation reveals issues",
    "archive": "Archive completed flows + elevate patterns",
    "export": "Generate project summary export",
    "handoff": "Create context handoff for session transfer",
    "refresh": "Sync context docs with current codebase state",
    "formula": "List and manage flow templates",
    "wisp": "Create ephemeral exploration flow (no audit trail)",
    "distill": "Extract reusable template from completed flow"
}

def update_file(filepath, pattern, replacement):
    if not os.path.exists(filepath):
        print(f"Missing: {filepath}")
        return
    with open(filepath, 'r') as f:
        content = f.read()
    
    new_content = re.sub(pattern, replacement, content, count=1, flags=re.MULTILINE)
    
    if new_content != content:
        with open(filepath, 'w') as f:
            f.write(new_content)
        print(f"Updated: {filepath}")

for cmd, desc in descriptions.items():
    # 1. Gemini TOML
    update_file(f"commands/flow/{cmd}.toml", r'^description\s*=\s*".*"', f'description = "{desc}"')
    
    # 2. Claude Markdown
    update_file(f"templates/claude/commands/flow-{cmd}.md", r'^description:\s*.*$', f'description: {desc}')
    
    # 3. Codex SKILL
    update_file(f"templates/codex/skills/flow-{cmd}/SKILL.md", r'^description:\s*".*"', f'description: "{desc}"')
    
    # 4. Antigravity SKILL
    update_file(f"templates/antigravity/skills/flow-{cmd}/SKILL.md", r'^description:\s*".*"', f'description: "{desc}"')
    
    # 5. OpenCode Markdown (already did, but let's make sure it perfectly matches)
    update_file(f"templates/opencode/commands/flow-{cmd}.md", r'^description:\s*.*$', f'description: {desc}')

print("Done.")

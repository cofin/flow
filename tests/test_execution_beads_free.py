from __future__ import annotations
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

TARGET_FILES = (
    "commands/flow-implement.md",
    "skills/flow-execution/SKILL.md",
    "skills/flow/references/implement.md",
    "skills/flow/references/discipline.md",
    "commands/flow/implement.toml",
    "skills/flow-execution/agents/openai.yaml",
    "agents/executor.md",
    "agents/code-reviewer.md",
)

def _read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")

def test_no_beads_references_in_execution_files() -> None:
    violations = []
    # Match raw "bd " command invocation or "beads" (case-insensitive)
    pattern = re.compile(r"\bbd\b|\bbeads\b", re.IGNORECASE)

    for relative_path in TARGET_FILES:
        file_path = REPO_ROOT / relative_path
        if not file_path.exists():
            continue
        content = file_path.read_text(encoding="utf-8")
        
        # We allow "no-Beads" or similar in description/documentation if absolutely necessary,
        # but the goal is complete removal. Let's find matches.
        for line_num, line in enumerate(content.splitlines(), start=1):
            if pattern.search(line):
                # Ignore frontmatter or metadata mentions of beads if they are there for config,
                # but let's report them as violations to be strict.
                violations.append(f"{relative_path}:{line_num}: {line.strip()}")

    assert not violations, "Found Beads references in execution files:\n" + "\n".join(violations)

def test_execution_references_bundles_layout() -> None:
    for relative_path in (
        "commands/flow-implement.md",
        "skills/flow/references/implement.md",
        "agents/executor.md",
    ):
        file_path = REPO_ROOT / relative_path
        if not file_path.exists():
            continue
        content = file_path.read_text(encoding="utf-8")
        
        # Ensure it points to bundles/specs/ or tasks/
        assert "bundles/specs" in content or "tasks/" in content
        # Ensure it does NOT point to legacy specs/active or similar
        assert "specs/active" not in content
        assert "specs/archive" not in content

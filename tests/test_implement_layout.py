from __future__ import annotations
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

def _read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")

def test_implement_defines_branched_workspaces() -> None:
    for relative_path in (
        "commands/flow-implement.md",
        "templates/opencode/commands/flow-implement.md",
        "skills/flow-execution/SKILL.md",
        "commands/flow/implement.toml",
    ):
        text = _read(relative_path)
        assert "use_branched_workspaces" in text

def test_implement_removes_legacy_superpowers() -> None:
    text = _read("templates/opencode/commands/flow-implement.md")
    assert "superpowers:subagent-driven-development" not in text

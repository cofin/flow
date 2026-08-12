from __future__ import annotations
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

def _read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")

def test_setup_does_not_create_flows_md() -> None:
    for relative_path in (
        "commands/flow/setup.toml",
        "commands/flow-setup.md",
        "templates/opencode/commands/flow-setup.md",
        "skills/flow/references/setup.md",
    ):
        text = _read(relative_path)
        assert "flows.md - Empty flow registry" not in text

def test_setup_defines_new_paths() -> None:
    for relative_path in (
        "commands/flow/setup.toml",
        "commands/flow-setup.md",
        "templates/opencode/commands/flow-setup.md",
        "skills/flow/references/setup.md",
    ):
        text = _read(relative_path)
        assert "bundles/specs/" in text
        assert "bundles/knowledge/" in text
        assert "knowledge/index.md" not in text or "bundles/knowledge/index.md" in text

def test_setup_prompts_for_branched_workspaces() -> None:
    for relative_path in (
        "commands/flow-setup.md",
        "templates/opencode/commands/flow-setup.md",
        "commands/flow/setup.toml",
    ):
        text = _read(relative_path)
        assert "branched workspaces" in text
        assert "use_branched_workspaces" in text

def test_setup_performs_environment_detection() -> None:
    for relative_path in (
        "commands/flow-setup.md",
        "templates/opencode/commands/flow-setup.md",
        "commands/flow/setup.toml",
    ):
        text = _read(relative_path)
        assert "Environment & Harness Detection" in text
        assert "hooks.json" in text

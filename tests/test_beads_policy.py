from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def test_default_beads_config_is_local_only_and_manual_export() -> None:
    config = json.loads(_read("templates/agent/beads.json"))

    assert config["sync"] == "manual"
    assert config["localOnly"] is True
    assert config["bdConfig"] == {
        "no-git-ops": True,
        "export.auto": False,
        "export.git-add": False,
    }
    assert config["syncPolicy"] == {
        "flowSyncAfterMutation": True,
        "autoExport": False,
        "autoGitAdd": False,
        "allowDoltPush": False,
    }
    assert config["dolt"]["push"] == "never"


def test_setup_surfaces_apply_beads_no_git_export_defaults() -> None:
    for relative_path in (
        "commands/flow/setup.toml",
        "commands/flow-setup.md",
        "templates/opencode/commands/flow-setup.md",
        "skills/flow/references/setup.md",
    ):
        text = _read(relative_path)

        assert "bd config set no-git-ops true" in text
        assert "bd config set export.auto false" in text
        assert "bd config set export.git-add false" in text


def test_runtime_guidance_requires_config_before_export_or_dolt_push() -> None:
    combined = "\n".join(
        _read(relative_path)
        for relative_path in (
            "AGENTS.md",
            "README.md",
            "skills/flow/SKILL.md",
            "commands/flow-sync.md",
            "commands/flow/sync.toml",
            "templates/agent/workflow.md",
        )
    )

    assert "syncPolicy" in combined
    assert "flowSyncAfterMutation" in combined
    assert "allowDoltPush" in combined
    assert "bd dolt push" in combined
    assert "Do not run `bd dolt push`" in combined

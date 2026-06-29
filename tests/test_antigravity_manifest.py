from __future__ import annotations

import importlib.util
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "tools" / "validate.py" # Point to validate.py


def _load_validate_antigravity_manifest_module():
    assert MODULE_PATH.is_file(), "Antigravity manifest validator must exist"
    spec = importlib.util.spec_from_file_location("validate_antigravity_manifest", MODULE_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


validate_antigravity_manifest = _load_validate_antigravity_manifest_module()


def test_antigravity_manifest_discovery_finds_root_manifest_only() -> None:
    manifests = set(validate_antigravity_manifest.discover_antigravity_plugin_manifests(REPO_ROOT))

    assert REPO_ROOT / "plugin.json" in manifests
    assert REPO_ROOT / ".codex-plugin" / "plugin.json" not in manifests
    assert REPO_ROOT / ".claude-plugin" / "plugin.json" not in manifests


def test_antigravity_hook_command_validation_rejects_legacy_extension_tokens(tmp_path: Path) -> None:
    (tmp_path / "plugin.json").write_text(
        json.dumps(
            {
                "$schema": "https://antigravity.google/schemas/v1/plugin.json",
                "name": "flow",
                "description": "Flow",
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "hooks.json").write_text(
        json.dumps(
            {
                "hooks": {
                    "SessionStart": [
                        {
                            "matcher": "*",
                            "hooks": [
                                {
                                    "type": "command",
                                    "command": "bash ${extensionPath}${/}hooks${/}session-start.sh",
                                }
                            ],
                        }
                    ]
                }
            }
        ),
        encoding="utf-8",
    )

    # Inverted assertion: returns list of violations on failure (truthy)
    assert validate_antigravity_manifest.validate_antigravity_hook_commands(tmp_path)


def test_antigravity_hook_command_validation_accepts_plugin_root_ladder(tmp_path: Path) -> None:
    (tmp_path / "plugin.json").write_text(
        json.dumps(
            {
                "$schema": "https://antigravity.google/schemas/v1/plugin.json",
                "name": "flow",
                "description": "Flow",
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "hooks.json").write_text(
        json.dumps(
            {
                "hooks": {
                    "SessionStart": [
                        {
                            "matcher": "*",
                            "hooks": [
                                {
                                    "type": "command",
                                    "command": 'r="${ANTIGRAVITY_PLUGIN_ROOT:-${PLUGIN_ROOT:-${AGY_PLUGIN_ROOT:-}}}"; bash "$r/hooks/session-start.sh"',
                                }
                            ],
                        }
                    ]
                }
            }
        ),
        encoding="utf-8",
    )

    # Inverted assertion: returns empty list on success (falsy)
    assert not validate_antigravity_manifest.validate_antigravity_hook_commands(tmp_path)

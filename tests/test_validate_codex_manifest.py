from __future__ import annotations

import importlib.util
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "tools" / "validate.py" # Point to validate.py


def _load_validate_codex_manifest_module():
    spec = importlib.util.spec_from_file_location("validate_codex_manifest", MODULE_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


validate_codex_manifest = _load_validate_codex_manifest_module()


def test_codex_manifest_discovery_excludes_claude_marketplace() -> None:
    marketplaces = set(validate_codex_manifest.discover_codex_marketplaces(REPO_ROOT))
    plugin_manifests = set(validate_codex_manifest.discover_codex_plugin_manifests(REPO_ROOT))

    assert REPO_ROOT / ".agents" / "plugins" / "marketplace.json" in marketplaces
    assert REPO_ROOT / ".claude-plugin" / "marketplace.json" not in marketplaces
    assert REPO_ROOT / ".codex-plugin" / "plugin.json" in plugin_manifests


def test_codex_package_layout_accepts_real_package_directories(tmp_path: Path) -> None:
    package = tmp_path / "plugins" / "flow"
    for name in validate_codex_manifest.PACKAGE_DIRS:
        (package / name).mkdir(parents=True)

    # Inverted assertion: success returns empty list (falsy)
    assert not validate_codex_manifest.validate_codex_package_layout(tmp_path)


def test_codex_package_layout_rejects_symlinked_package_payload(tmp_path: Path) -> None:
    package = tmp_path / "plugins" / "flow"
    for name in validate_codex_manifest.PACKAGE_DIRS:
        (package / name).mkdir(parents=True)
    (package / "skills").rmdir()
    (package / "skills").symlink_to(tmp_path)

    # Inverted assertion: failure returns list of violations (truthy)
    assert validate_codex_manifest.validate_codex_package_layout(tmp_path)


def _write_codex_hooks(root: Path, command: str) -> None:
    path = root / ".codex" / "hooks.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    manifest = {"hooks": {"SessionStart": [{"type": "command", "command": command}]}}
    path.write_text(json.dumps(manifest), encoding="utf-8")


def test_codex_hook_command_validation_rejects_legacy_extension_tokens(tmp_path: Path) -> None:
    _write_codex_hooks(tmp_path, "bash ${extensionPath}${/}hooks${/}session-start.sh")

    # Inverted assertion: failure returns list of violations (truthy)
    assert validate_codex_manifest.validate_codex_hook_commands(tmp_path)


def test_codex_hook_command_validation_rejects_relative_path(tmp_path: Path) -> None:
    _write_codex_hooks(tmp_path, "bash ./hooks/session-start.sh")

    # Inverted assertion: failure returns list of violations (truthy)
    assert validate_codex_manifest.validate_codex_hook_commands(tmp_path)


def test_codex_hook_command_validation_accepts_plugin_root(tmp_path: Path) -> None:
    _write_codex_hooks(tmp_path, 'bash "${PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:-.}}/hooks/session-start.sh"')

    # Inverted assertion: success returns empty list (falsy)
    assert not validate_codex_manifest.validate_codex_hook_commands(tmp_path)

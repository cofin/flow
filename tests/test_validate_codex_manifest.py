from __future__ import annotations

import importlib.util
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "tools" / "validate-codex-manifest.py"


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
    assert REPO_ROOT / ".claude-plugin" / "plugin.json" not in plugin_manifests


def test_codex_package_layout_accepts_real_package_directories(tmp_path: Path) -> None:
    package = tmp_path / "plugins" / "flow"
    for name in validate_codex_manifest.PACKAGE_DIRS:
        (package / name).mkdir(parents=True)

    assert validate_codex_manifest.validate_codex_package_layout(tmp_path)


def test_codex_package_layout_rejects_symlinked_package_payload(tmp_path: Path) -> None:
    package = tmp_path / "plugins" / "flow"
    for name in validate_codex_manifest.PACKAGE_DIRS:
        (package / name).mkdir(parents=True)
    (package / "skills").rmdir()
    (package / "skills").symlink_to(tmp_path)

    assert not validate_codex_manifest.validate_codex_package_layout(tmp_path)

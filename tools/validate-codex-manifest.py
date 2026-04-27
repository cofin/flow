#!/usr/bin/env python3
"""Validate Codex marketplace and plugin manifests for Codex CLI 0.125.0+."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterator
from pathlib import Path

PACKAGE_ROOT = Path("plugins/flow")
PACKAGE_DIRS = (
    ".codex-plugin",
    "skills",
    "commands",
    ".codex",
    "hooks",
)


def validate_marketplace(file_path: str | Path, repo_root: Path):
    file_path = Path(file_path)
    print(f"Validating marketplace: {file_path}")
    with file_path.open() as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"  ERROR: Invalid JSON: {e}")
            return False

    errors = 0
    for plugin in data.get('plugins', []):
        name = plugin.get('name', 'unknown')
        source_field = plugin.get('source', {})

        path = ""
        is_local = False
        if isinstance(source_field, str):
            path, is_local = source_field, True
        elif isinstance(source_field, dict) and source_field.get('source') == 'local':
            path = source_field.get('path', '')
            is_local = True

        if not is_local:
            continue

        if not path.startswith('./'):
            print(f"  ERROR [plugin {name}]: path '{path}' must start with './'")
            errors += 1
        normalized = path[2:] if path.startswith('./') else path
        if not normalized or normalized.strip('/') == '':
            print(f"  ERROR [plugin {name}]: path '{path}' must not be empty or just './'")
            errors += 1
        if '..' in path:
            print(f"  ERROR [plugin {name}]: path '{path}' must not contain '..'")
            errors += 1

        # Codex resolves source.path relative to the marketplace ROOT (the repo),
        # not relative to the marketplace.json file.
        resolved = (repo_root / normalized).resolve()
        if not resolved.is_dir():
            print(f"  ERROR [plugin {name}]: path '{path}' does not resolve to a directory under the repo root ({resolved})")
            errors += 1
        else:
            plugin_manifest = resolved / ".codex-plugin" / "plugin.json"
            if not plugin_manifest.is_file():
                print(f"  ERROR [plugin {name}]: path '{path}' is missing .codex-plugin/plugin.json (looked at {plugin_manifest})")
                errors += 1

    return errors == 0


def validate_plugin_manifest(file_path: str | Path):
    file_path = Path(file_path)
    print(f"Validating plugin manifest: {file_path}")
    with file_path.open() as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"  ERROR: Invalid JSON: {e}")
            return False

    errors = 0
    for key in data.get('userConfig', {}).keys():
        if not re.match(r'^[a-z][a-zA-Z0-9]*$', key):
            print(f"  ERROR [userConfig]: key '{key}' must be camelCase (no hyphens or underscores)")
            errors += 1
    return errors == 0


def validate_codex_package_layout(repo_root: Path) -> bool:
    """Verify plugins/flow/ is a real generated package layout."""
    package = repo_root / PACKAGE_ROOT
    print(f"Validating Codex package layout: {package}")
    errors = 0

    if package.is_symlink():
        print(f"  ERROR [symlink]: {PACKAGE_ROOT} (expected a real directory)")
        return False
    if not package.is_dir():
        print(f"  ERROR: package directory '{package}' is missing — run 'make sync-codex-package'")
        return False

    expected_names = set(PACKAGE_DIRS)
    actual_names = {p.name for p in package.iterdir()}

    for name in PACKAGE_DIRS:
        errors += _check_real_directory(package / name, repo_root)

    for symlink in sorted(p.relative_to(repo_root) for p in package.rglob("*") if p.is_symlink()):
        print(f"  ERROR [symlink]: {symlink} (package payload must contain real files)")
        errors += 1

    for stray in sorted(actual_names - expected_names):
        print(f"  ERROR [stray]: {PACKAGE_ROOT}/{stray} (expected only {sorted(expected_names)})")
        errors += 1

    if errors:
        print("  HINT: run 'make sync-codex-package' and commit the result")
    return errors == 0


def _check_real_directory(path: Path, repo_root: Path) -> int:
    rel_path = path.relative_to(repo_root)
    if path.is_symlink():
        print(f"  ERROR [symlink]: {rel_path} (expected a real directory)")
        return 1
    if not path.exists():
        print(f"  ERROR [missing-directory]: {rel_path}")
        return 1
    if not path.is_dir():
        print(f"  ERROR [not-a-directory]: {rel_path}")
        return 1
    return 0


def discover_codex_marketplaces(root: Path) -> Iterator[Path]:
    candidate = root / ".agents" / "plugins" / "marketplace.json"
    if candidate.is_file():
        yield candidate


def discover_codex_plugin_manifests(root: Path) -> Iterator[Path]:
    root_manifest = root / ".codex-plugin" / "plugin.json"
    if root_manifest.is_file():
        yield root_manifest
    package_manifest = root / PACKAGE_ROOT / ".codex-plugin" / "plugin.json"
    if package_manifest.is_file():
        yield package_manifest


def main():
    repo_root = Path(".").resolve()
    success = True

    for path in discover_codex_marketplaces(repo_root):
        if not validate_marketplace(path, repo_root):
            success = False

    for path in discover_codex_plugin_manifests(repo_root):
        if not validate_plugin_manifest(path):
            success = False

    if not validate_codex_package_layout(repo_root):
        success = False

    if not success:
        print("\nValidation failed!")
        sys.exit(1)
    else:
        print("\nAll manifests are valid.")


if __name__ == "__main__":
    main()

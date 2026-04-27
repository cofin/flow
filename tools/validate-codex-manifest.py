#!/usr/bin/env python3
"""
Validate Codex marketplace and plugin manifest files for compatibility with Codex CLI 0.125.0+.
"""

import json
import os
import re
import sys
from collections.abc import Iterator
from pathlib import Path

PACKAGE_ROOT = Path("plugins/flow")
# Whole-directory symlinks back to the repo-root sources.
PACKAGE_DIR_SYMLINKS = (
    (".codex-plugin", "../../.codex-plugin"),
    ("skills", "../../skills"),
)
# Per-file symlinks under plugins/flow/commands/. Only Codex-format kebab-case
# command markdowns are exposed; commands/flow/*.toml is Gemini-CLI-only.
PACKAGE_COMMANDS_DIR = "commands"
PACKAGE_COMMANDS_GLOB = "flow-*.md"
PACKAGE_COMMANDS_LINK_PREFIX = "../../../commands"


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
    """Verify plugins/flow/ is assembled with the expected symlinks."""
    package = repo_root / PACKAGE_ROOT
    print(f"Validating Codex package layout: {package}")
    errors = 0

    if not package.is_dir():
        print(f"  ERROR: package directory '{package}' is missing — run 'make sync-codex-package'")
        return False

    for name, expected_target in PACKAGE_DIR_SYMLINKS:
        link = package / name
        errors += _check_symlink(link, expected_target)

    cmds_dir = package / PACKAGE_COMMANDS_DIR
    src_cmds_dir = repo_root / "commands"
    if not cmds_dir.is_dir():
        print(f"  ERROR: '{cmds_dir}' is missing — run 'make sync-codex-package'")
        errors += 1
    else:
        expected = {p.name for p in src_cmds_dir.glob(PACKAGE_COMMANDS_GLOB) if p.is_file()}
        actual = {p.name for p in cmds_dir.iterdir()}
        for name in sorted(expected - actual):
            print(f"  ERROR [missing-link]: {PACKAGE_COMMANDS_DIR}/{name}")
            errors += 1
        for name in sorted(actual - expected):
            print(f"  ERROR [stray]: {PACKAGE_COMMANDS_DIR}/{name}")
            errors += 1
        for name in sorted(expected & actual):
            errors += _check_symlink(
                cmds_dir / name, f"{PACKAGE_COMMANDS_LINK_PREFIX}/{name}"
            )

    if errors:
        print("  HINT: run 'make sync-codex-package' and commit the result")
    return errors == 0


def _check_symlink(link: Path, expected_target: str) -> int:
    if not link.is_symlink():
        print(f"  ERROR [not-a-symlink]: {link} (expected -> {expected_target})")
        return 1
    # Normalize to POSIX separators so the comparison is portable across OSes
    # (os.readlink returns backslashes on Windows even when git stored '/').
    actual = os.readlink(link).replace("\\", "/")
    if actual != expected_target:
        print(f"  ERROR [wrong-target]: {link} -> {actual} (expected -> {expected_target})")
        return 1
    if not link.resolve().exists():
        print(f"  ERROR [dangling]: {link} -> {actual}")
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

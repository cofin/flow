#!/usr/bin/env python3
"""
Validate Codex marketplace and plugin manifest files for compatibility with Codex CLI 0.125.0+.
"""

import filecmp
import json
import re
import sys
from collections.abc import Iterator
from pathlib import Path

PACKAGE_ROOT = Path(".agents/plugins/plugins/flow")
PACKAGE_FULL_MIRRORS = (".codex-plugin", "skills")
# (subdir, filename glob) — Codex package gets only Codex-format command files;
# the commands/flow/*.toml subdirectory is Gemini-CLI-only.
PACKAGE_GLOB_MIRRORS = (("commands", "flow-*.md"),)


def validate_marketplace(file_path: str | Path):
    file_path = Path(file_path)
    print(f"Validating marketplace: {file_path}")
    with file_path.open() as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"  ERROR: Invalid JSON: {e}")
            return False

    errors = 0
    plugins = data.get('plugins', [])
    for plugin in plugins:
        name = plugin.get('name', 'unknown')
        source_field = plugin.get('source', {})

        path = ""
        is_local = False

        if isinstance(source_field, str):
            path = source_field
            is_local = True
        elif isinstance(source_field, dict):
            if source_field.get('source') == 'local':
                path = source_field.get('path', '')
                is_local = True
        
        if is_local:
            # 1. Must start with ./
            if not path.startswith('./'):
                print(f"  ERROR [plugin {name}]: path '{path}' must start with './'")
                errors += 1

            # 2. Must not be empty (after stripping ./)
            normalized = path[2:] if path.startswith('./') else path
            if not normalized or normalized.strip('/') == '':
                print(f"  ERROR [plugin {name}]: path '{path}' must not be empty or just './'")
                errors += 1
            
            # 3. No traversal (..)
            if '..' in path:
                print(f"  ERROR [plugin {name}]: path '{path}' must not contain '..'")
                errors += 1
            
            # 4. Path must exist relative to marketplace file and contain a plugin manifest
            marketplace_dir = file_path.parent
            resolved_path = (marketplace_dir / normalized).resolve()
            if not resolved_path.is_dir():
                print(f"  ERROR [plugin {name}]: path '{path}' does not exist or is not a directory")
                errors += 1
            else:
                plugin_manifest = resolved_path / ".codex-plugin" / "plugin.json"
                if not plugin_manifest.is_file():
                    print(f"  ERROR [plugin {name}]: path '{path}' is missing .codex-plugin/plugin.json")
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
    user_config = data.get('userConfig', {})
    for key in user_config.keys():
        # Check for camelCase (no hyphens or underscores)
        if not re.match(r'^[a-z][a-zA-Z0-9]*$', key):
            print(f"  ERROR [userConfig]: key '{key}' must be camelCase (no hyphens or underscores)")
            errors += 1

    return errors == 0


def validate_codex_package_sync(root: str | Path = ".") -> bool:
    """Ensure the Codex marketplace package mirrors the repo-root sources.

    Codex 0.125 cannot follow symlinks out of an installed plugin package, so
    .agents/plugins/plugins/flow/{.codex-plugin,commands,skills} must contain
    real copies that exactly match the repo-root sources.
    """
    root_path = Path(root)
    package = root_path / PACKAGE_ROOT
    print(f"Validating Codex package sync: {package}")
    errors = 0
    for name in PACKAGE_FULL_MIRRORS:
        errors += _check_full_mirror(root_path / name, package / name, Path(name))
    for name, pattern in PACKAGE_GLOB_MIRRORS:
        errors += _check_glob_mirror(root_path / name, package / name, Path(name), pattern)
    if errors:
        print("  HINT: run 'make sync-codex-package' and commit the result")
    return errors == 0


def _check_full_mirror(src: Path, dst: Path, label: Path) -> int:
    if not src.is_dir():
        print(f"  ERROR: source '{src}' is missing")
        return 1
    if not dst.is_dir():
        print(f"  ERROR: package mirror '{dst}' is missing — run 'make sync-codex-package'")
        return 1
    diff = filecmp.dircmp(str(src), str(dst))
    errors = 0
    for kind, paths in _collect_dircmp_mismatches(diff, label).items():
        for p in paths:
            print(f"  ERROR [{kind}]: {p}")
            errors += 1
    return errors


def _check_glob_mirror(src: Path, dst: Path, label: Path, pattern: str) -> int:
    if not src.is_dir():
        print(f"  ERROR: source '{src}' is missing")
        return 1
    if not dst.is_dir():
        print(f"  ERROR: package mirror '{dst}' is missing — run 'make sync-codex-package'")
        return 1
    expected = {p.name for p in src.glob(pattern) if p.is_file()}
    actual = {p.name for p in dst.iterdir()}
    errors = 0
    for name in sorted(expected - actual):
        print(f"  ERROR [missing]: {label / name}")
        errors += 1
    for name in sorted(actual - expected):
        print(f"  ERROR [stray]: {label / name}")
        errors += 1
    for name in sorted(expected & actual):
        s, d = src / name, dst / name
        if not (d.is_file() and filecmp.cmp(str(s), str(d), shallow=False)):
            print(f"  ERROR [differs]: {label / name}")
            errors += 1
    return errors


def _collect_dircmp_mismatches(diff: filecmp.dircmp, prefix: Path) -> dict[str, list[Path]]:
    mismatches: dict[str, list[Path]] = {
        "only-in-source": [prefix / x for x in diff.left_only],
        "only-in-package": [prefix / x for x in diff.right_only],
        "differs": [prefix / x for x in diff.diff_files],
        "unreadable": [prefix / x for x in diff.funny_files],
    }
    for sub_name, sub_diff in diff.subdirs.items():
        for label, paths in _collect_dircmp_mismatches(sub_diff, prefix / sub_name).items():
            mismatches[label].extend(paths)
    return mismatches


def discover_codex_marketplaces(root: str | Path = ".") -> Iterator[Path]:
    """Yield Codex marketplace manifests only."""
    root_path = Path(root)
    candidate = root_path / ".agents" / "plugins" / "marketplace.json"
    if candidate.is_file():
        yield candidate


def discover_codex_plugin_manifests(root: str | Path = ".") -> Iterator[Path]:
    """Yield Codex plugin manifests, excluding other hosts' plugin.json files."""
    root_path = Path(root)
    root_manifest = root_path / ".codex-plugin" / "plugin.json"
    if root_manifest.is_file():
        yield root_manifest
    agents_plugins = root_path / ".agents" / "plugins" / "plugins"
    if agents_plugins.is_dir():
        yield from sorted(agents_plugins.glob("*/.codex-plugin/plugin.json"))


def main():
    success = True

    for path in discover_codex_marketplaces():
        if not validate_marketplace(path):
            success = False

    for path in discover_codex_plugin_manifests():
        if not validate_plugin_manifest(path):
            success = False

    if not validate_codex_package_sync():
        success = False

    if not success:
        print("\nValidation failed!")
        sys.exit(1)
    else:
        print("\nAll manifests are valid.")

if __name__ == "__main__":
    main()

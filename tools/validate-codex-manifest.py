#!/usr/bin/env python3
"""
Validate Codex marketplace and plugin manifest files for compatibility with Codex CLI 0.125.0+.
"""

import json
import re
import sys
from collections.abc import Iterator
from pathlib import Path


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

    if not success:
        print("\nValidation failed!")
        sys.exit(1)
    else:
        print("\nAll manifests are valid.")

if __name__ == "__main__":
    main()

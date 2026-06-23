#!/usr/bin/env python3
"""Validate Antigravity plugin manifests and hook commands."""

from __future__ import annotations

import json
import sys
from collections.abc import Iterator
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_MANIFEST = "plugin.json"
HOOKS_MANIFEST = "hooks.json"
ANTIGRAVITY_SCHEMA = "https://antigravity.google/schemas/v1/plugin.json"
UNSAFE_TEMPLATE_TOKENS = ("${extensionPath}", "${/}")
ROOT_ENV_TOKENS = ("ANTIGRAVITY_PLUGIN_ROOT", "AGY_PLUGIN_ROOT", "PLUGIN_ROOT")


def discover_antigravity_plugin_manifests(repo_root: Path) -> Iterator[Path]:
    candidate = repo_root / PLUGIN_MANIFEST
    if candidate.is_file():
        yield candidate


def _load_json(path: Path) -> object | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        print(f"  ERROR [{path}]: JSON parse error: {exc}")
        return None


def validate_antigravity_plugin_manifest(repo_root: Path) -> bool:
    path = repo_root / PLUGIN_MANIFEST
    data = _load_json(path)
    if not isinstance(data, dict):
        return False

    ok = True
    if data.get("$schema") != ANTIGRAVITY_SCHEMA:
        print(f"  ERROR [{PLUGIN_MANIFEST}]: $schema must be {ANTIGRAVITY_SCHEMA!r}")
        ok = False
    for field in ("name", "description"):
        value = data.get(field)
        if not isinstance(value, str) or not value.strip():
            print(f"  ERROR [{PLUGIN_MANIFEST}]: {field!r} must be a non-empty string")
            ok = False
    return ok


def _iter_hook_commands(hooks_manifest: object) -> Iterator[str]:
    if not isinstance(hooks_manifest, dict):
        return
    hooks = hooks_manifest.get("hooks")
    if not isinstance(hooks, dict):
        return
    session_start = hooks.get("SessionStart")
    if not isinstance(session_start, list):
        return
    for matcher in session_start:
        if not isinstance(matcher, dict):
            continue
        nested_hooks = matcher.get("hooks")
        if not isinstance(nested_hooks, list):
            continue
        for hook in nested_hooks:
            if not isinstance(hook, dict):
                continue
            command = hook.get("command")
            if isinstance(command, str):
                yield command


def validate_antigravity_hook_commands(repo_root: Path) -> bool:
    path = repo_root / HOOKS_MANIFEST
    data = _load_json(path)
    if not isinstance(data, dict):
        return False
    if not isinstance(data.get("hooks"), dict):
        print(f"  ERROR [{HOOKS_MANIFEST}]: top-level 'hooks' record missing")
        return False

    commands = list(_iter_hook_commands(data))
    if not commands:
        print(f"  ERROR [{HOOKS_MANIFEST}]: no SessionStart command hooks found")
        return False

    ok = True
    for command in commands:
        for token in UNSAFE_TEMPLATE_TOKENS:
            if token in command:
                print(f"  ERROR [{HOOKS_MANIFEST}]: unsupported template token {token!r} in hook command")
                ok = False
        if not any(token in command for token in ROOT_ENV_TOKENS):
            print(f"  ERROR [{HOOKS_MANIFEST}]: hook command must resolve an Antigravity plugin root")
            ok = False
    return ok


def main() -> int:
    ok = True
    manifests = list(discover_antigravity_plugin_manifests(REPO_ROOT))
    if manifests != [REPO_ROOT / PLUGIN_MANIFEST]:
        print(f"  ERROR [missing]: {PLUGIN_MANIFEST}")
        ok = False
    ok = validate_antigravity_plugin_manifest(REPO_ROOT) and ok
    ok = validate_antigravity_hook_commands(REPO_ROOT) and ok
    if ok:
        print("[ OK ] Antigravity manifest valid")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

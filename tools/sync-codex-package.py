#!/usr/bin/env python3
"""Materialize the Codex plugin package at ``plugins/flow``."""

from __future__ import annotations

import argparse
import filecmp
import shutil
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

PACKAGE_ROOT = Path("plugins/flow")
DIRECTORY_ENTRIES = (".codex-plugin", "skills", "hooks")
CODEX_ENTRIES = ("INSTALL.md", "agents", "hooks.json")
COMMANDS_ROOT = Path("commands")
COMMANDS_GLOB = "flow-*.md"
STALE_HINT = "run `make sync-codex-package`"
IGNORED_NAMES = {
    ".DS_Store",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "__pycache__",
}


@dataclass(frozen=True)
class PackagePath:
    rel_path: str
    kind: str


def sync_package(repo_root: Path) -> None:
    """Rewrite ``plugins/flow`` from canonical repo-root sources."""
    package_root = repo_root / PACKAGE_ROOT
    _remove_existing(package_root)
    _build_package(repo_root, package_root)
    symlinks = _find_symlinks(package_root)
    if symlinks:
        formatted = "\n".join(f"  - {path}" for path in symlinks)
        msg = f"Generated package contains symlinks:\n{formatted}"
        raise RuntimeError(msg)
    print(f"assembled package at {package_root}")


def check_package(repo_root: Path) -> int:
    """Return non-zero when ``plugins/flow`` differs from generated output."""
    actual = repo_root / PACKAGE_ROOT
    if actual.is_symlink():
        print(f"Codex package is a symlink: {PACKAGE_ROOT}; {STALE_HINT}")
        return 1
    if not actual.exists():
        print(f"Codex package is missing: {PACKAGE_ROOT}; {STALE_HINT}")
        return 1

    with tempfile.TemporaryDirectory(prefix="flow-codex-package-") as tmp:
        expected = Path(tmp) / "flow"
        _build_package(repo_root, expected)
        differences = _compare_trees(expected, actual)

    if not differences:
        print("Codex package is up to date.")
        return 0

    print("Codex package is stale:")
    for difference in differences:
        print(f"  - {difference}")
    print(STALE_HINT)
    return 1


def _build_package(repo_root: Path, package_root: Path) -> None:
    package_root.mkdir(parents=True, exist_ok=True)
    for entry in DIRECTORY_ENTRIES:
        source = repo_root / entry
        destination = package_root / entry
        if not source.is_dir():
            raise RuntimeError(f"Missing canonical source directory: {source}")
        shutil.copytree(source, destination, ignore=_ignore_names)
    _copy_codex_directory(repo_root, package_root)
    _copy_codex_commands(repo_root, package_root)


def _copy_codex_directory(repo_root: Path, package_root: Path) -> None:
    source_root = repo_root / ".codex"
    if not source_root.is_dir():
        raise RuntimeError(f"Missing canonical source directory: {source_root}")
    destination_root = package_root / ".codex"
    destination_root.mkdir(parents=True, exist_ok=True)
    for entry in CODEX_ENTRIES:
        source = source_root / entry
        destination = destination_root / entry
        if source.is_dir():
            shutil.copytree(source, destination, ignore=_ignore_names)
        elif source.is_file():
            shutil.copy2(source, destination)
        else:
            raise RuntimeError(f"Missing canonical Codex source: {source}")


def _copy_codex_commands(repo_root: Path, package_root: Path) -> None:
    source_root = repo_root / COMMANDS_ROOT
    if not source_root.is_dir():
        raise RuntimeError(f"Missing canonical source directory: {source_root}")
    destination_root = package_root / COMMANDS_ROOT
    destination_root.mkdir(parents=True, exist_ok=True)
    for source in sorted(source_root.glob(COMMANDS_GLOB)):
        if source.is_file():
            shutil.copy2(source, destination_root / source.name)


def _ignore_names(_directory: str, names: list[str]) -> set[str]:
    return {name for name in names if name in IGNORED_NAMES or name.endswith((".pyc", ".pyo"))}


def _remove_existing(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.exists():
        shutil.rmtree(path)


def _compare_trees(expected: Path, actual: Path) -> list[str]:
    differences: list[str] = []
    expected_paths = _collect_paths(expected)
    actual_paths = _collect_paths(actual)

    for rel_path in sorted(expected_paths.keys() - actual_paths.keys()):
        differences.append(f"missing: {PACKAGE_ROOT / rel_path}")
    for rel_path in sorted(actual_paths.keys() - expected_paths.keys()):
        differences.append(f"extra: {PACKAGE_ROOT / rel_path}")

    for rel_path in sorted(expected_paths.keys() & actual_paths.keys()):
        expected_item = expected_paths[rel_path]
        actual_item = actual_paths[rel_path]
        display_path = PACKAGE_ROOT / rel_path
        if actual_item.kind == "symlink":
            differences.append(f"symlink: {display_path}")
            continue
        if expected_item.kind != actual_item.kind:
            differences.append(f"type mismatch: {display_path} ({actual_item.kind}, expected {expected_item.kind})")
            continue
        if expected_item.kind == "file" and not filecmp.cmp(expected / rel_path, actual / rel_path, shallow=False):
            differences.append(f"stale: {display_path}")

    return differences


def _collect_paths(root: Path) -> dict[str, PackagePath]:
    paths: dict[str, PackagePath] = {}
    for path in root.rglob("*"):
        rel_path = path.relative_to(root).as_posix()
        if path.is_symlink():
            kind = "symlink"
        elif path.is_dir():
            kind = "dir"
        elif path.is_file():
            kind = "file"
        else:
            kind = "other"
        paths[rel_path] = PackagePath(rel_path=rel_path, kind=kind)
    return paths


def _find_symlinks(root: Path) -> list[Path]:
    return [path for path in root.rglob("*") if path.is_symlink()]


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail when plugins/flow is stale")
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help=argparse.SUPPRESS,
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    repo_root = args.repo_root.resolve()
    try:
        if args.check:
            return check_package(repo_root)
        sync_package(repo_root)
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Synchronize approved script-free consumer skills into agent templates."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


APPROVED_SKILL_FILES: dict[str, tuple[str, ...]] = {
    "debloat": ("SKILL.md", "references/test-and-gate-debloat.md"),
    "flow-state": ("SKILL.md", "references/state.md"),
}
DEFAULT_TEMPLATE_PATH = Path("templates/agent/skills")


def render_templates(repo_root: Path) -> dict[Path, str]:
    """Return deterministic template paths and contents from canonical skills."""
    rendered: dict[Path, str] = {}
    for skill_name, relative_files in sorted(APPROVED_SKILL_FILES.items()):
        for relative_file in relative_files:
            source = repo_root / "skills" / skill_name / relative_file
            if not source.is_file():
                raise FileNotFoundError(f"missing canonical skill file: {source}")
            destination = Path(skill_name) / relative_file
            rendered[destination] = source.read_text(encoding="utf-8")
    return rendered


def write_templates(repo_root: Path, output_root: Path) -> list[Path]:
    """Write approved templates beneath the explicit output root."""
    written: list[Path] = []
    for relative, content in render_templates(repo_root).items():
        destination = output_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8")
        written.append(destination)
    return written


def check_templates(repo_root: Path, output_root: Path) -> list[str]:
    """Return precise missing or stale template diagnostics without writes."""
    diagnostics: list[str] = []
    for relative, expected in render_templates(repo_root).items():
        destination = output_root / relative
        display = (
            destination.relative_to(repo_root)
            if destination.is_relative_to(repo_root)
            else destination
        )
        if not destination.is_file():
            diagnostics.append(f"missing local skill template: {display}")
        elif destination.read_text(encoding="utf-8") != expected:
            diagnostics.append(f"stale local skill template: {display}")
    return diagnostics


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--output-root", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    repo_root = args.repo_root.resolve()
    output_root = (
        args.output_root.resolve()
        if args.output_root is not None
        else repo_root / DEFAULT_TEMPLATE_PATH
    )
    try:
        if args.write:
            written = write_templates(repo_root, output_root)
            print(f"wrote {len(written)} local skill template files")
            return 0
        diagnostics = check_templates(repo_root, output_root)
    except (OSError, UnicodeError) as exc:
        print(f"local skill template synchronization failed: {exc}", file=sys.stderr)
        return 1
    if diagnostics:
        print("Local skill templates are stale:")
        for diagnostic in diagnostics:
            print(f"  - {diagnostic}")
        return 1
    print("Local skill templates are current.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

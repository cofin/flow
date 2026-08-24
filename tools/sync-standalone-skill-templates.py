#!/usr/bin/env python3
"""Synchronize standalone Flow skill templates from canonical sources."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

STANDALONE_SKILLS = (
    "apilookup",
    "architecture-critic",
    "challenge",
    "consensus",
    "deepthink",
    "devils-advocate",
    "docgen",
    "flow",
    "flow-execution",
    "flow-planning",
    "flow-setup",
    "performance-analyst",
    "perspectives",
    "security-auditor",
    "tracer",
)
DEFAULT_OUTPUT = Path("templates/agent/skills")
PROJECT_ONLY_SKILLS = ("flow-memory-keeper",)


def render_templates(repo_root: Path) -> dict[Path, bytes]:
    """Return the complete deterministic standalone template inventory."""
    rendered: dict[Path, bytes] = {}
    for skill_name in STANDALONE_SKILLS:
        source_root = repo_root / "skills" / skill_name
        if not (source_root / "SKILL.md").is_file():
            raise FileNotFoundError(f"missing canonical standalone skill: {skill_name}")
        for source in sorted(path for path in source_root.rglob("*") if path.is_file()):
            rendered[Path(skill_name) / source.relative_to(source_root)] = (
                source.read_bytes()
            )
    for skill_name in PROJECT_ONLY_SKILLS:
        source_root = repo_root / DEFAULT_OUTPUT / skill_name
        if not (source_root / "SKILL.md").is_file():
            raise FileNotFoundError(
                f"missing project-only standalone skill: {skill_name}"
            )
        for source in sorted(path for path in source_root.rglob("*") if path.is_file()):
            rendered[Path(skill_name) / source.relative_to(source_root)] = (
                source.read_bytes()
            )
    return rendered


def write_templates(repo_root: Path, output_root: Path) -> list[Path]:
    written: list[Path] = []
    for relative, content in render_templates(repo_root).items():
        target = output_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        written.append(target)
    return written


def check_templates(repo_root: Path, output_root: Path) -> list[str]:
    expected = render_templates(repo_root)
    diagnostics: list[str] = []
    expected_paths = set(expected)
    for relative, content in expected.items():
        target = output_root / relative
        if not target.is_file():
            diagnostics.append(
                f"missing standalone skill template: {relative.as_posix()}"
            )
        elif target.read_bytes() != content:
            diagnostics.append(
                f"stale standalone skill template: {relative.as_posix()}"
            )
    managed_roots = {
        output_root / name for name in (*STANDALONE_SKILLS, *PROJECT_ONLY_SKILLS)
    }
    for root in sorted(managed_roots):
        if not root.exists():
            continue
        for target in sorted(path for path in root.rglob("*") if path.is_file()):
            relative = target.relative_to(output_root)
            if relative not in expected_paths:
                diagnostics.append(
                    f"unmanaged standalone skill template: {relative.as_posix()}"
                )
    return diagnostics


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--output-root", type=Path)
    args = parser.parse_args(argv)
    repo_root = args.repo_root.resolve()
    output_root = (args.output_root or repo_root / DEFAULT_OUTPUT).resolve()
    try:
        if args.write:
            print(
                f"wrote {len(write_templates(repo_root, output_root))} standalone skill template files"
            )
            return 0
        diagnostics = check_templates(repo_root, output_root)
    except (OSError, UnicodeError) as exc:
        print(
            f"standalone skill template synchronization failed: {exc}", file=sys.stderr
        )
        return 1
    if diagnostics:
        print("Standalone skill templates are stale:")
        for diagnostic in diagnostics:
            print(f"  - {diagnostic}")
        return 1
    print("Standalone skill templates are current.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

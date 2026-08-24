#!/usr/bin/env python3
"""Synchronize graph-declared project-specific Flow skill templates."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

DEFAULT_OUTPUT = Path("templates/agent/skills")
INSTALL_GRAPH = Path("contracts/standalone-install.json")
CUSTOM_START = "<!-- project-customization: start -->"
CUSTOM_END = "<!-- project-customization: end -->"


def _with_customization(content: bytes) -> bytes:
    return content.rstrip() + f"\n\n{CUSTOM_START}\n{CUSTOM_END}\n".encode()


def _merge_customization(expected: bytes, current: bytes) -> bytes:
    text = current.decode("utf-8")
    if text.count(CUSTOM_START) != 1 or text.count(CUSTOM_END) != 1:
        return expected
    custom = text.split(CUSTOM_START, 1)[1].split(CUSTOM_END, 1)[0]
    return expected.replace(
        f"{CUSTOM_START}\n{CUSTOM_END}".encode(),
        f"{CUSTOM_START}{custom}{CUSTOM_END}".encode(),
    )


def _normalized(content: bytes) -> bytes:
    text = content.decode("utf-8")
    if text.count(CUSTOM_START) != 1 or text.count(CUSTOM_END) != 1:
        return content
    before, rest = text.split(CUSTOM_START, 1)
    _, after = rest.split(CUSTOM_END, 1)
    return f"{before}{CUSTOM_START}\n{CUSTOM_END}{after}".encode()


def _load_graph(repo_root: Path) -> dict[str, object]:
    def reject_duplicates(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate standalone graph key: {key}")
            result[key] = value
        return result

    graph = json.loads(
        (repo_root / INSTALL_GRAPH).read_text(encoding="utf-8"),
        object_pairs_hook=reject_duplicates,
    )
    if not isinstance(graph, dict) or not isinstance(graph.get("nodes"), dict):
        raise TypeError("standalone install graph must declare nodes")
    return graph


def render_templates(repo_root: Path) -> dict[Path, bytes]:
    """Render only graph-declared project-specific standalone templates."""
    rendered: dict[Path, bytes] = {}
    nodes = _load_graph(repo_root)["nodes"]
    assert isinstance(nodes, dict)
    for node_id, raw_node in sorted(nodes.items()):
        if not isinstance(raw_node, dict):
            raise TypeError(f"invalid standalone graph node: {node_id}")
        source_value = raw_node.get("source")
        if not isinstance(source_value, str):
            raise TypeError(f"standalone graph node lacks source: {node_id}")
        template_source = Path(source_value)
        try:
            relative_root = template_source.relative_to(DEFAULT_OUTPUT)
        except ValueError:
            continue
        if raw_node.get("customized"):
            canonical_value = raw_node.get("canonical")
            if not isinstance(canonical_value, str):
                raise ValueError(f"customized node lacks canonical source: {node_id}")
            canonical_root = repo_root / canonical_value
            sources = sorted(
                path for path in canonical_root.rglob("*") if path.is_file()
            )
            if not sources:
                raise FileNotFoundError(
                    f"missing customized canonical source: {node_id}"
                )
            for source in sources:
                content = source.read_bytes()
                if source.name == "SKILL.md":
                    content = _with_customization(content)
                rendered[relative_root / source.relative_to(canonical_root)] = content
            continue
        project_root = repo_root / template_source
        sources = sorted(path for path in project_root.rglob("*") if path.is_file())
        if not sources:
            raise FileNotFoundError(f"missing project-specific template: {node_id}")
        for source in sources:
            rendered[relative_root / source.relative_to(project_root)] = (
                source.read_bytes()
            )
    return rendered


def write_templates(repo_root: Path, output_root: Path) -> list[Path]:
    written: list[Path] = []
    for relative, content in render_templates(repo_root).items():
        target = output_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.is_file() and CUSTOM_START.encode() in content:
            content = _merge_customization(content, target.read_bytes())
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
        elif _normalized(target.read_bytes()) != _normalized(content):
            diagnostics.append(
                f"stale standalone skill template: {relative.as_posix()}"
            )
    if output_root.exists():
        for target in sorted(path for path in output_root.rglob("*") if path.is_file()):
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
    except (OSError, UnicodeError, ValueError, TypeError) as exc:
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

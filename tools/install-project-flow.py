#!/usr/bin/env python3
"""Install an explicit, project-local Flow skill dependency closure."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from collections.abc import Sequence
from pathlib import Path, PurePosixPath
from typing import NamedTuple

CUSTOM_START = "<!-- project-customization: start -->"
CUSTOM_END = "<!-- project-customization: end -->"
HOST_MARKERS = {
    "antigravity": (".agents/hooks.json",),
    "claude_code": (".claude", "CLAUDE.md"),
    "codex_cli": (".codex",),
    "cursor": (".cursor",),
    "opencode": ("opencode.json",),
    "openclaw": (),
    "vscode_copilot": (".github/copilot-instructions.md",),
}
INSTALL_GRAPH_PATH = Path("contracts/standalone-install.json")
VALID_MODES = frozenset({"skip", "install", "update", "uninstall"})


class InstallError(RuntimeError):
    """Refuse an unsafe or ambiguous standalone install operation."""


class InstallResult(NamedTuple):
    """Observable result of one installer invocation."""

    action: str
    changed_paths: tuple[str, ...] = ()
    confirmation_paths: tuple[str, ...] = ()
    guidance: str = ""


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _customization_parts(text: str, *, path: Path) -> tuple[str, str, str] | None:
    lines = text.splitlines(keepends=True)
    starts = [index for index, line in enumerate(lines) if line.strip() == CUSTOM_START]
    ends = [index for index, line in enumerate(lines) if line.strip() == CUSTOM_END]
    if not starts and not ends:
        return None
    if len(starts) != 1 or len(ends) != 1 or ends[0] < starts[0]:
        raise InstallError(f"invalid customization block in {path.as_posix()}")
    return (
        "".join(lines[: starts[0]]),
        "".join(lines[starts[0] + 1 : ends[0]]),
        "".join(lines[ends[0] + 1 :]),
    )


def _normalized_content(data: bytes, *, path: Path) -> bytes:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return data
    parts = _customization_parts(text, path=path)
    if parts is None:
        return data
    before, _, after = parts
    return f"{before}{CUSTOM_START}\n{CUSTOM_END}\n{after}".encode()


def _content_hash(data: bytes, *, path: Path) -> str:
    return _sha256(_normalized_content(data, path=path))


def _merge_customization(canonical: bytes, current: bytes, *, path: Path) -> bytes:
    try:
        canonical_text = canonical.decode("utf-8")
        current_text = current.decode("utf-8")
    except UnicodeDecodeError:
        return canonical
    canonical_parts = _customization_parts(canonical_text, path=path)
    current_parts = _customization_parts(current_text, path=path)
    if canonical_parts is None or current_parts is None:
        return canonical
    before, _, after = canonical_parts
    _, custom, _ = current_parts
    return f"{before}{CUSTOM_START}\n{custom}{CUSTOM_END}\n{after}".encode()


def _has_customization(data: bytes, *, path: Path) -> bool:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return False
    parts = _customization_parts(text, path=path)
    return parts is not None and bool(parts[1].strip())


def _contained(root: Path, candidate: Path, *, description: str) -> Path:
    resolved_root = root.resolve()
    resolved = candidate.resolve()
    if not resolved.is_relative_to(resolved_root):
        raise InstallError(f"{description} escapes canonical skills root: {candidate}")
    return resolved


def _detect_host(project_root: Path) -> str:
    detected = [
        host
        for host, markers in HOST_MARKERS.items()
        if any((project_root / marker).exists() for marker in markers)
    ]
    if not detected:
        raise InstallError("active host is unknown; declare it explicitly")
    if len(detected) > 1:
        raise InstallError(f"active host is ambiguous: {', '.join(detected)}")
    return detected[0]


def _load_install_graph(source_root: Path) -> dict[str, object]:
    graph_path = source_root / INSTALL_GRAPH_PATH

    def reject_duplicates(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise InstallError(f"duplicate standalone graph key: {key}")
            result[key] = value
        return result

    try:
        graph = json.loads(
            graph_path.read_text(encoding="utf-8"),
            object_pairs_hook=reject_duplicates,
        )
    except (OSError, json.JSONDecodeError) as exc:
        raise InstallError(
            f"invalid standalone dependency graph: {graph_path}"
        ) from exc
    if not isinstance(graph, dict) or set(graph) != {
        "version",
        "roots",
        "nodes",
        "hosts",
    }:
        raise InstallError("standalone dependency graph has an invalid top-level shape")
    if graph["version"] != 1 or not isinstance(graph["roots"], list):
        raise InstallError(
            "standalone dependency graph has an unsupported version or roots"
        )
    if not isinstance(graph["nodes"], dict) or not isinstance(graph["hosts"], dict):
        raise InstallError(
            "standalone dependency graph nodes and hosts must be objects"
        )
    return graph


def _graph_closure(graph: dict[str, object], host: str) -> tuple[str, ...]:
    nodes = graph["nodes"]
    hosts = graph["hosts"]
    assert isinstance(nodes, dict) and isinstance(hosts, dict)
    if host not in hosts or not isinstance(hosts[host], list):
        raise InstallError(f"unsupported active host: {host}")
    roots = graph["roots"]
    assert isinstance(roots, list)
    visiting: list[str] = []
    visited: set[str] = set()

    def visit(node_id: str) -> None:
        if node_id in visiting:
            raise InstallError(
                f"cyclic standalone dependency: {' -> '.join((*visiting, node_id))}"
            )
        if node_id in visited:
            return
        node = nodes.get(node_id)
        if not isinstance(node, dict) or not isinstance(node.get("dependencies"), list):
            raise InstallError(
                f"missing or invalid standalone dependency node: {node_id}"
            )
        dependencies = node["dependencies"]
        if not all(isinstance(dependency, str) for dependency in dependencies):
            raise InstallError(f"invalid dependency edge from {node_id}")
        if len(dependencies) != len(set(dependencies)):
            raise InstallError(f"duplicate dependency edge from {node_id}")
        visiting.append(node_id)
        for dependency in dependencies:
            visit(dependency)
        visiting.pop()
        visited.add(node_id)

    for root in (*roots, *hosts[host]):
        if not isinstance(root, str):
            raise InstallError("standalone dependency roots must be strings")
        visit(root)
    return tuple(sorted(visited))


def _node_files(
    source_root: Path, node_id: str, node: dict[str, object]
) -> dict[str, bytes]:
    allowed = {
        "source",
        "destination",
        "dependencies",
        "canonical",
        "customized",
        "include",
    }
    if not set(node).issubset(allowed):
        raise InstallError(f"standalone dependency node has unknown fields: {node_id}")
    source_value, destination_value = node.get("source"), node.get("destination")
    if not isinstance(source_value, str) or not isinstance(destination_value, str):
        raise InstallError(
            f"standalone dependency node lacks source/destination: {node_id}"
        )
    source = _contained(
        source_root, source_root / source_value, description="dependency source"
    )
    destination = PurePosixPath(destination_value)
    if destination.is_absolute() or ".." in destination.parts:
        raise InstallError(f"invalid standalone destination: {node_id}")
    include = node.get("include")
    if include is not None and not isinstance(include, str):
        raise InstallError(f"invalid standalone include pattern: {node_id}")
    if source.is_file():
        files = (source,)
    elif source.is_dir():
        files = tuple(
            sorted(
                source.glob(include)
                if include
                else (p for p in source.rglob("*") if p.is_file())
            )
        )
    else:
        raise InstallError(f"missing standalone dependency source: {source_value}")
    if not files:
        raise InstallError(f"empty standalone dependency source: {source_value}")
    result: dict[str, bytes] = {}
    for path in files:
        _contained(source_root, path, description="dependency file")
        relative = Path(path.name) if source.is_file() else path.relative_to(source)
        target = (
            destination
            if source.is_file()
            else destination / PurePosixPath(relative.as_posix())
        )
        result[target.as_posix()] = path.read_bytes()
    return result


def _standalone_files(
    source_root: Path, host: str, *, graph: dict[str, object] | None = None
) -> dict[str, bytes]:
    """Return the declared minimal lifecycle closure for the selected host."""
    selected_graph = _load_install_graph(source_root) if graph is None else graph
    nodes = selected_graph["nodes"]
    assert isinstance(nodes, dict)
    desired: dict[str, bytes] = {}
    for node_id in _graph_closure(selected_graph, host):
        node = nodes[node_id]
        assert isinstance(node, dict)
        generated = _node_files(source_root, node_id, node)
        canonical_value = node.get("canonical")
        if canonical_value is not None:
            if not isinstance(canonical_value, str):
                raise InstallError(f"invalid canonical source: {node_id}")
            if not node.get("customized"):
                raise InstallError(
                    f"redundant generated canonical mirror in graph: {node_id}"
                )
            canonical_node = dict(node)
            canonical_node["source"] = canonical_value
            canonical_node["destination"] = node["destination"]
            canonical_node.pop("canonical", None)
            canonical_node.pop("include", None)
            canonical = _node_files(source_root, node_id, canonical_node)
            canonical = {
                path: content.rstrip() + f"\n\n{CUSTOM_START}\n{CUSTOM_END}\n".encode()
                if path.endswith("/SKILL.md")
                else content
                for path, content in canonical.items()
            }
            normalized_generated = {
                path: _normalized_content(content, path=Path(path))
                for path, content in generated.items()
            }
            normalized_canonical = {
                path: _normalized_content(content, path=Path(path))
                for path, content in canonical.items()
            }
            if normalized_generated != normalized_canonical:
                raise InstallError(f"stale generated standalone node: {node_id}")
        overlap = set(desired).intersection(generated)
        if overlap:
            raise InstallError(f"duplicate standalone destination: {min(overlap)}")
        desired.update(generated)
    return desired


def _load_state(state_path: Path) -> dict[str, object]:
    if not state_path.exists():
        return {}
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InstallError(f"invalid setup state: {state_path}") from exc
    if not isinstance(state, dict):
        raise InstallError("setup state must contain a JSON object")
    return state


def _managed_inventory(state: dict[str, object]) -> dict[str, str]:
    install = state.get("project_install")
    if install is None:
        return {}
    if not isinstance(install, dict):
        raise InstallError("project_install state must be an object")
    entries = install.get("managed_files", [])
    if not isinstance(entries, list):
        raise InstallError("project_install.managed_files must be a list")
    inventory: dict[str, str] = {}
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != {"path", "content_hash"}:
            raise InstallError("managed file entries require path and content_hash")
        path, content_hash = entry["path"], entry["content_hash"]
        if not isinstance(path, str) or not isinstance(content_hash, str):
            raise InstallError("managed file path and content_hash must be strings")
        pure = PurePosixPath(path)
        if pure.is_absolute() or ".." in pure.parts or path in inventory:
            raise InstallError(f"invalid managed path: {path}")
        if not re.fullmatch(r"[0-9a-f]{64}", content_hash):
            raise InstallError(f"invalid managed content hash: {path}")
        inventory[path] = content_hash
    return inventory


def _installed_host(state: dict[str, object]) -> str | None:
    install = state.get("project_install")
    if not isinstance(install, dict):
        return None
    host = install.get("active_host")
    return host if isinstance(host, str) else None


def _write_transaction(changes: dict[Path, bytes | None]) -> tuple[str, ...]:
    backups = {path: path.read_bytes() if path.is_file() else None for path in changes}
    created_directories: set[Path] = set()
    for path, content in changes.items():
        if content is None:
            continue
        parent = path.parent
        while not parent.exists():
            created_directories.add(parent)
            parent = parent.parent
    changed: list[str] = []
    try:
        for path, content in changes.items():
            if content is None:
                if path.exists():
                    path.unlink()
                    changed.append(path.as_posix())
                continue
            if path.is_file() and path.read_bytes() == content:
                continue
            path.parent.mkdir(parents=True, exist_ok=True)
            descriptor, temporary_name = tempfile.mkstemp(
                prefix=f".{path.name}.", dir=path.parent
            )
            try:
                with os.fdopen(descriptor, "wb") as temporary:
                    temporary.write(content)
                    temporary.flush()
                    os.fsync(temporary.fileno())
                os.replace(temporary_name, path)
            finally:
                if os.path.exists(temporary_name):
                    os.unlink(temporary_name)
            changed.append(path.as_posix())
    except Exception:
        for path, content in reversed(tuple(backups.items())):
            if content is None:
                if path.exists():
                    path.unlink()
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(content)
        for directory in sorted(
            created_directories, key=lambda path: len(path.parts), reverse=True
        ):
            try:
                directory.rmdir()
            except OSError:
                pass
        raise
    return tuple(changed)


def _state_bytes(
    state: dict[str, object], *, host: str | None, inventory: dict[str, str]
) -> bytes:
    managed = [
        {"path": path, "content_hash": inventory[path]} for path in sorted(inventory)
    ]
    contract = "\n".join(
        f"{entry['path']}\0{entry['content_hash']}" for entry in managed
    )
    state["project_install"] = {
        "mode": "standalone" if managed else "skip",
        "active_host": host if managed else None,
        "canonical_contract_hash": _sha256(contract.encode()) if managed else None,
        "managed_files": managed,
    }
    return (json.dumps(state, indent=2, sort_keys=True) + "\n").encode()


def install_project_flow(
    project_root: Path,
    *,
    source_root: Path,
    mode: str = "skip",
    host: str | None = None,
    global_plugin_detected: bool = False,
    confirm_global_plugin: bool = False,
    confirm_customized: Sequence[str] = (),
) -> InstallResult:
    """Apply one safe standalone lifecycle operation to ``project_root``."""
    project_root = project_root.resolve()
    source_root = source_root.resolve()
    if mode not in VALID_MODES:
        raise InstallError(f"invalid mode: {mode}")
    if mode == "skip":
        return InstallResult("skipped")
    if not project_root.is_dir():
        raise InstallError(f"project root is not a directory: {project_root}")

    state_path = project_root / ".agents" / "setup-state.json"
    state = _load_state(state_path)
    previous = _managed_inventory(state)

    if mode == "uninstall":
        if not previous:
            return InstallResult("unchanged")
        confirmations = set(confirm_customized)
        unknown = confirmations.difference(previous)
        if unknown:
            raise InstallError(f"confirmation path is not managed: {min(unknown)}")
        changes: dict[Path, bytes | None] = {}
        retained: dict[str, str] = {}
        required: list[str] = []
        for relative, expected_hash in sorted(previous.items()):
            target = _contained(
                project_root, project_root / relative, description="managed path"
            )
            if not target.exists():
                continue
            current = target.read_bytes()
            exact = _content_hash(current, path=target) == expected_hash
            customized = _has_customization(current, path=target)
            if (exact and not customized) or relative in confirmations:
                changes[target] = None
            else:
                retained[relative] = expected_hash
                required.append(relative)
        changes[state_path] = _state_bytes(
            state, host=_installed_host(state), inventory=retained
        )
        raw_changed = _write_transaction(changes)
        changed = tuple(
            path.relative_to(project_root).as_posix() for path in map(Path, raw_changed)
        )
        if required:
            return InstallResult("confirmation_required", changed, tuple(required))
        return InstallResult("uninstalled", changed)

    active_host = host or _detect_host(project_root)
    if global_plugin_detected and not confirm_global_plugin:
        raise InstallError(
            "global Flow plugin detected; explicit transition confirmation required"
        )

    desired = _standalone_files(source_root, active_host)

    changes = {}
    inventory: dict[str, str] = {}
    for relative, canonical in sorted(desired.items()):
        target = _contained(
            project_root, project_root / relative, description="managed path"
        )
        canonical_hash = _content_hash(canonical, path=target)
        if target.exists():
            current = target.read_bytes()
            if relative not in previous:
                raise InstallError(f"unmanaged target collision: {relative}")
            if _content_hash(current, path=target) != previous[relative]:
                raise InstallError(f"stale managed hash: {relative}")
            output = _merge_customization(canonical, current, path=target)
        else:
            output = canonical
        changes[target] = output
        inventory[relative] = canonical_hash

    stale_paths = set(previous).difference(desired)
    for relative in sorted(stale_paths):
        target = _contained(
            project_root, project_root / relative, description="managed path"
        )
        if not target.exists():
            continue
        current = target.read_bytes()
        if _content_hash(current, path=target) != previous[
            relative
        ] or _has_customization(current, path=target):
            raise InstallError(
                f"retired managed path requires uninstall confirmation: {relative}"
            )
        changes[target] = None
    changes[state_path] = _state_bytes(state, host=active_host, inventory=inventory)
    raw_changed = _write_transaction(changes)
    changed = tuple(
        path.relative_to(project_root).as_posix() for path in map(Path, raw_changed)
    )
    action = "installed" if not previous else ("updated" if changed else "unchanged")
    guidance = ""
    if global_plugin_detected:
        guidance = "Standalone Flow is prepared; disable the global Flow plugin for later project sessions."
    return InstallResult(action, changed, guidance=guidance)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, default=Path.cwd())
    parser.add_argument("--source-root", type=Path, default=Path(__file__).parents[1])
    parser.add_argument("--mode", choices=sorted(VALID_MODES), default="skip")
    parser.add_argument("--host", choices=sorted(HOST_MARKERS))
    parser.add_argument("--global-plugin-detected", action="store_true")
    parser.add_argument("--confirm-global-plugin", action="store_true")
    parser.add_argument("--confirm-customized", action="append", default=[])
    args = parser.parse_args(argv)
    try:
        result = install_project_flow(
            args.project,
            source_root=args.source_root,
            mode=args.mode,
            host=args.host,
            global_plugin_detected=args.global_plugin_detected,
            confirm_global_plugin=args.confirm_global_plugin,
            confirm_customized=args.confirm_customized,
        )
    except InstallError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps(result._asdict(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

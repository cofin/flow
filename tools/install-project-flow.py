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
LINK_RE = re.compile(r"(?<!!)\[[^]]*]\(([^)\s]+)(?:\s+[^)]*)?\)")
HOST_MARKERS = {
    "antigravity": (".agents/hooks.json",),
    "claude_code": (".claude", "CLAUDE.md"),
    "codex_cli": (".codex",),
    "cursor": (".cursor",),
    "opencode": ("opencode.json",),
    "openclaw": (),
    "vscode_copilot": (".github/copilot-instructions.md",),
}
PORTABLE_SKILLS = (
    "apilookup",
    "architecture-critic",
    "challenge",
    "consensus",
    "debloat",
    "deepthink",
    "devils-advocate",
    "docgen",
    "flow",
    "flow-completion",
    "flow-execution",
    "flow-memory-keeper",
    "flow-planning",
    "flow-setup",
    "flow-state",
    "flow-sync-status",
    "performance-analyst",
    "perspectives",
    "security-auditor",
    "tracer",
)
GENERATED_STANDALONE_SKILLS = frozenset(PORTABLE_SKILLS).difference(
    {
        "debloat",
        "flow-memory-keeper",
        "flow-state",
    }
)
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


def _dependency_closure(source_root: Path, seeds: Sequence[str]) -> tuple[Path, ...]:
    skills_root = (source_root / "skills").resolve()
    canonical_root = source_root.resolve()
    if not skills_root.is_dir():
        raise InstallError(f"canonical skills root is missing: {skills_root}")
    visiting: list[Path] = []
    visited: set[Path] = set()
    ordered: list[Path] = []

    def visit(path: Path) -> None:
        resolved = _contained(canonical_root, path, description="dependency")
        if resolved in visiting:
            cycle = " -> ".join(
                item.relative_to(canonical_root).as_posix()
                for item in (*visiting, resolved)
            )
            raise InstallError(f"cyclic dependency: {cycle}")
        if resolved in visited:
            return
        if not resolved.is_file():
            raise InstallError(f"missing dependency: {resolved}")
        visiting.append(resolved)
        if resolved.suffix.lower() == ".md":
            text = resolved.read_text(encoding="utf-8")
            for raw_target in LINK_RE.findall(text):
                target = raw_target.split("#", 1)[0]
                if not target or "://" in target or target.startswith("mailto:"):
                    continue
                dependency = resolved.parent / target
                _contained(canonical_root, dependency, description="dependency")
                visit(dependency)
        visiting.pop()
        visited.add(resolved)
        ordered.append(resolved)

    for seed in sorted(set(seeds)):
        pure = PurePosixPath(seed)
        if pure.is_absolute() or ".." in pure.parts:
            raise InstallError(f"invalid dependency seed: {seed}")
        visit(skills_root / pure)
    return tuple(
        sorted(ordered, key=lambda path: path.relative_to(canonical_root).as_posix())
    )


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


def _standalone_files(source_root: Path, host: str) -> dict[str, bytes]:
    """Return portable skills/roles and only the selected host's adapters."""
    desired: dict[str, bytes] = {}

    for skill in GENERATED_STANDALONE_SKILLS:
        canonical_root = source_root / "skills" / skill
        template_root = source_root / "templates" / "agent" / "skills" / skill
        canonical = {
            path.relative_to(canonical_root): path.read_bytes()
            for path in canonical_root.rglob("*")
            if path.is_file()
        }
        generated = {
            path.relative_to(template_root): path.read_bytes()
            for path in template_root.rglob("*")
            if path.is_file()
        }
        if not canonical:
            raise InstallError(f"missing canonical standalone skill: {skill}")
        if skill in {"flow-completion", "flow-sync-status"}:
            canonical[Path("SKILL.md")] = (
                canonical[Path("SKILL.md")].rstrip()
                + f"\n\n{CUSTOM_START}\n{CUSTOM_END}\n".encode()
            )
            generated = {
                relative: _normalized_content(content, path=template_root / relative)
                for relative, content in generated.items()
            }
        if generated != canonical:
            raise InstallError(f"stale generated standalone skill: {skill}")

    def include_tree(source: Path, destination: PurePosixPath) -> None:
        if not source.is_dir():
            raise InstallError(f"missing generated standalone source: {source}")
        for path in sorted(item for item in source.rglob("*") if item.is_file()):
            relative = destination / PurePosixPath(path.relative_to(source).as_posix())
            desired[relative.as_posix()] = path.read_bytes()

    for skill in PORTABLE_SKILLS:
        include_tree(
            source_root / "templates" / "agent" / "skills" / skill,
            PurePosixPath(".agents/skills") / skill,
        )
    include_tree(source_root / "agents", PurePosixPath(".agents/flow/agents"))

    if host == "antigravity":
        include_tree(
            source_root / "templates" / "antigravity" / "agents",
            PurePosixPath(".agents/agents"),
        )
    elif host == "codex_cli":
        include_tree(source_root / ".codex" / "agents", PurePosixPath(".codex/agents"))
    elif host == "opencode":
        include_tree(
            source_root / ".opencode" / "agents", PurePosixPath(".opencode/agents")
        )
        include_tree(
            source_root / "templates" / "opencode" / "commands",
            PurePosixPath(".opencode/commands"),
        )
    elif host == "vscode_copilot":
        include_tree(
            source_root / ".github" / "agents", PurePosixPath(".github/agents")
        )
    elif host == "claude_code":
        commands = source_root / "commands"
        for path in sorted(commands.glob("flow-*.md")):
            desired[f".claude/commands/{path.name}"] = path.read_bytes()
    elif host not in {"cursor", "openclaw"}:
        raise InstallError(f"unsupported active host: {host}")
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
    seeds: Sequence[str] = ("flow/SKILL.md",),
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
    if active_host not in HOST_MARKERS:
        raise InstallError(f"unsupported active host: {active_host}")
    if global_plugin_detected and not confirm_global_plugin:
        raise InstallError(
            "global Flow plugin detected; explicit transition confirmation required"
        )

    if (
        tuple(seeds) == ("flow/SKILL.md",)
        and (source_root / "templates/agent/skills").is_dir()
    ):
        desired = _standalone_files(source_root, active_host)
    else:
        if not seeds:
            raise InstallError("no canonical Flow skill roots were found")
        closure = _dependency_closure(source_root, seeds)
        desired = {}
        for source in closure:
            relative = source.relative_to(source_root)
            destination = PurePosixPath(".agents") / PurePosixPath(relative.as_posix())
            desired[destination.as_posix()] = source.read_bytes()

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
    if stale_paths:
        raise InstallError(
            f"stale managed inventory requires uninstall: {min(stale_paths)}"
        )
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
    parser.add_argument("--seed", action="append", dest="seeds")
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
            seeds=args.seeds or ("flow/SKILL.md",),
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

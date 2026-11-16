"""Shared runtime lease, Node CLI, dynamic model routing, and seed-prefetch helpers for Flow workflows."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

QUOTA_MARKERS: tuple[str, ...] = (
    "429",
    "resource_exhausted",
    "quota",
    "rate limit",
    "rate_limit",
    "capacity",
    "overloaded",
    "exhausted",
)


def resolve_plugin_root(explicit_root: str | None = None, *, marker: str = "sidecars/studio/flow-cli.mjs") -> Path:
    """Resolve the Flow plugin installation root containing ``marker``."""
    raw = str(explicit_root or os.environ.get("FLOW_PLUGIN_ROOT") or Path.cwd())
    candidate = Path(raw)
    if (candidate / marker).is_file():
        return candidate
    home_candidate = Path.home() / ".gemini" / "config" / "plugins" / "flow"
    if (home_candidate / marker).is_file():
        return home_candidate
    return candidate


def git_porcelain(cwd: Path | None = None) -> str:
    """Return ``git status --porcelain`` output or empty string outside Git."""
    git_bin = shutil.which("git")
    if git_bin is None:
        return ""
    proc = subprocess.run(
        [git_bin, "status", "--porcelain"],
        cwd=str(cwd) if cwd is not None else None,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    return proc.stdout if proc.returncode == 0 else ""


def acquire_runtime_lease(
    cwd: Path | None = None,
    *,
    harness: str = "agy",
    flow_id: str = "",
    chapter_id: str = "",
    task_ids: list[str] | None = None,
) -> Path | None:
    """Register a two-line v1 workflow runtime lease for Stop-gate coordination."""
    raw_tmp = os.environ.get("TMPDIR", "").rstrip("/\\") or tempfile.gettempdir().rstrip("/\\")
    rt_base = (os.environ.get("FLOW_RUNTIME_DIR", "").rstrip("/\\")) or f"{raw_tmp}/flow-runtime"
    norm_root = str(cwd or Path.cwd()).replace("\\", "/").rstrip("/")
    ws_id = re.sub(r"[^A-Za-z0-9._-]", "_", norm_root)[-120:] or "default"
    lease_dir = Path(rt_base) / ws_id / "subagents"
    meta = {
        "v": 1,
        "harness": harness,
        "pid": os.getpid(),
        "role": "flow-subagent",
        "flow_id": flow_id,
        "chapter_id": chapter_id,
        "task_ids": list(task_ids or []),
        "workspace": norm_root,
        "worktree": norm_root,
    }
    try:
        lease_dir.mkdir(parents=True, exist_ok=True)
        lease_path = lease_dir / f"workflow-{os.getpid()}.lease"
        lease_path.write_text(f"{int(time.time())}\n{json.dumps(meta)}\n", encoding="utf-8")
        return lease_path
    except OSError:
        return None


def release_runtime_lease(lease_path: Path | None) -> None:
    """Remove a previously acquired workflow runtime lease."""
    if lease_path is None:
        return
    try:
        lease_path.unlink(missing_ok=True)
    except OSError:
        pass


def run_node_cli(
    plugin_root: Path,
    cli_args: list[str],
    *,
    cwd: Path | None = None,
    timeout_s: int = 30,
) -> tuple[int, dict[str, Any] | list[Any] | None, str, str]:
    """Execute ``sidecars/studio/flow-cli.mjs`` and decode JSON output when available."""
    node_bin = shutil.which("node")
    cli_path = plugin_root / "sidecars" / "studio" / "flow-cli.mjs"
    if node_bin is None or not cli_path.is_file():
        return 127, None, "", "node binary or flow-cli.mjs unavailable"
    proc = subprocess.run(
        [node_bin, str(cli_path), *cli_args],
        cwd=str(cwd or Path.cwd()),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=timeout_s,
        check=False,
    )
    parsed: dict[str, Any] | list[Any] | None = None
    if proc.stdout.strip():
        try:
            loaded = json.loads(proc.stdout)
            if isinstance(loaded, (dict, list)):
                parsed = loaded
        except json.JSONDecodeError:
            parsed = None
    return proc.returncode, parsed, proc.stdout, proc.stderr


def resolve_dynamic_route(
    plugin_root: Path,
    task_kind: str,
    *,
    harness: str = "agy",
    risk: str = "normal",
    complexity: float = 2.0,
    author_vendor: str | None = None,
    cwd: Path | None = None,
) -> dict[str, Any]:
    """Query dynamic ``(model, effort, fallback_chain)`` via ``flow-cli.mjs models route``."""
    cmd = [
        "models",
        "route",
        "--task-kind",
        task_kind,
        "--harness",
        harness,
        "--risk",
        risk,
        "--complexity",
        str(complexity),
        "--root",
        str(cwd or Path.cwd()),
    ]
    if author_vendor:
        cmd.extend(["--author-vendor", author_vendor])
    rc, parsed, _, _ = run_node_cli(plugin_root, cmd, cwd=cwd)
    if rc == 0 and isinstance(parsed, dict):
        route = parsed.get("route") if isinstance(parsed.get("route"), dict) else parsed
        if "runtime_target" in route:
            return route
    upward_kinds = ("planning", "semantic_validation", "spec_review", "committee", "adversarial")
    fallback_tier = "pro" if task_kind in upward_kinds else "flash"
    return {
        "model": fallback_tier,
        "runtime_target": fallback_tier,
        "effort": "high" if fallback_tier == "pro" else "medium",
        "fallback_chain": [{"model": "flash", "runtime_target": "flash", "effort": "medium"}],
        "degraded": False,
    }


def prefetch_seeds(
    paths: list[str],
    call_tool_fn: Callable[[str, dict[str, Any]], Any],
    *,
    max_files: int = 8,
    end_line: int = 120,
) -> list[dict[str, str]]:
    """Prefetch bounded line windows from existing seed files using ``call_tool('read_file', ...)``."""
    digests: list[dict[str, str]] = []
    for raw_path in paths[:max_files]:
        target = Path(str(raw_path))
        if not target.is_file():
            continue
        try:
            content = call_tool_fn("read_file", {"Path": str(target), "StartLine": 1, "EndLine": end_line})
            digests.append({"path": str(raw_path), "snippet": str(content)[:4000]})
        except Exception:
            continue
    return digests

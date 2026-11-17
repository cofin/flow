"""Shared runtime lease, Node CLI, dynamic model routing, and seed-prefetch helpers for Flow workflows."""

from __future__ import annotations

import asyncio
import inspect
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
    from collections.abc import Awaitable, Callable

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
        nested_route = parsed.get("route")
        route = nested_route if isinstance(nested_route, dict) else parsed
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


def _dedupe_preserve(items: list[str]) -> list[str]:
    """Return unique non-empty strings in first-seen order."""
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        text = str(item).strip()
        if text and text not in seen:
            seen.add(text)
            ordered.append(text)
    return ordered


def _extract_markdown_verification_commands(text: str) -> list[str]:
    """Extract fenced shell commands from a markdown ``## Verification`` section."""
    commands: list[str] = []
    in_section = False
    in_fence = False
    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if not in_fence and re.match(r"^#{1,6}\s+verification\b", stripped, re.IGNORECASE):
            in_section = True
            continue
        if in_section and not in_fence and re.match(r"^#{1,6}\s+\S", stripped):
            break
        if not in_section:
            continue
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence and stripped and not stripped.startswith("#"):
            commands.append(stripped)
    return _dedupe_preserve(commands)


def resolve_workspace_commands(
    workspace: Path | str,
    tasks: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Resolve authoritative lint, test, and task verification commands for a workspace."""
    root = Path(workspace)
    lint_cmds: list[str] = []
    test_cmds: list[str] = []
    task_cmds: list[str] = []

    for task in tasks or []:
        if not isinstance(task, dict):
            continue
        raw_cmds = task.get("verification_commands")
        if isinstance(raw_cmds, list):
            task_cmds.extend(str(c) for c in raw_cmds)
        rel_path = str(task.get("path") or "").strip()
        if rel_path:
            task_file = root / rel_path
            if task_file.is_file():
                try:
                    task_cmds.extend(_extract_markdown_verification_commands(task_file.read_text(encoding="utf-8")))
                except OSError:
                    pass

    setup_state_path = root / ".agents" / "setup-state.json"
    if setup_state_path.is_file():
        try:
            setup_state = json.loads(setup_state_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            setup_state = {}
        if isinstance(setup_state, dict):
            prefs = setup_state.get("workflow_preferences")
            cmds_cfg = prefs.get("commands") if isinstance(prefs, dict) else None
            if isinstance(cmds_cfg, dict):
                for key in ("lint", "validate", "check"):
                    val = cmds_cfg.get(key)
                    if isinstance(val, str) and val.strip():
                        lint_cmds.append(val.strip())
                test_val = cmds_cfg.get("test")
                if isinstance(test_val, str) and test_val.strip():
                    test_cmds.append(test_val.strip())

    for mk_name in ("Makefile", "makefile"):
        mk_path = root / mk_name
        if not mk_path.is_file():
            continue
        try:
            mk_text = mk_path.read_text(encoding="utf-8")
        except OSError:
            continue
        targets = set(re.findall(r"^([A-Za-z0-9_.-]+)\s*:", mk_text, flags=re.MULTILINE))
        for target_name in ("lint", "validate", "check"):
            if target_name in targets:
                lint_cmds.append(f"make {target_name}")
        if "test" in targets:
            test_cmds.append("make test")
        elif "check" in targets:
            test_cmds.append("make check")
        break

    pyproject_path = root / "pyproject.toml"
    if pyproject_path.is_file():
        try:
            pyproject_text = pyproject_path.read_text(encoding="utf-8")
        except OSError:
            pyproject_text = ""
        use_uv = (root / "uv.lock").is_file() or bool(shutil.which("uv"))
        prefix = "uv run --no-sync " if use_uv else ""
        if "ruff" in pyproject_text or (root / ".venv" / "bin" / "ruff").is_file():
            lint_cmds.append(f"{prefix}ruff check")
        if "mypy" in pyproject_text or (root / ".venv" / "bin" / "mypy").is_file():
            lint_cmds.append(f"{prefix}mypy")
        if "pyright" in pyproject_text or (root / ".venv" / "bin" / "pyright").is_file():
            lint_cmds.append(f"{prefix}pyright")
        if "pytest" in pyproject_text or (root / "tests").is_dir():
            test_cmds.append(f"{prefix}pytest")

    pkg_path = root / "package.json"
    if pkg_path.is_file():
        try:
            pkg_json = json.loads(pkg_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            pkg_json = {}
        scripts = pkg_json.get("scripts") if isinstance(pkg_json, dict) else None
        if isinstance(scripts, dict):
            if (root / "pnpm-lock.yaml").is_file():
                pm = "pnpm run"
            elif (root / "yarn.lock").is_file():
                pm = "yarn"
            elif (root / "bun.lock").is_file() or (root / "bun.lockb").is_file():
                pm = "bun run"
            else:
                pm = "npm run"
            for name in ("lint", "typecheck", "check", "validate"):
                if name in scripts:
                    lint_cmds.append(f"{pm} {name}")
            if "test" in scripts:
                test_cmds.append(f"{pm} test")

    if (root / "Cargo.toml").is_file():
        lint_cmds.append("cargo clippy --all-targets")
        test_cmds.append("cargo test")

    if (root / "go.mod").is_file():
        lint_cmds.append("go vet ./...")
        test_cmds.append("go test ./...")

    deduped_task = _dedupe_preserve(task_cmds)
    deduped_lint = _dedupe_preserve(lint_cmds)
    deduped_test = _dedupe_preserve(test_cmds)
    recommended = _dedupe_preserve([*deduped_task, *deduped_lint, *deduped_test])
    return {
        "lint": deduped_lint,
        "test": deduped_test,
        "task_verification": deduped_task,
        "recommended": recommended,
    }


async def run_parallel_bounded(
    items: list[Any],
    fn: Callable[[Any], Any],
    *,
    parallel_fn: Callable[[list[Any], Callable[[Any], Any]], Any] | None = None,
    max_concurrency: int | None = None,
    return_exceptions: bool = False,
) -> list[Any]:
    """Execute ``fn`` over ``items`` with bounded concurrency and optional per-item exception capture."""
    if not items:
        return []
    limit = int(max_concurrency) if max_concurrency is not None and int(max_concurrency) > 0 else None
    semaphore = asyncio.Semaphore(limit) if limit is not None else None

    async def _invoke(item: Any) -> Any:
        """Invoke ``fn`` for one item under the bounded semaphore."""
        try:
            if semaphore is None:
                res = fn(item)
                return await res if inspect.isawaitable(res) else res
            async with semaphore:
                res = fn(item)
                return await res if inspect.isawaitable(res) else res
        except Exception as exc:
            if return_exceptions:
                return exc
            raise

    if parallel_fn is not None:
        raw = parallel_fn(items, _invoke)
        return list(await raw if inspect.isawaitable(raw) else raw)
    return list(await asyncio.gather(*(_invoke(item) for item in items)))


class WorkerPool:
    """Worker pool dispatching ready task groups across chapters."""

    def __init__(
        self,
        *,
        plugin_root: Path,
        flow_id: str,
        workspace: Path | str,
        workers: int = 4,
        chapter_id: str | None = None,
        all_ready_chapters: bool = False,
        max_loc: int = 300,
        max_files: int = 6,
        cli_runner: Callable[[Path, list[str]], tuple[int, Any, str, str]] | None = None,
    ) -> None:
        self.plugin_root = Path(plugin_root)
        self.flow_id = str(flow_id)
        self.workspace = Path(workspace)
        self.workers = max(1, min(12, int(workers)))
        self.chapter_id = str(chapter_id) if chapter_id else None
        self.all_ready_chapters = bool(all_ready_chapters)
        self.max_loc = max(50, int(max_loc))
        self.max_files = max(1, int(max_files))
        self._cli_runner = cli_runner or (lambda root, argv: run_node_cli(root, argv, cwd=self.workspace))

    def _plan_tasks(self, exclude_task_ids: set[str], exclude_paths: set[str]) -> dict[str, Any]:
        """Plan ready task groups while excluding active or failed tasks and paths."""
        argv = [
            "tasks",
            "plan",
            "--flow",
            self.flow_id,
            "--workers",
            str(self.workers),
            "--max-loc",
            str(self.max_loc),
            "--max-files",
            str(self.max_files),
            "--briefs",
            "--root",
            str(self.workspace),
        ]
        if self.all_ready_chapters:
            argv.append("--all-ready-chapters")
        elif self.chapter_id:
            argv.extend(["--chapter", self.chapter_id])
        if exclude_task_ids:
            argv.extend(["--exclude-tasks", ",".join(sorted(exclude_task_ids))])
        if exclude_paths:
            argv.extend(["--exclude-paths", ",".join(sorted(exclude_paths))])
        rc, parsed, stdout, stderr = self._cli_runner(self.plugin_root, argv)
        if rc != 0 or not isinstance(parsed, dict):
            raise RuntimeError(f"tasks plan failed (rc={rc}): {stderr or stdout}")
        return parsed

    def _claim_tasks(self, task_group: dict[str, Any], worker_id: int) -> None:
        """Persist task claim state for a chosen task group before worker execution."""
        task_ids = self._group_task_ids(task_group)
        if not task_ids:
            return
        argv = [
            "spec",
            "claim",
            "--flow",
            self.flow_id,
            "--tasks",
            ",".join(task_ids),
            "--by",
            f"worker-{worker_id}",
            "--no-release-stale",
            "--root",
            str(self.workspace),
        ]
        self._cli_runner(self.plugin_root, argv)

    def _complete_tasks(self, task_group: dict[str, Any], receipt: dict[str, Any]) -> None:
        """Persist task completion or blocked state without releasing sibling claims."""
        task_ids = self._group_task_ids(task_group)
        if not task_ids:
            return
        raw_status = str(receipt.get("status") or "completed").strip().lower()
        task_status = "completed" if raw_status == "completed" else "blocked"
        commit_sha = str(receipt.get("commit") or "").strip() or None
        deferred = bool(receipt.get("commit_deferred_to_coordinator"))
        blocked_reason = str(receipt.get("notes") or receipt.get("error") or "").strip() or None
        payload = [
            {
                "taskId": tid,
                "status": task_status,
                "commit": commit_sha,
                "commit_deferred_to_coordinator": deferred,
                "blocked_reason": blocked_reason if task_status == "blocked" else None,
            }
            for tid in task_ids
        ]
        argv = [
            "spec",
            "complete",
            "--flow",
            self.flow_id,
            "--payload",
            json.dumps(payload, ensure_ascii=False),
            "--no-release-stale",
            "--root",
            str(self.workspace),
        ]
        self._cli_runner(self.plugin_root, argv)

    @staticmethod
    def _group_task_ids(task_group: dict[str, Any]) -> list[str]:
        """Extract unique task IDs from a planned task group payload."""
        seen: set[str] = set()
        task_ids: list[str] = []
        for raw_tid in task_group.get("task_ids") or []:
            tid = str(raw_tid).strip()
            if tid and tid not in seen:
                seen.add(tid)
                task_ids.append(tid)
        for task in task_group.get("tasks") or []:
            if not isinstance(task, dict):
                continue
            tid = str(task.get("task_id") or task.get("id") or "").strip()
            if tid and tid not in seen:
                seen.add(tid)
                task_ids.append(tid)
        if not task_ids and task_group.get("task_id"):
            tid = str(task_group["task_id"]).strip()
            if tid:
                task_ids.append(tid)
        return task_ids

    @staticmethod
    def _group_paths(task_group: dict[str, Any]) -> set[str]:
        """Collect normalized code, test, and lock scope paths owned by a task group."""
        paths: set[str] = set()
        for key in ("files", "tests", "lock_scopes"):
            for entry in task_group.get(key) or []:
                norm = str(entry).strip().lstrip("./")
                if norm:
                    paths.add(norm)
        for task in task_group.get("tasks") or []:
            if not isinstance(task, dict):
                continue
            for key in ("files", "tests", "lock_scopes"):
                for entry in task.get(key) or []:
                    norm = str(entry).strip().lstrip("./")
                    if norm:
                        paths.add(norm)
        return paths

    async def run(
        self,
        execute_group: Callable[[dict[str, Any], int], Awaitable[dict[str, Any]] | dict[str, Any]],
    ) -> dict[str, Any]:
        """Run ready task groups across up to ``workers`` concurrent workers."""
        cond = asyncio.Condition()
        io_lock = asyncio.Lock()
        active_tasks: dict[int, dict[str, Any]] = {}
        failed_task_ids: set[str] = set()
        dispatched_task_ids: set[str] = set()
        receipts: list[dict[str, Any]] = []
        last_plan_summary: dict[str, Any] = {}
        plan_error: str | None = None

        async def _worker(worker_id: int) -> None:
            """Claim, run, and record ready task groups until none remain."""
            nonlocal last_plan_summary, plan_error
            while True:
                chosen: dict[str, Any] | None = None
                async with cond:
                    while True:
                        inflight_tasks: set[str] = set(failed_task_ids)
                        inflight_paths: set[str] = set()
                        for active in active_tasks.values():
                            inflight_tasks.update(self._group_task_ids(active))
                            inflight_paths.update(self._group_paths(active))
                        try:
                            async with io_lock:
                                planned = self._plan_tasks(inflight_tasks, inflight_paths)
                        except Exception as exc:
                            plan_error = str(exc)
                            cond.notify_all()
                            return
                        last_plan_summary = planned
                        candidates = list(planned.get("ready_tasks") or [])
                        if not candidates:
                            candidates = [
                                item
                                for item in list(planned.get("tasks") or [])
                                if isinstance(item, dict) and not item.get("waits_for_inflight")
                            ]
                        if candidates:
                            chosen = candidates[0]
                            active_tasks[worker_id] = chosen
                            dispatched_task_ids.update(self._group_task_ids(chosen))
                            async with io_lock:
                                self._claim_tasks(chosen, worker_id)
                            break
                        if not active_tasks:
                            cond.notify_all()
                            return
                        await cond.wait()

                if chosen is None:
                    return

                receipt: dict[str, Any]
                try:
                    out = execute_group(chosen, worker_id)
                    raw_receipt = await out if inspect.isawaitable(out) else out
                    if isinstance(raw_receipt, dict):
                        receipt = dict(raw_receipt)
                    else:
                        receipt = {
                            "group_id": chosen.get("group_id"),
                            "status": "blocked",
                            "notes": f"Executor returned non-dict receipt: {type(raw_receipt).__name__}",
                        }
                except Exception as exc:
                    receipt = {
                        "group_id": chosen.get("group_id"),
                        "task_ids": self._group_task_ids(chosen),
                        "chapter_ids": list(chosen.get("chapter_ids") or []),
                        "status": "blocked",
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                        "notes": f"Worker {worker_id} raised {type(exc).__name__}: {exc}",
                    }

                receipt.setdefault("group_id", chosen.get("group_id"))
                receipt.setdefault("worker_id", worker_id)
                receipt.setdefault("task_ids", self._group_task_ids(chosen))
                receipt.setdefault("chapter_ids", list(chosen.get("chapter_ids") or []))

                async with cond:
                    try:
                        if str(receipt.get("status") or "").lower() != "completed":
                            failed_task_ids.update(self._group_task_ids(chosen))
                        async with io_lock:
                            self._complete_tasks(chosen, receipt)
                        receipts.append(receipt)
                    finally:
                        active_tasks.pop(worker_id, None)
                        cond.notify_all()

        await asyncio.gather(*(_worker(worker_id) for worker_id in range(self.workers)))
        return {
            "receipts": receipts,
            "dispatched_tasks": sorted(dispatched_task_ids),
            "failed_tasks": sorted(failed_task_ids),
            "blocked": list(last_plan_summary.get("blocked") or []),
            "deferred": list(last_plan_summary.get("deferred") or []),
            "plan_error": plan_error,
        }

"""Run a Flow chapter using parallel task briefs, CLI checklist sync, and chapter review."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

_WF_PARENT = Path(__file__).resolve().parent.parent if "__file__" in globals() else Path.cwd() / "workflows"
if str(_WF_PARENT) not in sys.path:
    sys.path.insert(0, str(_WF_PARENT))

from flow_common import (
    QUOTA_MARKERS,
    WorkerPool,
    acquire_runtime_lease,
    release_runtime_lease,
    resolve_dynamic_route,
    resolve_plugin_root,
    resolve_workspace_commands,
    run_node_cli,
    run_parallel_bounded,
)

EXECUTION_SCHEMA = {
    "type": "object",
    "properties": {
        "status": {"type": "string", "enum": ["completed", "blocked"]},
        "code_commit": {"type": "string"},
        "sync_commit": {"type": "string"},
        "commit_deferred_to_coordinator": {"type": "boolean"},
        "files_modified": {"type": "array", "items": {"type": "string"}},
        "tests_verified": {"type": "array", "items": {"type": "string"}},
        "verification_evidence": {"type": "string"},
        "discoveries": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "status",
        "code_commit",
        "commit_deferred_to_coordinator",
        "files_modified",
        "tests_verified",
        "verification_evidence",
    ],
}

REVIEW_SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": ["PASS", "NEEDS_WORK"]},
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "severity": {"type": "string"},
                    "file": {"type": "string"},
                    "location": {"type": "string"},
                    "problem": {"type": "string"},
                    "fix": {"type": "string"},
                },
                "required": ["id", "severity", "file", "problem", "fix"],
            },
        },
    },
    "required": ["verdict", "findings"],
}

flow_id = str(args["flow_id"])
single_chapter = bool(args.get("single_chapter", False))
chapter_id = str(args.get("chapter_id") or "").strip()
task_paths = [str(t) for t in list(args.get("tasks") or [])]
all_ready_chapters = bool(args.get("all_ready_chapters", False)) or (not single_chapter and not chapter_id)
workers = max(1, min(12, int(args.get("workers") or 4)))
allow_uncommitted_arg = bool(args.get("allow_uncommitted", False))
base_commit = str(args.get("base_commit", "HEAD"))
bundle_root = Path(str(args.get("bundle_root", ".agents/bundles")))
execution_mode = str(args.get("execution_mode", "parallel_tasks"))
review_mode = str(args.get("review_mode", "auto"))
harness = str(args.get("harness") or os.environ.get("FLOW_HARNESS") or "agy")
tasks_per_worker = max(1, min(20, int(args.get("tasks_per_worker") or 4)))
executor_agent = str(args.get("executor_agent") or os.environ.get("FLOW_EXECUTOR_AGENT") or "self")
reviewer_agent = str(args.get("reviewer_agent") or os.environ.get("FLOW_REVIEWER_AGENT") or "self")
plugin_root = resolve_plugin_root(args.get("plugin_root"))

exec_route = resolve_dynamic_route(plugin_root, "implementation", harness=harness)
rev_route = resolve_dynamic_route(plugin_root, "spec_review", harness=harness)
preferred_exec_model = str(args.get("executor_model") or os.environ.get("FLOW_EXECUTOR_MODEL") or exec_route["runtime_target"])
preferred_rev_model = str(args.get("reviewer_model") or os.environ.get("FLOW_REVIEWER_MODEL") or rev_route["runtime_target"])
fallback_model = str(args.get("fallback_model") or os.environ.get("FLOW_FALLBACK_MODEL") or "flash")

exec_card = plugin_root / "templates" / "agent" / "executor-schema-card.md"
code_rev_card = plugin_root / "agents" / "code-reviewer.md"
qual_rev_card = plugin_root / "agents" / "quality-reviewer.md"
validator_script = plugin_root / "tools" / "validate.py"
root_spec = bundle_root / "specs" / flow_id / "spec.md"
chapter_spec = (bundle_root / "specs" / flow_id / "chapters" / chapter_id / "spec.md") if chapter_id else root_spec
target_spec = root_spec if (all_ready_chapters and not single_chapter) else chapter_spec
quota_state = {"degraded": False}


async def _run_exec_turn(prompt: str, role: str, model_override: str | None = None) -> tuple[dict, str]:
    """Execute one bounded worker task group with automatic quota/cooldown fallback."""
    chosen = model_override or preferred_exec_model
    active_model = fallback_model if (quota_state["degraded"] and chosen != fallback_model) else chosen
    active_agent = "self" if quota_state["degraded"] else executor_agent
    try:
        res = await with_budget(
            agent(
                prompt,
                schema=EXECUTION_SCHEMA,
                role=role,
                type_name=active_agent,
                workspace="inherit",
                model=active_model,
            ),
            max_tokens=240000,
            timeout=900,
        )
        return res, active_model
    except Exception as exc:
        msg = str(exc).lower()
        if active_model != fallback_model and any(m in msg for m in QUOTA_MARKERS):
            quota_state["degraded"] = True
            log(f"Quota hit on {active_model} for {role}; retrying on '{fallback_model}'")
            res = await with_budget(
                agent(
                    prompt,
                    schema=EXECUTION_SCHEMA,
                    role=f"{role} ({fallback_model} fallback)",
                    type_name="self",
                    workspace="inherit",
                    model=fallback_model,
                ),
                max_tokens=240000,
                timeout=900,
            )
            return res, fallback_model
        raise


async def _run_review_turn(prompt: str, role: str, model_override: str | None = None) -> dict:
    """Execute one read-only review turn with automatic quota fallback."""
    chosen = model_override or preferred_rev_model
    active_model = fallback_model if (quota_state["degraded"] and chosen != fallback_model) else chosen
    active_agent = "self" if quota_state["degraded"] else reviewer_agent
    try:
        out = await with_budget(
            agent(
                prompt,
                schema=REVIEW_SCHEMA,
                role=role,
                type_name=active_agent,
                workspace="inherit",
                model=active_model,
            ),
            max_tokens=200000,
            timeout=600,
        )
        return {"model_used": active_model, **out}
    except Exception as exc:
        msg = str(exc).lower()
        if active_model != fallback_model and any(m in msg for m in QUOTA_MARKERS):
            quota_state["degraded"] = True
            log(f"Quota hit on {active_model} for {role}; retrying review on '{fallback_model}'")
            out = await with_budget(
                agent(
                    prompt,
                    schema=REVIEW_SCHEMA,
                    role=f"{role} ({fallback_model} fallback)",
                    type_name="self",
                    workspace="inherit",
                    model=fallback_model,
                ),
                max_tokens=200000,
                timeout=600,
            )
            return {"model_used": fallback_model, **out}
        raise


def _sync_checklists_cli() -> None:
    """Run Node CLI checklist sync between batches without releasing sibling claims."""
    argv = ["spec", "sync", "--flow", flow_id, "--no-release-stale", "--root", str(Path.cwd())]
    if chapter_id and (single_chapter or not all_ready_chapters):
        argv.extend(["--chapter", chapter_id])
    run_node_cli(plugin_root, argv)


async def _execute_task_group(group: dict, worker_id: int) -> dict:
    """Run one planned task group inside worker ``worker_id``."""
    group_task_ids = [str(tid) for tid in (group.get("task_ids") or []) if str(tid).strip()]
    group_task_paths = [str(p) for p in (group.get("task_paths") or []) if str(p).strip()]
    group_tasks = list(group.get("tasks") or [])
    if not group_tasks:
        shared_verify = list(group.get("verification_commands") or [])
        if group_task_paths:
            group_tasks = [
                {
                    "task_id": group_task_ids[idx] if idx < len(group_task_ids) else group.get("task_id"),
                    "path": path_str,
                    "verification_commands": shared_verify if idx == 0 else [],
                }
                for idx, path_str in enumerate(group_task_paths)
            ]
        elif group_task_ids or group.get("task_id"):
            group_tasks = [
                {
                    "task_id": group_task_ids[0] if group_task_ids else group.get("task_id"),
                    "path": group.get("task_rel_path", ""),
                    "verification_commands": shared_verify,
                }
            ]
    resolved_cmds = resolve_workspace_commands(Path.cwd(), group_tasks)
    task_label = ",".join(
        group_task_ids or [str(t.get("task_id") or "") for t in group_tasks if t.get("task_id")]
    ) or str(group.get("group_id") or "task")
    cmd_hint = resolved_cmds["recommended"] or ["run only the workspace verification command declared in the task"]
    prompt = (
        f"Follow `{exec_card}` to implement task group `{group.get('group_id', task_label)}` "
        f"(tasks {task_label}) inside flow `{flow_id}`.\n"
        f"Workspace-resolved verification commands: {json.dumps(cmd_hint, ensure_ascii=False)}\n"
        "Use ONLY the task brief below instead of reading broad files:\n"
        f"{json.dumps(group.get('brief', {}), ensure_ascii=False)}\n"
        "Apply edits directly, run the listed verification command(s) once, and report exact outcomes."
    )
    receipt, model_used = await _run_exec_turn(prompt, f"Worker {worker_id} Task {group.get('group_id', task_label)}")
    return {
        "mode": "parallel_tasks",
        "worker_id": worker_id,
        "group_id": group.get("group_id"),
        "chapter_ids": list(group.get("chapter_ids") or []),
        "task_ids": group_task_ids or [str(t.get("task_id")) for t in group_tasks if t.get("task_id")],
        "task_id": group.get("task_id") or task_label,
        "commit": receipt.get("code_commit"),
        "model_used": model_used,
        **receipt,
    }


scope_label = chapter_id or ("all-ready-chapters" if all_ready_chapters else flow_id)
phase(f"Execute {flow_id}/{scope_label} ({execution_mode})")
log(f"Running {flow_id}/{scope_label} with up to {workers} worker(s)")

execution_receipts: list[dict] = []
scheduler_summary: dict = {}
okf_errors: list[str] = []
reviews: list[dict] = []
_wf_lease = acquire_runtime_lease()
try:
    if execution_mode == "parallel_tasks":
        pool = WorkerPool(
            plugin_root=plugin_root,
            flow_id=flow_id,
            workspace=Path.cwd(),
            workers=workers,
            chapter_id=chapter_id or None,
            all_ready_chapters=all_ready_chapters and not single_chapter,
        )
        scheduler_summary = await pool.run(_execute_task_group)
        execution_receipts.extend(scheduler_summary.get("receipts", []))
    elif execution_mode == "chapter_batch":
        resolved_batch_cmds = resolve_workspace_commands(Path.cwd(), [{"path": p} for p in task_paths])
        chunks = [task_paths[i : i + tasks_per_worker] for i in range(0, len(task_paths), tasks_per_worker)] or [task_paths]
        for chunk_idx, chunk_paths in enumerate(chunks, start=1):
            batch_prompt = (
                f"Follow `{exec_card}` to implement `{flow_id}/{scope_label}` (`{target_spec}`, root `{root_spec}`) "
                f"across ordered task worksheets {chunk_paths} (batch {chunk_idx} of {len(chunks)}) in one run.\n"
                f"Workspace-resolved verification commands: {json.dumps(resolved_batch_cmds['recommended'], ensure_ascii=False)}\n"
                "Apply edits directly, validate once with targeted tests, commit owned files, and sync checklists."
            )
            receipt, model_used = await _run_exec_turn(batch_prompt, f"Batch {chunk_idx}/{len(chunks)}")
            execution_receipts.append({"mode": "chapter_batch", "batch_index": chunk_idx, "tasks": chunk_paths, "model_used": model_used, **receipt})
            _sync_checklists_cli()
            if receipt.get("status") == "blocked":
                break
    else:
        per_task_out = await pipeline(
            task_paths,
            lambda task_path: _run_exec_turn(
                f"Follow `{exec_card}` to execute single Flow worksheet `{task_path}` for `{flow_id}/{scope_label}` (`{target_spec}`).",
                f"Execute {Path(task_path).name}",
            ),
        )
        for task_path, (receipt, model_used) in zip(task_paths, per_task_out):
            execution_receipts.append({"task_path": task_path, "model_used": model_used, **receipt})
        _sync_checklists_cli()

    if validator_script.is_file():
        defer_commits = allow_uncommitted_arg or any(bool(r.get("commit_deferred_to_coordinator")) for r in execution_receipts)
        val_argv = [sys.executable, str(validator_script), "--bundle", str(bundle_root), "--flow", flow_id]
        if defer_commits:
            val_argv.append("--allow-uncommitted")
        val_proc = subprocess.run(
            val_argv,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        if val_proc.returncode != 0:
            okf_errors = [ln.strip() for ln in (val_proc.stderr + "\n" + val_proc.stdout).splitlines() if ln.strip().startswith("ERROR:")]

    any_blocked = any(r.get("status") == "blocked" for r in execution_receipts)
    if not any_blocked:
        phase("Closeout Review")
        git_range = f"{base_commit}..HEAD"
        _, roster, _, _ = run_node_cli(
            plugin_root,
            ["review", "plan", "--range", git_range, "--spec", str(target_spec), "--mode", review_mode, "--harness", harness, "--root", str(Path.cwd())],
        )
        effective_mode = str(roster.get("mode", review_mode)) if isinstance(roster, dict) else review_mode
        if effective_mode == "single":
            try:
                out = await _run_review_turn(
                    f"Follow `{code_rev_card}` and `{qual_rev_card}` in strictly read-only mode across `{git_range}` for `{target_spec}`.",
                    f"Combined Review ({scope_label})",
                    preferred_rev_model,
                )
                reviews.append({"reviewer": "combined", **out})
            except Exception as exc:
                reviews.append(
                    {
                        "reviewer": "combined",
                        "verdict": "NEEDS_WORK",
                        "findings": [f"Reviewer failed ({type(exc).__name__}): {exc}"],
                    }
                )
        else:
            seats = list(roster.get("reviewers") or roster.get("seats") or []) if isinstance(roster, dict) else []
            if not seats:
                seats = [
                    {
                        "id": "code-reviewer",
                        "title": "Closeout Correctness Review",
                        "card": str(code_rev_card),
                        "model": preferred_rev_model,
                    },
                    {
                        "id": "quality-reviewer",
                        "title": "Closeout Quality Review",
                        "card": str(qual_rev_card),
                        "model": preferred_rev_model,
                    },
                ]

            async def _run_seat(seat: dict) -> dict:
                """Run one independent review seat and return its structured report."""
                seat_card = seat.get("card") or (
                    str(qual_rev_card) if seat.get("id") == "quality-reviewer" else str(code_rev_card)
                )
                seat_model = str(
                    args.get("reviewer_model")
                    or seat.get("model")
                    or (seat.get("model_route") or {}).get("runtime_target")
                    or preferred_rev_model
                )
                out = await _run_review_turn(
                    f"Follow `{seat_card}` in read-only mode as `{seat['id']}` ({seat.get('reason') or seat.get('title', seat['id'])}) across `{git_range}` for `{target_spec}`.",
                    str(seat.get("title") or seat.get("agent") or seat["id"]),
                    seat_model,
                )
                return {"reviewer": seat["id"], **out}

            raw_reviews = await run_parallel_bounded(
                seats,
                _run_seat,
                parallel_fn=parallel,
                max_concurrency=workers,
                return_exceptions=True,
            )
            for seat, item in zip(seats, raw_reviews):
                if isinstance(item, Exception):
                    reviews.append(
                        {
                            "reviewer": seat.get("id", "reviewer"),
                            "verdict": "NEEDS_WORK",
                            "findings": [f"Reviewer crashed ({type(item).__name__}): {item}"],
                        }
                    )
                else:
                    reviews.append(item)
finally:
    release_runtime_lease(_wf_lease)

executed_chapters = sorted({cid for r in execution_receipts for cid in (r.get("chapter_ids") or ([chapter_id] if chapter_id else [])) if cid})
print(
    json.dumps(
        {
            "flow_id": flow_id,
            "chapter_id": chapter_id,
            "chapters_executed": executed_chapters,
            "execution_mode": execution_mode,
            "workers": workers,
            "quota_degraded": quota_state["degraded"],
            "executions": execution_receipts,
            "scheduler": scheduler_summary,
            "okf_validation_errors": okf_errors,
            "reviews": reviews,
            "tokens": tokens_used(),
        }
    )
)

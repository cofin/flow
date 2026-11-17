"""Execute a Flow chapter using micro-sliced Context Packs, zero-token checklist sync, and consolidated closeout."""

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
    ExecutionSlotScheduler,
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
max_workers = max(1, min(12, int(args.get("max_workers") or args.get("max_concurrency") or 4)))
max_concurrency = max(1, min(12, int(args.get("max_concurrency") or max_workers)))
allow_uncommitted_arg = bool(args.get("allow_uncommitted", False))
base_commit = str(args.get("base_commit", "HEAD"))
bundle_root = Path(str(args.get("bundle_root", ".agents/bundles")))
execution_mode = str(args.get("execution_mode", "wave_slices"))
review_mode = str(args.get("review_mode", "auto"))
harness = str(args.get("harness") or os.environ.get("FLOW_HARNESS") or "agy")
batch_size = max(1, min(20, int(args.get("batch_size") or 4)))
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
    """Execute one bounded worker slice with automatic quota/cooldown fallback."""
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


def _sync_checklists_zero_token() -> None:
    """Run deterministic Node CLI checklist sync between batches without releasing sibling claims."""
    argv = ["spec", "sync", "--flow", flow_id, "--no-release-stale", "--root", str(Path.cwd())]
    if chapter_id and (single_chapter or not all_ready_chapters):
        argv.extend(["--chapter", chapter_id])
    run_node_cli(plugin_root, argv)


async def _execute_compiled_slice(sl: dict, slot_id: int) -> dict:
    """Execute one dynamically scheduled Context Pack slice inside worker slot ``slot_id``."""
    sl_task_ids = [str(tid) for tid in (sl.get("task_ids") or []) if str(tid).strip()]
    sl_task_paths = [str(p) for p in (sl.get("task_paths") or []) if str(p).strip()]
    sl_tasks = list(sl.get("tasks") or [])
    if not sl_tasks:
        shared_verify = list(sl.get("verification_commands") or [])
        if sl_task_paths:
            sl_tasks = [
                {
                    "task_id": sl_task_ids[idx] if idx < len(sl_task_ids) else sl.get("task_id"),
                    "path": path_str,
                    "verification_commands": shared_verify if idx == 0 else [],
                }
                for idx, path_str in enumerate(sl_task_paths)
            ]
        elif sl_task_ids or sl.get("task_id"):
            sl_tasks = [
                {
                    "task_id": sl_task_ids[0] if sl_task_ids else sl.get("task_id"),
                    "path": sl.get("task_rel_path", ""),
                    "verification_commands": shared_verify,
                }
            ]
    resolved_cmds = resolve_workspace_commands(Path.cwd(), sl_tasks)
    task_label = ",".join(sl_task_ids or [str(t.get("task_id") or "") for t in sl_tasks if t.get("task_id")]) or str(
        sl.get("slice_id") or "slice"
    )
    cmd_hint = resolved_cmds["recommended"] or ["run only the workspace verification command declared in the slice"]
    prompt = (
        f"Follow `{exec_card}` to execute bounded slice `{sl.get('slice_id', task_label)}` "
        f"(tasks {task_label}) inside flow `{flow_id}`.\n"
        f"Workspace-resolved verification commands: {json.dumps(cmd_hint, ensure_ascii=False)}\n"
        "Use ONLY the pre-extracted Context Pack below instead of reading broad files:\n"
        f"{json.dumps(sl.get('context_pack', {}), ensure_ascii=False)}\n"
        "Apply edits directly, run the listed verification command(s) once, and report exact outcomes."
    )
    receipt, model_used = await _run_exec_turn(prompt, f"Slot {slot_id} Slice {sl.get('slice_id', task_label)}")
    return {
        "mode": "wave_slices",
        "slot_id": slot_id,
        "slice_id": sl.get("slice_id"),
        "chapter_ids": list(sl.get("chapter_ids") or []),
        "task_ids": sl_task_ids or [str(t.get("task_id")) for t in sl_tasks if t.get("task_id")],
        "task_id": sl.get("task_id") or task_label,
        "commit": receipt.get("code_commit"),
        "model_used": model_used,
        **receipt,
    }


scope_label = chapter_id or ("all-ready-chapters" if all_ready_chapters else flow_id)
phase(f"Execute {flow_id}/{scope_label} ({execution_mode})")
log(f"Executing {flow_id}/{scope_label} with up to {max_workers} worker slot(s)")

execution_receipts: list[dict] = []
scheduler_summary: dict = {}
okf_errors: list[str] = []
reviews: list[dict] = []
_wf_lease = acquire_runtime_lease()
try:
    if execution_mode == "wave_slices":
        scheduler = ExecutionSlotScheduler(
            plugin_root=plugin_root,
            flow_id=flow_id,
            workspace=Path.cwd(),
            max_workers=max_workers,
            chapter_id=chapter_id or None,
            all_ready_chapters=all_ready_chapters and not single_chapter,
        )
        scheduler_summary = await scheduler.run(_execute_compiled_slice)
        execution_receipts.extend(scheduler_summary.get("receipts", []))
    elif execution_mode == "chapter_batch":
        resolved_batch_cmds = resolve_workspace_commands(Path.cwd(), [{"path": p} for p in task_paths])
        chunks = [task_paths[i : i + batch_size] for i in range(0, len(task_paths), batch_size)] or [task_paths]
        for chunk_idx, chunk_paths in enumerate(chunks, start=1):
            batch_prompt = (
                f"Follow `{exec_card}` to execute `{flow_id}/{scope_label}` (`{target_spec}`, root `{root_spec}`) "
                f"across ordered task worksheets {chunk_paths} (batch {chunk_idx} of {len(chunks)}) in one bounded turn.\n"
                f"Workspace-resolved verification commands: {json.dumps(resolved_batch_cmds['recommended'], ensure_ascii=False)}\n"
                "Apply edits cleanly, validate once with targeted tests, commit owned files, and sync checklists."
            )
            receipt, model_used = await _run_exec_turn(batch_prompt, f"Batch {chunk_idx}/{len(chunks)}")
            execution_receipts.append({"mode": "chapter_batch", "batch_index": chunk_idx, "tasks": chunk_paths, "model_used": model_used, **receipt})
            _sync_checklists_zero_token()
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
        _sync_checklists_zero_token()

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
        phase("Consolidated Closeout Review")
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
                    {"id": "code-reviewer", "title": "Closeout Correctness Review", "model": preferred_rev_model},
                    {"id": "quality-reviewer", "title": "Closeout Quality Review", "model": preferred_rev_model},
                ]

            async def _run_seat(seat: dict) -> dict:
                seat_model = str(
                    args.get("reviewer_model")
                    or seat.get("model")
                    or (seat.get("model_route") or {}).get("runtime_target")
                    or preferred_rev_model
                )
                out = await _run_review_turn(
                    f"Follow `{code_rev_card}` in read-only mode as `{seat['id']}` ({seat.get('reason') or seat.get('title', seat['id'])}) across `{git_range}` for `{target_spec}`.",
                    str(seat.get("title") or seat.get("agent") or seat["id"]),
                    seat_model,
                )
                return {"reviewer": seat["id"], **out}

            raw_reviews = await run_parallel_bounded(
                seats,
                _run_seat,
                parallel_fn=parallel,
                max_concurrency=max_concurrency,
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
            "max_workers": max_workers,
            "quota_degraded": quota_state["degraded"],
            "executions": execution_receipts,
            "scheduler": scheduler_summary,
            "okf_validation_errors": okf_errors,
            "reviews": reviews,
            "tokens": tokens_used(),
        }
    )
)

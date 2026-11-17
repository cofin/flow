"""Execute a Flow chapter using micro-sliced Context Packs, zero-token checklist sync, and consolidated closeout."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys

_WF_PARENT = Path(__file__).resolve().parent.parent if "__file__" in globals() else Path.cwd() / "workflows"
if str(_WF_PARENT) not in sys.path:
    sys.path.insert(0, str(_WF_PARENT))

from flow_common import (
    QUOTA_MARKERS,
    acquire_runtime_lease,
    release_runtime_lease,
    resolve_dynamic_route,
    resolve_plugin_root,
    run_node_cli,
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
chapter_id = str(args["chapter_id"])
task_paths = list(args["tasks"])
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
chapter_spec = bundle_root / "specs" / flow_id / "chapters" / chapter_id / "spec.md"
root_spec = bundle_root / "specs" / flow_id / "spec.md"
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


def _sync_checklists_zero_token() -> None:
    """Run deterministic Node CLI checklist sync between waves with zero LLM tokens."""
    run_node_cli(plugin_root, ["spec", "sync", "--flow", flow_id, "--chapter", chapter_id, "--root", str(Path.cwd())])


_, compiled_waves, _, _ = run_node_cli(
    plugin_root,
    ["slices", "compile", "--flow", flow_id, "--chapter", chapter_id, "--packs", "--root", str(Path.cwd())],
)

phase(f"Execute Chapter {chapter_id} ({execution_mode})")
log(f"Executing {len(task_paths)} task worksheet(s) for {flow_id}/{chapter_id}")

execution_receipts: list[dict] = []
okf_errors: list[str] = []
reviews: list[dict] = []
_wf_lease = acquire_runtime_lease()
try:
    waves = compiled_waves.get("waves", []) if isinstance(compiled_waves, dict) else []
    if execution_mode == "wave_slices" and waves:
        for w in waves:
            slices = list(w.get("slices", []))[:4]
            wave_idx = w.get("wave_index", 0)
            wave_out = await parallel(
                slices,
                lambda sl: _run_exec_turn(
                    (
                        f"Follow `{exec_card}` to execute single bounded micro-slice `{sl['task_id']}` "
                        f"(`{sl.get('task_rel_path', '')}`) inside `{flow_id}/{chapter_id}`.\n"
                        "Use ONLY the pre-extracted Context Pack below instead of reading broad files:\n"
                        f"{json.dumps(sl.get('context_pack', {}), ensure_ascii=False)}\n"
                        "Apply the edits directly, run the single targeted test command once, and report exact outcomes."
                    ),
                    f"Wave {wave_idx} Slice {sl['task_id']}",
                ),
            )
            for sl, (receipt, model_used) in zip(slices, wave_out):
                execution_receipts.append({"mode": "wave_slices", "wave": wave_idx, "task_id": sl["task_id"], "model_used": model_used, **receipt})
            _sync_checklists_zero_token()
            if any(r.get("status") == "blocked" for r in execution_receipts):
                break
    elif execution_mode == "chapter_batch":
        chunks = [task_paths[i : i + batch_size] for i in range(0, len(task_paths), batch_size)] or [task_paths]
        for chunk_idx, chunk_paths in enumerate(chunks, start=1):
            batch_prompt = (
                f"Follow `{exec_card}` to execute `{flow_id}/{chapter_id}` (`{chapter_spec}`, root `{root_spec}`) "
                f"across ordered task worksheets {chunk_paths} (batch {chunk_idx} of {len(chunks)}) in one bounded turn.\n"
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
                f"Follow `{exec_card}` to execute single Flow worksheet `{task_path}` for `{flow_id}/{chapter_id}` (`{chapter_spec}`).",
                f"Execute {Path(task_path).name}",
            ),
        )
        for task_path, (receipt, model_used) in zip(task_paths, per_task_out):
            execution_receipts.append({"task_path": task_path, "model_used": model_used, **receipt})
        _sync_checklists_zero_token()

    if validator_script.is_file():
        import subprocess
        val_proc = subprocess.run(
            [sys.executable, str(validator_script), "--bundle", str(bundle_root), "--flow", flow_id],
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
            ["review", "plan", "--range", git_range, "--spec", str(chapter_spec), "--mode", review_mode, "--harness", harness, "--root", str(Path.cwd())],
        )
        effective_mode = str(roster.get("mode", review_mode)) if isinstance(roster, dict) else review_mode
        if effective_mode == "single":
            out = await with_budget(
                agent(
                    f"Follow `{code_rev_card}` and `{qual_rev_card}` in strictly read-only mode across `{git_range}` for `{chapter_spec}`.",
                    schema=REVIEW_SCHEMA,
                    role=f"Combined Chapter Review ({chapter_id})",
                    type_name=reviewer_agent,
                    workspace="inherit",
                    model=preferred_rev_model,
                ),
                max_tokens=200000,
                timeout=600,
            )
            reviews.append({"reviewer": "combined", "model_used": preferred_rev_model, **out})
        else:
            seats = list(roster.get("reviewers") or roster.get("seats") or []) if isinstance(roster, dict) else []
            if not seats:
                seats = [
                    {"id": "code-reviewer", "title": "Chapter Correctness Review", "model": preferred_rev_model},
                    {"id": "quality-reviewer", "title": "Chapter Quality Review", "model": preferred_rev_model},
                ]
            reviews = await parallel(
                seats,
                lambda seat: with_budget(
                    agent(
                        f"Follow `{code_rev_card}` in read-only mode as `{seat['id']}` ({seat.get('reason') or seat.get('title', seat['id'])}) across `{git_range}` for `{chapter_spec}`.",
                        schema=REVIEW_SCHEMA,
                        role=str(seat.get("title") or seat.get("agent") or seat["id"]),
                        type_name=reviewer_agent,
                        workspace="inherit",
                        model=str(
                            args.get("reviewer_model")
                            or seat.get("model")
                            or (seat.get("model_route") or {}).get("runtime_target")
                            or preferred_rev_model
                        ),
                    ),
                    max_tokens=200000,
                    timeout=600,
                ),
            )
finally:
    release_runtime_lease(_wf_lease)

print(
    json.dumps(
        {
            "flow_id": flow_id,
            "chapter_id": chapter_id,
            "execution_mode": execution_mode,
            "quota_degraded": quota_state["degraded"],
            "executions": execution_receipts,
            "okf_validation_errors": okf_errors,
            "reviews": reviews,
            "tokens": tokens_used(),
        }
    )
)

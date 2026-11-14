"""Execute a single Flow chapter with chapter-batch edits, fast lint gating, OKF validation, and review."""

import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time

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

QUOTA_MARKERS = (
    "429",
    "resource_exhausted",
    "quota",
    "rate limit",
    "rate_limit",
    "capacity",
    "overloaded",
    "exhausted",
)

flow_id = str(args["flow_id"])
chapter_id = str(args["chapter_id"])
task_paths = list(args["tasks"])
base_commit = str(args.get("base_commit", "HEAD"))
bundle_root = Path(str(args.get("bundle_root", ".agents/bundles")))
execution_mode = str(args.get("execution_mode", "chapter_batch"))
review_mode = str(args.get("review_mode", "dual"))
preferred_exec_model = str(args.get("executor_model") or os.environ.get("FLOW_EXECUTOR_MODEL") or "inherit")
preferred_rev_model = str(args.get("reviewer_model") or os.environ.get("FLOW_REVIEWER_MODEL") or "inherit")
fallback_model = str(args.get("fallback_model") or os.environ.get("FLOW_FALLBACK_MODEL") or "flash")
executor_agent = str(args.get("executor_agent") or os.environ.get("FLOW_EXECUTOR_AGENT") or "self")
reviewer_agent = str(args.get("reviewer_agent") or os.environ.get("FLOW_REVIEWER_AGENT") or "self")

plugin_root = Path(str(args.get("plugin_root") or os.environ.get("FLOW_PLUGIN_ROOT") or Path.cwd()))
if not (plugin_root / "templates" / "agent" / "executor-schema-card.md").is_file():
    candidate = Path.home() / ".gemini" / "config" / "plugins" / "flow"
    if (candidate / "templates" / "agent" / "executor-schema-card.md").is_file():
        plugin_root = candidate

exec_card = plugin_root / "templates" / "agent" / "executor-schema-card.md"
code_rev_card = plugin_root / "agents" / "code-reviewer.md"
qual_rev_card = plugin_root / "agents" / "quality-reviewer.md"
validator_script = plugin_root / "tools" / "validate.py"
chapter_spec = bundle_root / "specs" / flow_id / "chapters" / chapter_id / "spec.md"
root_spec = bundle_root / "specs" / flow_id / "spec.md"

quota_state = {"degraded": False}


def _extract_task_ids(raw_tasks: list[Any]) -> list[str]:
    """Extract normalized short task identifiers from task path or identifier strings."""
    ids: list[str] = []
    for item in raw_tasks:
        name = Path(str(item)).name
        stem = Path(str(item)).stem
        task_id = name.split("-", 1)[0] if "-" in name else stem
        if task_id:
            ids.append(task_id)
    return ids


def _acquire_runtime_lease() -> Path | None:
    """Register an active workflow runtime lease for Stop-gate subagent coordination."""
    raw_tmp = os.environ.get("TMPDIR", "").rstrip("/\\") or tempfile.gettempdir().rstrip("/\\")
    rt_base = (os.environ.get("FLOW_RUNTIME_DIR", "").rstrip("/\\")) or f"{raw_tmp}/flow-runtime"
    norm_root = str(Path.cwd()).replace("\\", "/").rstrip("/")
    ws_id = re.sub(r"[^A-Za-z0-9._-]", "_", norm_root)[-120:] or "default"
    lease_dir = Path(rt_base) / ws_id / "subagents"
    try:
        lease_dir.mkdir(parents=True, exist_ok=True)
        lease_id = f"workflow-{os.getpid()}"
        lease_path = lease_dir / f"{lease_id}.lease"
        meta = {
            "v": 1,
            "harness": "agy",
            "conversation_id": lease_id,
            "parent_conversation_id": "",
            "workspace": norm_root,
            "worktree": norm_root,
            "role": "flow-subagent",
            "flow_id": flow_id,
            "chapter_id": chapter_id,
            "task_ids": _extract_task_ids(list(tasks)),
        }
        lease_path.write_text(
            f"{int(time.time())}\n{json.dumps(meta, separators=(',', ':'))}\n",
            encoding="utf-8",
        )
        return lease_path
    except OSError:
        return None


def _release_runtime_lease(lease_path: Path | None) -> None:
    """Remove a previously registered workflow runtime lease."""
    if lease_path is None:
        return
    try:
        lease_path.unlink(missing_ok=True)
    except OSError:
        pass


async def _run_exec_turn(prompt: str, role: str) -> tuple[dict, str]:
    """Run an executor turn with automatic quota fallback to configured fallback tier (never flash_lite)."""
    active_model = fallback_model if quota_state["degraded"] else preferred_exec_model
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
            max_tokens=320000,
            timeout=1200,
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
                max_tokens=320000,
                timeout=1200,
            )
            return res, fallback_model
        raise


phase(f"Execute Chapter {chapter_id} ({execution_mode})")
log(f"Executing {len(task_paths)} task worksheet(s) for {flow_id}/{chapter_id}")

execution_receipts: list[dict] = []
okf_errors: list[str] = []
reviews: list[dict] = []
_wf_lease = _acquire_runtime_lease()
try:
    if execution_mode == "chapter_batch":
        batch_prompt = (
            f"Follow `{exec_card}` to execute chapter `{flow_id}/{chapter_id}` (`{chapter_spec}`, root `{root_spec}`) "
            f"across ordered task worksheets {task_paths} in ONE cohesive warm batch:\n"
            "1. Read only the chapter spec, assigned worksheets, and their bounded `read_set` files.\n"
            "2. Apply all code and canonical unit test edits across the chapter batch so shared files are edited once.\n"
            "3. Validate ONCE with the Fast Chapter Gate (`< 60s`: offline ruff/mypy/pyright + targeted unit test file; "
            "do NOT run slow full test suites or `npx --yes` network wrappers, and never pass BypassSandbox=true).\n"
            "4. Commit owned code/test files first to obtain `<CODE_SHA>` (if `.git/` is read-only inside the sandbox "
            "and `git commit` is denied, set `commit_deferred_to_coordinator: true` without looping), then synchronize "
            "`tasks/*.md`, chapter `spec.md`, `chapters/index.md`, root `spec.md`, affected `knowledge/**`/`docs/**`, "
            "and `log.md` in present tense."
        )
        receipt, model_used = await _run_exec_turn(batch_prompt, f"Batch Execute {chapter_id}")
        execution_receipts.append({"mode": "chapter_batch", "model_used": model_used, **receipt})
    else:
        per_task_out = await pipeline(
            task_paths,
            lambda task_path: _run_exec_turn(
                f"Follow `{exec_card}` to execute single Flow worksheet `{task_path}` for `{flow_id}/{chapter_id}` "
                f"(`{chapter_spec}`). Validate with the fast static + targeted unit test gate (`< 60s`), never pass "
                "BypassSandbox=true, and synchronize task + chapter checklists in present tense.",
                f"Execute {Path(task_path).name}",
            ),
        )
        for task_path, (receipt, model_used) in zip(task_paths, per_task_out):
            execution_receipts.append({"task_path": task_path, "model_used": model_used, **receipt})

    if validator_script.is_file():
        val_proc = subprocess.run(
            [sys.executable, str(validator_script), "--bundle", str(bundle_root), "--flow", flow_id],
            capture_output=True,
            text=True,
            check=False,
        )
        if val_proc.returncode != 0:
            okf_errors = [
                ln.strip()
                for ln in (val_proc.stderr + "\n" + val_proc.stdout).splitlines()
                if ln.strip().startswith("ERROR:")
            ]

    any_blocked = any(r.get("status") == "blocked" for r in execution_receipts)

    async def _run_reviewer_turn(reviewer_id: str, role: str, prompt: str) -> dict:
        """Run one zero-context chapter reviewer with quota fallback."""
        active_model = fallback_model if (quota_state["degraded"] and preferred_rev_model != fallback_model) else preferred_rev_model
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
            return {"reviewer": reviewer_id, "agent_used": active_agent, "model_used": active_model, **out}
        except Exception as exc:
            msg = str(exc).lower()
            if active_model != fallback_model and any(m in msg for m in QUOTA_MARKERS):
                quota_state["degraded"] = True
                log(f"Quota hit on {active_model} for {role}; retrying on '{fallback_model}'")
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
                return {"reviewer": reviewer_id, "agent_used": "self", "model_used": fallback_model, **out}
            raise

    if not any_blocked:
        phase("Zero-Context Chapter Review")
        git_range = f"{base_commit}..HEAD"
        if review_mode == "single":
            single_out = await _run_reviewer_turn(
                "combined",
                f"Combined Chapter Review ({chapter_id})",
                (
                    f"Follow `{code_rev_card}` and `{qual_rev_card}` in strictly read-only mode (never edit files or "
                    f"pass BypassSandbox=true). Review chapter `{flow_id}/{chapter_id}` (`{chapter_spec}`, root "
                    f"`{root_spec}`) across Git range `{git_range}` (and working-tree diff if commit was deferred)."
                ),
            )
            reviews.append(single_out)
        else:
            reviewer_specs = [
                (
                    "code-reviewer",
                    "Chapter Correctness & Spec-Sync Review",
                    f"Follow `{code_rev_card}` in strictly read-only mode (never edit files or pass BypassSandbox=true). "
                    f"Review `{flow_id}/{chapter_id}` (`{chapter_spec}`, root `{root_spec}`) across `{git_range}` "
                    "(and working-tree diff if commit was deferred).",
                ),
                (
                    "quality-reviewer",
                    "Chapter Quality & Debloat Review",
                    f"Follow `{qual_rev_card}` in strictly read-only mode (never edit files or pass BypassSandbox=true). "
                    f"Review `{flow_id}/{chapter_id}` (`{chapter_spec}`) across `{git_range}` "
                    "(and working-tree diff if commit was deferred).",
                ),
            ]
            reviews = await parallel(
                reviewer_specs,
                lambda item: _run_reviewer_turn(item[0], item[1], item[2]),
            )
finally:
    _release_runtime_lease(_wf_lease)

summary = {
    "flow_id": flow_id,
    "chapter_id": chapter_id,
    "execution_mode": execution_mode,
    "quota_degraded": quota_state["degraded"],
    "executions": execution_receipts,
    "okf_validation_errors": okf_errors,
    "reviews": reviews,
    "tokens": tokens_used(),
}
print(json.dumps(summary))

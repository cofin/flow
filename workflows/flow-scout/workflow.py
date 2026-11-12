"""Run parallel read-only SubsystemDigest reconnaissance scouts with quota-aware budgets."""

import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import time

DIGEST_SCHEMA = {
    "type": "object",
    "properties": {
        "subsystem": {"type": "string"},
        "symbols_and_exact_signatures": {"type": "array", "items": {"type": "string"}},
        "seams_and_dependency_categories": {"type": "array", "items": {"type": "string"}},
        "canonical_tests_and_fixtures": {"type": "array", "items": {"type": "string"}},
        "edge_cases_and_gotchas": {"type": "array", "items": {"type": "string"}},
        "affected_docs_and_okf_chapters": {"type": "array", "items": {"type": "string"}},
        "open_design_forks": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "subsystem",
        "symbols_and_exact_signatures",
        "seams_and_dependency_categories",
        "canonical_tests_and_fixtures",
        "edge_cases_and_gotchas",
        "affected_docs_and_okf_chapters",
        "open_design_forks",
    ],
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

subsystems = list(args.get("subsystems", []))
preferred_model = str(args.get("scout_model") or os.environ.get("FLOW_SCOUT_MODEL") or "flash")
scout_agent = str(args.get("scout_agent") or os.environ.get("FLOW_SCOUT_AGENT") or "self")
timeout_seconds = int(args.get("timeout_seconds", 300))
quota_state = {"degraded": False}


def _git_porcelain() -> str:
    """Capture working-tree status to confirm read-only scouts leave zero mutations."""
    proc = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, check=False)
    return proc.stdout if proc.returncode == 0 else ""


def _acquire_runtime_lease() -> Path | None:
    """Register an active workflow runtime lease for Stop-gate subagent coordination."""
    raw_tmp = os.environ.get("TMPDIR", "").rstrip("/\\") or tempfile.gettempdir().rstrip("/\\")
    rt_base = (os.environ.get("FLOW_RUNTIME_DIR", "").rstrip("/\\")) or f"{raw_tmp}/flow-runtime"
    norm_root = str(Path.cwd()).replace("\\", "/").rstrip("/")
    ws_id = re.sub(r"[^A-Za-z0-9._-]", "_", norm_root)[-120:] or "default"
    lease_dir = Path(rt_base) / ws_id / "subagents"
    try:
        lease_dir.mkdir(parents=True, exist_ok=True)
        lease_path = lease_dir / f"workflow-{os.getpid()}.lease"
        lease_path.write_text(f"{int(time.time())}\n", encoding="utf-8")
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


async def _run_scout(item: dict) -> dict:
    """Execute one bounded subsystem scout with quota fallback only on narrow <=3-file fetches."""
    name = str(item.get("name", "subsystem"))
    paths = [str(p) for p in item.get("paths", [])]
    focus = str(item.get("focus", "")).strip()
    allow_lite = bool(item.get("narrow_fetch", False)) and len(paths) <= 3
    fallback_model = "flash_lite" if allow_lite and preferred_model == "flash" else None
    active_model = fallback_model if (quota_state["degraded"] and fallback_model) else preferred_model
    focus_clause = f" Focus: {focus}" if focus else ""
    prompt = (
        f"Scout subsystem `{name}` across exact paths {paths}.{focus_clause}\n"
        "Stay strictly read-only: read only these scoped repository files, canonical tests, and referenced "
        ".agents/bundles/knowledge/ chapters. Never edit files, never browse plugin reference docs, and never "
        "pass BypassSandbox=true. Return a concise SubsystemDigest."
    )
    try:
        digest = await with_budget(
            agent(
                prompt,
                schema=DIGEST_SCHEMA,
                role=f"Scout {name}",
                type_name=scout_agent,
                workspace="inherit",
                model=active_model,
            ),
            max_tokens=120000,
            timeout=timeout_seconds,
        )
        return {"subsystem": name, "status": "completed", "model_used": active_model, "digest": digest}
    except BudgetExceeded as exc:
        log(f"Scout {name} hit budget limit: {exc}")
        return {"subsystem": name, "status": "timed_out", "model_used": active_model, "error": str(exc), "digest": None}
    except Exception as exc:
        msg = str(exc).lower()
        if fallback_model and active_model != fallback_model and any(m in msg for m in QUOTA_MARKERS):
            quota_state["degraded"] = True
            log(f"Quota hit for narrow scout {name} on {active_model}; retrying on {fallback_model}")
            digest = await with_budget(
                agent(
                    prompt,
                    schema=DIGEST_SCHEMA,
                    role=f"Scout {name} ({fallback_model})",
                    type_name=scout_agent,
                    workspace="inherit",
                    model=fallback_model,
                ),
                max_tokens=80000,
                timeout=timeout_seconds,
            )
            return {"subsystem": name, "status": "completed", "model_used": fallback_model, "digest": digest}
        return {"subsystem": name, "status": "failed", "model_used": active_model, "error": str(exc), "digest": None}


before_status = _git_porcelain()
phase("Sharded Subsystem Reconnaissance")
log(f"Dispatching {len(subsystems)} read-only scout(s) on model={preferred_model}")
results: list[dict] = []
_wf_lease = _acquire_runtime_lease()
try:
    results = await parallel(subsystems, _run_scout)
finally:
    _release_runtime_lease(_wf_lease)
after_status = _git_porcelain()

summary = {
    "subsystems_count": len(subsystems),
    "results": results,
    "worktree_clean": before_status == after_status,
    "tokens": tokens_used(),
}
print(json.dumps(summary))

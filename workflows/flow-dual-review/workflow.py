"""Orchestrate parallel zero-context code and quality reviews with quota-aware model routing."""

import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import time

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
                    "category": {"type": "string"},
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

git_range = str(args["git_range"])
spec_path = str(args.get("spec_path", ""))
review_mode = str(args.get("review_mode", "dual"))
timeout_seconds = int(args.get("timeout_seconds", 600))
preferred_review_model = str(args.get("reviewer_model") or os.environ.get("FLOW_REVIEWER_MODEL") or "inherit")

plugin_root = Path(str(args.get("plugin_root") or os.environ.get("FLOW_PLUGIN_ROOT") or Path.cwd()))
if not (plugin_root / "agents" / "code-reviewer.md").is_file():
    candidate = Path.home() / ".gemini" / "config" / "plugins" / "flow"
    if (candidate / "agents" / "code-reviewer.md").is_file():
        plugin_root = candidate

code_card = plugin_root / "agents" / "code-reviewer.md"
qual_card = plugin_root / "agents" / "quality-reviewer.md"
spec_clause = f" against `{spec_path}`" if spec_path else ""
quota_state = {"degraded": False}


def _git_porcelain() -> str:
    """Capture working-tree status to confirm reviewers made zero file mutations."""
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


async def _run_reviewer(role_id: str, card_title: str, model_tier: str, prompt: str) -> dict:
    """Run one zero-context reviewer on Pro/inherit first, falling back to flash only on quota exhaustion."""
    active_model = "flash" if (quota_state["degraded"] and model_tier != "flash") else model_tier
    try:
        out = await with_budget(
            agent(
                prompt,
                schema=REVIEW_SCHEMA,
                role=card_title,
                type_name="self",
                workspace="inherit",
                model=active_model,
            ),
            max_tokens=200000,
            timeout=timeout_seconds,
        )
        return {"reviewer": role_id, "model_used": active_model, **out}
    except Exception as exc:
        msg = str(exc).lower()
        if active_model != "flash" and any(m in msg for m in QUOTA_MARKERS):
            quota_state["degraded"] = True
            log(f"Quota hit on {active_model} for {card_title}; retrying on 'flash'")
            out = await with_budget(
                agent(
                    prompt,
                    schema=REVIEW_SCHEMA,
                    role=f"{card_title} (flash fallback)",
                    type_name="self",
                    workspace="inherit",
                    model="flash",
                ),
                max_tokens=200000,
                timeout=timeout_seconds,
            )
            return {"reviewer": role_id, "model_used": "flash", **out}
        raise


before_status = _git_porcelain()
phase("Zero-Context Review")
log(f"Running {review_mode} review on {git_range}{spec_clause} (preferred_model={preferred_review_model})")

reports: list[dict] = []
_wf_lease = _acquire_runtime_lease()
try:
    if review_mode == "single":
        single_report = await _run_reviewer(
            "combined",
            "Combined Correctness & Quality Review",
            preferred_review_model,
            (
                f"Follow `{code_card}` and `{qual_card}` in strictly read-only mode (never edit files or pass "
                f"BypassSandbox=true). Review exact Git range `{git_range}`{spec_clause} for correctness, spec/Markdown "
                "sync, SUT test integrity, dead code, and OKF hygiene."
            ),
        )
        reports = [single_report]
    else:
        reviewer_defs = [
            (
                "code-reviewer",
                "Correctness & Spec Review",
                preferred_review_model,
                (
                    f"Follow `{code_card}` in strictly read-only mode (never edit files or pass BypassSandbox=true). "
                    f"Review exact Git range `{git_range}`{spec_clause} for correctness, spec/Markdown sync, anti-skip "
                    "file ownership, and SUT test integrity."
                ),
            ),
            (
                "quality-reviewer",
                "Quality & Debloat Review",
                preferred_review_model,
                (
                    f"Follow `{qual_card}` in strictly read-only mode (never edit files or pass BypassSandbox=true). "
                    f"Review exact Git range `{git_range}`{spec_clause} for dead code, prose sediment, OKF hygiene, "
                    "and test strength."
                ),
            ),
        ]
        reports = await parallel(
            reviewer_defs,
            lambda item: _run_reviewer(item[0], item[1], item[2], item[3]),
        )
finally:
    _release_runtime_lease(_wf_lease)

after_status = _git_porcelain()
combined = {
    "git_range": git_range,
    "spec_path": spec_path,
    "review_mode": review_mode,
    "quota_degraded": quota_state["degraded"],
    "worktree_clean": before_status == after_status,
    "reviews": reports,
    "code_review": reports[0],
    "quality_review": reports[1] if len(reports) > 1 else reports[0],
    "tokens": tokens_used(),
}
print(json.dumps(combined))

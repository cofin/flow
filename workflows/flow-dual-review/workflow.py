"""Run independent reviews with optional second-vendor checks."""

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
    SIMPLIFY_SCHEMA,
    acquire_runtime_lease,
    git_porcelain,
    release_runtime_lease,
    resolve_dynamic_route,
    resolve_plugin_root,
    run_node_cli,
    run_parallel_bounded,
)

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

git_range = str(args["git_range"])
spec_path = str(args.get("spec_path", ""))
review_mode = str(args.get("review_mode", "auto"))
goal = str(args.get("goal", "")).strip()
harness = str(args.get("harness") or os.environ.get("FLOW_HARNESS") or "agy")
author_vendor = str(args.get("author_vendor") or "")
timeout_seconds = int(args.get("timeout_seconds", 600))
workers = max(1, min(12, int(args.get("workers") or 4)))
plugin_root = resolve_plugin_root(args.get("plugin_root"), marker="agents/code-reviewer.md")

route = resolve_dynamic_route(plugin_root, "spec_review", harness=harness, author_vendor=author_vendor or None)
preferred_review_model = str(args.get("reviewer_model") or os.environ.get("FLOW_REVIEWER_MODEL") or route["runtime_target"])
fallback_model = str(args.get("fallback_model") or os.environ.get("FLOW_FALLBACK_MODEL") or "flash")
code_reviewer_agent = str(args.get("code_reviewer_agent") or os.environ.get("FLOW_REVIEWER_AGENT") or "self")
quality_reviewer_agent = str(args.get("quality_reviewer_agent") or os.environ.get("FLOW_QUALITY_REVIEWER_AGENT") or code_reviewer_agent)

code_card = plugin_root / "agents" / "code-reviewer.md"
qual_card = plugin_root / "agents" / "quality-reviewer.md"
simplify_card = plugin_root / "templates" / "agent" / "simplify-card.md"
spec_clause = f" against `{spec_path}`" if spec_path else ""
quota_state = {"degraded": False}

cli_args = ["review", "plan", "--range", git_range, "--mode", review_mode, "--harness", harness, "--root", str(Path.cwd())]
if spec_path:
    cli_args.extend(["--spec", spec_path])
if author_vendor:
    cli_args.extend(["--author-vendor", author_vendor])
_, roster_plan, _, _ = run_node_cli(plugin_root, cli_args)
effective_mode = str(roster_plan.get("mode", review_mode)) if isinstance(roster_plan, dict) else review_mode
suppressions = list(roster_plan.get("suppressions", [])) if isinstance(roster_plan, dict) else []
suppression_clause = f" Respect verified false-positive suppressions: {suppressions}." if suppressions else ""

feedback_clause = ""
if spec_path:
    parts = [p for p in Path(spec_path).parts if p]
    flow_id_guess = ""
    if "specs" in parts:
        idx = parts.index("specs")
        if idx + 1 < len(parts):
            flow_id_guess = parts[idx + 1]
    if flow_id_guess:
        fb_code, fb_payload, _, _ = run_node_cli(
            plugin_root,
            ["spec", "feedback", "--flow", flow_id_guess, "--root", str(Path.cwd())],
        )
        if fb_code == 0 and isinstance(fb_payload, dict):
            open_notes = [c for c in fb_payload.get("comments", []) if isinstance(c, dict) and c.get("state") == "open"]
            if open_notes:
                snippets = [
                    f"[{c.get('commentKind', 'feedback')} L{c.get('startLine', 1)}] {c.get('body', '')}"
                    for c in open_notes[:10]
                ]
                feedback_clause = f" Open spec review notes to verify: {'; '.join(snippets)}."

before_status = git_porcelain()
phase("Independent Review")
log(f"Running {effective_mode} review on {git_range}{spec_clause} (preferred_model={preferred_review_model})")


def _resolve_seat_card(seat: dict) -> Path:
    """Resolve a review seat card path relative to ``plugin_root``."""
    raw_card = seat.get("card")
    if raw_card:
        candidate = Path(str(raw_card))
        return candidate if candidate.is_absolute() else plugin_root / candidate
    seat_id = str(seat.get("id") or "")
    if seat_id == "simplify":
        return simplify_card
    if "quality" in seat_id or seat.get("agent") == "quality-reviewer":
        return qual_card
    return code_card


async def _run_seat_with_fallback(
    prompt: str,
    role: str,
    agent_type: str,
    chosen_model: str,
    schema: dict | None = None,
) -> tuple[dict, str]:
    """Execute one read-only review seat with automatic quota fallback."""
    active_schema = schema if schema is not None else REVIEW_SCHEMA
    active_model = fallback_model if (quota_state["degraded"] and chosen_model != fallback_model) else chosen_model
    active_agent = "self" if quota_state["degraded"] else agent_type
    try:
        out = await with_budget(
            agent(
                prompt,
                schema=active_schema,
                role=role,
                type_name=active_agent,
                workspace="inherit",
                model=active_model,
            ),
            max_tokens=200000,
            timeout=timeout_seconds,
        )
        return out, active_model
    except Exception as exc:
        msg = str(exc).lower()
        if active_model != fallback_model and any(m in msg for m in QUOTA_MARKERS):
            quota_state["degraded"] = True
            log(f"Quota hit on {active_model} for {role}; retrying on '{fallback_model}'")
            out = await with_budget(
                agent(
                    prompt,
                    schema=active_schema,
                    role=f"{role} ({fallback_model} fallback)",
                    type_name="self",
                    workspace="inherit",
                    model=fallback_model,
                ),
                max_tokens=200000,
                timeout=timeout_seconds,
            )
            return out, fallback_model
        raise


def _build_simplify_prompt(target_ref: str) -> str:
    """Construct the read-only subtraction prompt without author rationales."""
    goal_line = (
        f" Pinned goal: {goal}."
        if goal
        else " Pinned goal: infer in 1 to 2 lines from the target before evaluating cuts."
    )
    return (
        f"Follow `{simplify_card}` in strictly read-only mode across `{target_ref}`{spec_clause}."
        f"{goal_line}{suppression_clause} "
        "Subtraction only: never propose new guards, retries, watchdogs, flags, wrappers, comments, or tests. "
        "Prove every negative claim with an untruncated repo-wide `git grep -n -F` check plus export, config, "
        "wire-schema, and dynamic-dispatch checks. Classify each cut as `equivalent` or `behavior_change`."
    )


reports: list[dict] = []
_wf_lease = acquire_runtime_lease()
try:
    seats = list(roster_plan.get("reviewers") or roster_plan.get("seats") or []) if isinstance(roster_plan, dict) else []
    if not seats:
        seats = [
            {"id": "code-reviewer", "title": "Correctness & Spec-Sync Review", "card": str(code_card), "model": preferred_review_model},
            {"id": "quality-reviewer", "title": "Quality & Debloat Review", "card": str(qual_card), "model": preferred_review_model},
        ]
    if effective_mode == "simplify":
        out, model_used = await _run_seat_with_fallback(
            _build_simplify_prompt(git_range),
            "Subtraction-Only Simplify Review",
            quality_reviewer_agent,
            preferred_review_model,
            schema=SIMPLIFY_SCHEMA,
        )
        reports = [{"reviewer": "simplify", "model_used": model_used, **out}]
    elif effective_mode == "single":
        out, model_used = await _run_seat_with_fallback(
            f"Follow `{code_card}` and `{qual_card}` in strictly read-only mode across `{git_range}`{spec_clause}.{suppression_clause}{feedback_clause}",
            "Combined Correctness & Quality Review",
            code_reviewer_agent,
            preferred_review_model,
        )
        reports = [{"reviewer": "combined", "model_used": model_used, **out}]
    else:

        async def _drive_seat(seat: dict) -> dict:
            """Run one independent review seat and normalize its fallback report."""
            used_model = str(
                args.get("reviewer_model")
                or seat.get("model")
                or (seat.get("model_route") or {}).get("runtime_target")
                or preferred_review_model
            )
            seat_id = str(seat.get("id") or "")
            is_simplify = seat_id == "simplify"
            seat_agent = (
                quality_reviewer_agent
                if is_simplify or "quality" in seat_id or seat.get("agent") == "quality-reviewer"
                else code_reviewer_agent
            )
            if is_simplify:
                out, model_used = await _run_seat_with_fallback(
                    _build_simplify_prompt(git_range),
                    str(seat.get("title") or "Subtraction-Only Simplify Review"),
                    seat_agent,
                    used_model,
                    schema=SIMPLIFY_SCHEMA,
                )
                return {"reviewer": seat_id, "model_used": model_used, **out}
            seat_card = _resolve_seat_card(seat)
            out, model_used = await _run_seat_with_fallback(
                (
                    f"Follow `{seat_card}` in strictly read-only mode as seat `{seat_id}` "
                    f"({seat.get('reason') or seat.get('title', seat_id)}) across `{git_range}`{spec_clause}.{suppression_clause}{feedback_clause}"
                ),
                str(seat.get("title") or seat.get("agent") or seat_id),
                seat_agent,
                used_model,
            )
            return {"reviewer": seat_id, "model_used": model_used, **out}

        raw_reports = await run_parallel_bounded(
            seats,
            _drive_seat,
            parallel_fn=parallel,
            max_concurrency=workers,
            return_exceptions=True,
        )
        for seat, item in zip(seats, raw_reports):
            if isinstance(item, Exception):
                reports.append(
                    {
                        "reviewer": seat.get("id", "reviewer"),
                        "model_used": preferred_review_model,
                        "verdict": "NEEDS_WORK",
                        "findings": [
                            {
                                "id": f"REV-ERR-{seat.get('id', 'seat')}",
                                "severity": "Important",
                                "category": "reviewer_error",
                                "file": spec_path or "git-diff",
                                "location": str(seat.get("id", "seat")),
                                "problem": f"Review seat crashed ({type(item).__name__}): {item}",
                                "fix": "Re-run failed review seat or verify diff manually.",
                            }
                        ],
                    }
                )
            else:
                reports.append(item)
finally:
    release_runtime_lease(_wf_lease)

after_status = git_porcelain()
print(
    json.dumps(
        {
            "git_range": git_range,
            "review_mode": effective_mode,
            "quota_degraded": quota_state["degraded"],
            "git_status_unchanged": before_status == after_status,
            "reports": reports,
            "tokens": tokens_used(),
        }
    )
)

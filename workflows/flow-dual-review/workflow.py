"""Orchestrate ReviewRoster-planned zero-context reviews with cross-vendor adversarial seats."""

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
    git_porcelain,
    release_runtime_lease,
    resolve_dynamic_route,
    resolve_plugin_root,
    run_node_cli,
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
harness = str(args.get("harness") or os.environ.get("FLOW_HARNESS") or "agy")
author_vendor = str(args.get("author_vendor") or "")
timeout_seconds = int(args.get("timeout_seconds", 600))
plugin_root = resolve_plugin_root(args.get("plugin_root"), marker="agents/code-reviewer.md")

route = resolve_dynamic_route(plugin_root, "spec_review", harness=harness, author_vendor=author_vendor or None)
preferred_review_model = str(args.get("reviewer_model") or os.environ.get("FLOW_REVIEWER_MODEL") or route["runtime_target"])
fallback_model = str(args.get("fallback_model") or os.environ.get("FLOW_FALLBACK_MODEL") or "flash")
code_reviewer_agent = str(args.get("code_reviewer_agent") or os.environ.get("FLOW_REVIEWER_AGENT") or "self")
quality_reviewer_agent = str(args.get("quality_reviewer_agent") or os.environ.get("FLOW_QUALITY_REVIEWER_AGENT") or code_reviewer_agent)

code_card = plugin_root / "agents" / "code-reviewer.md"
qual_card = plugin_root / "agents" / "quality-reviewer.md"
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

before_status = git_porcelain()
phase("Zero-Context Review")
log(f"Running {effective_mode} review on {git_range}{spec_clause} (preferred_model={preferred_review_model})")

reports: list[dict] = []
_wf_lease = acquire_runtime_lease()
try:
    seats = list(roster_plan.get("reviewers") or roster_plan.get("seats") or []) if isinstance(roster_plan, dict) else []
    if not seats:
        seats = [
            {"id": "code-reviewer", "title": "Correctness & Spec-Sync Review", "card": str(code_card), "model": preferred_review_model},
            {"id": "quality-reviewer", "title": "Quality & Debloat Review", "card": str(qual_card), "model": preferred_review_model},
        ]
    if effective_mode == "single":
        out = await with_budget(
            agent(
                f"Follow `{code_card}` and `{qual_card}` in strictly read-only mode across `{git_range}`{spec_clause}.{suppression_clause}",
                schema=REVIEW_SCHEMA,
                role="Combined Correctness & Quality Review",
                type_name=code_reviewer_agent,
                workspace="inherit",
                model=preferred_review_model,
            ),
            max_tokens=200000,
            timeout=timeout_seconds,
        )
        reports = [{"reviewer": "combined", "model_used": preferred_review_model, **out}]
    else:
        raw_reports = await parallel(
            seats,
            lambda seat: with_budget(
                agent(
                    (
                        f"Follow `{seat.get('card') or code_card}` in strictly read-only mode as seat `{seat['id']}` "
                        f"({seat.get('reason') or seat.get('title', seat['id'])}) across `{git_range}`{spec_clause}.{suppression_clause}"
                    ),
                    schema=REVIEW_SCHEMA,
                    role=str(seat.get("title") or seat.get("agent") or seat["id"]),
                    type_name=quality_reviewer_agent if "quality" in str(seat["id"]) or seat.get("agent") == "quality-reviewer" else code_reviewer_agent,
                    workspace="inherit",
                    model=str(
                        args.get("review_model")
                        or seat.get("model")
                        or (seat.get("model_route") or {}).get("runtime_target")
                        or preferred_review_model
                    ),
                ),
                max_tokens=200000,
                timeout=timeout_seconds,
            ),
        )
        for seat, out in zip(seats, raw_reports):
            used_model = (
                args.get("review_model")
                or seat.get("model")
                or (seat.get("model_route") or {}).get("runtime_target")
                or preferred_review_model
            )
            reports.append({"reviewer": seat["id"], "model_used": used_model, **out})
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

"""Orchestrate Flow chapter planning, seed prefetching, disk-idle completion recovery, OKF validation, and spec review."""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

_WF_PARENT = Path(__file__).resolve().parent.parent if "__file__" in globals() else Path.cwd() / "workflows"
if str(_WF_PARENT) not in sys.path:
    sys.path.insert(0, str(_WF_PARENT))

from flow_common import (
    QUOTA_MARKERS,
    acquire_runtime_lease,
    prefetch_seeds,
    release_runtime_lease,
    resolve_dynamic_route,
    resolve_plugin_root,
    run_parallel_bounded,
)

PLANNER_SCHEMA = {
    "type": "object",
    "properties": {
        "files_written": {"type": "array", "items": {"type": "string"}},
        "task_summaries": {"type": "array", "items": {"type": "string"}},
        "root_spec_issues": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["files_written", "task_summaries", "root_spec_issues"],
}

REVIEW_SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": ["APPROVED", "ISSUES_FOUND"]},
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "severity": {"type": "string", "enum": ["Critical", "Important", "Minor"]},
                    "category": {"type": "string"},
                    "file": {"type": "string"},
                    "location": {"type": "string"},
                    "problem": {"type": "string"},
                    "fix": {"type": "string"},
                },
                "required": ["id", "severity", "file", "location", "problem", "fix"],
            },
        },
    },
    "required": ["verdict", "findings"],
}

TASK_LINK_RE = re.compile(r"\((tasks/[^)\s]+\.md)\)")

flow_id = str(args["flow_id"])
chapters = list(args["chapters"])
seed_files = list(args.get("seed_files", []))
bundle_root = Path(str(args.get("bundle_root", ".agents/bundles")))
planner_mode_arg = str(args.get("planner_mode", "auto"))
worksheet_format = str(args.get("worksheet_format", "compact"))
review_mode = str(args.get("review", "single"))
run_mode = str(args.get("mode", "plan_and_review"))
max_review_rounds = int(args.get("max_review_rounds", 1))
harness = str(args.get("harness") or os.environ.get("FLOW_HARNESS") or "agy")
plugin_root = resolve_plugin_root(args.get("plugin_root"), marker="templates/agent/plan-schema-card.md")

plan_route = resolve_dynamic_route(plugin_root, "planning", harness=harness, risk="high")
rev_route = resolve_dynamic_route(plugin_root, "spec_review", harness=harness, risk="high")
preferred_planner_model = str(args.get("planner_model") or os.environ.get("FLOW_PLANNER_MODEL") or plan_route["runtime_target"] or "inherit")
preferred_reviewer_model = str(args.get("reviewer_model") or os.environ.get("FLOW_REVIEWER_MODEL") or rev_route["runtime_target"] or "inherit")
planner_agent = str(args.get("planner_agent") or os.environ.get("FLOW_PLANNER_AGENT") or "self")
reviewer_agent = str(args.get("reviewer_agent") or os.environ.get("FLOW_REVIEWER_AGENT") or "self")
planner_degraded_flag = bool(args.get("planner_degraded", False))
planner_timeout_s = int(args.get("planner_timeout_seconds", 900))
disk_idle_grace_s = int(args.get("disk_idle_grace_seconds", 45))
reviewer_timeout_s = int(args.get("reviewer_timeout_seconds", 600))
workers = max(1, min(12, int(args.get("workers") or 4)))

schema_card_path = plugin_root / "templates" / "agent" / "plan-schema-card.md"
reviewer_card_path = plugin_root / "templates" / "agent" / "spec-reviewer-prompt.md"
simplify_card_path = plugin_root / "templates" / "agent" / "simplify-card.md"
validator_script = plugin_root / "tools" / "validate.py"
flow_dir = bundle_root / "specs" / flow_id
chapters_dir = flow_dir / "chapters"

_is_fallback_model = bool(plan_route.get("degraded")) or preferred_planner_model in ("flash", "flash_lite", "sonnet", "haiku") or planner_degraded_flag
quota_state = {"degraded": _is_fallback_model}
degraded_reasons: list[str] = []
if _is_fallback_model:
    degraded_reasons.append(f"configured planner_model={preferred_planner_model!r} instead of the strongest model")


def _chapter_disk_status(ch_id: str) -> tuple[bool, list[str], float]:
    """Check whether spec.md, all listed task worksheets, and planner-notes.md exist for ``ch_id``."""
    ch_path = chapters_dir / ch_id
    spec_file = ch_path / "spec.md"
    notes_file = ch_path / "planner-notes.md"
    if not spec_file.is_file() or spec_file.stat().st_size == 0:
        return False, [], 0.0
    if not notes_file.is_file() or notes_file.stat().st_size == 0:
        return False, [], 0.0

    spec_text = spec_file.read_text(encoding="utf-8")
    task_rels = TASK_LINK_RE.findall(spec_text)
    if not task_rels:
        tasks_subdir = ch_path / "tasks"
        if tasks_subdir.is_dir():
            task_rels = [f"tasks/{p.name}" for p in sorted(tasks_subdir.glob("*.md")) if p.name != "index.md"]
    if not task_rels:
        return False, [], 0.0

    files_checked = [spec_file, notes_file]
    for rel_t in task_rels:
        tf = ch_path / rel_t
        if not tf.is_file() or tf.stat().st_size == 0:
            return False, [], 0.0
        files_checked.append(tf)

    latest_mtime = max(p.stat().st_mtime for p in files_checked)
    rel_written = [
        str(p.relative_to(bundle_root.parent.parent if bundle_root.is_relative_to(Path.cwd()) else bundle_root))
        for p in files_checked
    ]
    return True, rel_written, latest_mtime


def _parse_planner_notes(ch_id: str) -> tuple[list[str], list[str]]:
    """Extract task summaries and root_spec_issues from ``chapters/<ch_id>/planner-notes.md``."""
    notes_file = chapters_dir / ch_id / "planner-notes.md"
    if not notes_file.is_file():
        return [], []
    section = ""
    summaries: list[str] = []
    issues: list[str] = []
    for raw_line in notes_file.read_text(encoding="utf-8").splitlines():
        stripped = raw_line.strip()
        if stripped.startswith("## "):
            heading_lower = stripped[3:].strip().lower()
            if "task summar" in heading_lower:
                section = "summaries"
            elif "root spec issue" in heading_lower:
                section = "issues"
            else:
                section = "other"
            continue
        if not stripped.startswith(("-", "*")):
            continue
        item = stripped.lstrip("-*").strip()
        if not item or item.lower() in ("none", "none.", "n/a"):
            continue
        if section == "summaries":
            summaries.append(item)
        elif section == "issues":
            issues.append(item)
    return summaries, issues


def _stamp_degraded_frontmatter(spec_path: Path, reason: str, model_used: str) -> None:
    """Stamp ``planning_quality: degraded`` and ``planning_degraded_reason`` into ``spec_path``."""
    if not spec_path.is_file():
        return
    text = spec_path.read_text(encoding="utf-8").replace("\r\n", "\n")
    if not text.startswith("---\n"):
        return
    end_idx = text.find("\n---\n", 4)
    if end_idx == -1:
        return
    fm_lines = [
        ln
        for ln in text[4:end_idx].splitlines()
        if not ln.startswith(("planning_quality:", "planning_degraded_reason:", "planned_with_model:"))
    ]
    safe_reason = reason.replace('"', "'")
    fm_lines.append("planning_quality: degraded")
    fm_lines.append(f'planning_degraded_reason: "{safe_reason}"')
    fm_lines.append(f"planned_with_model: {model_used}")
    spec_path.write_text("---\n" + "\n".join(fm_lines) + text[end_idx:], encoding="utf-8")


async def _watch_disk_completion(ch_ids: list[str]) -> list[str] | None:
    """Poll disk until all ``ch_ids`` are complete and mtime-idle for ``disk_idle_grace_s`` seconds."""
    if disk_idle_grace_s <= 0:
        await asyncio.sleep(planner_timeout_s + 60)
        return None
    while True:
        await asyncio.sleep(5)
        all_ready = True
        newest = 0.0
        collected: list[str] = []
        for cid in ch_ids:
            ok, files_list, mtime = _chapter_disk_status(cid)
            if not ok:
                all_ready = False
                break
            collected.extend(files_list)
            if mtime > newest:
                newest = mtime
        if all_ready and newest > 0 and (time.time() - newest) >= disk_idle_grace_s:
            return collected


async def _invoke_planner(prompt: str, role: str, ch_ids: list[str]) -> dict:
    """Run a planner agent with quota fallback to flash (never flash_lite) and disk-idle recovery."""
    active_model = "flash" if quota_state["degraded"] else preferred_planner_model
    fallback_model = "flash" if active_model != "flash" else None

    async def _call_model(target_model: str, target_agent: str) -> dict:
        """Invoke the planner model and wait for agent completion or idle disk files."""
        agent_fut = asyncio.ensure_future(
            with_budget(
                agent(
                    prompt,
                    schema=PLANNER_SCHEMA,
                    role=role if target_model == preferred_planner_model else f"{role} ({target_model} fallback)",
                    type_name=target_agent,
                    workspace="inherit",
                    model=target_model,
                ),
                max_tokens=300000,
                timeout=planner_timeout_s,
            )
        )
        watcher_fut = asyncio.ensure_future(_watch_disk_completion(ch_ids))
        done, pending = await asyncio.wait({agent_fut, watcher_fut}, return_when=asyncio.FIRST_COMPLETED)
        for p in pending:
            p.cancel()
        for p in pending:
            try:
                await p
            except (asyncio.CancelledError, Exception):
                pass

        if agent_fut in done:
            res = agent_fut.result()
            return {
                "status": "completed",
                "completed_from_disk": False,
                "model_used": target_model,
                "result": res,
            }

        reason = f"planner stalled after writing all chapter files; recovered from disk after {disk_idle_grace_s}s idle"
        degraded_reasons.append(f"{','.join(ch_ids)}: {reason}")
        return {
            "status": "completed_from_disk",
            "completed_from_disk": True,
            "model_used": target_model,
            "degraded_reason": reason,
            "result": None,
        }

    try:
        return await _call_model(active_model, planner_agent)
    except BudgetExceeded as exc:
        reason = f"planner timed out ({exc})"
        degraded_reasons.append(f"{','.join(ch_ids)}: {reason}")
        return {
            "status": "timed_out",
            "completed_from_disk": False,
            "model_used": active_model,
            "degraded_reason": reason,
            "result": None,
        }
    except Exception as exc:
        msg = str(exc).lower()
        if fallback_model and any(m in msg for m in QUOTA_MARKERS):
            quota_state["degraded"] = True
            q_reason = (
                f"primary thinking model ({active_model}) hit quota/capacity; planned with fallback '{fallback_model}'"
            )
            degraded_reasons.append(q_reason)
            log(f"WARNING: {q_reason}")
            out = await _call_model(fallback_model, "self")
            out["degraded_reason"] = q_reason
            return out
        raise


def _build_chapter_prompt(ch_list: list[dict]) -> str:
    """Construct a compact planner prompt referencing only root spec, plan-schema-card.md, prefetched seeds, and chapter files."""
    blocks = []
    all_seed_paths: list[str] = [str(p) for p in seed_files]
    for ch in ch_list:
        reads = [str(p) for p in (ch.get("read_files") or [])]
        all_seed_paths.extend(reads)
        reads_line = f"Scoped source files: {reads}\n" if reads else ""
        blocks.append(f"Chapter `{ch['id']}` (`{chapters_dir / ch['id']}`):\n{reads_line}Brief: {ch['brief']}")
    prefetched = prefetch_seeds(all_seed_paths, globals().get("call_tool"), max_files=6, end_line=100)
    seed_section = f"\nPrefetched seed excerpts:\n{json.dumps(prefetched, ensure_ascii=False)}\n" if prefetched else ""
    joined_blocks = "\n\n".join(blocks)
    return (
        f"Author Flow chapter specification(s) and `{worksheet_format}` task worksheet(s) for flow `{flow_id}`.\n"
        f"1. Read ONLY `{flow_dir / 'spec.md'}`, `{schema_card_path}`, and the scoped chapter source files below.\n"
        "2. Do NOT read Flow plugin `skills/*/references/*.md`, do NOT edit production code, and do NOT pass BypassSandbox=true.\n"
        "3. Design small tasks (`<=250` LOC, `<=3` files per task) on separate files so parallel workers can run together.\n"
        "4. Follow OKF v0.2 strictly: `status: draft`, workflow `state: planned`, `<= 40`-line `<!-- truth: start -->` "
        "block, `sources:` with matching `[^id]:` body footnotes, and all required headings.\n"
        "5. Write `chapters/<id>/planner-notes.md` BEFORE calling finish.\n"
        f"{seed_section}\n"
        f"{joined_blocks}"
    )


def _run_okf_validator() -> list[str]:
    """Run deterministic tools/validate.py against ``flow_id`` and return any error lines."""
    if not validator_script.is_file():
        return []
    proc = subprocess.run(
        [sys.executable, str(validator_script), "--bundle", str(bundle_root), "--flow", flow_id],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if proc.returncode == 0:
        return []
    return [ln.strip() for ln in (proc.stderr + "\n" + proc.stdout).splitlines() if ln.strip().startswith("ERROR:")]


chapter_reports: list[dict] = []
okf_errors: list[str] = []
review_reports: list[dict] = []
review_skipped_reason: str | None = None
all_complete = False
all_root_issues: list[str] = []
effective_planner_mode = (
    ("single_batch" if len(chapters) <= 1 else "per_chapter") if planner_mode_arg == "auto" else planner_mode_arg
)

_wf_lease = acquire_runtime_lease()
try:
    if run_mode in ("plan_and_review", "plan_only"):
        phase("Chapter Planning")
        log(f"Planning {len(chapters)} chapter(s) for {flow_id} in {effective_planner_mode} mode")
        if effective_planner_mode == "single_batch":
            batch_out = await _invoke_planner(
                _build_chapter_prompt(chapters),
                f"Chapter Planner ({len(chapters)} ch)",
                [str(c["id"]) for c in chapters],
            )
            raw_res = batch_out.get("result") or {}
            for ch in chapters:
                cid = str(ch["id"])
                ok_disk, disk_files, _ = _chapter_disk_status(cid)
                disk_summaries, disk_issues = _parse_planner_notes(cid)
                chapter_reports.append(
                    {
                        "chapter_id": cid,
                        "complete_on_disk": ok_disk,
                        "completed_from_disk": bool(batch_out.get("completed_from_disk")),
                        "model_used": batch_out.get("model_used", preferred_planner_model),
                        "degraded_reason": batch_out.get("degraded_reason"),
                        "files_written": disk_files or list(raw_res.get("files_written", [])),
                        "task_summaries": disk_summaries or list(raw_res.get("task_summaries", [])),
                        "root_spec_issues": disk_issues or list(raw_res.get("root_spec_issues", [])),
                    }
                )
        else:
            raw_parallel = await run_parallel_bounded(
                chapters,
                lambda ch: _invoke_planner(
                    _build_chapter_prompt([ch]),
                    f"Chapter Planner {ch['id']}",
                    [str(ch["id"])],
                ),
                parallel_fn=parallel,
                max_concurrency=workers,
                return_exceptions=True,
            )
            for ch, item_out in zip(chapters, raw_parallel):
                cid = str(ch["id"])
                if isinstance(item_out, Exception):
                    ok_disk, disk_files, _ = _chapter_disk_status(cid)
                    disk_summaries, disk_issues = _parse_planner_notes(cid)
                    chapter_reports.append(
                        {
                            "chapter_id": cid,
                            "complete_on_disk": ok_disk,
                            "completed_from_disk": False,
                            "model_used": preferred_planner_model,
                            "degraded_reason": f"planner failed ({type(item_out).__name__}): {item_out}",
                            "files_written": disk_files,
                            "task_summaries": disk_summaries,
                            "root_spec_issues": disk_issues or [f"Planner crashed ({type(item_out).__name__}): {item_out}"],
                        }
                    )
                    continue
                raw_res = item_out.get("result") or {}
                ok_disk, disk_files, _ = _chapter_disk_status(cid)
                disk_summaries, disk_issues = _parse_planner_notes(cid)
                chapter_reports.append(
                    {
                        "chapter_id": cid,
                        "complete_on_disk": ok_disk,
                        "completed_from_disk": bool(item_out.get("completed_from_disk")),
                        "model_used": item_out.get("model_used", preferred_planner_model),
                        "degraded_reason": item_out.get("degraded_reason"),
                        "files_written": disk_files or list(raw_res.get("files_written", [])),
                        "task_summaries": disk_summaries or list(raw_res.get("task_summaries", [])),
                        "root_spec_issues": disk_issues or list(raw_res.get("root_spec_issues", [])),
                    }
                )
    else:
        for ch in chapters:
            cid = str(ch["id"])
            ok_disk, disk_files, _ = _chapter_disk_status(cid)
            disk_summaries, disk_issues = _parse_planner_notes(cid)
            chapter_reports.append(
                {
                    "chapter_id": cid,
                    "complete_on_disk": ok_disk,
                    "completed_from_disk": False,
                    "model_used": preferred_planner_model,
                    "degraded_reason": None,
                    "files_written": disk_files,
                    "task_summaries": disk_summaries,
                    "root_spec_issues": disk_issues,
                }
            )

    phase("Completion & Spec Validation")
    if degraded_reasons:
        combined_reason = "; ".join(dict.fromkeys(degraded_reasons))
        _stamp_degraded_frontmatter(
            flow_dir / "spec.md", combined_reason, "flash" if quota_state["degraded"] else preferred_planner_model
        )
        for rep in chapter_reports:
            if rep.get("degraded_reason") or quota_state["degraded"]:
                _stamp_degraded_frontmatter(
                    chapters_dir / rep["chapter_id"] / "spec.md",
                    str(rep.get("degraded_reason") or combined_reason),
                    str(rep.get("model_used", "flash")),
                )

    okf_errors = _run_okf_validator()
    if okf_errors and run_mode != "review_only":
        log(f"Spec validation caught {len(okf_errors)} issue(s); running targeted repair turn")
        repair_prompt = (
            f"Fix these exact OKF v0.2 validation errors under `{flow_dir}` without truncating contracts or "
            f"editing production code (follow `{schema_card_path}`):\n" + "\n".join(okf_errors)
        )
        await with_budget(
            agent(
                repair_prompt,
                schema={"type": "string"},
                role="OKF Schema Repair",
                type_name=planner_agent,
                workspace="inherit",
                model="flash" if quota_state["degraded"] else preferred_planner_model,
            ),
            max_tokens=100000,
            timeout=300,
        )
        okf_errors = _run_okf_validator()

    all_complete = all(bool(r["complete_on_disk"]) for r in chapter_reports)
    all_root_issues = [iss for r in chapter_reports for iss in r["root_spec_issues"]]

    if run_mode == "plan_only" or review_mode == "none" or max_review_rounds <= 0:
        review_skipped_reason = "disabled_by_args"
    elif not all_complete:
        review_skipped_reason = "incomplete_chapters"
    elif okf_errors:
        review_skipped_reason = "okf_validation_failed"
    elif all_root_issues and run_mode != "review_only":
        review_skipped_reason = "root_spec_issues_pending"
    else:
        phase("Independent Spec Review")
        rev_model = (
            "flash" if (quota_state["degraded"] and preferred_reviewer_model != "flash") else preferred_reviewer_model
        )

        async def _run_spec_reviewer(scope_name: str, prompt_text: str) -> dict:
            """Run one independent spec review pass."""
            active_rev = "flash" if (quota_state["degraded"] and rev_model != "flash") else rev_model
            active_rev_agent = "self" if quota_state["degraded"] else reviewer_agent
            try:
                out = await with_budget(
                    agent(
                        prompt_text,
                        schema=REVIEW_SCHEMA,
                        role=f"Spec Review ({scope_name})",
                        type_name=active_rev_agent,
                        workspace="inherit",
                        model=active_rev,
                    ),
                    max_tokens=200000 if scope_name == "combined" else 160000,
                    timeout=reviewer_timeout_s,
                )
                return {"scope": scope_name, "agent_used": active_rev_agent, "model_used": active_rev, **out}
            except Exception as exc:
                msg = str(exc).lower()
                if active_rev != "flash" and any(m in msg for m in QUOTA_MARKERS):
                    quota_state["degraded"] = True
                    log(f"Quota hit on {active_rev} for Spec Review ({scope_name}); retrying on 'flash'")
                    out = await with_budget(
                        agent(
                            prompt_text,
                            schema=REVIEW_SCHEMA,
                            role=f"Spec Review ({scope_name}, flash fallback)",
                            type_name="self",
                            workspace="inherit",
                            model="flash",
                        ),
                        max_tokens=200000 if scope_name == "combined" else 160000,
                        timeout=reviewer_timeout_s,
                    )
                    return {"scope": scope_name, "model_used": "flash", **out}
                raise

        if review_mode == "single":
            rev_prompt = (
                f"Follow `{reviewer_card_path}` and `{schema_card_path}` (plus the subtraction lens in `{simplify_card_path}`) "
                f"in strictly read-only mode (never pass BypassSandbox=true). Audit root `{flow_dir / 'spec.md'}`, "
                f"`{chapters_dir / 'index.md'}`, and all chapters {[c['id'] for c in chapters]} under `{chapters_dir}` "
                "in a single combined pass, flagging unearned chapters, wrappers, or speculative flags that can be cut or merged."
            )
            review_reports.append(await _run_spec_reviewer("combined", rev_prompt))
        else:
            targets = [*[str(c["id"]) for c in chapters], "cross_chapter"]
            raw_reviews = await run_parallel_bounded(
                targets,
                lambda target: _run_spec_reviewer(
                    target,
                    (
                        f"Follow `{reviewer_card_path}` and `{schema_card_path}` (plus `{simplify_card_path}`) "
                        f"in strictly read-only mode. Review `{flow_dir / 'spec.md'}` and scope `{target}` under "
                        f"`{chapters_dir}`, flagging unearned chapters, wrappers, or speculative flags that can be cut or merged."
                    ),
                ),
                parallel_fn=parallel,
                max_concurrency=workers,
                return_exceptions=True,
            )
            for target, rev_out in zip(targets, raw_reviews):
                if isinstance(rev_out, Exception):
                    review_reports.append(
                        {
                            "target": target,
                            "model_used": preferred_reviewer_model,
                            "verdict": "ISSUES_FOUND",
                            "findings": [
                                {
                                    "id": f"REV-ERR-{target}",
                                    "severity": "Important",
                                    "category": "reviewer_error",
                                    "file": str(flow_dir / "spec.md"),
                                    "location": target,
                                    "problem": f"Spec reviewer crashed ({type(rev_out).__name__}): {rev_out}",
                                    "fix": f"Re-run independent spec review for scope `{target}`.",
                                }
                            ],
                        }
                    )
                else:
                    review_reports.append(rev_out)
finally:
    release_runtime_lease(_wf_lease)

planning_quality = "degraded" if degraded_reasons else "standard"
planning_warning = (
    "WARNING: Specification was NOT planned with the strongest model ("
    + "; ".join(dict.fromkeys(degraded_reasons))
    + "). Surface this warning to the user before approval."
    if planning_quality == "degraded"
    else None
)

report = {
    "flow_id": flow_id,
    "planner_mode": effective_planner_mode,
    "planning_quality": planning_quality,
    "planning_warning": planning_warning,
    "degraded_reasons": list(dict.fromkeys(degraded_reasons)),
    "all_chapters_complete": all_complete,
    "needs_root_sync": bool(all_root_issues),
    "root_spec_issues": all_root_issues,
    "okf_validation_errors": okf_errors,
    "chapters": chapter_reports,
    "review_skipped_reason": review_skipped_reason,
    "reviews": review_reports,
    "tokens": tokens_used(),
}
print(json.dumps(report))

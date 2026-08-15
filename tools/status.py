"""Render a progress dashboard over the OKF spec bundles.

Dev/CI utility for the Flow repo itself. Runtime agents build the same
dashboard inline from the bundle files; see the flow-sync-status skill.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(os.environ.get("FLOW_REPO_ROOT", Path(__file__).resolve().parents[1]))

SPEC_ACTIVE_STATES = ("planned", "active")

NOTE_LINE_PATTERN = re.compile(r"^\s*-\s*\[(.*?)\]\s*(.*)$")


def _parse_yaml_frontmatter(content: str) -> tuple[dict[str, Any] | None, int]:
    content = content.replace("\r\n", "\n")
    if not content.startswith("---\n"):
        return None, 0
    parts = content.split("---\n", 2)
    if len(parts) < 3:
        return None, 0
    try:
        data = yaml.safe_load(parts[1])
    except yaml.YAMLError:
        return None, 0
    if not isinstance(data, dict):
        return None, 0
    return data, len(content) - len(parts[2])


def _task_state(task_data: dict[str, Any]) -> str:
    return task_data.get("state") or task_data.get("status") or "open"


def _extract_notes(content: str, fm_len: int, task_id: str) -> list[dict[str, str]]:
    body = content[fm_len:]
    notes: list[dict[str, str]] = []

    heading_match = re.search(r"^##\s+Notes\s+&\s+Discoveries\b", body, re.MULTILINE | re.IGNORECASE)
    if not heading_match:
        return []

    start_idx = heading_match.end()
    # Notes block continues until next heading or end of file
    next_heading = re.search(r"^#", body[start_idx:], re.MULTILINE)
    notes_block = body[start_idx:start_idx + next_heading.start()] if next_heading else body[start_idx:]

    for line in notes_block.splitlines():
        match = NOTE_LINE_PATTERN.match(line)
        if match:
            notes.append({
                "timestamp": match.group(1).strip(),
                "text": match.group(2).strip(),
                "task_id": task_id,
            })
    return notes


def generate_status_dashboard(repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    specs_dir = repo_root / ".agents" / "bundles" / "specs"
    if not specs_dir.is_dir():
        return {
            "active_flows_count": 0,
            "flows": {},
            "recent_notes": [],
        }

    flows_info: dict[str, Any] = {}
    all_notes: list[dict[str, str]] = []

    for spec_dir in specs_dir.iterdir():
        if not spec_dir.is_dir():
            continue
        spec_file = spec_dir / "spec.md"
        if not spec_file.is_file():
            continue

        try:
            content = spec_file.read_text(encoding="utf-8")
            spec_data, fm_len = _parse_yaml_frontmatter(content)
            if not spec_data:
                continue
            if (spec_data.get("state") or spec_data.get("status")) not in SPEC_ACTIVE_STATES:
                continue

            flow_id = spec_data.get("flow_id") or spec_dir.name

            tasks: dict[str, dict[str, Any]] = {}
            if (tasks_dir := spec_dir / "tasks").is_dir():
                for task_file in sorted(tasks_dir.glob("*.md")):
                    task_content = task_file.read_text(encoding="utf-8")
                    task_data, t_fm_len = _parse_yaml_frontmatter(task_content)
                    if not task_data:
                        continue
                    short_id = task_file.stem
                    t_id = task_data.get("id") or f"{flow_id}:{short_id}"
                    tasks[short_id] = {
                        "id": t_id,
                        "short_id": short_id,
                        "state": _task_state(task_data),
                        "depends_on": task_data.get("depends_on") or [],
                        "file_path": task_file,
                    }
                    all_notes.extend(_extract_notes(task_content, t_fm_len, t_id))

            total_tasks = len(tasks)
            closed_count = sum(1 for t in tasks.values() if t["state"] == "closed")
            skipped_count = sum(1 for t in tasks.values() if t["state"] == "skipped")

            denom = total_tasks - skipped_count
            progress = (closed_count / denom * 100.0) if denom > 0 else 0.0

            active_tasks: list[str] = []
            ready_queue: list[str] = []
            blocked_queue: list[str] = []

            for short_id, t_info in tasks.items():
                state = t_info["state"]
                if state == "in_progress":
                    active_tasks.append(short_id)
                elif state == "open":
                    is_ready = True
                    for dep in t_info["depends_on"]:
                        # depends_on carries short ids; tolerate legacy full ids
                        dep_short = str(dep).rsplit(":", 1)[-1]
                        dep_task = tasks.get(dep_short)
                        if not dep_task or dep_task["state"] != "closed":
                            is_ready = False
                            break
                    if is_ready:
                        ready_queue.append(short_id)
                    else:
                        blocked_queue.append(short_id)
                elif state == "blocked":
                    blocked_queue.append(short_id)

            flows_info[flow_id] = {
                "total_tasks": total_tasks,
                "closed_count": closed_count,
                "skipped_count": skipped_count,
                "progress_percentage": round(progress, 1),
                "active_tasks": sorted(active_tasks),
                "ready_queue": sorted(ready_queue),
                "blocked_queue": sorted(blocked_queue),
            }
        except (OSError, ValueError, yaml.YAMLError) as exc:
            print(f"warning: skipping malformed spec bundle {spec_dir.name}: {exc}", file=sys.stderr)
            continue

    # ISO timestamp comparison works lexicographically if standard format is used
    all_notes.sort(key=lambda note: note["timestamp"], reverse=True)
    recent_notes = all_notes[:5]

    return {
        "active_flows_count": len(flows_info),
        "flows": flows_info,
        "recent_notes": recent_notes,
    }


def print_dashboard(dashboard: dict[str, Any]) -> None:
    if dashboard["active_flows_count"] == 0:
        print("No active flows.")
        return

    print("================================================================================")
    print("                           DEVELOPER STATUS DASHBOARD                           ")
    print("================================================================================")
    print(f"Active Flows: {dashboard['active_flows_count']}\n")

    for flow_id, flow_info in dashboard["flows"].items():
        progress = flow_info["progress_percentage"]
        bar_len = int(progress / 5)
        bar = "█" * bar_len + "░" * (20 - bar_len)
        print(f"Flow: {flow_id} [{bar}] {progress}%")
        print(f"  Tasks: {flow_info['closed_count']}/{flow_info['total_tasks']} closed (skipped: {flow_info['skipped_count']})")
        if flow_info["active_tasks"]:
            print(f"  Active Task(s): {', '.join(flow_info['active_tasks'])}")

        if flow_info["ready_queue"]:
            print(f"  Ready Queue (next up): {', '.join(flow_info['ready_queue'])}")

        if flow_info["blocked_queue"]:
            print(f"  Blocked Queue: {', '.join(flow_info['blocked_queue'])}")
        print()

    print("--------------------------------------------------------------------------------")
    print("Recent Notes & Discoveries:")
    if dashboard["recent_notes"]:
        for note in dashboard["recent_notes"]:
            print(f"  [{note['timestamp']}] ({note['task_id']}): {note['text']}")
    else:
        print("  No recent notes.")
    print("--------------------------------------------------------------------------------")

    print("\nNext Recommendations:")
    has_recommendation = False
    for flow_id, flow_info in dashboard["flows"].items():
        if flow_info["active_tasks"]:
            print(f"  [{flow_id}]: Continue working on active task(s): {', '.join(flow_info['active_tasks'])}")
            has_recommendation = True
        elif flow_info["ready_queue"]:
            print(f"  [{flow_id}]: Claim and start next ready task: {flow_info['ready_queue'][0]}")
            has_recommendation = True
        elif flow_info["blocked_queue"]:
            print(f"  [{flow_id}]: Investigate blocked dependencies to unblock tasks: {', '.join(flow_info['blocked_queue'])}")
            has_recommendation = True

    if not has_recommendation:
        print("  All tasks completed. Propose docs updates or archive completed flows.")
    print("================================================================================")


if __name__ == "__main__":
    print_dashboard(generate_status_dashboard(REPO_ROOT))

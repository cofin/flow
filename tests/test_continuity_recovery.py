"""Direct-read continuity scenarios that do not depend on installed runtimes."""

from __future__ import annotations

import json
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
STATE_REFERENCE = REPO_ROOT / "skills" / "flow" / "references" / "state.md"
NONTERMINAL = {
    "prepared",
    "task_writes_started",
    "recovery_required",
    "rollback_in_progress",
}


def _frontmatter(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    assert text.startswith("---\n")
    raw = text.split("---\n", 2)[1]
    values: dict[str, object] = {}
    for line in raw.splitlines():
        if ":" not in line:
            continue
        key, raw_value = line.split(":", 1)
        value = raw_value.strip().strip('"')
        if value == "null":
            values[key] = None
        elif value.startswith("["):
            values[key] = json.loads(value)
        else:
            values[key] = value
    return values


def _roots(repo: Path) -> tuple[Path, Path]:
    configured = repo / ".agents"
    setup = repo / ".agents" / "setup-state.json"
    if setup.is_file():
        configured = (
            repo / json.loads(setup.read_text(encoding="utf-8"))["root_directory"]
        )
    bundle = configured / "bundles"
    config = configured / "config.json"
    if config.is_file():
        bundle = (
            configured / json.loads(config.read_text(encoding="utf-8"))["bundles_dir"]
        )
    return configured, bundle


def _direct_reconstruct(repo: Path) -> dict[str, object]:
    configured, bundle = _roots(repo)
    journals = []
    for path in sorted((configured / "tasks" / "transactions").glob("*/journal.md")):
        values = _frontmatter(path)
        if values.get("state") in NONTERMINAL:
            values["path"] = path
            journals.append(values)

    applied = [item for item in journals if item.get("applied_writes") != []]
    if len(applied) > 1:
        return {
            "result": "conflict",
            "candidates": [item["operation_id"] for item in applied],
        }
    if applied:
        selected = applied[0]
        action = selected.get("recovery_selected") or "finish|rollback"
        return {
            "result": "recovery_required",
            "operation": "recover",
            "action": action,
            "flow_id": selected["flow_id"],
            "flow_root": repo / str(selected["flow_root"]),
        }
    if journals:
        return {
            "result": "arbitration_required",
            "candidates": [item["operation_id"] for item in journals],
        }

    specs = sorted((bundle / "specs").glob("*/spec.md"))
    active = [path for path in specs if _frontmatter(path).get("state") == "active"]
    assert len(active) == 1
    spec = _frontmatter(active[0])
    tasks = sorted((active[0].parent / "tasks").glob("*.md"))
    task_rows = [_frontmatter(path) for path in tasks]
    if any(
        row.get("plan_revision") != spec.get("plan_revision")
        or row.get("plan_commit") != spec.get("plan_commit")
        or int(str(row.get("state_revision", "0")))
        > int(str(spec.get("state_revision", "0")))
        for row in task_rows
    ):
        return {"result": "refused", "reason": "stale_identity"}
    claims = [row for row in task_rows if row.get("state") == "in_progress"]
    if len(claims) > 1 or (claims and claims[0].get("id") != spec.get("current_task")):
        return {"result": "refused", "reason": "claim_conflict"}
    blockers = [row["id"] for row in task_rows if row.get("state") == "blocked"]
    return {
        "result": "active",
        "flow_id": spec["flow_id"],
        "task": claims[0]["id"] if claims else None,
        "blockers": blockers,
    }


def _write_active_flow(
    repo: Path, *, custom: bool, crlf: bool = False
) -> tuple[Path, Path]:
    configured = repo / (".flow-local" if custom else ".agents")
    if custom:
        (repo / ".agents").mkdir(parents=True)
        (repo / ".agents" / "setup-state.json").write_text(
            json.dumps({"root_directory": ".flow-local"}), encoding="utf-8"
        )
        configured.mkdir()
        (configured / "config.json").write_text(
            json.dumps({"bundles_dir": "okf-data"}), encoding="utf-8"
        )
        bundle = configured / "okf-data"
    else:
        bundle = configured / "bundles"
    flow = bundle / "specs" / "demo"
    (flow / "tasks").mkdir(parents=True)
    newline = "\r\n" if crlf else "\n"
    (flow / "spec.md").write_text(
        newline.join(
            (
                "---",
                "type: Spec",
                "flow_id: demo",
                "state: active",
                "plan_revision: 2",
                "plan_commit: abc1234",
                "state_revision: 4",
                "current_task: demo:1.1",
                "---",
                "# Demo",
                "",
            )
        ),
        encoding="utf-8",
    )
    (flow / "tasks" / "1.1.md").write_text(
        newline.join(
            (
                "---",
                "type: Task",
                "id: demo:1.1",
                "state: in_progress",
                "plan_revision: 2",
                "plan_commit: abc1234",
                "state_revision: 4",
                "---",
                "# Task 1.1",
                "",
            )
        ),
        encoding="utf-8",
    )
    return configured, flow


def _write_journal(
    configured: Path,
    operation_id: str,
    *,
    state: str,
    applied: list[str],
    flow_root: str,
    selected: str | None = None,
) -> None:
    directory = configured / "tasks" / "transactions" / operation_id
    directory.mkdir(parents=True)
    selected_line = f"recovery_selected: {selected}\n" if selected else ""
    (directory / "journal.md").write_text(
        "---\n"
        f"operation_id: {operation_id}\n"
        f"state: {state}\n"
        "flow_id: archived-demo\n"
        f"flow_root: {flow_root}\n"
        f"applied_writes: {json.dumps(applied)}\n"
        f"{selected_line}"
        "---\n",
        encoding="utf-8",
    )


@pytest.mark.parametrize("custom", [False, True], ids=["default", "custom-root"])
@pytest.mark.parametrize("crlf", [False, True], ids=["lf", "crlf"])
def test_forward_reader_reconstructs_active_claim_without_hooks(
    custom: bool, crlf: bool, tmp_path: Path
) -> None:
    _write_active_flow(tmp_path, custom=custom, crlf=crlf)
    assert _direct_reconstruct(tmp_path) == {
        "result": "active",
        "flow_id": "demo",
        "task": "demo:1.1",
        "blockers": [],
    }


def test_stale_identity_fails_closed(tmp_path: Path) -> None:
    _, flow = _write_active_flow(tmp_path, custom=False)
    task = flow / "tasks" / "1.1.md"
    task.write_text(
        task.read_text(encoding="utf-8").replace(
            "plan_commit: abc1234", "plan_commit: stale99"
        ),
        encoding="utf-8",
    )
    assert _direct_reconstruct(tmp_path) == {
        "result": "refused",
        "reason": "stale_identity",
    }


def test_blocked_task_is_reported_without_selection(tmp_path: Path) -> None:
    _, flow = _write_active_flow(tmp_path, custom=False)
    spec = flow / "spec.md"
    spec.write_text(
        spec.read_text(encoding="utf-8").replace(
            "current_task: demo:1.1", "current_task: null"
        ),
        encoding="utf-8",
    )
    task = flow / "tasks" / "1.1.md"
    task.write_text(
        task.read_text(encoding="utf-8").replace(
            "state: in_progress", "state: blocked"
        ),
        encoding="utf-8",
    )
    assert _direct_reconstruct(tmp_path) == {
        "result": "active",
        "flow_id": "demo",
        "task": None,
        "blockers": ["demo:1.1"],
    }


def test_journal_first_recovers_deleted_archive_under_custom_roots(
    tmp_path: Path,
) -> None:
    configured, flow = _write_active_flow(tmp_path, custom=True)
    for path in sorted(flow.rglob("*"), reverse=True):
        if path.is_file():
            path.unlink()
        else:
            path.rmdir()
    flow.rmdir()
    _write_journal(
        configured,
        "20260814T120000Z-agent-archive-archived-demo-00",
        state="recovery_required",
        applied=["spec.md"],
        flow_root=".flow-local/okf-data/specs/archived-demo",
        selected="rollback",
    )
    _write_journal(
        configured,
        "20260814T120001Z-agent-claim-other-00",
        state="prepared",
        applied=[],
        flow_root=".flow-local/okf-data/specs/other",
    )

    result = _direct_reconstruct(tmp_path)
    assert result["result"] == "recovery_required"
    assert result["operation"] == "recover"
    assert result["action"] == "rollback"
    assert result["flow_root"] == tmp_path / ".flow-local/okf-data/specs/archived-demo"
    assert ".agents/bundles" not in str(result["flow_root"])


def test_multiple_applied_journals_fail_closed(tmp_path: Path) -> None:
    configured, _ = _write_active_flow(tmp_path, custom=False)
    for index in range(2):
        _write_journal(
            configured,
            f"20260814T12000{index}Z-agent-close-demo-{index:02d}",
            state="recovery_required",
            applied=["tasks/1.1.md"],
            flow_root=".agents/bundles/specs/demo",
        )
    result = _direct_reconstruct(tmp_path)
    assert result["result"] == "conflict"
    assert len(result["candidates"]) == 2


def test_state_reference_is_the_single_direct_read_authority() -> None:
    text = STATE_REFERENCE.read_text(encoding="utf-8")
    contract = text.split("## Direct-read continuity contract", 1)[1].split(
        "## File-tool transaction protocol", 1
    )[0]
    assert "After compaction, handoff, or session loss" in contract
    assert [
        line.split(".", 1)[0]
        for line in contract.splitlines()
        if _is_numbered_step(line)
    ] == [
        "1",
        "2",
        "3",
        "4",
        "5",
        "6",
    ]
    assert "Installed hooks/plugins may only emit static routing" in contract


def _is_numbered_step(line: str) -> bool:
    return len(line) > 2 and line[0].isdigit() and line[1:3] == ". "

"""Behavioral validation for executable Flow plans and continuity state."""

from __future__ import annotations

import importlib.util
import json
import shutil
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = REPO_ROOT / "tests" / "fixtures" / "okf" / "continuity"


def _load_validate_module():
    spec = importlib.util.spec_from_file_location(
        "validate_flow_plan_quality", REPO_ROOT / "tools" / "validate.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


validate = _load_validate_module()


def _fixture(tmp_path: Path) -> tuple[Path, Path]:
    shutil.copytree(FIXTURE_ROOT, tmp_path, dirs_exist_ok=True)
    bundle = tmp_path / ".agents" / "bundles" / "specs" / "demo-flow"
    return tmp_path, bundle


def _replace(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    assert old in text
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def _messages(violations) -> str:
    return "\n".join(
        f"{item.path.as_posix()}:{item.line}: {item.message}" for item in violations
    )


def test_complete_executable_plan_and_continuity_pass(tmp_path: Path) -> None:
    root, bundle = _fixture(tmp_path)
    assert validate.validate_okf_bundle(bundle, root) == []


@pytest.mark.parametrize(
    ("mutation", "expected"),
    [
        (
            (
                "## Steps\n1. Add a failing continuation scenario.\n2. Implement the continuation behavior.\n",
                "## Steps\nTODO\n",
            ),
            "Steps",
        ),
        (
            (
                "## Verification\nRun `pytest tests/test_continuation.py` and require a passing result.\n",
                "## Verification\nTest it.\n",
            ),
            "Verification",
        ),
        (
            (
                "## Acceptance Criteria\n- The continuation behavior is observable.\n",
                "## Acceptance Criteria\n- Works correctly.\n",
            ),
            "Acceptance Criteria",
        ),
    ],
)
def test_layout_valid_stub_cannot_pass_plan_validation(
    tmp_path: Path, mutation: tuple[str, str], expected: str
) -> None:
    root, bundle = _fixture(tmp_path)
    _replace(bundle / "tasks" / "1.2.md", *mutation)
    violations = validate.validate_okf_bundle(bundle, root)
    assert expected in _messages(violations)


def test_vague_language_is_scoped_to_executable_worksheet_fields(
    tmp_path: Path,
) -> None:
    root, bundle = _fixture(tmp_path)
    task = bundle / "tasks" / "1.2.md"
    task.write_text(
        task.read_text(encoding="utf-8")
        + "\n> Historical quote: TODO maybe handle this later.\n"
        + "\n## Notes & Discoveries\n- [2026-08-14 12:01] TODO appeared in rejected input.\n",
        encoding="utf-8",
    )
    assert validate.validate_okf_bundle(bundle, root) == []


@pytest.mark.parametrize(
    ("old", "new", "section"),
    [
        (
            "## Objective\nDeliver a visible continuation behavior.\n",
            "## Objective\nImprove the code as needed.\n",
            "Objective",
        ),
        (
            "## Steps\n1. Add a failing continuation scenario.\n2. Implement the continuation behavior.\n",
            "## Steps\n1. Implement the thing.\n",
            "Steps",
        ),
        (
            "## Verification\nRun `pytest tests/test_continuation.py` and require a passing result.\n",
            "## Verification\nRun `pytest` and verify it.\n",
            "Verification",
        ),
        (
            "## Acceptance Criteria\n- The continuation behavior is observable.\n",
            "## Acceptance Criteria\n- The change is done.\n",
            "Acceptance Criteria",
        ),
    ],
)
def test_placeholder_only_worksheet_bodies_are_not_executable(
    tmp_path: Path, old: str, new: str, section: str
) -> None:
    root, bundle = _fixture(tmp_path)
    _replace(bundle / "tasks" / "1.2.md", old, new)
    assert section in _messages(validate.validate_okf_bundle(bundle, root))


def test_null_current_task_requires_snapshot_claim_none(tmp_path: Path) -> None:
    root, bundle = _fixture(tmp_path)
    spec = bundle / "spec.md"
    task = bundle / "tasks/1.2.md"
    _replace(spec, 'current_task: "1.2"', "current_task: null")
    _replace(task, "state: in_progress", "state: open")
    _replace(task, "claimed_by: flow-executor", "claimed_by: null")
    _replace(task, "claimed_at: 2026-08-14T12:00:00Z", "claimed_at: null")

    messages = _messages(validate.validate_okf_bundle(bundle, root))
    assert "snapshot current task/claim must be none" in messages


@pytest.mark.parametrize(
    ("scope", "targets", "expected"),
    [
        ("phase", ["1.2"], "phase checkpoint is spec-only"),
        ("task", [], "task checkpoint targets disagree"),
        ("plan", ["1.2"], "plan checkpoint targets disagree"),
    ],
)
def test_checkpoint_scope_controls_operation_targets(
    tmp_path: Path, scope: str, targets: list[str], expected: str
) -> None:
    root, bundle = _fixture(tmp_path)
    operation_id = "20260814T121000Z-flow-executor-checkpoint-spec-00"
    spec = bundle / "spec.md"
    _replace(
        spec,
        "last_operation: 20260814T120000Z-flow-executor-claim-1-2-00",
        f"last_operation: {operation_id}",
    )
    _replace(
        spec, 'operation_targets: ["1.2"]', f"operation_targets: {json.dumps(targets)}"
    )
    transaction = root / ".agents/tasks/transactions" / operation_id / "journal.md"
    transaction.parent.mkdir(parents=True)
    transaction.write_text(
        "---\n"
        f"operation_id: {operation_id}\n"
        "request:\n"
        "  operation: checkpoint\n"
        f"  targets: {json.dumps(['1.1', '1.2'] if scope == 'plan' else ['1.2'] if scope == 'task' else [])}\n"
        "  payload:\n"
        f"    scope: {scope}\n"
        "---\n",
        encoding="utf-8",
    )

    assert expected in _messages(validate.validate_okf_bundle(bundle, root))


@pytest.mark.parametrize("field", ["plan_revision", "plan_commit"])
def test_plan_identity_must_match_every_task(tmp_path: Path, field: str) -> None:
    root, bundle = _fixture(tmp_path)
    task = bundle / "tasks" / "1.1.md"
    if field == "plan_revision":
        _replace(task, "plan_revision: 2", "plan_revision: 1")
    else:
        _replace(task, "plan_commit: null", "plan_commit: abc1234")
    violations = validate.validate_okf_bundle(bundle, root)
    assert "tasks/1.1.md" in _messages(violations)
    assert field in _messages(violations)


def test_lagging_untouched_task_revision_is_valid(tmp_path: Path) -> None:
    root, bundle = _fixture(tmp_path)
    assert validate.validate_okf_bundle(bundle, root) == []


def test_partial_operation_target_update_is_rejected(tmp_path: Path) -> None:
    root, bundle = _fixture(tmp_path)
    task = bundle / "tasks" / "1.2.md"
    _replace(task, 'operation_targets: ["1.2"]', "operation_targets: []")
    violations = validate.validate_okf_bundle(bundle, root)
    assert "operation_targets" in _messages(violations)
    assert "tasks/1.2.md" in _messages(violations)


def test_spec_only_operation_keeps_targets_empty_and_tasks_lagging(
    tmp_path: Path,
) -> None:
    root, bundle = _fixture(tmp_path)
    spec = bundle / "spec.md"
    _replace(spec, "state_revision: 3", "state_revision: 4")
    _replace(
        spec,
        "last_operation: 20260814T120000Z-flow-executor-claim-1-2-00",
        "last_operation: 20260814T121000Z-flow-executor-reconcile-spec-00",
    )
    _replace(spec, 'operation_targets: ["1.2"]', "operation_targets: []")
    _replace(spec, "revision `3`", "revision `4`")
    _replace(
        spec,
        "last_operation: 20260814T120000Z-flow-executor-claim-1-2-00",
        "last_operation: 20260814T121000Z-flow-executor-reconcile-spec-00",
    )
    _replace(spec, 'operation_targets: ["1.2"]', "operation_targets: []")
    assert validate.validate_okf_bundle(bundle, root) == []


def test_dependency_cycle_and_missing_dependency_are_actionable(tmp_path: Path) -> None:
    root, bundle = _fixture(tmp_path)
    first = bundle / "tasks" / "1.1.md"
    _replace(first, "depends_on: []", 'depends_on: ["1.2", "9.9"]')
    violations = validate.validate_okf_bundle(bundle, root)
    messages = _messages(violations)
    assert "tasks/1.1.md" in messages
    assert "missing dependency '9.9'" in messages
    assert "dependency cycle" in messages


def test_claim_timestamp_dependency_and_competing_claim_are_validated(
    tmp_path: Path,
) -> None:
    root, bundle = _fixture(tmp_path)
    first = bundle / "tasks" / "1.1.md"
    _replace(first, "state: closed", "state: in_progress")
    _replace(first, "claimed_by: null", "claimed_by: second-agent")
    _replace(first, "claimed_at: null", "claimed_at: yesterday")
    violations = validate.validate_okf_bundle(bundle, root)
    messages = _messages(violations)
    assert "competing in_progress claim" in messages
    assert "claimed_at" in messages
    assert "dependency '1.1' is not closed" in messages


@pytest.mark.parametrize("state", ["planned", "active", "completed"])
def test_lifecycle_requires_consistent_continuity_snapshot(
    tmp_path: Path, state: str
) -> None:
    root, bundle = _fixture(tmp_path)
    spec = bundle / "spec.md"
    _replace(spec, "state: active", f"state: {state}")
    _replace(spec, "(`active`)", f"(`{state}`)")
    assert validate.validate_okf_bundle(bundle, root) == []
    _replace(spec, "revision `3`", "revision `99`")
    violations = validate.validate_okf_bundle(bundle, root)
    assert "Continuity Snapshot" in _messages(violations)
    assert "state_revision" in _messages(violations)


def test_older_bundle_returns_migration_violations_not_exception(
    tmp_path: Path,
) -> None:
    root, bundle = _fixture(tmp_path)
    task = bundle / "tasks" / "1.2.md"
    _replace(task, "plan_revision: 2\n", "")
    _replace(task, "## Steps\n", "")
    violations = validate.validate_okf_bundle(bundle, root)
    messages = _messages(violations)
    assert "plan_revision" in messages
    assert "worksheet section 'Steps'" in messages


@pytest.mark.parametrize(
    "relative",
    [
        "skills/flow/SKILL.md",
        "hooks/session-start.md",
        "commands/flow/status.toml",
        "plugins/flow/runtime.md",
        "agents/flow-reconciler.md",
    ],
)
def test_installed_runtime_dependency_scan_is_scope_aware(
    tmp_path: Path, relative: str
) -> None:
    installed = tmp_path / relative
    installed.parent.mkdir(parents=True)
    installed.write_text(
        "---\nname: flow\ndescription: Use when Flow is active.\n---\n"
        "## Workflow\nRun python3 tools/priming.py to scan tasks/*.md dynamically for continuity state.\n",
        encoding="utf-8",
    )
    maintainer = tmp_path / "tools" / "validate.py"
    maintainer.parent.mkdir()
    maintainer.write_text("# uv run python tools/priming.py in maintainer tests\n")
    violations = validate.validate_installed_runtime_dependencies(tmp_path)
    messages = _messages(violations)
    assert relative in messages
    assert "tools/priming.py" in messages
    assert "dynamic task/spec scan" in messages
    assert "tools/validate.py" not in messages


def test_dependency_drift_is_reported_at_the_claimed_task(tmp_path: Path) -> None:
    root, bundle = _fixture(tmp_path)
    first = bundle / "tasks" / "1.1.md"
    _replace(first, "state: closed", "state: open")
    violations = validate.validate_okf_bundle(bundle, root)
    messages = _messages(violations)
    assert "tasks/1.2.md" in messages
    assert "dependency '1.1' is not closed" in messages


@pytest.mark.parametrize(
    ("old", "new", "expected"),
    [
        (
            "## Objective\nDeliver a visible continuation behavior.\n",
            "## Objective\nx\n",
            "Objective",
        ),
        (
            "## Context\nEdit `src/continuation.py` using the existing foundation.\n",
            "## Context\nx\n",
            "Context",
        ),
        (
            "## Steps\n1. Add a failing continuation scenario.\n2. Implement the continuation behavior.\n",
            "## Steps\n1. x\n",
            "Steps",
        ),
        (
            "## Verification\nRun `pytest tests/test_continuation.py` and require a passing result.\n",
            "## Verification\n`x`\n",
            "Verification",
        ),
        (
            "## Acceptance Criteria\n- The continuation behavior is observable.\n",
            "## Acceptance Criteria\n- x\n",
            "Acceptance Criteria",
        ),
    ],
)
def test_one_token_worksheet_fields_are_not_executable(
    tmp_path: Path, old: str, new: str, expected: str
) -> None:
    root, bundle = _fixture(tmp_path)
    _replace(bundle / "tasks" / "1.2.md", old, new)
    assert expected in _messages(validate.validate_okf_bundle(bundle, root))


def test_timestamps_priority_and_verification_strategy_use_closed_contracts(
    tmp_path: Path,
) -> None:
    root, bundle = _fixture(tmp_path)
    task = bundle / "tasks" / "1.2.md"
    _replace(task, "priority: P2", "priority: urgent")
    _replace(
        task, "verification_strategy: behavior_tdd", "verification_strategy: vibes"
    )
    _replace(
        task,
        "claimed_at: 2026-08-14T12:00:00Z",
        "claimed_at: 2026-08-14T12:00:00+01:00",
    )
    messages = _messages(validate.validate_okf_bundle(bundle, root))
    assert "priority" in messages
    assert "verification_strategy" in messages
    assert "claimed_at" in messages and "UTC" in messages


def test_activate_is_spec_only_and_snapshot_checkpoint_must_match(
    tmp_path: Path,
) -> None:
    root, bundle = _fixture(tmp_path)
    spec = bundle / "spec.md"
    _replace(
        spec,
        "last_operation: 20260814T120000Z-flow-executor-claim-1-2-00",
        "last_operation: 20260814T121000Z-flow-executor-activate-spec-00",
    )
    _replace(
        spec,
        "last_operation: 20260814T120000Z-flow-executor-claim-1-2-00",
        "last_operation: 20260814T121000Z-flow-executor-activate-spec-00",
    )
    _replace(spec, "`task:1.1@abc1234`", "`task:9.9@bad9999`")
    messages = _messages(validate.validate_okf_bundle(bundle, root))
    assert "activate" in messages and "operation_targets" in messages
    assert "Last verified checkpoint" in messages

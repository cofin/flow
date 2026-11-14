"""Tests for quota-aware model routing, ephemeral runtime pinning, and chapter disjoint gating."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from tools.model_router import (
    check_chapter_disjoint,
    classify_model,
    load_local_model_config,
    main,
    materialize_runtime_agents,
    parse_models_input,
    parse_quota_percent,
    resolve_models,
)


@pytest.mark.parametrize(
    ("raw_val", "expected"),
    (
        (77, 77.0),
        ("77%", 77.0),
        ("0.54", 54.0),
        (0.25, 25.0),
        (1, 1.0),
        ("0%", 0.0),
        (-5, 0.0),
        (150, 100.0),
        (None, None),
        ("", None),
        (True, None),
    ),
)
def test_parse_quota_percent_normalizes_formats(raw_val: Any, expected: float | None) -> None:
    """Verify percentage strings, integers, and fractional floats normalize onto 0..100."""
    assert parse_quota_percent(raw_val) == expected


def test_resolve_models_prefers_frontier_pro_above_floor_and_high_thinking_flash_for_workers() -> None:
    """Verify coordinator/planner pick highest >=25% Pro while workers pick extra/high thinking Flash."""
    sample_inventory = [
        {"model": "opus-tier-high", "display_name": "Opus (High)", "quota": "22%"},
        {"model": "pro-primary-coord", "display_name": "Pro Coordinator", "quota": "54%"},
        {"model": "pro-alt-high", "display_name": "Pro Alt (High)", "quota": "69%"},
        {"model": "flash-think-high", "display_name": "Flash Thinking (High)", "quota": "77%"},
        {"model": "flash-think-xhigh", "display_name": "Flash Thinking (XHigh)", "quota": "77%"},
        {"model": "flash-next", "display_name": "Flash Next", "quota": "99%"},
    ]
    candidates = [classify_model(item) for item in sample_inventory]
    report = resolve_models(candidates)

    assert report.planning_quality == "standard"
    assert report.degraded_reason is None
    assert report.roles["coordinator"].model == "pro-alt-high"
    assert report.roles["planner"].model == "pro-alt-high"
    assert report.roles["spec_reviewer"].model == "pro-alt-high"
    assert "opus-tier-high" not in report.roles["coordinator"].fallback_chain[:2]

    assert report.roles["executor"].model == "flash-think-xhigh"
    assert report.roles["verifier"].model == "flash-think-xhigh"
    assert report.roles["code_reviewer"].model == "flash-think-xhigh"
    assert report.roles["scout_heavy"].model == "flash-think-xhigh"
    assert report.roles["scout_narrow"].model == "flash-next"
    assert report.small_swarm_quota_ok is True


def test_resolve_models_marks_degraded_when_all_pro_below_floor_and_disables_swarm_when_flash_low() -> None:
    """Verify Pro exhaustion flags degraded planning and <=25% Flash quota blocks small_swarm."""
    low_inventory = [
        {"model": "pro-main", "display_name": "Pro Main", "quota": "12%"},
        {"model": "flash-think-xhigh", "display_name": "Flash Thinking (XHigh)", "quota": "25%"},
        {"model": "flash-next", "display_name": "Flash Next", "quota": "60%"},
    ]
    report = resolve_models([classify_model(item) for item in low_inventory])

    assert report.planning_quality == "degraded"
    assert report.degraded_reason is not None and "25%" in report.degraded_reason
    assert report.roles["planner"].model == "flash-think-xhigh"
    assert report.small_swarm_quota_ok is False
    assert "25%" in report.swarm_quota_reason


def test_local_config_overrides_and_materialize_runtime_agents(tmp_path: Path) -> None:
    """Verify user/project config overrides family/placeholder and writes isolated runtime agent.json files."""
    cfg_file = tmp_path / "models.json"
    cfg_file.write_text(
        json.dumps(
            {
                "pro_quota_floor": 25,
                "swarm_quota_floor": 25,
                "models": {
                    "custom-fast-worker": {
                        "family": "thinking_flash",
                        "thinking": "xhigh",
                        "placeholder": "RUNTIME_ENUM_CUSTOM_FAST",
                        "priority": 50,
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    project_root = tmp_path / "proj"
    (project_root / ".agents").mkdir(parents=True)
    (project_root / ".agents" / "setup-state.json").write_text(
        json.dumps({"model_routing": {"swarm_quota_floor": 30}}),
        encoding="utf-8",
    )

    cfg = load_local_model_config(project_root=project_root, config_path=cfg_file)
    assert cfg["swarm_quota_floor"] == 30.0

    raw_text = "- `custom-fast-worker` (Custom Worker) — 80% remaining\n- `pro-main` (Pro) — 50% remaining\n"
    candidates = parse_models_input(raw_text, cfg)
    report = resolve_models(candidates, config=cfg)

    assert report.roles["executor"].model == "custom-fast-worker"
    assert report.roles["executor"].runtime_target == "RUNTIME_ENUM_CUSTOM_FAST"
    assert report.small_swarm_quota_ok is True

    out_dir = tmp_path / "brain" / "conv-1" / ".agents" / "agents"
    written = materialize_runtime_agents(report, out_dir)
    exec_json = json.loads(Path(written["executor"]).read_text(encoding="utf-8"))
    assert exec_json == {
        "name": "runtime-executor",
        "role": "executor",
        "model": "RUNTIME_ENUM_CUSTOM_FAST",
        "requested_model": "custom-fast-worker",
        "disable_model_selection": True,
    }


def _write_task(
    tasks_dir: Path,
    filename: str,
    *,
    state: str,
    files: list[str],
    tests: list[str],
    deps: list[str],
) -> None:
    """Write a minimal Flow task frontmatter file inside ``tasks_dir``."""
    tasks_dir.mkdir(parents=True, exist_ok=True)
    tid = filename.split("-", 1)[0]
    files_yaml = json.dumps(files)
    tests_yaml = json.dumps(tests)
    deps_yaml = json.dumps(deps)
    (tasks_dir / filename).write_text(
        "---\n"
        "type: Task\n"
        f"id: demo:{tid}\n"
        f"state: {state}\n"
        f"files: {files_yaml}\n"
        f"tests: {tests_yaml}\n"
        f"depends_on: {deps_yaml}\n"
        "---\n\n"
        "## Objective & Scope Boundary\n\nScoped slice.\n",
        encoding="utf-8",
    )


@pytest.mark.parametrize(
    ("case_id", "task_specs", "harness", "flash_quota", "expected_mode", "expected_writers"),
    (
        (
            "disjoint-three-tasks",
            [
                ("t01-a.md", "pending", ["src/a.py"], ["tests/test_a.py"], []),
                ("t02-b.md", "pending", ["src/b.py"], ["tests/test_b.py"], []),
                ("t03-c.md", "pending", ["src/c.py"], ["tests/test_c.py"], []),
            ],
            "agy",
            77.0,
            "small_swarm",
            3,
        ),
        (
            "disjoint-four-tasks-packed-to-three-writers",
            [
                ("t01-a.md", "pending", ["src/a.py"], ["tests/test_a.py"], []),
                ("t02-b.md", "pending", ["src/b.py"], ["tests/test_b.py"], []),
                ("t03-c.md", "pending", ["src/c.py"], ["tests/test_c.py"], []),
                ("t04-d.md", "pending", ["src/d.py"], ["tests/test_d.py"], []),
            ],
            "agy",
            77.0,
            "small_swarm",
            3,
        ),
        (
            "overlapping-shared-file-falls-back",
            [
                ("t01-a.md", "pending", ["src/shared.py"], ["tests/test_a.py"], []),
                ("t02-b.md", "pending", ["src/shared.py"], ["tests/test_b.py"], []),
            ],
            "agy",
            77.0,
            "chapter_batch",
            0,
        ),
        (
            "flash-quota-at-25-floor-falls-back",
            [
                ("t01-a.md", "pending", ["src/a.py"], ["tests/test_a.py"], []),
                ("t02-b.md", "pending", ["src/b.py"], ["tests/test_b.py"], []),
            ],
            "agy",
            25.0,
            "chapter_batch",
            0,
        ),
        (
            "non-swarm-harness-falls-back",
            [
                ("t01-a.md", "pending", ["src/a.py"], ["tests/test_a.py"], []),
                ("t02-b.md", "pending", ["src/b.py"], ["tests/test_b.py"], []),
            ],
            "claude",
            90.0,
            "chapter_batch",
            0,
        ),
        (
            "single-task-chapter-falls-back",
            [
                ("t01-a.md", "pending", ["src/a.py"], ["tests/test_a.py"], []),
            ],
            "agy",
            80.0,
            "chapter_batch",
            0,
        ),
    ),
)
def test_check_chapter_disjoint_gates_small_swarm_vs_chapter_batch(
    tmp_path: Path,
    case_id: str,
    task_specs: list[tuple[str, str, list[str], list[str], list[str]]],
    harness: str,
    flash_quota: float,
    expected_mode: str,
    expected_writers: int,
) -> None:
    """Verify check_chapter_disjoint enforces disjointness, <=4 workers, host harness, and >25% Flash quota."""
    bundle = tmp_path / ".agents" / "bundles"
    tasks_dir = bundle / "specs" / "demo" / "chapters" / "ch01-core" / "tasks"
    for filename, state, files, tests, deps in task_specs:
        _write_task(tasks_dir, filename, state=state, files=files, tests=tests, deps=deps)

    plan = check_chapter_disjoint(
        bundle,
        "demo",
        "ch01-core",
        harness=harness,
        flash_quota=flash_quota,
    )
    assert plan.mode == expected_mode, f"[{case_id}] {plan.reason}"
    assert plan.writer_count == expected_writers
    if expected_mode == "small_swarm":
        assert plan.total_workers <= 4
        assert plan.verifier_count == 1
        assert plan.conflicts == ()


def test_cli_check_disjoint_and_resolve_roundtrip(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Verify model_router CLI subcommands execute cleanly and emit valid JSON."""
    models_file = tmp_path / "models.json"
    models_file.write_text(
        json.dumps([{"model": "pro-main", "quota": 54}, {"model": "flash-high", "quota": 77}]),
        encoding="utf-8",
    )
    assert main(["resolve", "--models-json", str(models_file), "--project", str(tmp_path)]) == 0
    resolved = json.loads(capsys.readouterr().out)
    assert resolved["roles"]["coordinator"]["model"] == "pro-main"
    assert resolved["roles"]["executor"]["model"] == "flash-high"
    assert resolved["small_swarm_quota_ok"] is True

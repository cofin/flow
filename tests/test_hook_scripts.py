"""Shell priming hooks must match the Python oracle and behave idempotently."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

import shutil

REPO_ROOT = Path(__file__).resolve().parents[1]
DETECT_SH = REPO_ROOT / "hooks" / "detect-env.sh"
AGY_SH = REPO_ROOT / "hooks" / "agy-pre-invocation.sh"
DETECT_PS1 = REPO_ROOT / "hooks" / "detect-env.ps1"
AGY_PS1 = REPO_ROOT / "hooks" / "agy-pre-invocation.ps1"

POWERSHELL = shutil.which("pwsh") or shutil.which("powershell")

posix_only = pytest.mark.skipif(sys.platform == "win32", reason="sh scripts run on POSIX")
needs_powershell = pytest.mark.skipif(POWERSHELL is None, reason="PowerShell not available")


def _build_fixture_project(root: Path) -> None:
    bundles = root / ".agents" / "bundles"
    knowledge = bundles / "knowledge"
    (bundles / "product").mkdir(parents=True)
    knowledge.mkdir(parents=True)
    (bundles / "product" / "product.md").write_text(
        "---\ntype: Guide\ntitle: Product\n---\n\n# Product\n\nLine one.\nLine two.\n",
        encoding="utf-8",
    )
    (knowledge / "workflow.md").write_text(
        "---\ntype: Guide\n---\n\n# Workflow\n\n<!-- truth: start -->\n- Run make check\n<!-- truth: end -->\n",
        encoding="utf-8",
    )
    (knowledge / "patterns.md").write_text(
        "---\ntype: Pattern\n---\n\n# Patterns\n\n- Pattern one\n- Pattern two\n",
        encoding="utf-8",
    )
    flow_dir = bundles / "specs" / "demo-flow"
    (flow_dir / "tasks").mkdir(parents=True)
    (flow_dir / "spec.md").write_text(
        "---\ntype: Spec\nflow_id: demo-flow\ntitle: Demo Flow\nstate: active\n"
        "description: A demo flow\ncreated_at: 2026-08-11T12:00:00Z\nupdated_at: 2026-08-11T12:00:00Z\n---\n# Demo\n",
        encoding="utf-8",
    )
    (flow_dir / "tasks" / "1.1.md").write_text(
        "---\ntype: Task\nid: demo-flow:1.1\ntitle: First task\nstate: open\npriority: P1\n"
        "depends_on: []\nfiles: []\ntests: []\ncreated_at: 2026-08-11T12:00:00Z\nupdated_at: 2026-08-11T12:00:00Z\ncommit: null\n---\n",
        encoding="utf-8",
    )
    (flow_dir / "tasks" / "1.2.md").write_text(
        "---\ntype: Task\nid: demo-flow:1.2\ntitle: Closed task\nstate: closed\n"
        "depends_on: []\nfiles: []\ntests: []\ncreated_at: 2026-08-11T12:00:00Z\nupdated_at: 2026-08-11T12:00:00Z\ncommit: abc1234\n---\n",
        encoding="utf-8",
    )
    skill_dir = bundles / "skills" / "demo-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: demo-skill\ndescription: A demo skill\n---\n# Demo Skill\n",
        encoding="utf-8",
    )


@posix_only
def test_detect_env_matches_python_oracle(tmp_path: Path) -> None:
    _build_fixture_project(tmp_path)

    shell_out = subprocess.run(
        ["bash", str(DETECT_SH)], cwd=tmp_path, capture_output=True, text=True, check=True
    ).stdout
    oracle_out = subprocess.run(
        [sys.executable, str(REPO_ROOT / "tools" / "priming.py"), "--markdown"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    ).stdout

    assert shell_out == oracle_out
    assert "## Project Purpose" in shell_out
    assert "## Active Flows & Tasks" in shell_out
    assert "Closed task" not in shell_out  # closed tasks are not pending


@posix_only
def test_detect_env_honors_config_json(tmp_path: Path) -> None:
    _build_fixture_project(tmp_path)
    # Relocate bundles via config.json
    (tmp_path / ".agents" / "bundles").rename(tmp_path / "kb")
    (tmp_path / ".agents" / "config.json").write_text(json.dumps({"bundles_dir": "kb"}), encoding="utf-8")

    shell_out = subprocess.run(
        ["bash", str(DETECT_SH)], cwd=tmp_path, capture_output=True, text=True, check=True
    ).stdout
    oracle_out = subprocess.run(
        [sys.executable, str(REPO_ROOT / "tools" / "priming.py"), "--markdown"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    ).stdout

    assert shell_out == oracle_out
    assert "kb/specs/demo-flow/spec.md" in shell_out


@posix_only
def test_detect_env_reports_empty_project(tmp_path: Path) -> None:
    (tmp_path / ".agents").mkdir()
    shell_out = subprocess.run(
        ["bash", str(DETECT_SH)], cwd=tmp_path, capture_output=True, text=True, check=True
    ).stdout
    assert shell_out.strip() == "No project context resolved."


def _run_agy(stdin_payload: dict, cwd: Path) -> dict:
    result = subprocess.run(
        ["bash", str(AGY_SH)],
        cwd=cwd,
        input=json.dumps(stdin_payload),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


@posix_only
def test_agy_hook_injects_once_per_conversation(tmp_path: Path) -> None:
    _build_fixture_project(tmp_path)
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    payload = {
        "conversationId": "conv-123",
        "invocationNum": 0,
        "artifactDirectoryPath": str(artifacts),
    }

    first = _run_agy(payload, tmp_path)
    assert len(first["injectSteps"]) == 1
    assert "## Project Purpose" in first["injectSteps"][0]["ephemeralMessage"]

    second = _run_agy(payload, tmp_path)
    assert second == {"injectSteps": []}


@posix_only
def test_agy_hook_skips_later_invocations(tmp_path: Path) -> None:
    _build_fixture_project(tmp_path)
    payload = {"conversationId": "conv-456", "invocationNum": 4}
    assert _run_agy(payload, tmp_path) == {"injectSteps": []}


@posix_only
def test_agy_hook_survives_empty_stdin(tmp_path: Path) -> None:
    _build_fixture_project(tmp_path)
    result = subprocess.run(
        ["bash", str(AGY_SH)],
        cwd=tmp_path,
        input="",
        capture_output=True,
        text=True,
        env={**os.environ, "TMPDIR": str(tmp_path)},
    )
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert "injectSteps" in payload


@needs_powershell
def test_detect_env_ps1_matches_python_oracle(tmp_path: Path) -> None:
    _build_fixture_project(tmp_path)

    shell_out = subprocess.run(
        [POWERSHELL, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(DETECT_PS1)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    oracle_out = subprocess.run(
        [sys.executable, str(REPO_ROOT / "tools" / "priming.py"), "--markdown"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    ).stdout

    assert shell_out.replace("\r\n", "\n").strip() == oracle_out.strip()


@needs_powershell
def test_agy_ps1_injects_once_per_conversation(tmp_path: Path) -> None:
    _build_fixture_project(tmp_path)
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    payload = json.dumps(
        {"conversationId": "conv-ps1", "invocationNum": 0, "artifactDirectoryPath": str(artifacts)}
    )

    def run() -> dict:
        result = subprocess.run(
            [POWERSHELL, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(AGY_PS1)],
            cwd=tmp_path,
            input=payload,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr
        return json.loads(result.stdout)

    first = run()
    assert len(first["injectSteps"]) == 1
    assert "## Project Purpose" in first["injectSteps"][0]["ephemeralMessage"]
    assert run() == {"injectSteps": []}

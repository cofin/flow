from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def test_makefile_python_tool_targets_use_dev_extra() -> None:
    makefile = _read("Makefile")

    assert "uv run --extra dev tools/validate-skills.py" in makefile
    assert "uv run --extra dev tools/validate-codex-manifest.py" in makefile
    assert "uv run --extra dev tools/sync-manifests.py" in makefile


def test_quality_workflow_installs_dev_extra() -> None:
    workflow = _read(".github/workflows/check.yml")

    assert "uv sync --extra dev" in workflow

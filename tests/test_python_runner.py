"""Tests for Python environment manager and entrypoint detection across project layouts."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

from tools.validate import REPO_ROOT

NODE_BIN = shutil.which("node")


def _detect_via_node(workspace_dir: Path, plugin_root: Path | None = None) -> dict[str, Any]:
    """Invoke sidecars/studio/python-runner.mjs to inspect ``workspace_dir`` and return parsed JSON."""
    assert NODE_BIN is not None
    runner_module = (REPO_ROOT / "sidecars" / "studio" / "python-runner.mjs").as_uri()
    plug = str(plugin_root or REPO_ROOT)
    script = (
        f"import {{ detectWorkspacePython, resolveCatalogWorkerCommand }} from {json.dumps(runner_module)};"
        f"const info = detectWorkspacePython({json.dumps(str(workspace_dir))});"
        f"const worker = resolveCatalogWorkerCommand({json.dumps(plug)}, {json.dumps(str(workspace_dir))});"
        "process.stdout.write(JSON.stringify({ info, worker }));"
    )
    proc = subprocess.run(
        [NODE_BIN, "--input-type=module", "-e", script],
        capture_output=True,
        text=True,
        check=True,
    )
    parsed: dict[str, Any] = json.loads(proc.stdout)
    return parsed


@pytest.mark.skipif(NODE_BIN is None, reason="node binary required")
@pytest.mark.parametrize(
    ("manager", "lockfile", "pyproject_toml", "expected_prefix", "expected_script"),
    [
        (
            "uv",
            "uv.lock",
            '[project]\nname = "demo"\n[project.scripts]\ndemo-cli = "demo.cli:main"\n',
            ["uv", "run"],
            "demo-cli",
        ),
        (
            "hatch",
            "hatch.toml",
            (
                '[project]\nname = "demo"\n[project.scripts]\n'
                'hatch-app = "demo.app:run"\n[tool.hatch.envs.default.scripts]\ncheck = "pytest"\n'
            ),
            ["hatch", "run"],
            "hatch-app",
        ),
        (
            "pdm",
            "pdm.lock",
            (
                '[project]\nname = "demo"\n[project.scripts]\n'
                'pdm-svc = "demo.svc:main"\n[tool.pdm.scripts]\nlint = "ruff check"\n'
            ),
            ["pdm", "run"],
            "pdm-svc",
        ),
        (
            "poetry",
            "poetry.lock",
            '[tool.poetry]\nname = "demo"\n[tool.poetry.scripts]\npoetry-tool = "demo.tool:main"\n',
            ["poetry", "run"],
            "poetry-tool",
        ),
    ],
)
def test_workspace_python_detector_identifies_managers_and_entrypoints(
    tmp_path: Path,
    manager: str,
    lockfile: str,
    pyproject_toml: str,
    expected_prefix: list[str],
    expected_script: str,
) -> None:
    """Verify uv, hatch, pdm, and poetry lockfiles/configs and script entrypoints are detected accurately."""
    (tmp_path / lockfile).write_text("# lock\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text(pyproject_toml, encoding="utf-8")

    result = _detect_via_node(tmp_path)
    info = result["info"]
    assert info["manager"] == manager
    assert info["runPrefix"] == expected_prefix
    assert expected_script in info["entrypoints"]


@pytest.mark.skipif(NODE_BIN is None, reason="node binary required")
def test_resolve_catalog_worker_prefers_local_plugin_venv_without_pypi(tmp_path: Path) -> None:
    """Verify catalog worker resolution uses local plugin .venv/bin/flow-catalog without PyPI assumptions."""
    result = _detect_via_node(tmp_path, plugin_root=REPO_ROOT)
    worker = result["worker"]
    assert worker["strategy"] in ("plugin-venv", "uv-project-group")
    joined = " ".join(worker["args"])
    assert "flow[catalog]" not in joined

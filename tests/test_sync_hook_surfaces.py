"""Native emitters and generated drift checks exercise the shipped outputs."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools/sync-hook-surfaces.py"
BASH = os.environ.get("FLOW_TEST_BASH") or shutil.which("bash")


def test_hook_generation_detects_drift_without_repair(tmp_path: Path) -> None:
    (tmp_path / "hooks").mkdir()
    for name in ("primer.txt", "hooks-codex.json"):
        shutil.copyfile(ROOT / "hooks" / name, tmp_path / "hooks" / name)
    command = [sys.executable, str(SCRIPT), "--repo-root", str(tmp_path)]
    subprocess.run(command, check=True)
    for script in (tmp_path / "hooks").glob("*.sh"):
        assert b"\r" not in script.read_bytes()
    subprocess.run([*command, "--check"], check=True)
    manifest = tmp_path / ".codex/hooks.json"
    manifest.write_text("{}\n")
    result = subprocess.run(
        [*command, "--check"], capture_output=True, text=True, check=False
    )
    assert result.returncode == 1
    assert ".codex/hooks.json" in result.stdout
    assert manifest.read_text() == "{}\n"


@pytest.mark.skipif(BASH is None, reason="Bash unavailable")
def test_cursor_manifest_runs_native_context_emitter() -> None:
    manifest = json.loads((ROOT / ".cursor/hooks.json").read_text())
    command = manifest["hooks"]["sessionStart"][0]["command"]
    result = subprocess.run(
        [BASH, "-c", command],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        input="{}",
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {
        "additional_context": (ROOT / "hooks/primer.txt").read_text().strip()
    }

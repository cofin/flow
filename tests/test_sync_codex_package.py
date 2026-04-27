"""Tests for materializing the Codex plugin package."""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "tools" / "sync-codex-package.py"


def _write_fake_repo(root: Path) -> None:
    files = {
        ".codex-plugin/plugin.json": '{"name": "flow"}\n',
        ".codex/INSTALL.md": "# Installing Flow for Codex\n",
        ".codex/agents/executor.toml": 'name = "executor"\n',
        ".codex/config.toml": "[profiles.flow]\n",
        ".codex/hooks.json": "{}\n",
        "skills/flow/SKILL.md": "---\nname: flow\n---\n",
        "skills/flow/references/status.md": "# Status\n",
        "commands/flow-setup.md": "# Setup\n",
        "commands/flow/sync.toml": 'description = "Gemini-only command"\n',
        "hooks/hooks-codex.json": "{}\n",
        "hooks/lib/skill-map.json": "{}\n",
        "hooks/session-start.sh": "#!/usr/bin/env bash\n",
    }
    for rel_path, content in files.items():
        path = root / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def _run_sync(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--repo-root", str(root), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def _assert_no_symlinks(path: Path) -> None:
    for child in path.rglob("*"):
        assert not child.is_symlink(), f"{child.relative_to(path)} should be a real file or directory"


@pytest.fixture
def fake_repo(tmp_path: Path) -> Path:
    _write_fake_repo(tmp_path)
    return tmp_path


def test_sync_creates_real_package_tree_from_flow_sources(fake_repo: Path) -> None:
    result = _run_sync(fake_repo)

    assert result.returncode == 0, result.stderr
    package = fake_repo / "plugins" / "flow"
    assert (package / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8") == '{"name": "flow"}\n'
    assert (package / "skills" / "flow" / "SKILL.md").read_text(encoding="utf-8") == "---\nname: flow\n---\n"
    assert (package / "commands" / "flow-setup.md").read_text(encoding="utf-8") == "# Setup\n"
    assert not (package / "commands" / "flow" / "sync.toml").exists()
    assert (package / ".codex" / "agents" / "executor.toml").is_file()
    assert (package / ".codex" / "hooks.json").is_file()
    assert not (package / ".codex" / "config.toml").exists()
    assert (package / "hooks" / "lib" / "skill-map.json").is_file()
    _assert_no_symlinks(package)


def test_check_passes_when_package_matches(fake_repo: Path) -> None:
    assert _run_sync(fake_repo).returncode == 0

    result = _run_sync(fake_repo, "--check")

    assert result.returncode == 0, result.stderr


def _make_stale(package: Path) -> None:
    (package / "skills" / "flow" / "SKILL.md").write_text("stale\n", encoding="utf-8")


def _remove_file(package: Path) -> None:
    (package / "hooks" / "hooks-codex.json").unlink()


def _add_extra(package: Path) -> None:
    (package / "extra.txt").write_text("extra\n", encoding="utf-8")


def _add_symlink(package: Path) -> None:
    _replace_with_symlink(
        package / "commands" / "flow-setup.md",
        Path("../../../commands/flow-setup.md"),
    )


@pytest.mark.parametrize(
    "mutate",
    [
        pytest.param(_make_stale, id="stale"),
        pytest.param(_remove_file, id="missing"),
        pytest.param(_add_extra, id="extra"),
        pytest.param(_add_symlink, id="symlink"),
    ],
)
def test_check_fails_on_stale_missing_extra_or_symlinked_output(
    fake_repo: Path,
    mutate: Callable[[Path], None],
) -> None:
    assert _run_sync(fake_repo).returncode == 0
    mutate(fake_repo / "plugins" / "flow")

    result = _run_sync(fake_repo, "--check")

    assert result.returncode == 1
    assert "run `make sync-codex-package`" in result.stdout


def _replace_with_symlink(path: Path, target: Path) -> None:
    if not hasattr(os, "symlink"):
        pytest.skip("symlinks are not supported on this platform")
    path.unlink()
    try:
        path.symlink_to(target)
    except OSError as exc:
        pytest.skip(f"symlinks are not available: {exc}")

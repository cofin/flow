"""Installed hooks must emit bounded static routing without child processes."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
HOOKS = REPO_ROOT / "hooks"
SESSION_ENTRYPOINTS = (
    HOOKS / "session-start.sh",
    HOOKS / "session-start.ps1",
    HOOKS / "session-start.js",
    HOOKS / "session-start.cmd",
)
AGY_ENTRYPOINTS = (HOOKS / "agy-pre-invocation.sh", HOOKS / "agy-pre-invocation.ps1")
MANIFESTS = tuple(sorted(HOOKS.glob("hooks-*.json")))
POWERSHELL = shutil.which("pwsh") or shutil.which("powershell")
NODE = shutil.which("node")
BASH = shutil.which("bash")

STATIC_ROUTING = (
    "Flow continuity is direct Markdown. Resolve the configured root from "
    ".agents/setup-state.json (default .agents/), read its index.md, then follow "
    "skills/flow/references/state.md. After compaction or session loss, use the "
    "journal-first direct-read continuity contract there; never treat hook context as authority."
)

FORBIDDEN_CALL_GRAPH = re.compile(
    r"child_process|spawnSync|execFileSync|detect-env|priming\.py|bd\s+ready|"
    r"\bpython(?:3)?\b|\bsed\b|\bawk\b",
    re.IGNORECASE,
)


def _build_legacy_tree(
    root: Path, *, large: bool, malformed: str | None = None
) -> None:
    knowledge = root / ".agents" / "bundles" / "knowledge"
    knowledge.mkdir(parents=True)
    marker_text = {
        None: "<!-- truth: start -->\nSECRET MARKER TEXT\n<!-- truth: end -->",
        "missing": "SECRET MARKER TEXT",
        "duplicate": (
            "<!-- truth: start -->\nSECRET MARKER TEXT\n<!-- truth: end -->\n"
            "<!-- truth: start -->\nDUPLICATE\n<!-- truth: end -->"
        ),
        "misordered": "<!-- truth: end -->\nSECRET MARKER TEXT\n<!-- truth: start -->",
    }[malformed]
    (knowledge / "workflow.md").write_text(marker_text, encoding="utf-8")
    if large:
        tasks = root / ".agents" / "bundles" / "specs" / "legacy" / "tasks"
        tasks.mkdir(parents=True)
        for number in range(120):
            (tasks / f"{number}.md").write_text(
                f"---\ntype: Task\nid: legacy:{number}\nstate: open\n---\nLEAK-{number}\n",
                encoding="utf-8",
            )


def _stub_commands(root: Path) -> tuple[Path, Path]:
    stub_dir = root / "stubs"
    stub_dir.mkdir()
    sentinel = root / "child-command-ran"
    body = f"#!/bin/sh\nprintf touched > {sentinel}\nexit 97\n"
    for name in (
        "bd",
        "python",
        "python3",
        "sed",
        "awk",
        "node",
        "arbitrary-child",
    ):
        command = stub_dir / name
        command.write_text(body, encoding="utf-8")
        command.chmod(0o755)
    return stub_dir, sentinel


def _run(
    command: list[str],
    *,
    cwd: Path,
    source: str,
    stub_dir: Path,
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    payload = {
        "source": source,
        "contamination": "RAW PARTIAL OUTPUT\nSECRET DIAGNOSTIC",
    }
    env = {**os.environ, "PATH": str(stub_dir), **(extra_env or {})}
    return subprocess.run(
        command,
        cwd=cwd,
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
        timeout=10,
        check=False,
    )


def _assert_session_payload(result: subprocess.CompletedProcess[str]) -> None:
    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    assert result.stdout.count("\n") == 1
    payload = json.loads(result.stdout)
    assert payload == {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": STATIC_ROUTING,
        }
    }
    context = payload["hookSpecificOutput"]["additionalContext"]
    assert len(context) <= 512
    assert "RAW PARTIAL OUTPUT" not in context
    assert "SECRET" not in context


def _assert_agy_payload(result: subprocess.CompletedProcess[str]) -> None:
    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    assert result.stdout.count("\n") == 1
    payload = json.loads(result.stdout)
    assert payload == {"injectSteps": [{"ephemeralMessage": STATIC_ROUTING}]}
    assert len(payload["injectSteps"][0]["ephemeralMessage"]) <= 512


def _manifest_commands(payload: object) -> list[str]:
    commands: list[str] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key == "command" and isinstance(value, str):
                commands.append(value)
            else:
                commands.extend(_manifest_commands(value))
    elif isinstance(payload, list):
        for value in payload:
            commands.extend(_manifest_commands(value))
    return commands


def test_manifest_targets_resolve_to_direct_emitters() -> None:
    targets: set[Path] = set()
    for manifest in MANIFESTS:
        commands = _manifest_commands(json.loads(manifest.read_text(encoding="utf-8")))
        for command in commands:
            assert "||" not in command and "&&" not in command and "|" not in command
            matches = re.findall(
                r"hooks/(session-start|agy-pre-invocation)\.(sh|ps1|js|cmd)", command
            )
            assert len(matches) == 1, (manifest, command)
            stem, suffix = matches[0]
            target = HOOKS / f"{stem}.{suffix}"
            assert target.is_file()
            targets.add(target)

    assert targets
    for target in targets:
        source = target.read_text(encoding="utf-8")
        assert not FORBIDDEN_CALL_GRAPH.search(source), target


def test_shipped_entrypoints_have_no_dynamic_call_graph() -> None:
    for path in (*SESSION_ENTRYPOINTS, *AGY_ENTRYPOINTS):
        source = path.read_text(encoding="utf-8")
        assert not FORBIDDEN_CALL_GRAPH.search(source), path

    javascript = (HOOKS / "session-start.js").read_text(encoding="utf-8")
    assert "node:child_process" not in javascript
    assert not re.search(r"\b(?:spawn|exec|fork)(?:Sync|FileSync)?\s*\(", javascript)


@pytest.mark.skipif(BASH is None, reason="Bash not available")
@pytest.mark.parametrize("source", ["startup", "compact"])
@pytest.mark.parametrize("large", [False, True], ids=["small", "large"])
@pytest.mark.parametrize("malformed", [None, "missing", "duplicate", "misordered"])
def test_shell_entrypoints_emit_static_json_without_children(
    tmp_path: Path, source: str, large: bool, malformed: str | None
) -> None:
    _build_legacy_tree(tmp_path, large=large, malformed=malformed)
    stub_dir, sentinel = _stub_commands(tmp_path)

    session = _run(
        [BASH, str(HOOKS / "session-start.sh")],
        cwd=tmp_path,
        source=source,
        stub_dir=stub_dir,
    )
    agy = _run(
        [BASH, str(HOOKS / "agy-pre-invocation.sh")],
        cwd=tmp_path,
        source=source,
        stub_dir=stub_dir,
    )

    _assert_session_payload(session)
    _assert_agy_payload(agy)
    assert not sentinel.exists()


@pytest.mark.skipif(NODE is None, reason="Node not available")
@pytest.mark.parametrize("source", ["startup", "compact"])
def test_javascript_entrypoint_emits_static_json_without_children(
    tmp_path: Path, source: str
) -> None:
    _build_legacy_tree(tmp_path, large=True, malformed="duplicate")
    stub_dir, sentinel = _stub_commands(tmp_path)
    result = _run(
        [NODE, str(HOOKS / "session-start.js")],
        cwd=tmp_path,
        source=source,
        stub_dir=stub_dir,
    )
    _assert_session_payload(result)
    assert not sentinel.exists()


@pytest.mark.skipif(POWERSHELL is None, reason="PowerShell not available")
@pytest.mark.parametrize("source", ["startup", "compact"])
def test_powershell_entrypoints_emit_static_json_without_children(
    tmp_path: Path, source: str
) -> None:
    _build_legacy_tree(tmp_path, large=True, malformed="misordered")
    stub_dir, sentinel = _stub_commands(tmp_path)
    session = _run(
        [POWERSHELL, "-NoProfile", "-File", str(HOOKS / "session-start.ps1")],
        cwd=tmp_path,
        source=source,
        stub_dir=stub_dir,
    )
    agy = _run(
        [POWERSHELL, "-NoProfile", "-File", str(HOOKS / "agy-pre-invocation.ps1")],
        cwd=tmp_path,
        source=source,
        stub_dir=stub_dir,
    )
    _assert_session_payload(session)
    _assert_agy_payload(agy)
    assert not sentinel.exists()


def test_non_flow_root_is_static_and_successful(tmp_path: Path) -> None:
    stub_dir, sentinel = _stub_commands(tmp_path)
    result = _run(
        [BASH, str(HOOKS / "session-start.sh")],
        cwd=tmp_path,
        source="compact",
        stub_dir=stub_dir,
    )
    _assert_session_payload(result)
    assert not sentinel.exists()

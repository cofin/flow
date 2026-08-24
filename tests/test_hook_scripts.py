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
JQ = shutil.which("jq")

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
    original_path = os.environ.get("PATH", "")
    test_path = os.pathsep.join(filter(None, (str(stub_dir), original_path)))
    env = {**os.environ, "PATH": test_path, **(extra_env or {})}
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
                r"hooks/(session-start|agy-pre-invocation|block-dangerous-git)\.(sh|ps1|js|cmd)",
                command,
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


def _run_git_guardrail(
    payload: object | str,
    *,
    path: str | None = None,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    if path is not None:
        env["PATH"] = path
    return subprocess.run(
        [BASH, str(HOOKS / "block-dangerous-git.sh")],
        cwd=REPO_ROOT,
        input=payload if isinstance(payload, str) else json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
        timeout=10,
        check=False,
    )


@pytest.mark.skipif(BASH is None or JQ is None, reason="Bash and jq are required")
@pytest.mark.parametrize(
    "command",
    [
        "git push origin main",
        "git push --force-with-lease origin main",
        "git reset --hard HEAD~1",
        "git clean -fdx",
        "git tag v1.2.3",
        "git tag -d v1.2.3",
        "git branch -D obsolete",
        "git -C ./repo push origin main",
        "git --no-pager -C ./repo reset --hard HEAD",
        "git status && git push origin main",
        "git status;git push origin main",
        "git status\ngit push origin main",
        "git -c alias.ship=push ship origin main",
        "git -c alias.release=tag release v1.2.3",
        "git -c alias.prune=branch prune -D obsolete",
        "git -c alias.scrub=clean scrub -fdx",
        "git -c alias.rewind=reset rewind --hard HEAD~1",
        "git -calias.ship=push ship origin main",
        "git clean",
        "git clean -i",
        "git clean --interactive",
        "git clean --dry-run --interactive",
        "git -c clean.requireForce=false clean",
        "g'i't push origin main",
        'g""it push origin main',
        "env g'i't push origin main",
        "/usr/bin/g'i't push origin main",
        "printf safe | git push origin main",
        "make lint && g'i't push origin main",
        '"/usr/bin/git" push origin main',
        'g"i"t push origin main',
        'gi""t push origin main',
        "'g'it push origin main",
        "! git push origin main",
        "time git push origin main",
        "exec git push origin main",
        "nice git push origin main",
        "sudo git push origin main",
        "</dev/null git push origin main",
        "2>/dev/null git push origin main",
        "{ git push origin main; }",
        "if true; then git push origin main; fi",
        "bash -c 'git push origin main'",
        "git-push origin main",
        "/usr/lib/git-core/git-push origin main",
        "git-reset --hard HEAD",
        "/usr/lib/git-core/git-reset --hard HEAD",
        "git-clean -fdx",
        "/usr/lib/git-core/git-clean -fdx",
        "git-tag v1.2.3",
        "/usr/lib/git-core/git-tag v1.2.3",
        "git-branch -D obsolete",
        "/usr/lib/git-core/git-branch -D obsolete",
        "git fetch --tags origin",
        "git fetch -t origin",
        "git fetch --prune-tags origin",
        "git fetch origin refs/tags/v1.2.3",
        "git fetch origin refs/heads/main:refs/tags/release",
        "git fetch origin '+refs/tags/*:refs/tags/*'",
        "git pull --tags origin main",
        "git pull --prune-tags origin main",
        "git -c remote.origin.tagOpt=--tags fetch origin",
        "git -c fetch.pruneTags=true fetch origin",
        "git --config-env=remote.origin.tagOpt=TAG_OPTION fetch origin",
        "git-fetch --tags origin",
        "/usr/lib/git-core/git-fetch origin refs/tags/v1.2.3",
        "git-pull --tags origin main",
        "git fetch origin tag v1.2.3",
        "git pull origin tag v1.2.3",
        "git-fetch origin tag v1.2.3",
        "git -c 'remote.origin.fetch=+refs/tags/*:refs/tags/*' fetch origin",
        "git -c remote.origin.fetch=refs/heads/main:refs/tags/release fetch origin",
        "git --config-env=remote.origin.fetch=FETCH_SPEC fetch origin",
        "git fetch --tag origin",
        "git-fetch --tag origin",
        "git pull --tag origin main",
        "git fetch --prune-tag origin",
        "git fetch -pt origin",
        "git pull -t origin main",
        "git tag --ignore-case v1.0",
        "git tag --sort=refname v1.0",
        "git tag --column v1.0",
        "git fetch -P origin",
        "git fetch --ta origin",
        "git fetch --prune- origin",
        "git -c fetch.pruneTags=yes fetch origin",
        "git -c fetch.pruneTags fetch origin",
        "git -c remote.origin.tagOpt=--tags pull origin main",
        "git config remote.origin.tagOpt --tags",
        "git config fetch.pruneTags true",
        "GIT_CONFIG_PARAMETERS=remote.origin.tagopt=--tags git fetch origin",
        "GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=remote.origin.tagopt GIT_CONFIG_VALUE_0=--tags git fetch origin",
        "git symbolic-ref refs/tags/v1 refs/heads/main",
        "git fetch origin tags/v3.0:tags/v3.0",
        "git remote add --tags origin https://example.invalid/repo.git",
        "git branch -Df obsolete",
        "git branch -fD obsolete",
        "git clean -n -f -d --no-dry-run",
        "git.exe push origin main",
        "Git push origin main",
        "git Push origin main",
        "git status &&\ngit push origin main",
        "(git push origin main)",
        "git status || git push origin main",
        "git fetch origin && git tag v1.2.3",
    ],
)
def test_git_guardrail_blocks_nested_destructive_commands(command: str) -> None:
    result = _run_git_guardrail({"tool_input": {"command": command}})

    assert result.returncode == 2, result
    assert "Blocked by Flow Git guardrail:" in result.stderr
    assert result.stdout == ""


@pytest.mark.skipif(BASH is None or JQ is None, reason="Bash and jq are required")
@pytest.mark.parametrize(
    "command",
    [
        "git status --short",
        "git -C ./repo diff --check",
        'git commit -m "fix parser bug"',
        'git commit -m "don\'t regress"',
        "git commit -m 'preserve quoted words'",
        "git commit -m 'say \"hello\" safely'",
        'git commit --trailer "Reviewed-by: Flow Maintainer"',
        'git grep "literal multi word pattern"',
        "git reset --soft HEAD~1",
        "git clean -n",
        "git clean --dry-run -dX",
        "git tag --list 'v*'",
        "git branch --list",
        "printf safe",
        "printf '%s' literal",
        "printf safe | wc -c",
        "value=$HOME printf safe",
        "make lint && make test",
        "eval 'printf safe'",
        "bash -c 'printf safe'",
        "git-reset --soft HEAD~1",
        "/usr/lib/git-core/git-clean -n",
        "git-tag --list 'v*'",
        "/usr/lib/git-core/git-branch --list",
        "git-status --short",
        "/usr/lib/git-core/git-status --short",
        'git-commit -m "safe direct helper"',
        "git fetch origin main",
        "git fetch --no-tags origin main",
        "git pull origin main",
        "git -c remote.origin.tagOpt=--no-tags fetch origin main",
        "git-fetch origin main",
        "/usr/lib/git-core/git-pull origin main",
        "git -c 'remote.origin.fetch=+refs/heads/*:refs/remotes/origin/*' fetch origin",
        "git status && git diff --stat",
        "git log --oneline | head -5",
        "git status; git diff --check",
        "(git status)",
        "{ git status; }",
        'git commit -m "fix(hooks): block abbreviated tag fetch options"',
        "git commit -m 'costs $5 (roughly)'",
        "git grep 'foo\\.bar'",
        "git tag --sort=refname",
        "git tag --ignore-case --list 'v*'",
        "GIT_CONFIG_GLOBAL=/dev/null git status",
        "git fetch --prune origin",
        "git clean --no-dry-run -n",
        "git branch -d merged-topic",
        "git remote -v",
        "git config user.name",
        "git symbolic-ref HEAD",
        "make lint && git status --short",
        "echo $HOME",
        'printf "%s" "$HOME"',
        "ls *.py",
        "uv run pytest tests/test_x.py::test_y[0]",
        "git status > /dev/null",
        "git log --format=%h 2>&1 | head -3",
        "git log --grep='a|b'",
        'git commit -m "fix(hooks): x; y | z"',
        "git commit -m \"$(cat <<'EOF'\nfeat: add thing\nEOF\n)\"",
        "source ./env.sh && git status",
        'for f in *.py; do git add "$f"; done',
        "v=$(git rev-parse HEAD); echo $v",
        "echo `git rev-parse HEAD`",
        "GIT_CONFIG_GLOBAL=/dev/null git config user.name",
        "git frobnicate",
        "git --unknown-global status",
        "git tag --unknown-option",
    ],
)
def test_git_guardrail_allows_parsed_safe_commands(command: str) -> None:
    result = _run_git_guardrail({"tool_input": {"command": command}})

    assert result.returncode == 0, result.stderr
    assert result.stdout == ""
    assert result.stderr == ""

@pytest.mark.skipif(BASH is None or JQ is None, reason="Bash and jq are required")
@pytest.mark.parametrize(
    ("command", "returncode"),
    [
        ('git commit -m "' + "word " * 4000 + '"', 0),
        ('git commit -m "' + "word " * 4000 + '" && git push origin main', 2),
        ("git log " + " ".join(f"--grep=t{i}" for i in range(1500)), 0),
        ("cat > f.py <<'EOF'\n" + "x = 1  # comment\n" * 800 + "EOF", 0),
    ],
)
def test_git_guardrail_classifies_large_commands_within_timeout(
    command: str, returncode: int
) -> None:
    result = _run_git_guardrail({"tool_input": {"command": command}})

    assert result.returncode == returncode, result

@pytest.mark.skipif(BASH is None or JQ is None, reason="Bash and jq are required")
@pytest.mark.parametrize(
    "command",
    [
        "git $FLOW_GIT_COMMAND origin main",
        "git $(printf push) origin main",
        "$CMD push origin main",
        '"${CMD}" push origin main',
        "/usr/bin/g?t push origin main",
        "./[g]it push origin main",
        r"g\it push origin main",
        "$'git' push origin main",
        'bash -c "$CMD push origin main"',
        'eval "$CMD push origin main"',
        'timeout 5 bash -c "$CMD push origin main"',
        "alias ship='git push'; ship origin main",
        "source ./commands.sh",
        'source "$COMMAND_FILE"',
        "bash -c \"g''it push\"",
        "git-frobnicate unsafe",
    ],
)
def test_git_guardrail_allows_unclassifiable_commands(command: str) -> None:
    """The guardrail catches literal mistakes; obfuscated or dynamic Git is out of scope."""
    result = _run_git_guardrail({"tool_input": {"command": command}})

    assert result.returncode == 0, result




@pytest.mark.skipif(BASH is None or JQ is None, reason="Bash and jq are required")
@pytest.mark.parametrize(
    ("payload", "diagnostic"),
    [
        ("not-json", "expected a non-empty string at .tool_input.command"),
        ({}, "expected a non-empty string at .tool_input.command"),
        ({"tool_input": {}}, "expected a non-empty string at .tool_input.command"),
        (
            {"tool_input": {"command": ""}},
            "expected a non-empty string at .tool_input.command",
        ),
        (
            {"tool_input": {"command": "   \t"}},
            "expected a non-empty string at .tool_input.command",
        ),
        (
            {"tool_input": {"command": 7}},
            "expected a non-empty string at .tool_input.command",
        ),
    ],
)
def test_git_guardrail_fails_closed_for_invalid_payloads(
    payload: object | str, diagnostic: str
) -> None:
    result = _run_git_guardrail(payload)

    assert result.returncode == 2
    assert diagnostic in result.stderr
    assert result.stdout == ""


@pytest.mark.skipif(BASH is None, reason="Bash not available")
def test_git_guardrail_skips_classification_without_jq(tmp_path: Path) -> None:
    result = _run_git_guardrail(
        {"tool_input": {"command": "git status"}},
        path=str(tmp_path),
    )

    assert result.returncode == 0
    assert result.stderr == (
        "Flow Git guardrail: jq is unavailable; skipping Git classification\n"
    )
    assert result.stdout == ""


@pytest.mark.skipif(BASH is None or JQ is None, reason="Bash and jq are required")
def test_git_guardrail_allows_unrelated_redirection_without_execution(
    tmp_path: Path,
) -> None:
    sentinel = tmp_path / "executed"
    result = _run_git_guardrail(
        {"tool_input": {"command": f"printf unsafe > {sentinel}"}}
    )

    assert result.returncode == 0
    assert result.stdout == ""
    assert result.stderr == ""
    assert not sentinel.exists()

"""The three command surfaces (Claude .md, Codex .toml, OpenCode templates) must not drift."""
from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

CLAUDE_COMMANDS = REPO_ROOT / "commands"
CODEX_COMMANDS = REPO_ROOT / "commands" / "flow"
OPENCODE_COMMANDS = REPO_ROOT / "templates" / "opencode" / "commands"

TASK_STATE_TOKENS = ("open", "in_progress", "closed", "blocked", "skipped")
SPEC_STATE_TOKENS = ("planned", "active", "completed", "archived")

WORKFLOW_STATE_IN_STATUS = re.compile(
    r"status:\s*(open|in_progress|closed|blocked|skipped|planned|active|completed)\b"
)


def _claude_names() -> set[str]:
    return {p.stem.removeprefix("flow-") for p in CLAUDE_COMMANDS.glob("flow-*.md")}


def _codex_names() -> set[str]:
    return {p.stem for p in CODEX_COMMANDS.glob("*.toml")}


def _opencode_names() -> set[str]:
    return {p.stem.removeprefix("flow-") for p in OPENCODE_COMMANDS.glob("flow-*.md")}


def test_command_inventories_match() -> None:
    claude = _claude_names()
    assert claude, "no Claude commands found"
    assert claude == _codex_names(), "Claude .md and Codex .toml command sets differ"
    assert claude == _opencode_names(), "Claude .md and OpenCode template command sets differ"


def _iter_all_command_files():
    yield from sorted(CLAUDE_COMMANDS.glob("flow-*.md"))
    yield from sorted(CODEX_COMMANDS.glob("*.toml"))
    yield from sorted(OPENCODE_COMMANDS.glob("flow-*.md"))


def test_no_workflow_state_in_status_key() -> None:
    offenders = []
    for path in _iter_all_command_files():
        rel = path.relative_to(REPO_ROOT).as_posix()
        for num, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if "legacy" in line.lower() or "migrat" in line.lower():
                continue
            if WORKFLOW_STATE_IN_STATUS.search(line):
                offenders.append(f"{rel}:{num}: {line.strip()[:100]}")
    assert offenders == [], "Workflow state stored in status::\n" + "\n".join(offenders)


def test_bundle_paths_never_legacy() -> None:
    offenders = []
    for path in _iter_all_command_files():
        rel = path.relative_to(REPO_ROOT).as_posix()
        text = path.read_text(encoding="utf-8")
        for num, line in enumerate(text.splitlines(), start=1):
            if "legacy" in line.lower() or "migrat" in line.lower() or "pre-bundle" in line.lower():
                continue
            if re.search(r"\.agents/specs/|\.agents/patterns\.md|\.agents/knowledge/|\.agents/flows\.md", line):
                offenders.append(f"{rel}:{num}: {line.strip()[:100]}")
    assert offenders == [], "Legacy paths in command surfaces:\n" + "\n".join(offenders)


def test_state_vocabulary_consistent_across_twins() -> None:
    # Any command that names task/spec states must use only canonical tokens
    canonical = set(TASK_STATE_TOKENS) | set(SPEC_STATE_TOKENS)
    state_pattern = re.compile(r"state:\s*([a-z_|]+)")
    offenders = []
    for path in _iter_all_command_files():
        rel = path.relative_to(REPO_ROOT).as_posix()
        for num, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            for match in state_pattern.finditer(line):
                for token in match.group(1).split("|"):
                    token = token.strip("`<>{} ")
                    if token and not token.startswith("<") and token not in canonical:
                        offenders.append(f"{rel}:{num}: state token {token!r}")
    assert offenders == [], "Non-canonical state tokens:\n" + "\n".join(offenders)

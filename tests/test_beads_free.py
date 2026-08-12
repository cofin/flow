"""No shipped prompt surface may reference the retired Beads tracker or legacy layout.

Scope grows as trees are converted; templates/opencode and per-harness agent
copies join the scan when harness parity lands.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

SCAN_ROOTS = (
    "commands",
    "skills",
    "agents",
    "templates/agent",
)
ROOT_FILES = (
    "README.md",
    "AGENTS.md",
    "CLAUDE.md",
    "plugin.json",
    "package.json",
    ".claude-plugin/plugin.json",
    ".claude-plugin/marketplace.json",
    ".codex-plugin/plugin.json",
    ".codex/INSTALL.md",
    ".opencode/INSTALL.md",
    ".cursor/rules/flow.mdc",
)
SUFFIXES = {".md", ".toml", ".json", ".yaml", ".mdc"}

# Setup surfaces describe MIGRATING AWAY from legacy artifacts; only they may
# name them, and only in that context.
MIGRATION_FILES = {
    "commands/flow-setup.md",
    "commands/flow/setup.toml",
    "skills/flow/references/setup.md",
}

BEADS_PATTERN = re.compile(r"\bbd\b|beads", re.IGNORECASE)
LEGACY_PATH_PATTERNS = (
    re.compile(r"\.agents/specs/"),
    re.compile(r"\.agents/patterns\.md"),
    re.compile(r"\.agents/knowledge/"),
    re.compile(r"\.agents/flows\.md"),
    re.compile(r"useBeads"),
    re.compile(r"validate-skills"),
)
NO_PYTHON_ROOTS = ("commands", "skills")
PYTHON_PATTERN = re.compile(r"python3? tools/")


def _iter_files():
    for root in SCAN_ROOTS:
        base = REPO_ROOT / root
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if path.is_file() and path.suffix in SUFFIXES:
                yield path
    for name in ROOT_FILES:
        path = REPO_ROOT / name
        if path.is_file():
            yield path


def test_shipped_surfaces_are_beads_free() -> None:
    offenders = []
    for path in _iter_files():
        rel = path.relative_to(REPO_ROOT).as_posix()
        if rel in MIGRATION_FILES:
            continue
        text = path.read_text(encoding="utf-8")
        for num, line in enumerate(text.splitlines(), start=1):
            if BEADS_PATTERN.search(line):
                offenders.append(f"{rel}:{num}: {line.strip()[:100]}")
    assert offenders == [], "Beads references in shipped surfaces:\n" + "\n".join(offenders)


def test_migration_files_mention_beads_only_for_removal() -> None:
    for rel in MIGRATION_FILES:
        text = (REPO_ROOT / rel).read_text(encoding="utf-8")
        for num, line in enumerate(text.splitlines(), start=1):
            if BEADS_PATTERN.search(line):
                lowered = line.lower()
                assert "legacy" in lowered or "remove" in lowered or "delete" in lowered or "migrat" in lowered, (
                    f"{rel}:{num} mentions Beads outside a legacy-migration context: {line.strip()}"
                )


def test_no_legacy_layout_paths() -> None:
    offenders = []
    for path in _iter_files():
        rel = path.relative_to(REPO_ROOT).as_posix()
        if rel in MIGRATION_FILES:
            # Migration instructions must name the legacy paths they migrate away from
            continue
        text = path.read_text(encoding="utf-8")
        for num, line in enumerate(text.splitlines(), start=1):
            for pattern in LEGACY_PATH_PATTERNS:
                if pattern.search(line):
                    offenders.append(f"{rel}:{num}: {line.strip()[:100]}")
    assert offenders == [], "Legacy layout references:\n" + "\n".join(offenders)


def test_prompts_do_not_shell_out_to_python_tools() -> None:
    offenders = []
    for root in NO_PYTHON_ROOTS:
        for path in sorted((REPO_ROOT / root).rglob("*")):
            if not (path.is_file() and path.suffix in SUFFIXES):
                continue
            rel = path.relative_to(REPO_ROOT).as_posix()
            for num, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
                if PYTHON_PATTERN.search(line) and "do not run" not in line.lower() and "not run external" not in line.lower():
                    offenders.append(f"{rel}:{num}: {line.strip()[:100]}")
    assert offenders == [], "Prompt files shell out to python tools:\n" + "\n".join(offenders)

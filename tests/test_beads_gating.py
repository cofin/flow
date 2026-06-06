"""Guards GH #53: every prompt that invokes `bd` must gate on the useBeads toggle.

The SessionStart hook (`detect-env.{sh,ps1}`) reports when Beads is missing or
disabled via `useBeads=false`. Commands/skills/agents that shell out to `bd` must
honor that — otherwise disabling Beads is silently defeated or errors noisily.
This test asserts every `bd`-referencing prompt carries the Beads-mode gate marker.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PROMPT_DIRS = ("commands", "skills", "agents")
# A `bd <subcommand>` invocation in prose/bash (not "bd" inside a word).
BD_CALL = re.compile(r"(?<![\w-])bd\s+[a-z]")
# Literal (lowercased) phrases that mark a file as Beads-aware / gated.
GATE_MARKERS = (
    "usebeads",
    "beads backend",
    "missing (none)",
    "beads mode",
    "disabled via plugin config",
)


def _is_gated(text: str) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in GATE_MARKERS)


def _iter_prompt_files():
    for rel in PROMPT_DIRS:
        root = REPO_ROOT / rel
        if not root.is_dir():
            continue
        for path in root.rglob("*"):
            if path.suffix in {".md", ".toml"} and path.is_file():
                yield path


def test_every_bd_prompt_is_gated_on_use_beads() -> None:
    ungated: list[str] = []
    for path in _iter_prompt_files():
        text = path.read_text(encoding="utf-8")
        if BD_CALL.search(text) and not _is_gated(text):
            ungated.append(str(path.relative_to(REPO_ROOT)))
    assert ungated == [], (
        "These prompts invoke `bd` without a useBeads gate (GH #53). Add the "
        "'Beads mode' gate so disabling Beads is honored:\n  " + "\n  ".join(sorted(ungated))
    )

#!/usr/bin/env python3
"""Validate Claude Code plugin and marketplace manifests using the official ``claude`` CLI.

Wraps ``claude plugin validate <path>`` so CI fails on the same schema errors
Claude Code's loader would surface at install time. Avoids hand-rolling a
schema that drifts from the real validator.

Exit 0 on clean; exit 1 if any target fails or ``claude`` is unavailable.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

TARGETS: tuple[Path, ...] = (
    REPO_ROOT / ".claude-plugin" / "plugin.json",
    REPO_ROOT / ".claude-plugin" / "marketplace.json",
)


def _validate(target: Path) -> bool:
    if not target.is_file():
        print(f"  MISSING: {target}", file=sys.stderr)
        return False
    result = subprocess.run(
        ["claude", "plugin", "validate", str(target)],
        capture_output=True,
        text=True,
        check=False,
    )
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    return result.returncode == 0


def main() -> int:
    if shutil.which("claude") is None:
        print("ERROR: 'claude' CLI not found on PATH.", file=sys.stderr)
        print("Install Claude Code or skip with `SKIP_CLAUDE_VALIDATE=1`.", file=sys.stderr)
        return 1

    failures = [t for t in TARGETS if not _validate(t)]
    if failures:
        print(f"\n{len(failures)} manifest(s) failed Claude Code validation.", file=sys.stderr)
        return 1
    print(f"All {len(TARGETS)} Claude manifests valid.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

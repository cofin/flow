"""Module execution entrypoint for ``python -m tools.catalog``."""

from __future__ import annotations

from tools.catalog.cli import main

if __name__ == "__main__":
    raise SystemExit(main())

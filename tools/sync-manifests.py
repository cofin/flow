"""Verify every bump-my-version-tracked file is in sync with current_version.

Reads ``[[tool.bumpversion.files]]`` from ``pyproject.toml`` and, for each
entry, substitutes ``{current_version}`` into the ``search`` pattern and
asserts the resulting literal appears in the target file. Catches the case
where a manual edit (or a partially applied ``make release``) leaves one
manifest at an old version while the others advance.

Exit 0 on clean; exit 1 with a per-file diagnostic list otherwise.
"""

import sys
from pathlib import Path
from typing import Any, cast

if sys.version_info >= (3, 11):
    import tomllib as _tomllib
else:  # pragma: no cover - py310 fallback path
    import tomli as _tomllib  # type: ignore[import-not-found,unused-ignore]

_toml_loads_any: Any = _tomllib.loads  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]


def _toml_loads(text: str) -> dict[str, Any]:
    """Parse a TOML string into a dict, tolerant of py310 ``tomli`` fallback."""
    return cast("dict[str, Any]", _toml_loads_any(text))


REPO_ROOT = Path(__file__).resolve().parents[1]


def check(repo_root: Path | None = None) -> list[str]:
    """Return a list of human-readable error strings. Empty list == in sync."""
    root = repo_root if repo_root is not None else REPO_ROOT
    pyproject_path = root / "pyproject.toml"
    if not pyproject_path.is_file():
        return [f"{pyproject_path}: missing"]
    data = _toml_loads(pyproject_path.read_text(encoding="utf-8"))
    bump_section = data.get("tool", {}).get("bumpversion", {})
    if not bump_section:
        return ["pyproject.toml: no [tool.bumpversion] section"]
    current = bump_section.get("current_version")
    if not isinstance(current, str) or not current:
        return ["pyproject.toml: [tool.bumpversion].current_version missing or empty"]
    files: list[dict[str, Any]] = bump_section.get("files", [])
    if not files:
        return ["pyproject.toml: no [[tool.bumpversion.files]] entries"]

    errors: list[str] = []
    for entry in files:
        filename = entry.get("filename")
        search_template = entry.get("search")
        if not isinstance(filename, str) or not filename:
            errors.append(f"{entry!r}: missing filename")
            continue
        if not isinstance(search_template, str) or not search_template:
            errors.append(f"{filename}: missing search pattern")
            continue
        expected = search_template.replace("{current_version}", current)
        target = root / filename
        if not target.is_file():
            errors.append(f"{filename}: file missing")
            continue
        body = target.read_text(encoding="utf-8")
        if expected not in body:
            errors.append(f"{filename}: version string {expected!r} not found (expected current_version={current})")
    return errors


def main() -> int:
    errors = check()
    if errors:
        for err in errors:
            print(f"[FAIL] {err}", file=sys.stderr)
        print(f"\n{len(errors)} manifest(s) out of sync", file=sys.stderr)
        return 1
    data = _toml_loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    bump = data["tool"]["bumpversion"]
    current = bump["current_version"]
    file_count = len(bump.get("files", []))
    print(f"[ OK ] {file_count} manifests in sync at version {current}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

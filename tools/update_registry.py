#!/usr/bin/env python3
"""Update the apilookup version registry from public package registries.

Usage:
    uv run tools/update_registry.py                  # Update all entries
    uv run tools/update_registry.py litestar react   # Update specific skills
"""

import json
import sys
import urllib.request
import urllib.error
from pathlib import Path
from datetime import date

REGISTRY_PATH = Path(__file__).resolve().parent.parent / "skills" / "apilookup" / "references" / "registry.json"

API_ENDPOINTS = {
    "pypi": "https://pypi.org/pypi/{package}/json",
    "npm": "https://registry.npmjs.org/{package}/latest",
    "crates": "https://crates.io/api/v1/crates/{package}",
    "go": "https://proxy.golang.org/{package}/@latest",
}


def extract_version(data: dict, path: str) -> str | None:
    """Walk a dot-separated path into a nested dict to get the version string."""
    current = data
    for key in path.split("."):
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    return str(current) if current is not None else None


VERSION_PATHS = {
    "pypi": "info.version",
    "npm": "version",
    "crates": "crate.max_stable_version",
    "go": "Version",
}


def fetch_latest_version(registry: str, package: str) -> str | None:
    """Fetch the latest version for a package from its registry API."""
    if registry not in API_ENDPOINTS:
        return None

    url = API_ENDPOINTS[registry].format(package=package)
    req = urllib.request.Request(url, headers={"User-Agent": "flow-registry-updater/1.0"})

    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError:
        return None
    except Exception:
        return None

    version_path = VERSION_PATHS.get(registry)
    if not version_path:
        return None

    return extract_version(data, version_path)


def main() -> int:
    # Load registry
    with open(REGISTRY_PATH, encoding="utf-8") as f:
        registry = json.load(f)

    today = date.today().isoformat()

    # Filter to specific skills if provided as CLI args
    filter_skills = set(sys.argv[1:]) if len(sys.argv) > 1 else None

    updated_count = 0
    error_count = 0
    skipped_manual: list[str] = []
    something_changed = False

    for skill_name in sorted(registry.keys()):
        if filter_skills and skill_name not in filter_skills:
            continue

        entry = registry[skill_name]
        pkg_registry = entry.get("package_registry")
        pkg_name = entry.get("package_name")

        if not pkg_registry or not pkg_name:
            skipped_manual.append(skill_name)
            entry["last_checked"] = today
            something_changed = True
            continue

        print(f"  Checking {skill_name} ({pkg_name} on {pkg_registry})...", end=" ", flush=True)

        latest = fetch_latest_version(pkg_registry, pkg_name)

        if latest is None:
            print("FAILED")
            error_count += 1
            continue

        old_version = entry.get("current_version", "0.0.0")
        if latest != old_version:
            entry["current_version"] = latest
            entry["last_checked"] = today
            print(f"{old_version} -> {latest}")
            updated_count += 1
            something_changed = True
        else:
            entry["last_checked"] = today
            print(f"{latest} (unchanged)")
            something_changed = True

    # Write registry back only if something to write
    if something_changed:
        with open(REGISTRY_PATH, "w", encoding="utf-8") as f:
            f.write(json.dumps(registry, indent=2, ensure_ascii=False) + "\n")

    # Print summary
    print()
    print(f"Updated: {updated_count}")
    print(f"Errors:  {error_count}")
    if skipped_manual:
        print(f"Manual update needed: {', '.join(sorted(skipped_manual))}")

    return 0 if error_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

# Registry Schema Reference

Documents the `registry.json` format used by the `apilookup` skill to store and look up package/library version data.

---

## Entry Format

Each entry in `registry.json` is keyed by a canonical identifier (e.g. `"sqlalchemy"`, `"react"`) and contains the following structure:

```json
{
  "sqlalchemy": {
    "display_name": "SQLAlchemy",
    "current_version": "2.0.36",
    "last_checked": "2025-11-14",
    "package_registry": "pypi",
    "package_name": "SQLAlchemy",
    "docs_url": "https://docs.sqlalchemy.org/en/20/",
    "changelog_url": "https://docs.sqlalchemy.org/en/20/changelog/",
    "github": "sqlalchemy/sqlalchemy",
    "search_hints": ["sqlalchemy", "sqla", "orm", "sql toolkit", "database orm"]
  }
}
```

---

## Field Reference

| Field | Type | Required | Description |
|---|---|---|---|
| `display_name` | string | yes | Human-readable name for display and matching |
| `current_version` | string | yes | Last known stable version (semver or equivalent) |
| `last_checked` | string (ISO date) | yes | Date when version was last verified against the registry (format: `YYYY-MM-DD`) |
| `package_registry` | string \| null | no | One of: `pypi`, `npm`, `crates_io`, `go_proxy`, or `null` for platform services (e.g. cloud SDKs with no single registry) |
| `package_name` | string | no | Package name on the registry. Required when `package_registry` is set |
| `docs_url` | string | yes | Primary official documentation URL |
| `changelog_url` | string | no | Changelog, release notes, or migration guide URL |
| `github` | string | no | GitHub `owner/repo` path (e.g. `"pallets/flask"`) |
| `search_hints` | string[] | no | Keywords for matching user queries to this entry (common aliases, abbreviations, related terms) |

---

## Package Registry API Endpoints

These endpoints are used by the update script to fetch the current version for each package registry.

| Registry | Endpoint | Version JSONPath |
|---|---|---|
| PyPI | `https://pypi.org/pypi/{package}/json` | `$.info.version` |
| npm | `https://registry.npmjs.org/{package}/latest` | `$.version` |
| crates.io | `https://crates.io/api/v1/crates/{package}` | `$.crate.newest_version` |
| Go proxy | `https://proxy.golang.org/{module}/@latest` | `$.Version` |

---

## Staleness Thresholds

The age of a registry entry (based on `last_checked`) determines how the lookup behaves at runtime.

| Age | Lookup Behavior |
|---|---|
| < 30 days | Use cached version from `registry.json` directly; no live lookup performed |
| 30–90 days | Use cached version but emit a staleness notice suggesting the user verify currency |
| > 90 days | Warn that the cached version may be significantly outdated; recommend running the update script or checking the registry manually |

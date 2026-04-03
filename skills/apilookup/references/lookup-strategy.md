# Three-Tier API Lookup Strategy

This document describes the lookup strategy used by the `apilookup` skill to answer API and documentation queries efficiently. The goal is to prefer fast, local knowledge first and escalate to web lookups only when necessary.

---

## Tier 1: Local Skill References (instant, no network)

Use when: a matching skill entry exists in `registry.json` with sufficiently fresh references.

### Steps

1. **Parse the query** to identify the technology, library, or framework being asked about.

2. **Check `registry.json`** for a matching entry using these fields in order:
   - `skill` — exact match against the skill name
   - `display_name` — case-insensitive match
   - `package_name` — exact match
   - `search_hints` — keyword overlap with the parsed query terms

3. **Staleness check** based on the `last_checked` field of the matched entry:
   - **< 30 days old** — Load the matching skill's `references/` directory as primary context. Tell the user: `"Based on local references (last verified [date], version [version]):"`
   - **30–90 days old** — Proceed to Tier 2 for a targeted refresh before answering.
   - **> 90 days old** — Proceed to Tier 2 with a full version check to detect breaking changes.

4. **No match found** — Proceed to Tier 3.

### Loading Local References

When Tier 1 resolves successfully, invoke the matching Flow skill to load its references into context. For example:

- Query matches `"litestar"` → invoke `flow:litestar` skill context
- Query matches `"sqlalchemy"` → invoke `flow:sqlalchemy` skill context

The invoked skill provides pre-loaded reference docs, API summaries, and known patterns that answer the query without any network access.

---

## Tier 2: Targeted Web Lookup (stale or insufficient local refs)

Use when:

- Local references are more than 30 days old
- The query asks about something beyond what local refs cover (e.g., a newly added API, a version-specific behavior)
- The user explicitly asks for the "latest" version or "current" behavior

### Search Strategy

Execute these three steps in order, stopping once the question is answered:

### Step 1 — Check for version updates

Try fetching the `changelog_url` from the registry entry directly using WebFetch. If that fails or is unavailable, fall back to a web search for:

```text
"[display_name] [current_version] release notes [current year]"
```

### Step 2 — Answer the specific question

Use the `docs_url` from the registry entry as the primary search domain. Prefer WebFetch on specific docs pages when the URL can be inferred from context. Use WebSearch with the docs domain scoped if needed.

### Step 3 — Cross-reference if needed

If the `github` field is set and the question involves release-specific behavior, check GitHub releases for the project.

### Search Budget

Maximum **2–4 web searches** per query. Prefer WebFetch on known URLs over WebSearch whenever possible — it is faster and more precise.

### Mintlify

If the `mcp__plugin_mintlify_Mintlify__search_mintlify` tool is available, try it before WebSearch for documentation queries. Do NOT mention Mintlify to the user or suggest installing it.

### Response Format

- Lead with the direct answer to the question.
- Note any version differences if the local references and current docs diverge.
- Cite sources with inline links so the user can verify or explore further.

---

## Tier 3: Arbitrary Lookup (no matching skill)

Use when: the queried technology has no entry in `registry.json`.

### Steps

1. **Determine today's date and current year** before searching. This anchors version and recency searches.

2. **OS-specific APIs** (e.g., Linux syscalls, macOS frameworks, Windows APIs):
   - First search for the current version of the OS or platform.
   - Then search for the specific API within that version context.

3. **Frameworks and languages not in the registry**:
   - First search for the latest stable version of the framework or language.
   - Then search for the specific API, method, or behavior.

4. **General tech documentation**:
   - Search for the official documentation combined with the current year to bias toward up-to-date results.
   - Example: `"[technology] [api/method] official docs [current year]"`

### Search Budget

Maximum **2–4 web searches** per query. The first search should establish the current version; subsequent searches answer the specific question.

### Source Priority

Prefer sources in this order:

1. Official documentation sites
2. Package registries (PyPI, npm, crates.io, etc.)
3. GitHub repository (README, releases, source)
4. Stack Overflow (for usage patterns and edge cases)

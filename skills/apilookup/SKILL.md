---
name: apilookup
description: "Use when answering questions about current external library APIs, SDK documentation, package versions, breaking changes, migration guides, or deprecations."
---

# API & SDK Documentation Lookup

Lookup up-to-date documentation, API signatures, breaking changes, and migration guides for external libraries and SDK dependencies.

## Workflow

1. **Identify Target Dependency & Version**: Inspect `pyproject.toml`, `package.json`, or lockfiles to determine exact active versions.
2. **Execute Targeted Search**: Query SDK documentation, changelogs, and release notes for breaking changes and deprecations.
3. **Verify Compatibility**: Confirm that the API usage matches the installed version.

## Guardrails

- Never guess API signatures or configuration formats when working across major framework version boundaries.
- Inspect official primary-source documentation and typed declaration files.

## Output

Return the verified signature, migration notes, and a minimal runnable code example.

## Validation

Confirm the documented API signature against official library documentation and type declarations.

## Example

For a library migration, inspect the target version changelog, identify breaking signature changes, and provide the updated function call.

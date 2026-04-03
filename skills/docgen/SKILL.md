---
name: docgen
description: "Auto-activate when generating documentation, writing API docs, documenting modules or components, creating README content, building reference guides, or systematically documenting a codebase. Produces structured per-component documentation with completeness tracking — every file in scope gets documented, progress is explicit ([3/12 files]). Use when: documenting multiple files or components, ensuring complete coverage of a module, generating structured docs from code, or when /flow-docs needs systematic file-by-file analysis. Not for ad-hoc comments in code, inline docstrings, or single-function explanations."
---

# Docgen

Systematic documentation generation with progress tracking and completeness guarantees. Analyzes code file-by-file, ensures nothing is skipped, and produces structured output per component.

Docgen complements `flow-docs` — it provides the systematic analysis engine for flow-docs' five-phase workflow. It can also be used standalone for ad-hoc documentation tasks when you need structured, complete documentation without a full flow-docs run.

The core guarantee: every file in scope gets documented. Progress is tracked explicitly (`[3/12 files documented]`) so you always know what's been covered and what remains.

<workflow>

## Workflow

### 1. Scope the Target

Identify what needs documenting: single file, directory, module, or entire package. Be specific — "the auth module" means every file in that directory.

### 2. Build the File Manifest

Enumerate every file to document with its path. This is the completeness checklist — no file gets dropped silently. Count them: this is your denominator.

### 3. Analyze Each File

For each file in the manifest:

- **Read the file fully** — do not guess from file names
- Extract: purpose, public interface, dependencies, key patterns
- Document using the component template in `references/component-template.md`:
  - **Purpose** — one sentence
  - **Public Interface** — every export with signature and description
  - **Dependencies** — imports and external services
  - **Key Patterns** — design patterns, invariants, async considerations
  - **Usage Example** — minimal, copy-pasteable
  - **Notes** — edge cases and gotchas (only if they exist)
- Scale the template to complexity: a 10-line utility needs Purpose + Interface + Example; a complex service gets the full template
- Mark the file as documented. Report progress: `[3/12 files documented]`

### 4. Cross-Reference

After all files are documented:

- Verify imports and dependencies between documented components
- Note common patterns across the module
- Flag circular dependencies or unclear boundaries

### 5. Synthesize

Produce the final documentation:

- Module overview (what it does, how components relate)
- Per-component documentation (from step 3)
- Dependency map (what depends on what)

</workflow>

<guardrails>

### Guardrails

- **Don't guess from file names** — read the actual code. File and function names lie. Read the implementation before writing any documentation claim.
- **Don't skip small files** — they often contain critical glue (re-exports, config, type definitions).
- **Don't document in batches from memory** — read each file fresh. Memory drifts.
- **Don't declare completeness without checking the manifest** — every file must be checked off.
- **Don't restate code without explaining WHY** — `// increments counter by 1` on `counter++` adds no value. Explain the reason behind the logic.

</guardrails>

<validation>

### Validation Checkpoint

Before declaring documentation complete, verify:

- [ ] Every file in the manifest was documented (none skipped)
- [ ] Progress was tracked explicitly throughout
- [ ] Cross-references between components are accurate
- [ ] Documentation was generated from code reading, not memory

</validation>

<example>

## Example

**Documenting `src/auth/`:**

**Manifest:** 4 files — `middleware.ts`, `session.ts`, `guards.ts`, `index.ts`

[1/4] `middleware.ts` — Authentication middleware. Extracts JWT from Authorization header, validates with `session.verify()`, attaches user to request context. Exports: `authMiddleware()`.

[2/4] `session.ts` — Session management. Creates/verifies JWTs using `jsonwebtoken`. Token lifetime: 24h. Exports: `createSession()`, `verify()`.

[3/4] `guards.ts` — Route guards. `requireAdmin()` checks `user.role === 'admin'`. `requireAuth()` checks session exists. Both use `authMiddleware` output.

[4/4] `index.ts` — Re-exports: `authMiddleware`, `requireAdmin`, `requireAuth`, `createSession`.

**Cross-reference:** `guards.ts` depends on `middleware.ts` output. `middleware.ts` depends on `session.ts`. `index.ts` is the public API surface.

</example>

## Usage Patterns

- "Document the authentication module"
- "Generate API reference docs for this package"
- "I need complete docs for everything in src/services/"
- "What does this module do and how do I use it?" (single-component mode)

## References

- **[Docgen Strategy](references/docgen-strategy.md)** — Five-step documentation workflow: scope target, build file manifest, analyze each file, cross-reference, synthesize
- **[Component Template](references/component-template.md)** — Per-component documentation structure with scaling guidance for utilities, services, and config files

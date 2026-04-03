# Docgen Strategy

## Documentation Workflow

### 1. Scope the Target

Identify what needs documenting: single file, directory, module, or entire package. List all files in scope before beginning any analysis.

### 2. Build the File Manifest

Enumerate every file to document with its path. This is the completeness checklist — no file gets dropped silently.

### 3. Analyze Each File

For each file in the manifest:

- Read the file fully
- Extract: purpose, public interface, dependencies, key patterns
- Document using the component template (see `component-template.md`)
- Mark the file as documented in the manifest

### 4. Cross-Reference

After all files are documented:

- Identify dependencies between components
- Note common patterns across the module
- Flag any circular dependencies or unclear boundaries

### 5. Synthesize

Produce the final documentation:

- Module overview (what it does, how components relate)
- Per-component documentation (from step 3)
- Usage examples (how to use the module as a consumer)
- Dependency map (what depends on what)

---

## Progress Tracking

Maintain a running count throughout the process: `[3/12 files documented]`

- Never skip a file — if a file is trivial, document it briefly but still mark it
- If a file is too large to analyze fully, note what was covered and what was deferred
- The manifest is the source of truth for completeness; every file must be checked off

---

## Anti-Patterns

**Documenting only the "interesting" files and skipping boilerplate**
Every file matters. Boilerplate files often contain configuration, defaults, or constraints that consumers need to know about.

**Writing documentation that restates code without explaining WHY**
`// increments counter by 1` on `counter++` adds no value. Explain the reason behind the logic, not the mechanics.

**Generating docs without reading the actual code (guessing from names)**
File and function names lie. Read the implementation before writing any documentation claim.

**Producing a wall of text with no structure**
Use the component template. Structure is what makes documentation usable. A reader should be able to scan to the section they need.

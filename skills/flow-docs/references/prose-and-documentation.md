# Technical Prose, User Guides, & Manifest-Driven Documentation

Standards for authoring accurate, scannable READMEs, user guides, module documentation, and specifications that pass cold-reader comprehension on the first read.

## Cold-Reader Comprehension Standard

A document passes comprehension only if a competent engineer or isolated agent session with **zero prior conversational context** can read the file on disk and immediately understand:

1. **Purpose**: What problem this system, module, or feature solves and why it exists.
2. **Mental Model & Boundaries**: Where the public seam sits, how data flows across components, and what is explicitly out of scope.
3. **Usage & Verification**: How to invoke, configure, or verify it with a copy-pasteable command or runnable example.
4. **Invariants & Edge Cases**: What constraints must hold and what non-obvious failure modes exist.

If understanding a section requires remembering an earlier chat turn or guessing unstated assumptions, rewrite the section until it is self-contained.

## Manifest-Driven Coverage Workflow (`[k/N files documented]`)

When documenting a module, package, or subsystem, never guess from filenames or document only the "interesting" files:

1. **Scope the Target**: Identify every file in scope (single module, directory, or package) before writing prose.
2. **Build the File Manifest**: Enumerate all target paths as a checklist and maintain a running progress counter (`[3/12 files documented]`). Every file—including configuration, defaults, and entry points—must be accounted for.
3. **Read Source First**: Read each file completely and extract its purpose, public interface, dependencies, key invariants, and failure modes.
4. **Scale Depth to Complexity**:
   - **Small utility or function (`~10–30` lines)**:
     - **Purpose**: One sentence stating what it does and why.
     - **Public Interface**: Signature, parameter types, and return value.
     - **Usage Example**: Minimal copy-pasteable call and expected output.
   - **Deep module or stateful service**:
     - **Purpose**: One sentence stating the responsibility hidden behind its seam.
     - **Public Interface**: Entry points, required vs. optional parameters, return types, and raised errors.
     - **Dependencies**: Internal seams and external boundary adapters.
     - **Key Invariants & Patterns**: Ordering rules, concurrency/state invariants, and rationale (`Reason:`).
     - **Usage Example**: Runnable example demonstrating the primary caller path.
     - **Gotchas**: Non-obvious edge cases (include only when real traps exist; never invent filler notes).
   - **Configuration or manifest file**:
     - **Purpose**: What subsystem the file configures.
     - **Key Settings**: Each setting, its default, and the runtime behavior it controls.
5. **Shard Across Subagents & Synthesize**: When a manifest spans multiple subsystems or chapters, assign disjoint file slices (`<= 6` source files per subagent) so every module receives concrete examples, signature tables, and edge-case coverage without coordinator context compaction; verify every `path/to/file::Symbol` reference on disk and confirm `[N/N files documented]`.
6. **Keep Living Markdown Synchronized in Present Tense**: Whenever a chapter finishes or a plan is revised, rewrite affected `docs/**`, `.agents/bundles/knowledge/**`, and `specs/<flow_id>/` roadmaps in place so readers see current state, remaining chapters, and the full plan—never chronological revision diaries.

## Progressive Guide & Tutorial Structure

Keep user-facing guides focused on **one concept per page** (`~80–200` Markdown lines) and structure each guide in four parts:

1. **Runnable Example First**: Lead with a complete, working code or CLI example rather than multi-paragraph background theory.
2. **Expected Output**: Show the exact terminal output, return value, or state transition produced by the example.
3. **Focused Walkthrough**: Explain the load-bearing lines and why they work in `3–5` short paragraphs. Never restate obvious language syntax (`// increments counter by 1`).
4. **Next Steps / Related Links**: Close with `2–3` links to adjacent guides, architecture chapters, or reference pages.

## Plain-Language & Anti-Bloat Prose Rules

| Rule | Bad (Bloated / Slop) | Good (Direct & Accurate) |
| --- | --- | --- |
| **State the mechanism directly** | *"This robust, seamless orchestrator leverages a multi-stage pipeline to effortlessly ensure reliability."* | *"The dispatcher validates task frontmatter, runs the declared test command, and records the commit SHA."* |
| **Pair rules with a one-line `Reason:`** | *"You must never mock internal classes because it is bad practice."* | *"Test through the module's public interface without mocking internal collaborators. Reason: internal mocks break during behavior-preserving refactors."* |
| **Semantic headings over numbered buzzwords** | *"## The Multi-Tier Validation Hierarchy"* | *"## Validation Checks"* |
| **Present-tense truth over chronological sediment** | *"In v1.2 we polled the database, then in v1.4 we used webhooks, and now we consume from the event stream."* | *"Workers consume order events from the Redis stream group using `XREADGROUP`."* |
| **Positive framing over negation** | *"Don't put implementation diagrams in `docs/`, don't use more than 6 nodes, and don't include private helpers."* | *"Keep diagrams in `docs/` conceptual (`4–6` nodes showing the user mental model), and place detailed module diagrams in `.agents/bundles/knowledge/architecture/`."* |

## Diagrams & Code Examples

- **Conceptual vs. Architectural Diagrams**:
  - In `README.md` and user-facing `docs/`, keep Mermaid diagrams high-level and conceptual (`4–6` nodes illustrating the user mental model without internal helper classes).
  - In `.agents/bundles/knowledge/architecture/`, include concrete module boundaries, seams, adapters, and dataflow edges anchored to `path/to/file::Symbol`.
  - Quote Mermaid node labels that contain parentheses, brackets, or colons (`id["Parser (POSIX sh)"]`).
- **Verified Code Snippets**:
  - Every code block in documentation must be runnable and free of syntax errors, placeholder ellipses (`...`) that hide required setup, or leaked test harness fixtures.

## Documentation Validation (`/flow:docs validate`)

When auditing repository documentation (`README.md`, `docs/**`, `.agents/bundles/**`, `.agents/skills/**`), verify:

1. **Structural Completeness**: No `[TODO]`, `[TBD]`, or `[NEEDS CLARIFICATION]` placeholders remain.
2. **Codebase Currency**: Every cited file path, CLI flag, make target, and `path/to/file::Symbol` exists in the current working tree.
3. **Link Integrity**: Every relative Markdown link resolves to an existing file and heading on disk.
4. **Prose Hygiene**: Zero AI puffery, numbered buzzwords, chronological sediment, or leaked internal workflow ceremony.

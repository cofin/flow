# Component Template

## Per-Component Documentation Structure

```markdown
## [Component Name]

**Purpose:** One sentence — what this component does and why it exists.

**Public Interface:**
- List every public function/class/export with signature and one-line description
- Note required vs optional parameters
- Note return types

**Dependencies:**
- What this component imports/requires
- What external services it talks to

**Key Patterns:**
- Notable design patterns used (repository pattern, middleware chain, etc.)
- Important invariants or constraints
- Thread safety / async considerations if relevant

**Usage Example:**
- Minimal working example showing the primary use case
- Should be copy-pasteable

**Notes:**
- Edge cases, gotchas, or non-obvious behavior
- Only include if they exist — don't invent notes for completeness
```

---

## Scaling the Template

Not every component needs every section. Match depth to complexity:

**10-line utility function:** Purpose + Public Interface + Usage Example
- The function is simple enough that its interface and an example tell the whole story
- Skip Dependencies, Key Patterns, and Notes unless genuinely notable

**Complex service class:** Full template
- A service with multiple methods, external dependencies, and stateful behavior warrants every section
- Key Patterns and Notes carry important information that the interface alone won't convey

**Configuration file:** Purpose + Key Patterns
- What this config controls and what each significant setting does
- No Public Interface (configs are data, not code) — Key Patterns explains what each setting affects

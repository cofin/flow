# General Code Style Principles

Core principles that apply across all languages and frameworks.

## Philosophy

### Simplicity Over Cleverness

- Prefer straightforward solutions over clever abstractions
- Only add complexity when it solves a real problem
- Three similar lines of code is better than a premature abstraction

### Avoid Over-Engineering

- Only make changes that are directly requested or clearly necessary
- Don't add features, refactor code, or make "improvements" beyond what was asked
- Don't add error handling for scenarios that can't happen
- Don't create helpers for one-time operations
- Don't design for hypothetical future requirements

### Code Should Be Self-Documenting

- Document *why* something is done, not *what*
- Keep documentation up-to-date with code changes
- Comments should add information, not restate the code

## Universal Rules

### Type Safety

- Use the strongest type system available in your language
- Prefer explicit types for public APIs
- Use type inference for obvious local contexts
- Avoid escape hatches (`any`, `unknown`, unsafe casts) unless necessary

### Null Handling

- Use language-native null safety features
- Prefer nullable types over sentinel values
- Handle null explicitly at system boundaries

### Error Handling

- Validate at system boundaries (user input, external APIs)
- Trust internal code and framework guarantees
- Don't add defensive checks for impossible conditions
- Map errors deterministically - never swallow or ignore

### Naming Conventions

| Concept | Convention |
|---------|------------|
| Types/Classes | `PascalCase` |
| Functions/Methods | `camelCase` (JS/TS), `snake_case` (Python/Rust) |
| Variables | `camelCase` (JS/TS), `snake_case` (Python/Rust) |
| Constants | `SCREAMING_SNAKE_CASE` |
| Private members | Leading underscore `_` (Python), visibility modifiers (others) |

### Import Organization

1. Standard library / built-ins
2. Third-party packages
3. Internal / local modules
4. Type-only imports (if applicable)

Alphabetize within each group.

## Code Organization

### File Structure

- One primary export per file
- Keep related code together
- Prefer flat structures over deep nesting

### Function Design

- Single responsibility
- Prefer pure functions where possible
- Keep functions short and focused
- Avoid side effects in return expressions

### Consistency

- Follow existing patterns in the codebase
- Match surrounding code style when editing
- Use automated formatters (`prettier`, `ruff`, `rustfmt`, `gofmt`)

## What NOT to Do

- Don't add docstrings/comments to code you didn't change
- Don't add backwards-compatibility hacks for unused code
- Don't use feature flags or shims when you can just change the code
- Don't add configuration for things that don't need it
- Don't create abstractions until you have 3+ use cases

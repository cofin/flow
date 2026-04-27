---
name: tracer
description: "Use when tracing execution paths, mapping dependencies, understanding unfamiliar code, following data flow, investigating end-to-end behavior, debugging call chains, or deciding which files to read next."
---

# Tracer

Systematic code exploration that builds understanding incrementally by tracing execution paths and mapping dependencies, rather than randomly reading files. Start at a known entry point and follow connections outward, building a map as you go.

<workflow>

## Workflow

### 1. Identify the Entry Point

What's the starting location? An API endpoint, a function call, a config file, a user action. Be specific — "the auth system" is too vague; `POST /api/auth/login` is an entry point.

### 2. Read the Entry Point

Understand what it does. Note every outgoing call or dependency.

### 3. Choose a Branch

Pick the most relevant outgoing connection to follow. Don't try to trace everything at once — choose the branch most likely to answer the question.

### 4. Follow the Chain

Read the next file/function. Note what it calls. Add to the map. Repeat.

### 5. Record the Path

Maintain a running trace: `A → B → C → D`. Include file paths and line numbers.

**What to record at each node:**

- File path and function/class name
- What it does (one sentence)
- What it calls (outgoing edges)
- Data transformations (what goes in, what comes out)

### 6. Decide: Deeper vs Wider

- **Branch understood** → backtrack and follow a different branch from an earlier node
- **Branch is critical** → keep going deeper
- **Question answered** → stop and synthesize

### 7. Synthesize the Map

When enough of the system is traced, describe the overall flow. Connect the nodes into a coherent narrative that answers the original question.

**When to stop:**

- Leaf reached (DB query, external API call, stdlib function)
- Boundary crossed (third-party library internals)
- Question answered
- Critical path covered

</workflow>

### Trace Mode Selection

Pick the mode based on the question being asked:

| Mode | Question | Best for |
|------|----------|----------|
| **Execution** | "What happens when X is called?" | Request flows, feature behavior |
| **Dependency** | "What depends on X?" | Impact analysis, refactoring |
| **Data** | "How does data get from A to B?" | Data pipeline debugging |

For complex investigations, start with execution trace for the happy path, then dependency trace on key components, then data trace on critical structures. See `references/trace-modes.md` for detailed mode descriptions.

<guardrails>

### Guardrails

- **Never read a file without knowing WHY.** Every file must be because the previous file pointed you there. If you can't say "I'm reading this because X imports/calls it," you're guessing.
- **Don't trace everything at once.** Choose branches deliberately. Breadth-first exploration builds no understanding.
- **Don't skip recording.** If you read a file and don't add it to the map, the trace is incomplete.
- **Don't cross boundaries unnecessarily.** Third-party library internals are rarely worth tracing unless the bug is there.

</guardrails>

<validation>

### Validation Checkpoint

Before presenting the trace, verify:

- [ ] Every file read was because a previous file pointed to it
- [ ] Path recorded with file paths and line numbers
- [ ] Map answers the original question
- [ ] Stop conditions were respected (didn't over-trace or under-trace)

</validation>

<example>

## Example

**Trace:** "What happens when `POST /api/users` is called?"

| Node | File | Function | Calls | Data |
|------|------|----------|-------|------|
| 1 | `src/routes/users.ts:14` | `createUser` | `UserService.create()` | `req.body → {name, email}` |
| 2 | `src/services/user.ts:42` | `create()` | `validate()`, `UserRepo.insert()` | `{name, email} → UserDTO` |
| 3 | `src/repos/user.ts:28` | `insert()` | `db.query()` | `UserDTO → SQL INSERT` |
| 4 | *(leaf)* | PostgreSQL | — | `INSERT INTO users...` |

**Path:** `POST /api/users` → `createUser` → `UserService.create` → `UserRepo.insert` → SQL INSERT.

</example>

## Complements

- **systematic-debugging** — provides the "understand the system" phase before hypothesis formation
- **brainstorming** — understanding existing code before designing changes
- **flow-research** — structured codebase investigation

## References

- **[Tracing Strategy](references/tracing-strategy.md)** — Core principle, seven-step workflow, what to record at each node, when to stop
- **[Trace Modes](references/trace-modes.md)** — Execution trace, dependency trace, data trace, and combining modes

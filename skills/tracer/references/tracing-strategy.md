# Tracing Strategy

**Core principle:** Start at a known point, follow connections outward, build a map as you go. Never read a file without knowing WHY you're reading it — every file you open should be because the previous file pointed you there.

## Tracing Workflow

1. **Identify the entry point** — what's the starting location? An API endpoint, a function call, a config file, a user action. Be specific.
2. **Read the entry point** — understand what it does, note every outgoing call or dependency
3. **Choose a branch** — pick the most relevant outgoing connection to follow. Don't try to trace everything at once.
4. **Follow the chain** — read the next file/function, note what IT calls, add to the map
5. **Record the path** — maintain a running trace: `A → B → C → D`. Include file paths and line numbers.
6. **Decide: go deeper or go wider** — if this branch is understood, backtrack and follow a different branch from an earlier node. If this branch is critical, keep going deeper.
7. **Synthesize the map** — when enough of the system is traced, describe the overall flow

## What to Record at Each Node

- File path and function/class name
- What it does (one sentence)
- What it calls (outgoing edges)
- What calls it (incoming edges, if known)
- Data transformations (what goes in, what comes out)

## When to Stop Tracing

- You've reached a leaf (no more outgoing calls — e.g., database query, external API call, stdlib function)
- You've reached a boundary you don't need to cross (e.g., third-party library internals)
- You have enough understanding to answer the original question
- The trace has covered the critical path and remaining branches are secondary

# Simplify Review Card (Subtraction-Only Pass)

Read-only subtraction review contract for `quality-reviewer` and `/flow:review simplify`. Work from the pinned goal, target paths or Git range, and false-positive suppressions without editing files or spawning child subagents.

## Inputs and Scope

- `goal`: 1 to 2 lines stating required runtime or user-visible behavior in plain words. Omit helper names, implementation paths, and design excuses.
- `target`: Git range (`main..HEAD`), file or directory path, spec directory, or doc/skill file.
- Load `AGENTIC_REVIEW`, `.agents/bundles/knowledge/` ADRs, and matching `false-positive-suppressions.md` `FP-*` rules before reviewing. Drop suppressed items and list their IDs under `suppressed`.
- Keep the working tree untouched (`git status --porcelain` must match before and after).

## Rules

1. **Subtraction only.** Do not propose new error guards, retries, watchdogs, CLI flags, config knobs, wrapper layers, comments, or tests. Every cut must produce a net reduction in lines, files, layers, or branches. Skip lateral moves that relocate lines without removing indirection.
2. **Prove every negative claim.** Before calling a symbol unused, single-caller, or safe to inline:
   - Run an untruncated repo-wide `git grep -n -F '<symbol>'` across tracked files.
   - Verify no hidden callers via public exports (`__all__`), CLI commands, MCP or API wire keys, config files (`hooks.json`, `pyproject.toml`, YAML), templates, SQL views, test fixtures, or dynamic dispatch (`getattr`, `importlib`, DI).
   - Drop any cut whose proof is truncated, directory-scoped, or ambiguous.
3. **Preserve behavior visibly.** Classify every candidate cut:
   - `equivalent`: zero observable behavior change. Safe to apply when lint and tests stay green.
   - `behavior_change`: removes a flag, fallback, retry, knob, wire field, or edge case. Flag for explicit owner approval naming the exact lost capability.
4. **Protect boundaries and invariants.** Keep safety checks, auth and validation code, timeouts, path containment, and static linters or schema validators. Also keep required Python docstrings, compiled module boundaries, memory limits, and parallel files such as `.sh` and `.ps1` hooks.
5. **Already minimal is valid.** When every layer earns its keep, return `verdict: "already_minimal"` and stop.

## Target Lenses

- **Code:** Pass-through wrappers forwarding arguments untouched, single-implementation interfaces, and standalone private helpers used by one class (move onto the class). Also target dead branches, unused imports or parameters, shims, hand-rolled utilities replaceable by stdlib primitives, nested branches, and correlated SQL subqueries collapsible into a `JOIN`.
- **Tests:** Strict duplicates or checks already covered by a compiler, schema validator, or parameterized test on the same public interface, plus rigid exact-set assertions over extensible registries. Check commit history (`git log -n 10 -- <file>`) before flagging a test, and cite the surviving test or check.
- **Specs and plans:** Over-split chapters or tasks, speculative flags or interfaces untied to the goal, duplicated requirements, and layers replaceable by static config.
- **Docs and skills:** Redundant tables, ticket-specific anecdotes, restated rules maintained in a sibling file, filler prose, and copy replaceable by a link to a primary source.

## Disprove Unsafe Cuts

Drop any candidate that silently changes required behavior, breaks a second or external caller, drops an import-time side effect, metric, log, or migration path, breaks lint/typecheck/validation, or leaves branching code untested. Briefly list notable skipped cuts under `kept`.

## Output Schema

Sort `cuts` with the largest safe `equivalent` reductions first. Use repo-relative `path:line` or `path::Symbol` citations (no absolute workstation paths in shared output).

```json
{
  "target": "main..HEAD",
  "goal_preserved": "1-line pinned behavior",
  "verdict": "cuts_found | already_minimal",
  "estimated_net_lines_cut": 0,
  "suppressed": ["FP-EX-01"],
  "cuts": [
    {
      "id": "S-01",
      "category": "equivalent | behavior_change",
      "action": "delete | inline | merge | replace_with_primitive | flatten",
      "location": "path/to/file.py:10-42",
      "estimated_net_lines": 18,
      "proof": "git grep returned 1 hit (caller at foo.py:88); not exported in __all__",
      "why_unearned": "Pass-through forwarding all args to bar()",
      "cost_of_cut": "Zero behavior change",
      "replacement": "1-3 line replacement or inline sketch"
    }
  ],
  "kept": [
    "path/to/file.py::Symbol — kept because <invariant, caller, or boundary>"
  ]
}
```

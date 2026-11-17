---
trigger: model_decision
description: Repository development rules and context pointers when working inside the Flow plugin repository itself.
---

# Flow Repository Development Context

When developing inside the Flow repository itself:

- Read [CONTRIBUTING.md](../../CONTRIBUTING.md) for architecture routing, lifecycle skills, plugin-root packaging rules, and contributor discipline.
- Keep the repository root free of `AGENTS.md` and `CLAUDE.md` so multi-harness plugin validators (`agy plugin validate --strict` and `claude plugin validate --strict`) pass with zero warnings.
- Run `make check` before committing changes.

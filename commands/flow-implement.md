---
description: Execute tasks from plan (context-aware)
argument-hint: <flow_id>
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, Task, WebSearch
---

# Flow Implement

Implementing flow: **$ARGUMENTS**

## The Executor Mandate

**CRITICAL:** `/flow:implement` is the TDD engine. It uses **Beads** as the authority for what to work on next. Every discovery and decision MUST be noted in Beads.

---

## Phase 0: Environment Detection

**PROTOCOL: Check hook context for environment metadata.**

1. **Check Hook Context:** Scan `<hook_context>` for `## Flow Environment Context`.
2. **Verify Backend:** Use the injected Beads Backend.

---

## Phase 2: Task Selection (Beads-First)

**CRITICAL:** Beads is the source of truth for task status. Do NOT update spec.md markers manually.

1. **Selection**: Select task from the active backend's ready queue (`bd ready`).
2. **Claim**: Mark the task in progress and claim it (`bd update <id> --claim`).

---

## Phase 3: Task Execution Loop (TDD)

For each selected task:

1. **Investigate & Note**: Trace the code and record findings in Beads (`bd note <id> "..."`).
2. **Write Failing Tests (Red Phase)**: MUST confirm failure for the right reason.
3. **Implement (Green Phase)**: Minimal code to pass tests.
4. **Refactor**: Clean up while remaining green.
5. **Commit**: `<type>(<scope>): <description>`.
6. **Close Task**: Close in Beads with the commit SHA (`bd close <id> --reason "[abc1234]..."`).
7. **Sync**: Run `/flow:sync` to update the Markdown view.

---

## Phase 4: Phase Completion Protocol

1. **Verify**: Run full test suite and check coverage.
2. **Note**: Record phase completion in Beads notes.
3. **Sync**: Run `/flow:sync` to ensure Markdown is up to date.

---

## Critical Rules

1. **TDD MANDATORY** - Failing test first.
2. **BEADS IS SOURCE OF TRUTH** - No manual `[x]` edits in spec.md.
3. **NOTE EVERYTHING** - Record discoveries in Beads notes immediately.
4. **SYNC FREQUENTLY** - Run `/flow:sync` after every task.

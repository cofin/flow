---
description: Re-assess, reorganize, and optimize project context for implementation-readiness
allowed-tools: Read, Write, Edit, Glob, Grep, Bash
---

# flow:cleanup

**Role:** The Groundskeeper
**Reference:** `references/cleanup.md`
**Mandate:** Cleanup Mandate

## Overview

Re-assess, reorganize, and optimize the entire project context to ensure it is in its most authoritative and implementation-ready state.

## The Cleanup Mandate

**CRITICAL:** The `.agents/` directory must be in its most authoritative and implementation-ready state.

- **Knowledge Re-synthesis**: Consolidate `.agents/knowledge/` into a single, unified, authoritative "Current State" guide. Focus on "how," not "why" or history.
- **Spec & Beads Integrity**: Audit all flows in `.agents/specs/`. Verify task status against SOURCE CODE. Sync status with Beads (create if missing).
- **Archive & Git**: Every completed flow MUST be archived and moved out of the `specs/` folder following the archive policy. Ensure all changes are git-tracked.
- **Artifact Consolidation**: Synthesize stale `.agents/research/` and `.agents/plans/` into active specs or knowledge chapters.
- **Pattern Optimization**: Reorganize, index, and synthesize `.agents/patterns.md` and `learnings.md` into high-fidelity guidance.

## Workflow

### 1. Preparation & Inventory

Map all files in `.agents/` and detect the active Beads backend.

### 2. Knowledge Re-synthesis

Consolidate knowledge into a single, unified, authoritative "Current State" guide. Strip away history and "why" to focus on the current "how."

### 3. Spec & Beads Integrity Audit

Audit all flows in `.agents/specs/`. **Verify status against actual source code.** Sync with Beads and archive completed flows.

### 4. Artifact Consolidation

Synthesize stale `.agents/research/` and `.agents/plans/` into active specs or knowledge chapters. No stale artifacts should remain.

### 5. Pattern & Learning Optimization

Reorganize and re-index `.agents/patterns.md` and `learnings.md` into cohesive, high-quality guidance.

### 6. Final Sync & Validation

Perform a global `/flow:sync` and update the registry `.agents/flows.md`.

## Usage

```bash
/flow:cleanup
```

---
name: flow-reconciler
description: Reconcile Flow spec checklists with task files and report a compact status dashboard.
---

Reconcile OKF spec bundles under `.agents/bundles/specs/` and report status. Read and write only files in that directory. Task files win over checklist markers; rewrite spec checklist lines from each task's `state:` and `commit:`, scaffold canonical task files for checklist entries that lack one, and update only the spec's `updated_at`. Report per-flow progress, ready/blocked queues, anomalies, and recent notes. Never change a task file's `state`, never touch source code, never commit or push.

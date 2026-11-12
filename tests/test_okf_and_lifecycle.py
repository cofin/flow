"""Tests for OKF v0.2 bundle validation, chaptered blueprints, and Flow lifecycle reference integrity."""

from __future__ import annotations

import ast
import asyncio
import json
import os
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from tools.validate import COMPACT_TASK_HEADINGS, REPO_ROOT, REQUIRED_TASK_HEADINGS, validate_okf_bundle
from tools.worktree_env import (
    bootstrap_worktree,
    inspect_worktree,
    is_link_or_junction,
    sync_main_bundle_to_worktree,
    sync_worktree_bundle_to_main,
)

SIX_CHAPTER_IDS: tuple[str, ...] = (
    "ch01-tokens",
    "ch02-middleware",
    "ch03-sessions",
    "ch04-audit",
    "ch05-benchmarks",
    "ch06-docs-and-okf",
)

FORBIDDEN_DOCS_LOCKIN_TERMS: tuple[str, ...] = (
    "zensical",
    "mkdocstrings",
    "griffe",
    "shibuya",
)

FORBIDDEN_EXTERNAL_AND_PROJECT_TERMS: tuple[str, ...] = (
    "elephant",
    "goldfish",
    "conductor",
    "heilmeier",
    "fowler",
    "pocock",
    "docgen",
    "grilling",
    "tracer-bullet",
    "writing-for-agents",
    "tools/validate.py",
    "make validate",
    "make release",
    "bump-my-version",
    "single-file-validator",
    "flow-session-start",
    "v0.24",
    "v0.25",
    "zensical",
    "mkdocstrings",
)


def _render_task_blueprint(
    *,
    task_id: str,
    chapter_id: str,
    state: str = "pending",
    commit: str = "null",
    read_set: list[str] | None = None,
    estimated_loc: int = 120,
    omit_heading: str | None = None,
) -> str:
    """Render an OKF v0.2 Task worksheet with all required 8-section blueprint headings."""
    reads = read_set if read_set is not None else ["src/auth/tokens.py", "tests/auth/test_tokens.py"]
    reads_yaml = "\n".join(f"  - {entry}" for entry in reads)
    sections = [
        ("Objective & Scope Boundary", "Deliver the vertical slice within bounded scope[^task-src]."),
        ("Bounded Read Manifest", "- `src/auth/tokens.py::TokenSigner`"),
        ("Symbol & Signature Contracts", "```python\ndef verify_token(raw: str) -> Principal: ...\n```"),
        ("Edge Cases & Error Semantics", "| Case | Behavior |\n| --- | --- |\n| Empty token | Raise `AuthError` |"),
        (
            "Public-Seam Test Blueprint",
            "| Case | Input | Expected |\n| --- | --- | --- |\n| Expired | `tok_exp` | `AuthError` |",
        ),
        ("Verification", "```bash\nuv run pytest tests/auth/test_tokens.py\n```"),
        ("Acceptance Criteria", "- [ ] Verifies token signatures via public seam."),
        ("Notes & Discoveries", "- [2026-11-06 12:00] Initial vertical-slice blueprint."),
    ]
    body_blocks = [f"## {heading}\n\n{content}" for heading, content in sections if f"## {heading}" != omit_heading]
    body_joined = "\n\n".join(body_blocks)
    return (
        "---\n"
        "type: Task\n"
        f"id: {task_id}\n"
        f"chapter_id: {chapter_id}\n"
        f"title: Execute {task_id}\n"
        f"description: Vertical slice blueprint for {task_id}.\n"
        "status: stable\n"
        f"state: {state}\n"
        "priority: P1\n"
        "verification_strategy: behavior_tdd\n"
        "read_set:\n"
        f"{reads_yaml}\n"
        f"estimated_loc: {estimated_loc}\n"
        f"commit: {commit}\n"
        "sources:\n"
        "  - id: task-src\n"
        "    resource: src/auth/tokens.py::TokenSigner\n"
        "    title: Token signer seam\n"
        "tags: [feature, auth, tdd]\n"
        "---\n\n"
        f"{body_joined}\n\n"
        "[^task-src]: `src/auth/tokens.py::TokenSigner` — Token signer seam.\n"
    )


def _seed_valid_multichapter_bundle(tmp_path: Path) -> Path:
    """Create a valid 6-chapter OKF v0.2 bundle in ``tmp_path`` and return ``bundle_dir``."""
    bundle_dir = tmp_path / ".agents" / "bundles"
    knowledge_dir = bundle_dir / "knowledge" / "patterns"
    flow_dir = bundle_dir / "specs" / "auth-refactor"
    chapters_dir = flow_dir / "chapters"
    knowledge_dir.mkdir(parents=True)
    chapters_dir.mkdir(parents=True)

    (bundle_dir / "index.md").write_text(
        '---\nokf_version: "0.2"\nbundle: sample-repo\n---\n\n# Sample Bundle\n\n'
        "* [Serialization](knowledge/patterns/index.md)\n"
        "* [Auth Refactor](specs/auth-refactor/spec.md)\n",
        encoding="utf-8",
    )
    (bundle_dir / "log.md").write_text("## 2026-11-06 — Setup\n\nInitialized bundle.\n", encoding="utf-8")
    (knowledge_dir / "index.md").write_text(
        "# Patterns\n\n* [Serialization](serialization.md) — Centralized msgspec JSON helpers.\n",
        encoding="utf-8",
    )
    (knowledge_dir / "serialization.md").write_text(
        "---\n"
        "type: Pattern\n"
        "title: Serialization\n"
        "description: Centralized msgspec JSON helpers.\n"
        "status: stable\n"
        "tags: [serialization, json]\n"
        "sources:\n"
        "  - id: ser-1\n"
        "    resource: src/ser.py::encode_json\n"
        "    title: Serializer\n"
        "---\n\n"
        "<!-- truth: start -->\n"
        "- Use `encode_json`[^ser-1].\n"
        "<!-- truth: end -->\n\n"
        "```yaml\n"
        "---\n"
        "example_frontmatter_in_fence: allowed\n"
        "---\n"
        "```\n\n"
        "[^ser-1]: `src/ser.py::encode_json` — Serializer.\n",
        encoding="utf-8",
    )

    index_lines = ["# Chapters: Auth Refactor", ""]
    checklist_lines: list[str] = []
    for idx, ch_id in enumerate(SIX_CHAPTER_IDS, start=1):
        ch_dir = chapters_dir / ch_id
        tasks_dir = ch_dir / "tasks"
        tasks_dir.mkdir(parents=True)
        is_done = ch_id == "ch01-tokens"
        is_empirical = ch_id == "ch05-benchmarks"
        ch_state = "completed" if is_done else ("active" if ch_id == "ch02-middleware" else "planned")
        planning_status = "empirical_dependent" if is_empirical else "complete"
        replan_line = (
            'replan_trigger: "Latency p99 baseline from ch04-audit"' if is_empirical else "replan_trigger: null"
        )
        deps_line = "depends_on_chapters: [ch04-audit]" if is_empirical else "depends_on_chapters: []"
        rev_line = "last_reviewed_commit: 1111111" if is_done else "last_reviewed_commit: null"
        task_state = "completed" if is_done else "pending"
        task_commit = "1111111" if is_done else "null"
        task_mark = "[x] [1111111]" if is_done else "[ ]"
        task_filename = f"t0{idx}-slice.md"

        (ch_dir / "spec.md").write_text(
            "---\n"
            "type: Spec\n"
            f"parent_flow: auth-refactor\n"
            f"chapter_id: {ch_id}\n"
            f"title: Chapter {ch_id}\n"
            f"description: Scoped blueprint for {ch_id}.\n"
            "status: stable\n"
            f"state: {ch_state}\n"
            f"planning_status: {planning_status}\n"
            f"{deps_line}\n"
            f"{replan_line}\n"
            f"{rev_line}\n"
            "sources:\n"
            "  - id: ch-src\n"
            "    resource: src/auth/tokens.py::TokenSigner\n"
            "    title: Token signer\n"
            "tags: [feature, auth]\n"
            "---\n\n"
            "<!-- truth: start -->\n"
            f"- Chapter `{ch_id}` preserves public seam invariants[^ch-src].\n"
            "<!-- truth: end -->\n\n"
            "## 1. Specification, Context & Provenance\n\nScoped context.\n\n"
            "## 2. Requirements, Concrete Contracts & Architecture\n\nContracts.\n\n"
            "## 3. Documentation & OKF Knowledge Plan\n\n"
            "- [0/1 files documented] [Serialization](../../../../knowledge/patterns/serialization.md)\n\n"
            "## 4. Requirement-to-Task Traceability Matrix\n\n| Req | Task |\n| --- | --- |\n| R1 | t01 |\n\n"
            f"## 5. Implementation Plan\n\n- {task_mark} [t0{idx}](tasks/{task_filename}) — Deliver slice\n\n"
            "## 6. Current State & Remaining Plan Snapshot\n\nPresent-tense chapter snapshot.\n\n"
            "[^ch-src]: `src/auth/tokens.py::TokenSigner` — Token signer.\n",
            encoding="utf-8",
        )
        (tasks_dir / task_filename).write_text(
            _render_task_blueprint(
                task_id=f"auth-refactor:{ch_id}:t0{idx}",
                chapter_id=ch_id,
                state=task_state,
                commit=task_commit,
            ),
            encoding="utf-8",
        )
        index_lines.append(f"* [{ch_id}]({ch_id}/spec.md) — [{ch_state}] Present-tense scope for {ch_id}.")
        if is_done:
            checklist_lines.append(f"- [x] [1111111] [{ch_id}](chapters/{ch_id}/spec.md) — Completed chapter")
        elif is_empirical:
            checklist_lines.append(
                f"- [ ] [{ch_id}](chapters/{ch_id}/spec.md) — Benchmarks [empirical_dependent: ch04-audit p99]"
            )
        else:
            checklist_lines.append(f"- [ ] [{ch_id}](chapters/{ch_id}/spec.md) — Remaining chapter")

    (chapters_dir / "index.md").write_text("\n".join(index_lines) + "\n", encoding="utf-8")
    chapters_yaml = ", ".join(SIX_CHAPTER_IDS)
    checklist_block = "\n".join(checklist_lines)
    (flow_dir / "spec.md").write_text(
        "---\n"
        "type: Spec\n"
        "flow_id: auth-refactor\n"
        "title: Auth Refactor\n"
        "description: Multi-chapter authentication architecture upgrade.\n"
        "status: stable\n"
        "state: active\n"
        "has_chapters: true\n"
        f"chapters: [{chapters_yaml}]\n"
        "current_chapter: ch02-middleware\n"
        "current_task: auth-refactor:ch02-middleware:t02\n"
        "last_reviewed_chapter: ch01-tokens\n"
        "last_reviewed_commit: 1111111\n"
        "sources:\n"
        "  - id: root-src\n"
        "    resource: src/auth/tokens.py::TokenSigner\n"
        "    title: Root seam\n"
        "tags: [feature, auth]\n"
        "---\n\n"
        "<!-- truth: start -->\n"
        "- Full roadmap across 6 chapters with zero scope truncation[^root-src].\n"
        "<!-- truth: end -->\n\n"
        "## 1. Specification, Context & Provenance\n\nSee [chapter catalog](chapters/index.md).\n\n"
        "## 2. Requirements, Concrete Contracts & Architecture\n\nCross-chapter contracts.\n\n"
        "## 3. Documentation & OKF Knowledge Plan\n\n- [1/2 files documented]\n\n"
        "## 4. Requirement-to-Task Traceability Matrix\n\n| Req | Chapter |\n| --- | --- |\n| R1 | ch01-tokens |\n\n"
        f"## 5. Implementation Plan\n\n{checklist_block}\n\n"
        "## 6. Current State & Remaining Plan Snapshot\n\nChapter 1 verified at `1111111`; chapters 2–6 remain.\n\n"
        "[^root-src]: `src/auth/tokens.py::TokenSigner` — Root seam.\n",
        encoding="utf-8",
    )
    return bundle_dir


def _mutate_missing_footnote(bundle_dir: Path) -> None:
    """Write a knowledge chapter whose declared source id has no matching footnote."""
    (bundle_dir / "knowledge" / "patterns" / "serialization.md").write_text(
        "---\n"
        "type: Pattern\n"
        "title: Serialization\n"
        "description: Centralized msgspec JSON helpers.\n"
        "sources:\n"
        "  - id: missing-fn\n"
        "    resource: src/ser.py\n"
        "---\n\nBody without footnote definition.\n",
        encoding="utf-8",
    )


def _mutate_subdir_index_frontmatter(bundle_dir: Path) -> None:
    """Inject forbidden YAML frontmatter into a subdirectory index.md file."""
    ch_index = bundle_dir / "specs" / "auth-refactor" / "chapters" / "index.md"
    ch_index.write_text("---\ntitle: Invalid\n---\n\n" + ch_index.read_text(encoding="utf-8"), encoding="utf-8")


def _mutate_log_frontmatter(bundle_dir: Path) -> None:
    """Inject forbidden YAML frontmatter into log.md."""
    log_path = bundle_dir / "log.md"
    log_path.write_text("---\ntitle: Log\n---\n\n" + log_path.read_text(encoding="utf-8"), encoding="utf-8")


def _mutate_body_hr(bundle_dir: Path) -> None:
    """Append a standalone --- horizontal rule outside code fences in spec.md."""
    spec_path = bundle_dir / "specs" / "auth-refactor" / "spec.md"
    spec_path.write_text(spec_path.read_text(encoding="utf-8") + "\n---\n\nTrailing text.\n", encoding="utf-8")


def _mutate_revision_history_heading(bundle_dir: Path) -> None:
    """Append a forbidden ## Revision History section to a living spec.md."""
    spec_path = bundle_dir / "specs" / "auth-refactor" / "spec.md"
    spec_path.write_text(spec_path.read_text(encoding="utf-8") + "\n## Revision History\n\nOld.\n", encoding="utf-8")


def _mutate_struck_checklist(bundle_dir: Path) -> None:
    """Add a struck-through obsolete checklist item instead of rewriting in place."""
    spec_path = bundle_dir / "specs" / "auth-refactor" / "spec.md"
    spec_path.write_text(spec_path.read_text(encoding="utf-8") + "\n- [ ] ~~Obsolete item~~\n", encoding="utf-8")


def _mutate_invalid_okf_status(bundle_dir: Path) -> None:
    """Place workflow state 'active' inside OKF document maturity key 'status'."""
    target = bundle_dir / "knowledge" / "patterns" / "serialization.md"
    target.write_text(target.read_text(encoding="utf-8").replace("status: stable", "status: active"), encoding="utf-8")


def _mutate_state_word_in_tags(bundle_dir: Path) -> None:
    """Add a forbidden workflow state word into tags."""
    target = bundle_dir / "knowledge" / "patterns" / "serialization.md"
    target.write_text(
        target.read_text(encoding="utf-8").replace("tags: [serialization, json]", "tags: [serialization, completed]"),
        encoding="utf-8",
    )


def _mutate_oversized_truth_block(bundle_dir: Path) -> None:
    """Expand a truth block past the 40-line cap."""
    target = bundle_dir / "knowledge" / "patterns" / "serialization.md"
    forty_one_lines = "\n".join(f"- Invariant {i}[^ser-1]." for i in range(41))
    target.write_text(
        target.read_text(encoding="utf-8").replace("- Use `encode_json`[^ser-1].", forty_one_lines),
        encoding="utf-8",
    )


def _mutate_broken_relative_link(bundle_dir: Path) -> None:
    """Insert a broken relative Markdown link inside a bundle spec."""
    spec_path = bundle_dir / "specs" / "auth-refactor" / "spec.md"
    spec_path.write_text(
        spec_path.read_text(encoding="utf-8") + "\nSee [missing](chapters/ch99-missing/spec.md).\n",
        encoding="utf-8",
    )


def _mutate_five_tasks_in_chapter(bundle_dir: Path) -> None:
    """Create 5 task worksheets inside a single chapter to exceed MAX_CHAPTER_TASKS (4)."""
    ch_dir = bundle_dir / "specs" / "auth-refactor" / "chapters" / "ch02-middleware"
    tasks_dir = ch_dir / "tasks"
    extra_lines: list[str] = []
    for num in range(3, 7):
        fname = f"t0{num}-extra.md"
        (tasks_dir / fname).write_text(
            _render_task_blueprint(task_id=f"auth-refactor:ch02:t0{num}", chapter_id="ch02-middleware"),
            encoding="utf-8",
        )
        extra_lines.append(f"- [ ] [t0{num}](tasks/{fname}) — Extra slice")
    ch_spec = ch_dir / "spec.md"
    ch_spec.write_text(ch_spec.read_text(encoding="utf-8") + "\n" + "\n".join(extra_lines) + "\n", encoding="utf-8")


def _mutate_missing_task_heading(bundle_dir: Path) -> None:
    """Omit one of the 8 required Task blueprint headings."""
    task_path = bundle_dir / "specs" / "auth-refactor" / "chapters" / "ch02-middleware" / "tasks" / "t02-slice.md"
    task_path.write_text(
        _render_task_blueprint(
            task_id="auth-refactor:ch02-middleware:t02",
            chapter_id="ch02-middleware",
            omit_heading="## Edge Cases & Error Semantics",
        ),
        encoding="utf-8",
    )


def _mutate_oversized_read_set(bundle_dir: Path) -> None:
    """Declare 7 files in read_set to exceed MAX_TASK_READ_SET (6)."""
    task_path = bundle_dir / "specs" / "auth-refactor" / "chapters" / "ch02-middleware" / "tasks" / "t02-slice.md"
    task_path.write_text(
        _render_task_blueprint(
            task_id="auth-refactor:ch02-middleware:t02",
            chapter_id="ch02-middleware",
            read_set=[f"src/mod_{idx}.py" for idx in range(7)],
        ),
        encoding="utf-8",
    )


def _mutate_oversized_estimated_loc(bundle_dir: Path) -> None:
    """Declare estimated_loc > 250 on a task worksheet."""
    task_path = bundle_dir / "specs" / "auth-refactor" / "chapters" / "ch02-middleware" / "tasks" / "t02-slice.md"
    task_path.write_text(
        _render_task_blueprint(
            task_id="auth-refactor:ch02-middleware:t02",
            chapter_id="ch02-middleware",
            estimated_loc=300,
        ),
        encoding="utf-8",
    )


def _mutate_chapter_missing_from_index(bundle_dir: Path) -> None:
    """Remove ch03-sessions from chapters/index.md while leaving it on disk."""
    ch_index = bundle_dir / "specs" / "auth-refactor" / "chapters" / "index.md"
    filtered = [ln for ln in ch_index.read_text(encoding="utf-8").splitlines() if "ch03-sessions" not in ln]
    ch_index.write_text("\n".join(filtered) + "\n", encoding="utf-8")


def _mutate_chapter_missing_from_root_spec(bundle_dir: Path) -> None:
    """Remove ch03-sessions from the root spec.md body roadmap while leaving it on disk."""
    spec_path = bundle_dir / "specs" / "auth-refactor" / "spec.md"
    filtered = [ln for ln in spec_path.read_text(encoding="utf-8").splitlines() if "- [ ] [ch03-sessions]" not in ln]
    spec_path.write_text("\n".join(filtered) + "\n", encoding="utf-8")


def _mutate_completed_chapter_without_review_sha(bundle_dir: Path) -> None:
    """Clear last_reviewed_commit on a completed chapter spec."""
    ch_spec = bundle_dir / "specs" / "auth-refactor" / "chapters" / "ch01-tokens" / "spec.md"
    ch_spec.write_text(
        ch_spec.read_text(encoding="utf-8").replace("last_reviewed_commit: 1111111", "last_reviewed_commit: null"),
        encoding="utf-8",
    )


def _mutate_completed_chapter_unmarked_in_root(bundle_dir: Path) -> None:
    """Leave completed chapter ch01-tokens unchecked [ ] in root spec.md."""
    spec_path = bundle_dir / "specs" / "auth-refactor" / "spec.md"
    spec_path.write_text(
        spec_path.read_text(encoding="utf-8").replace("- [x] [1111111] [ch01-tokens]", "- [ ] [ch01-tokens]"),
        encoding="utf-8",
    )


def _mutate_current_chapter_stuck_on_completed(bundle_dir: Path) -> None:
    """Point current_chapter at already-completed ch01-tokens while ch02..ch06 remain open."""
    spec_path = bundle_dir / "specs" / "auth-refactor" / "spec.md"
    spec_path.write_text(
        spec_path.read_text(encoding="utf-8").replace(
            "current_chapter: ch02-middleware", "current_chapter: ch01-tokens"
        ),
        encoding="utf-8",
    )


def _mutate_empirical_chapter_missing_trigger(bundle_dir: Path) -> None:
    """Clear replan_trigger on an empirical_dependent chapter."""
    ch_spec = bundle_dir / "specs" / "auth-refactor" / "chapters" / "ch05-benchmarks" / "spec.md"
    ch_spec.write_text(
        ch_spec.read_text(encoding="utf-8").replace(
            'replan_trigger: "Latency p99 baseline from ch04-audit"', "replan_trigger: null"
        ),
        encoding="utf-8",
    )


def _mutate_empirical_chapter_missing_deps(bundle_dir: Path) -> None:
    """Clear depends_on_chapters on an empirical_dependent chapter."""
    ch_spec = bundle_dir / "specs" / "auth-refactor" / "chapters" / "ch05-benchmarks" / "spec.md"
    ch_spec.write_text(
        ch_spec.read_text(encoding="utf-8").replace("depends_on_chapters: [ch04-audit]", "depends_on_chapters: []"),
        encoding="utf-8",
    )


def _mutate_task_checklist_marker_drift(bundle_dir: Path) -> None:
    """Mark task worksheet completed while leaving its owning chapter checklist unchecked [ ]."""
    task_path = bundle_dir / "specs" / "auth-refactor" / "chapters" / "ch02-middleware" / "tasks" / "t02-slice.md"
    task_path.write_text(
        _render_task_blueprint(
            task_id="auth-refactor:ch02-middleware:t02",
            chapter_id="ch02-middleware",
            state="completed",
            commit="2222222",
        ),
        encoding="utf-8",
    )


def _mutate_mixed_root_tasks_and_chapters(bundle_dir: Path) -> None:
    """Add a root specs/<flow_id>/tasks/*.md worksheet alongside chapters/."""
    root_tasks = bundle_dir / "specs" / "auth-refactor" / "tasks"
    root_tasks.mkdir(parents=True)
    (root_tasks / "t99-mixed.md").write_text(
        _render_task_blueprint(task_id="auth-refactor:t99", chapter_id="root"),
        encoding="utf-8",
    )


def _mutate_degraded_without_reason(bundle_dir: Path) -> None:
    """Set planning_quality: degraded on root spec.md without planning_degraded_reason."""
    spec_path = bundle_dir / "specs" / "auth-refactor" / "spec.md"
    spec_path.write_text(
        spec_path.read_text(encoding="utf-8").replace(
            "state: active",
            "state: active\nplanning_quality: degraded",
        ),
        encoding="utf-8",
    )


def _mutate_completed_root_with_open_chapters(bundle_dir: Path) -> None:
    """Mark root spec.md completed while chapters ch02..ch06 remain planned/active."""
    spec_path = bundle_dir / "specs" / "auth-refactor" / "spec.md"
    spec_path.write_text(
        spec_path.read_text(encoding="utf-8").replace("state: active", "state: completed"),
        encoding="utf-8",
    )


def _mutate_completed_chapter_with_open_task(bundle_dir: Path) -> None:
    """Mark ch02-middleware completed while its task t02-slice.md remains pending."""
    ch_spec = bundle_dir / "specs" / "auth-refactor" / "chapters" / "ch02-middleware" / "spec.md"
    ch_spec.write_text(
        ch_spec.read_text(encoding="utf-8")
        .replace("state: active", "state: completed")
        .replace("last_reviewed_commit: null", "last_reviewed_commit: 2222222"),
        encoding="utf-8",
    )


def _mutate_unauthorized_deferred_task(bundle_dir: Path) -> None:
    """Mark task t02-slice.md deferred without deferred_by: user."""
    ch_spec = bundle_dir / "specs" / "auth-refactor" / "chapters" / "ch02-middleware" / "spec.md"
    ch_spec.write_text(
        ch_spec.read_text(encoding="utf-8").replace("- [ ] [t02]", "- [-] [t02]"),
        encoding="utf-8",
    )
    task_path = bundle_dir / "specs" / "auth-refactor" / "chapters" / "ch02-middleware" / "tasks" / "t02-slice.md"
    task_path.write_text(
        _render_task_blueprint(
            task_id="auth-refactor:ch02-middleware:t02",
            chapter_id="ch02-middleware",
            state="deferred",
        ),
        encoding="utf-8",
    )


def _mutate_unauthorized_deferred_chapter(bundle_dir: Path) -> None:
    """Mark chapter ch03-sessions skipped without deferred_by: user."""
    ch_spec = bundle_dir / "specs" / "auth-refactor" / "chapters" / "ch03-sessions" / "spec.md"
    ch_spec.write_text(
        ch_spec.read_text(encoding="utf-8").replace("state: planned", "state: skipped"),
        encoding="utf-8",
    )


BUNDLE_REJECTION_CASES: tuple[tuple[str, Callable[[Path], None], str], ...] = (
    ("missing-footnote", _mutate_missing_footnote, "source id 'missing-fn' missing matching [^missing-fn]: footnote"),
    ("subdir-index-frontmatter", _mutate_subdir_index_frontmatter, "index.md must not contain YAML frontmatter"),
    ("log-frontmatter", _mutate_log_frontmatter, "log.md: log.md must not contain YAML frontmatter"),
    ("body-hr", _mutate_body_hr, "standalone '---' horizontal rule forbidden in bundle Markdown body"),
    (
        "revision-history-heading",
        _mutate_revision_history_heading,
        "historical revision/changelog heading forbidden in present-tense bundle file",
    ),
    ("struck-checklist", _mutate_struck_checklist, "struck-through checklist item forbidden"),
    ("invalid-okf-status", _mutate_invalid_okf_status, "invalid OKF status 'active'"),
    ("state-word-in-tags", _mutate_state_word_in_tags, "tag 'completed' encodes lifecycle state/status"),
    ("oversized-truth-block", _mutate_oversized_truth_block, "truth block has 41 lines (exceeds 40-line limit)"),
    ("broken-relative-link", _mutate_broken_relative_link, "broken relative link 'chapters/ch99-missing/spec.md'"),
    ("five-tasks-in-chapter", _mutate_five_tasks_in_chapter, "found 5 task worksheets (exceeds 4-task chapter cap"),
    (
        "missing-task-heading",
        _mutate_missing_task_heading,
        "missing required Task blueprint heading '## Edge Cases & Error Semantics'",
    ),
    ("oversized-read-set", _mutate_oversized_read_set, "read_set has 7 entries (exceeds 6-file cap)"),
    ("oversized-estimated-loc", _mutate_oversized_estimated_loc, "estimated_loc 300 exceeds 250-line cap"),
    (
        "chapter-missing-from-index",
        _mutate_chapter_missing_from_index,
        "chapters/index.md: missing entry for chapter 'ch03-sessions'",
    ),
    (
        "chapter-missing-from-root-spec",
        _mutate_chapter_missing_from_root_spec,
        "spec.md: full-plan body/checklist missing chapter 'ch03-sessions'",
    ),
    (
        "completed-chapter-without-review-sha",
        _mutate_completed_chapter_without_review_sha,
        "state is 'completed' without valid hex last_reviewed_commit",
    ),
    (
        "completed-chapter-unmarked-in-root",
        _mutate_completed_chapter_unmarked_in_root,
        "completed chapter 'ch01-tokens' must be marked [x] in checklist",
    ),
    (
        "current-chapter-stuck-on-completed",
        _mutate_current_chapter_stuck_on_completed,
        "current_chapter 'ch01-tokens' must reference an open chapter",
    ),
    (
        "empirical-chapter-missing-trigger",
        _mutate_empirical_chapter_missing_trigger,
        "empirical_dependent chapter requires non-empty replan_trigger",
    ),
    (
        "empirical-chapter-missing-deps",
        _mutate_empirical_chapter_missing_deps,
        "empirical_dependent chapter requires non-empty depends_on_chapters",
    ),
    (
        "task-checklist-marker-drift",
        _mutate_task_checklist_marker_drift,
        "has checklist marker [ ] but worksheet state 'completed' requires [x]",
    ),
    (
        "mixed-root-tasks-and-chapters",
        _mutate_mixed_root_tasks_and_chapters,
        "multi-chapter spec must not mix root tasks/*.md with chapters/",
    ),
    (
        "degraded-without-reason",
        _mutate_degraded_without_reason,
        "planning_quality is 'degraded' without non-empty planning_degraded_reason",
    ),
    (
        "completed-root-with-open-chapters",
        _mutate_completed_root_with_open_chapters,
        "cannot skip chapters",
    ),
    (
        "completed-chapter-with-open-task",
        _mutate_completed_chapter_with_open_task,
        "chapter is marked 'completed' while tasks remain open",
    ),
    (
        "unauthorized-deferred-task",
        _mutate_unauthorized_deferred_task,
        "without user authorization",
    ),
    (
        "unauthorized-deferred-chapter",
        _mutate_unauthorized_deferred_chapter,
        "without user authorization",
    ),
)


def test_validate_okf_bundle_accepts_valid_multichapter_bundle(tmp_path: Path) -> None:
    """Verify OKF v0.2 validation accepts a 6-chapter bundle, fenced YAML examples, and empirical dependencies."""
    bundle_dir = _seed_valid_multichapter_bundle(tmp_path)
    assert validate_okf_bundle(bundle_dir) == []


@pytest.mark.parametrize(
    ("case_id", "mutator", "expected_substring"),
    BUNDLE_REJECTION_CASES,
    ids=[case[0] for case in BUNDLE_REJECTION_CASES],
)
def test_validate_okf_bundle_rejects_structural_and_sync_violations(
    tmp_path: Path,
    case_id: str,
    mutator: Callable[[Path], None],
    expected_substring: str,
) -> None:
    """Verify validate_okf_bundle flags OKF v0.2, task blueprint, living-doc, and chapter-sync violations."""
    bundle_dir = _seed_valid_multichapter_bundle(tmp_path)
    mutator(bundle_dir)
    errors = validate_okf_bundle(bundle_dir)
    assert any(expected_substring in err for err in errors), f"[{case_id}] expected {expected_substring!r} in {errors}"


def test_state_contract_and_lifecycle_references_stay_lean() -> None:
    """Verify that skills/flow/references/state.md stays compact and documents all chaptered and task schemas."""
    refs_dir = REPO_ROOT / "skills" / "flow" / "references"
    expected_refs = {
        "archive.md",
        "cleanup.md",
        "discipline.md",
        "finish.md",
        "implement.md",
        "interaction.md",
        "learn.md",
        "prd.md",
        "research.md",
        "revert.md",
        "review.md",
        "revise.md",
        "setup.md",
        "spec.md",
        "state.md",
        "status.md",
        "studio.md",
        "validate.md",
    }
    found_refs = {p.name for p in refs_dir.glob("*.md")}
    assert found_refs == expected_refs

    state_path = refs_dir / "state.md"
    assert state_path.stat().st_size < 12000
    state_text = state_path.read_text(encoding="utf-8")
    assert "has_chapters" in state_text
    assert "planning_status" in state_text
    assert "last_reviewed_commit" in state_text
    assert "Documentation & OKF Knowledge Plan" in state_text
    assert "Current State & Remaining Plan Snapshot" in state_text
    missing_headings = [heading for heading in REQUIRED_TASK_HEADINGS if heading not in state_text]
    assert missing_headings == []


def test_flow_docs_reference_inventory() -> None:
    """Verify flow-docs maintains its three tool-agnostic reference chapters."""
    docs_refs_dir = REPO_ROOT / "skills" / "flow-docs" / "references"
    found_docs_refs = {p.name for p in docs_refs_dir.glob("*.md")}
    assert found_docs_refs == {
        "agent-context.md",
        "prose-and-documentation.md",
        "prs-commits-and-changelogs.md",
    }


@pytest.mark.parametrize("forbidden_lockin", FORBIDDEN_DOCS_LOCKIN_TERMS)
def test_flow_docs_remains_tool_agnostic(forbidden_lockin: str) -> None:
    """Verify skills/flow-docs contains no documentation-generator lock-in terms."""
    offenders = [
        doc_file.relative_to(REPO_ROOT).as_posix()
        for doc_file in (REPO_ROOT / "skills" / "flow-docs").rglob("*.md")
        if forbidden_lockin in doc_file.read_text(encoding="utf-8").lower()
    ]
    assert offenders == []


@pytest.mark.parametrize(
    ("rel_path", "expected_phrase"),
    (
        ("skills/flow/references/interaction.md", "Orthogonal Frontier Batch"),
        ("skills/flow/references/interaction.md", "Pre-Draft Question Coverage Gate"),
        ("skills/flow/references/spec.md", "Problem Statement & Objectives"),
        ("skills/flow/references/spec.md", "Zero-Context Isolation Rules"),
        ("skills/flow/references/spec.md", "Compare Interface Alternatives"),
        ("skills/flow/references/spec.md", "Anti-Truncation Rule"),
        ("skills/flow/references/spec.md", 'type_name="self"'),
        ("skills/flow/references/prd.md", "North Star Goal & Problem Framing"),
        ("skills/flow/references/prd.md", "chapters/index.md"),
        ("skills/flow/references/implement.md", "Public-Seam TDD"),
        ("skills/flow/references/implement.md", "Hypothesis-Driven Bug Diagnosis Loop"),
        ("skills/flow/references/implement.md", "pre-review present-tense Markdown/OKF synchronization"),
        ("skills/flow/references/implement.md", "last_reviewed_commit"),
        ("skills/flow/references/revise.md", "anti-truncation-chapter-expansion"),
        ("skills/flow/references/revise.md", "present-tense-full-plan-sync"),
        ("skills/flow/references/review.md", "Baseline Structural Code Smells"),
        ("skills/flow/references/review.md", "quality-review-v1"),
        ("skills/flow/references/review.md", "Present-Tense Markdown, Full-Plan Roadmap, & Doc-Sync Conformance"),
        ("rules/flow-antigravity.md", 'type_name="self"'),
        ("rules/flow-antigravity.md", "chapters/index.md"),
    ),
)
def test_lifecycle_references_encode_chaptered_planning_and_sync_contracts(
    rel_path: str,
    expected_phrase: str,
) -> None:
    """Verify core Flow references and rules encode anti-truncation chaptered planning and pre-review sync."""
    content = (REPO_ROOT / rel_path).read_text(encoding="utf-8")
    assert expected_phrase in content


@pytest.mark.parametrize("forbidden_term", FORBIDDEN_EXTERNAL_AND_PROJECT_TERMS)
def test_shipped_files_omit_forbidden_external_and_project_terms(forbidden_term: str) -> None:
    """Verify shipped Markdown and TOML files omit external source names and internal maintenance commands."""
    shipped_paths = (
        *REPO_ROOT.glob("skills/**/*.md"),
        *REPO_ROOT.glob("agents/*.md"),
        *REPO_ROOT.glob(".codex/agents/*.toml"),
        *REPO_ROOT.glob("rules/*.md"),
        *REPO_ROOT.glob("templates/**/*.md"),
        REPO_ROOT / "AGENTS.md",
        REPO_ROOT / "README.md",
    )
    offenders = [
        path.relative_to(REPO_ROOT).as_posix()
        for path in shipped_paths
        if forbidden_term in path.read_text(encoding="utf-8").lower()
    ]
    assert offenders == []


def test_validate_okf_bundle_accepts_compact_worksheet_and_user_deferral(tmp_path: Path) -> None:
    """Verify validate_okf_bundle accepts compact 6-heading task worksheets and user-authorized deferrals."""
    bundle_dir = _seed_valid_multichapter_bundle(tmp_path)
    compact_sections = "\n\n".join(f"{heading}\n\nPopulated[^t-src]." for heading in COMPACT_TASK_HEADINGS)
    task_path = bundle_dir / "specs" / "auth-refactor" / "chapters" / "ch02-middleware" / "tasks" / "t02-slice.md"
    task_path.write_text(
        "---\n"
        "type: Task\n"
        "id: auth-refactor:ch02-middleware:t02\n"
        "chapter_id: ch02-middleware\n"
        "title: Compact slice\n"
        "description: Small compact blueprint.\n"
        "status: stable\n"
        "state: deferred\n"
        "deferred_by: user\n"
        'deferred_reason: "Moved to follow-up release per user decision."\n'
        "worksheet_format: compact\n"
        "verification_strategy: behavior_tdd\n"
        "read_set: [src/auth/tokens.py]\n"
        "estimated_loc: 45\n"
        "sources:\n"
        "  - id: t-src\n"
        "    resource: src/auth/tokens.py::TokenSigner\n"
        "tags: [feature, auth]\n"
        "---\n\n"
        f"{compact_sections}\n\n"
        "[^t-src]: `src/auth/tokens.py::TokenSigner` — Signer.\n",
        encoding="utf-8",
    )
    ch_spec = bundle_dir / "specs" / "auth-refactor" / "chapters" / "ch02-middleware" / "spec.md"
    ch_spec.write_text(
        ch_spec.read_text(encoding="utf-8").replace("- [ ] [t02]", "- [-] [t02]"),
        encoding="utf-8",
    )
    assert validate_okf_bundle(bundle_dir) == []


def test_validate_okf_bundle_verifies_git_commit_file_ownership(tmp_path: Path) -> None:
    """Verify validate_okf_bundle rejects completed tasks whose Git commit touched zero declared files."""
    git_env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "Flow Test",
        "GIT_AUTHOR_EMAIL": "flow@example.com",
        "GIT_COMMITTER_NAME": "Flow Test",
        "GIT_COMMITTER_EMAIL": "flow@example.com",
    }
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, env=git_env, check=True)
    subprocess.run(["git", "config", "commit.gpgsign", "false"], cwd=tmp_path, env=git_env, check=True)
    (tmp_path / "src" / "auth").mkdir(parents=True)
    (tmp_path / "src" / "auth" / "tokens.py").write_text("class TokenSigner:\n    pass\n", encoding="utf-8")
    subprocess.run(["git", "add", "src/auth/tokens.py"], cwd=tmp_path, env=git_env, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "feat: tokens"], cwd=tmp_path, env=git_env, check=True)
    good_sha = subprocess.run(
        ["git", "rev-parse", "--short=7", "HEAD"], cwd=tmp_path, env=git_env, check=True, capture_output=True, text=True
    ).stdout.strip()

    (tmp_path / "README.md").write_text("# Unrelated\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=tmp_path, env=git_env, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "docs: readme"], cwd=tmp_path, env=git_env, check=True)
    unrelated_sha = subprocess.run(
        ["git", "rev-parse", "--short=7", "HEAD"], cwd=tmp_path, env=git_env, check=True, capture_output=True, text=True
    ).stdout.strip()

    bundle_dir = _seed_valid_multichapter_bundle(tmp_path)
    t1_path = bundle_dir / "specs" / "auth-refactor" / "chapters" / "ch01-tokens" / "tasks" / "t01-slice.md"
    ch1_spec = bundle_dir / "specs" / "auth-refactor" / "chapters" / "ch01-tokens" / "spec.md"
    root_spec = bundle_dir / "specs" / "auth-refactor" / "spec.md"

    ch1_spec.write_text(
        ch1_spec.read_text(encoding="utf-8").replace("1111111", good_sha),
        encoding="utf-8",
    )
    root_spec.write_text(
        root_spec.read_text(encoding="utf-8").replace("1111111", good_sha),
        encoding="utf-8",
    )
    t1_path.write_text(
        t1_path.read_text(encoding="utf-8").replace(
            "commit: 1111111", f"commit: {good_sha}\nfiles: [src/auth/tokens.py]"
        ),
        encoding="utf-8",
    )
    assert validate_okf_bundle(bundle_dir, flow_id="auth-refactor", project_root=tmp_path) == []

    ch1_spec.write_text(
        ch1_spec.read_text(encoding="utf-8").replace(f"[{good_sha}]", f"[{unrelated_sha}]"),
        encoding="utf-8",
    )
    t1_path.write_text(
        t1_path.read_text(encoding="utf-8").replace(f"commit: {good_sha}", f"commit: {unrelated_sha}"),
        encoding="utf-8",
    )
    ownership_errors = validate_okf_bundle(bundle_dir, flow_id="auth-refactor", project_root=tmp_path)
    assert any("modified none of the task's declared files/tests" in err for err in ownership_errors)


@pytest.mark.parametrize("ignore_policy", ("shared", "local-only"))
def test_worktree_env_routing_symlinking_and_fallback_sync(tmp_path: Path, ignore_policy: str) -> None:
    """Verify tools/worktree_env.py routes shared vs local-only Git worktrees and symlinks .venv and .agents."""
    git_env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "Flow Test",
        "GIT_AUTHOR_EMAIL": "flow@example.com",
        "GIT_COMMITTER_NAME": "Flow Test",
        "GIT_COMMITTER_EMAIL": "flow@example.com",
    }
    main_repo = tmp_path / "main-repo"
    wt_repo = tmp_path / "wt-feature"
    main_repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=main_repo, env=git_env, check=True)
    subprocess.run(["git", "config", "commit.gpgsign", "false"], cwd=main_repo, env=git_env, check=True)
    (main_repo / "app.py").write_text("X = 1\n", encoding="utf-8")
    (main_repo / ".venv" / "bin").mkdir(parents=True)
    (main_repo / "uv.toml").write_text('[[index]]\nurl = "https://pypi.org/simple"\n', encoding="utf-8")

    setup_payload = {
        "setup_status": "complete",
        "bundle_root": ".agents/bundles",
        "okf_version": "0.2",
        "workflow_preferences": {"ignore_policy": ignore_policy},
    }
    (main_repo / ".agents" / "bundles").mkdir(parents=True)
    (main_repo / ".agents" / "setup-state.json").write_text(json.dumps(setup_payload), encoding="utf-8")
    (main_repo / ".agents" / "bundles" / "index.md").write_text(
        '---\nokf_version: "0.2"\nbundle: demo\n---\n\n# Demo\n',
        encoding="utf-8",
    )
    (main_repo / ".agents" / "bundles" / "log.md").write_text("# Log\n\n- 2026-11-01 init\n", encoding="utf-8")

    if ignore_policy == "shared":
        subprocess.run(["git", "add", "app.py", ".agents"], cwd=main_repo, env=git_env, check=True)
    else:
        exclude = main_repo / ".git" / "info" / "exclude"
        exclude.parent.mkdir(parents=True, exist_ok=True)
        exclude.write_text(".agents/\n", encoding="utf-8")
        subprocess.run(["git", "add", "app.py"], cwd=main_repo, env=git_env, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "chore: seed"], cwd=main_repo, env=git_env, check=True)
    subprocess.run(
        ["git", "worktree", "add", "-q", "-b", "feat/wt", str(wt_repo)], cwd=main_repo, env=git_env, check=True
    )

    inspected = inspect_worktree(wt_repo)
    assert inspected.is_linked_worktree is True
    assert inspected.ignore_policy == ignore_policy

    bootstrapped = bootstrap_worktree(wt_repo)
    assert is_link_or_junction(wt_repo / ".venv")
    assert is_link_or_junction(wt_repo / "uv.toml")

    if ignore_policy == "shared":
        assert bootstrapped.routing_mode == "shared-worktree"
        assert Path(bootstrapped.target_agents_dir or "") == (wt_repo / ".agents").resolve()
        assert not is_link_or_junction(wt_repo / ".agents")
    else:
        assert bootstrapped.routing_mode == "local-only-main"
        assert Path(bootstrapped.target_agents_dir or "") == (main_repo / ".agents").resolve()
        assert is_link_or_junction(wt_repo / ".agents")
        assert (wt_repo / ".agents").resolve() == (main_repo / ".agents").resolve()

        (wt_repo / ".agents").unlink()
        seeded = sync_main_bundle_to_worktree(wt_repo)
        assert seeded["status"] == "synced"
        assert (wt_repo / ".agents" / "bundles" / "index.md").is_file()
        fallback_spec = wt_repo / ".agents" / "bundles" / "specs" / "wt-flow"
        fallback_spec.mkdir(parents=True)
        (fallback_spec / "spec.md").write_text("---\ntype: Spec\n---\n", encoding="utf-8")
        (wt_repo / ".agents" / "bundles" / "log.md").write_text("# Log\n\n- 2026-11-12 wt entry\n", encoding="utf-8")
        synced = sync_worktree_bundle_to_main(wt_repo)
        assert synced["status"] == "synced"
        assert (main_repo / ".agents" / "bundles" / "specs" / "wt-flow" / "spec.md").is_file()
        assert "2026-11-12 wt entry" in (main_repo / ".agents" / "bundles" / "log.md").read_text(encoding="utf-8")


def test_flow_spec_planning_workflow_quota_fallback_and_disk_idle_recovery(tmp_path: Path) -> None:
    """Verify flow-spec-planning recovers stalled planners from disk and stamps planning_quality: degraded on 429."""
    bundle_dir = _seed_valid_multichapter_bundle(tmp_path)
    (tmp_path / "src" / "auth").mkdir(parents=True)
    (tmp_path / "src" / "auth" / "tokens.py").write_text("class TokenSigner:\n    pass\n", encoding="utf-8")

    flow_dir = bundle_dir / "specs" / "mini-flow"
    ch_dir = flow_dir / "chapters" / "ch01-core"
    (ch_dir / "tasks").mkdir(parents=True)
    (flow_dir / "chapters" / "index.md").write_text(
        "# Chapters\n\n* [ch01-core](ch01-core/spec.md)\n", encoding="utf-8"
    )
    (flow_dir / "spec.md").write_text(
        "---\n"
        "type: Spec\n"
        "flow_id: mini-flow\n"
        "title: Mini Flow\n"
        "description: Small multi-chapter test flow.\n"
        "status: draft\n"
        "state: planned\n"
        "has_chapters: true\n"
        "chapters: [ch01-core]\n"
        "current_chapter: ch01-core\n"
        "sources:\n"
        "  - id: s1\n"
        "    resource: src/auth/tokens.py::TokenSigner\n"
        "    title: Signer\n"
        "tags: [feature, auth]\n"
        "---\n\n"
        "<!-- truth: start -->\n"
        "- Preserves TokenSigner seam[^s1].\n"
        "<!-- truth: end -->\n\n"
        "## 1. Specification, Context & Provenance\n\nContext.\n\n"
        "## 2. Requirements, Concrete Contracts & Architecture\n\nContracts.\n\n"
        "## 3. Documentation & OKF Knowledge Plan\n\n- [0/1 files documented]\n\n"
        "## 4. Requirement-to-Task Traceability Matrix\n\n| Req | Ch |\n| --- | --- |\n| R1 | ch01-core |\n\n"
        "## 5. Implementation Plan\n\n- [ ] [ch01-core](chapters/ch01-core/spec.md) — Core slice\n\n"
        "## 6. Current State & Remaining Plan Snapshot\n\nPlanned.\n\n"
        "[^s1]: `src/auth/tokens.py::TokenSigner` — Signer.\n",
        encoding="utf-8",
    )

    script_path = REPO_ROOT / "workflows" / "flow-spec-planning" / "workflow.py"
    source = script_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(script_path))
    code_obj = compile(tree, str(script_path), "exec", flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT)

    class FakeBudgetExceededError(Exception):
        pass

    printed_lines: list[str] = []
    call_models: list[str] = []

    async def fake_agent(
        prompt: str,
        *,
        schema: dict[str, Any],
        role: str = "",
        type_name: str = "self",
        workspace: str = "inherit",
        model: str = "inherit",
    ) -> dict[str, Any]:
        assert type_name == "self"
        assert schema
        call_models.append(model)
        if "Planner" in role and model == "inherit":
            raise RuntimeError("429 RESOURCE_EXHAUSTED: primary model quota exceeded")
        if "Planner" in role:
            (ch_dir / "spec.md").write_text(
                "---\n"
                "type: Spec\n"
                "parent_flow: mini-flow\n"
                "chapter_id: ch01-core\n"
                "title: Chapter ch01-core\n"
                "description: Scoped blueprint.\n"
                "status: draft\n"
                "state: planned\n"
                "planning_status: complete\n"
                "depends_on_chapters: []\n"
                "replan_trigger: null\n"
                "last_reviewed_commit: null\n"
                "sources:\n"
                "  - id: cs1\n"
                "    resource: src/auth/tokens.py::TokenSigner\n"
                "    title: Signer\n"
                "tags: [feature, auth]\n"
                "---\n\n"
                "<!-- truth: start -->\n"
                "- Scoped invariant[^cs1].\n"
                "<!-- truth: end -->\n\n"
                "## 1. Specification, Context & Provenance\n\nCtx.\n\n"
                "## 2. Requirements, Concrete Contracts & Architecture\n\nContracts.\n\n"
                "## 3. Documentation & OKF Knowledge Plan\n\n- [0/1 files documented]\n\n"
                "## 4. Requirement-to-Task Traceability Matrix\n\n| Req | Task |\n| --- | --- |\n| R1 | t01 |\n\n"
                "## 5. Implementation Plan\n\n- [ ] [t01](tasks/t01-core.md) — Core task\n\n"
                "## 6. Current State & Remaining Plan Snapshot\n\nPlanned.\n\n"
                "[^cs1]: `src/auth/tokens.py::TokenSigner` — Signer.\n",
                encoding="utf-8",
            )
            (ch_dir / "tasks" / "t01-core.md").write_text(
                _render_task_blueprint(task_id="mini-flow:ch01-core:t01", chapter_id="ch01-core"),
                encoding="utf-8",
            )
            (ch_dir / "planner-notes.md").write_text(
                "# Planner Notes\n\n## Task Summaries\n\n- t01: Deliver core slice\n\n## Root Spec Issues\n\n- None\n",
                encoding="utf-8",
            )
            old_ts = 1700000000.0
            for written in (ch_dir / "spec.md", ch_dir / "tasks" / "t01-core.md", ch_dir / "planner-notes.md"):
                os.utime(written, (old_ts, old_ts))
            await asyncio.sleep(60)
        return {"verdict": "APPROVED", "findings": []}

    async def fake_with_budget(coro: Any, **_kwargs: Any) -> Any:
        return await coro

    async def fake_parallel(items: list[Any], fn: Callable[[Any], Any]) -> list[Any]:
        return list(await asyncio.gather(*(fn(item) for item in items)))

    ns: dict[str, Any] = {
        "__builtins__": __builtins__,
        "args": {
            "flow_id": "mini-flow",
            "chapters": [{"id": "ch01-core", "brief": "Implement core slice", "read_files": ["src/auth/tokens.py"]}],
            "bundle_root": str(bundle_dir),
            "plugin_root": str(REPO_ROOT),
            "disk_idle_grace_seconds": 1,
            "planner_timeout_seconds": 30,
            "review": "single",
        },
        "agent": fake_agent,
        "with_budget": fake_with_budget,
        "BudgetExceeded": FakeBudgetExceededError,
        "parallel": fake_parallel,
        "phase": lambda _name: None,
        "log": lambda _msg: None,
        "tokens_used": lambda: 1234,
        "print": lambda text: printed_lines.append(str(text)),
    }

    async def _drive() -> None:
        coro = eval(code_obj, ns, ns)
        if asyncio.iscoroutine(coro):
            await coro

    asyncio.run(_drive())
    assert printed_lines
    report = json.loads(printed_lines[-1])
    assert report["all_chapters_complete"] is True
    assert report["okf_validation_errors"] == []
    assert report["planning_quality"] == "degraded"
    assert report["planning_warning"] is not None
    assert report["chapters"][0]["completed_from_disk"] is True
    assert report["chapters"][0]["task_summaries"] == ["t01: Deliver core slice"]
    assert "flash" in call_models

    stamped_root = (flow_dir / "spec.md").read_text(encoding="utf-8")
    assert "planning_quality: degraded" in stamped_root
    assert "planning_degraded_reason:" in stamped_root

"""Deterministic Flow state, journal compaction, and cross-session reorientation utility.

Provides CLI subcommands and programmatic helpers for maintainer and test workflows:
- ``reorient``: Inspects a Flow repository across machine and harness boundaries,
  audits local untracked ``transactions/*/journal.md`` state, reconciles Git
  commits and working tree drift against ``spec.md`` and ``tasks/*.md``, releases
  stale cross-harness claims, synchronizes Markdown checklist markers and state
  revisions, prunes obsolete terminal journals, and emits a handoff report.
- ``snapshot``: Emits a compact single-pass status snapshot of active flows.
- ``prune-journals``: Removes superseded or obsolete terminal transaction
  journal directories while preserving nonterminal recovery candidates and the
  latest terminal journal per flow.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

FRONTMATTER_PATTERN = re.compile(r"\A---\n(.*?)\n---\n?(.*)\Z", re.DOTALL)
TASK_ID_MENTION_PATTERN = re.compile(r"\b(?:task\s+)?(\d+\.\d+)\b", re.IGNORECASE)
HEADING_LINE_PATTERN = re.compile(r"^\s*\x23+\s*(.+)$")
CHECKLIST_TASK_PATTERN = re.compile(
    r"^(\s*-\s*\[([ ~x!-])\]\s*Task\s+([a-zA-Z0-9._-]+)\s*:\s*)(.*?)(?:\s*\[([a-fA-F0-9]{7,40})\])?$",
    re.MULTILINE,
)

NONTERMINAL_JOURNAL_STATES = {
    "prepared",
    "task_writes_started",
    "recovery_required",
    "contended",
    "rollback_in_progress",
    "applying",
}
TERMINAL_JOURNAL_STATES = {"committed", "rolled_back", "superseded"}
STATE_TO_MARKER = {
    "open": " ",
    "todo": " ",
    "in_progress": "~",
    "closed": "x",
    "done": "x",
    "blocked": "!",
    "skipped": "-",
}


@dataclass
class TaskSummary:
    """Normalized state of a single task worksheet."""

    task_id: str
    title: str
    state: str
    status: str
    priority: str
    depends_on: list[str]
    claimed_by: str | None
    claimed_at: str | None
    plan_revision: int | None
    state_revision: int | None
    commit: str | None
    path: str


@dataclass
class DriftItem:
    """Single detected cross-machine or cross-harness drift finding."""

    category: str
    severity: str
    target: str
    summary: str
    recommended_operation: str
    auto_fixable: bool = False


@dataclass
class ReorientReport:
    """Complete cross-session reorientation and handoff report."""

    flow_id: str
    flow_status: str
    configured_root: str
    current_harness: str | None
    head_commit: str | None
    branch: str | None
    working_tree_clean: bool
    modified_paths: list[str]
    transaction_status: str
    pruned_journals: list[str]
    plan_revision: int | None
    state_revision: int | None
    plan_commit: str | None
    task_counts: dict[str, int]
    tasks: list[TaskSummary]
    drift_items: list[DriftItem]
    applied_actions: list[str]
    ready_tasks: list[str]
    in_progress_tasks: list[str]
    blocked_tasks: list[str]
    recommended_next_action: str

    def to_dict(self) -> dict[str, Any]:
        """Serialize the report to a plain dictionary."""
        return asdict(self)


def utc_now_iso() -> str:
    """Return canonical UTC ISO-8601 timestamp."""
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_markdown_frontmatter(path: Path) -> tuple[dict[str, Any], str]:
    """Parse YAML frontmatter and body from a Markdown file."""
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    match = FRONTMATTER_PATTERN.match(text)
    if match is None:
        return {}, text
    loaded = yaml.safe_load(match.group(1))
    frontmatter = loaded if isinstance(loaded, dict) else {}
    return frontmatter, match.group(2)


def dump_markdown_frontmatter(frontmatter: dict[str, Any], body: str) -> str:
    """Render YAML frontmatter and Markdown body back to text."""
    rendered_yaml = yaml.safe_dump(
        frontmatter,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
    ).strip()
    normalized_body = body if body.startswith("\n") else f"\n{body}"
    return f"---\n{rendered_yaml}\n---{normalized_body}"


def resolve_agents_root(repo_root: Path) -> Path:
    """Resolve the configured Flow root from .agents/setup-state.json."""
    setup_state = repo_root / ".agents" / "setup-state.json"
    if setup_state.is_file():
        try:
            payload = json.loads(setup_state.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            payload = {}
        configured = (
            payload.get("root_directory")
            or payload.get("configured_root")
            or payload.get("root")
        )
        if isinstance(configured, str) and configured.strip():
            candidate = (repo_root / configured.strip()).resolve()
            if candidate.exists():
                return candidate
    return (repo_root / ".agents").resolve()


def resolve_bundle_root(agents_root: Path) -> Path:
    """Resolve the configured bundle root from config.json or default bundles/."""
    config_path = agents_root / "config.json"
    if config_path.is_file():
        try:
            payload = json.loads(config_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            payload = {}
        bundles_dir = payload.get("bundles_dir")
        if isinstance(bundles_dir, str) and bundles_dir.strip():
            return (agents_root / bundles_dir.strip()).resolve()
    return (agents_root / "bundles").resolve()


def resolve_flow_id(agents_root: Path, explicit_flow_id: str | None) -> str:
    """Determine the target flow_id from explicit argument, index.md, or specs/."""
    bundle_root = resolve_bundle_root(agents_root)
    specs_root = bundle_root / "specs"
    if explicit_flow_id:
        target = specs_root / explicit_flow_id
        if not target.is_dir():
            msg = f"Flow bundle not found: {target}"
            raise FileNotFoundError(msg)
        return explicit_flow_id

    for index_candidate in (bundle_root / "index.md", agents_root / "index.md"):
        if index_candidate.is_file():
            frontmatter, body = parse_markdown_frontmatter(index_candidate)
            active = frontmatter.get("active_flow") or frontmatter.get("flow_id")
            if isinstance(active, str) and (specs_root / active).is_dir():
                return active
            for match in re.finditer(r"specs/([a-zA-Z0-9._-]+)/spec\.md", body):
                candidate_id = match.group(1)
                if (specs_root / candidate_id).is_dir():
                    return candidate_id

    if not specs_root.is_dir():
        msg = f"No specs directory found under {specs_root}"
        raise FileNotFoundError(msg)

    candidates = sorted(
        path.name for path in specs_root.iterdir() if (path / "spec.md").is_file()
    )
    if not candidates:
        msg = f"No flow bundles found under {specs_root}"
        raise FileNotFoundError(msg)
    for candidate_id in candidates:
        spec_fm, _ = parse_markdown_frontmatter(specs_root / candidate_id / "spec.md")
        raw_state = spec_fm.get("state") or spec_fm.get("status")
        if raw_state in {"active", "in_progress", "planned", "ready", "draft"}:
            return candidate_id
    return candidates[0]


def run_git(repo_root: Path, args: list[str]) -> str | None:
    """Run a read-only git command and return stripped stdout or None on failure."""
    completed = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        return None
    return completed.stdout.strip()


def commit_exists_in_head(repo_root: Path, commit_hash: str) -> bool:
    """Return True when commit_hash is a valid commit ancestor of HEAD."""
    completed = subprocess.run(
        ["git", "merge-base", "--is-ancestor", commit_hash, "HEAD"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    return completed.returncode == 0


def recent_commit_subjects(repo_root: Path, limit: int = 30) -> list[tuple[str, str]]:
    """Return (short_sha, subject) pairs from recent git history."""
    output = run_git(repo_root, ["log", f"-n{limit}", "--format=%h\t%s"])
    if not output:
        return []
    commits: list[tuple[str, str]] = []
    for line in output.splitlines():
        if "\t" in line:
            sha, subject = line.split("\t", maxsplit=1)
            commits.append((sha.strip(), subject.strip()))
    return commits


def working_tree_modified_paths(repo_root: Path) -> list[str]:
    """Return modified/untracked file paths from git status --porcelain."""
    output = run_git(repo_root, ["status", "--porcelain"])
    if not output:
        return []
    paths: list[str] = []
    for line in output.splitlines():
        if len(line) > 3:
            paths.append(line[3:].strip())
    return paths


def extract_title(frontmatter: dict[str, Any], body: str, fallback: str) -> str:
    """Extract task or spec title from frontmatter or first Markdown heading."""
    title = frontmatter.get("title")
    if isinstance(title, str) and title.strip():
        return title.strip()
    for line in body.splitlines():
        match = HEADING_LINE_PATTERN.match(line)
        if match:
            return match.group(1).strip()
    return fallback


def task_sort_key(task_id: str) -> tuple[int, ...]:
    """Sort dotted numeric task IDs naturally."""
    short = task_id.rsplit(":", 1)[-1]
    parts = short.split(".")
    if all(part.isdigit() for part in parts):
        return tuple(int(part) for part in parts)
    return (sys.maxsize,)


def normalize_task_state(frontmatter: dict[str, Any]) -> tuple[str, str]:
    """Return (canonical_state, legacy_status) for a task frontmatter dict."""
    raw = str(frontmatter.get("state") or frontmatter.get("status") or "open")
    if raw in {"done", "closed"}:
        return "closed", "done"
    if raw in {"todo", "open"}:
        return "open", "todo"
    if raw == "in_progress":
        return "in_progress", "in_progress"
    if raw == "blocked":
        return "blocked", "blocked"
    if raw == "skipped":
        return "skipped", "skipped"
    return raw, raw


def inspect_and_prune_transactions(
    agents_root: Path, flow_id: str, *, prune_terminal: bool = False
) -> tuple[str, list[str]]:
    """Inspect local transaction journals and optionally prune obsolete terminal ones."""
    tx_dir = agents_root / "transactions"
    if not tx_dir.is_dir():
        return "none_local", []

    json_journal = tx_dir / f"{flow_id}.json"
    if json_journal.is_file():
        try:
            payload = json.loads(json_journal.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return "corrupt_journal", []
        if not isinstance(payload, dict):
            return "corrupt_journal", []
        return str(payload.get("status") or payload.get("state") or "unknown"), []

    nonterminal: list[str] = []
    terminal_dirs: list[Path] = []
    for journal_md in sorted(tx_dir.glob("*/journal.md")):
        try:
            fm, _ = parse_markdown_frontmatter(journal_md)
        except (OSError, ValueError, yaml.YAMLError):
            return "corrupt_journal", []
        j_flow = fm.get("flow_id")
        if j_flow is not None and str(j_flow) != flow_id:
            continue
        j_state = str(fm.get("state") or fm.get("status") or "unknown")
        if j_state in NONTERMINAL_JOURNAL_STATES:
            nonterminal.append(j_state)
        elif j_state in TERMINAL_JOURNAL_STATES:
            terminal_dirs.append(journal_md.parent)

    pruned: list[str] = []
    if prune_terminal and not nonterminal and len(terminal_dirs) > 1:
        for old_dir in terminal_dirs[:-1]:
            shutil.rmtree(old_dir, ignore_errors=True)
            pruned.append(old_dir.name)

    if nonterminal:
        return nonterminal[0], pruned
    if terminal_dirs:
        return "committed", pruned
    return "none_local", pruned


def reconcile_spec_checklist_body(
    spec_body: str, task_map: dict[str, tuple[str, str | None]]
) -> str:
    """Synchronize spec.md checklist markers and commit SHAs with task truth."""
    matches = list(CHECKLIST_TASK_PATTERN.finditer(spec_body))
    updated = spec_body
    for match in reversed(matches):
        prefix = match.group(1)
        old_marker = match.group(2)
        short_id = match.group(3)
        title = match.group(4).strip()
        old_sha = match.group(5)
        if short_id not in task_map:
            continue
        t_state, t_commit = task_map[short_id]
        new_marker = STATE_TO_MARKER.get(t_state, " ")
        sha = t_commit if t_state == "closed" and t_commit else old_sha if t_state == "closed" else None
        new_prefix = prefix.replace(f"[{old_marker}]", f"[{new_marker}]", 1)
        replacement = f"{new_prefix}{title}"
        if sha:
            replacement += f" [{sha}]"
        start, end = match.span()
        updated = updated[:start] + replacement + updated[end:]
    return updated


def reorient_flow(
    repo_root: Path,
    *,
    flow_id: str | None = None,
    current_harness: str | None = None,
    apply_fixes: bool = False,
) -> ReorientReport:
    """Analyze a Flow bundle across machine/harness state and optionally align it."""
    agents_root = resolve_agents_root(repo_root)
    bundle_root = resolve_bundle_root(agents_root)
    resolved_flow_id = resolve_flow_id(agents_root, flow_id)
    flow_dir = bundle_root / "specs" / resolved_flow_id
    spec_path = flow_dir / "spec.md"
    tasks_dir = flow_dir / "tasks"

    spec_fm, spec_body = parse_markdown_frontmatter(spec_path)
    uses_state_key = "state" in spec_fm or "status" not in spec_fm
    spec_plan_rev = (
        int(spec_fm["plan_revision"])
        if isinstance(spec_fm.get("plan_revision"), int)
        else None
    )
    spec_state_rev = (
        int(spec_fm["state_revision"])
        if isinstance(spec_fm.get("state_revision"), int)
        else None
    )
    spec_plan_commit = (
        str(spec_fm["plan_commit"])
        if isinstance(spec_fm.get("plan_commit"), str)
        else None
    )
    flow_status = str(spec_fm.get("state") or spec_fm.get("status") or "active")

    head_commit = run_git(repo_root, ["rev-parse", "--short", "HEAD"])
    branch = run_git(repo_root, ["rev-parse", "--abbrev-ref", "HEAD"])
    modified_paths = working_tree_modified_paths(repo_root)
    commits = recent_commit_subjects(repo_root)

    tx_status, pruned_journals = inspect_and_prune_transactions(
        agents_root, resolved_flow_id, prune_terminal=apply_fixes
    )
    drift_items: list[DriftItem] = []
    applied_actions: list[str] = []
    if pruned_journals:
        applied_actions.append(
            f"Pruned {len(pruned_journals)} obsolete terminal transaction journal(s)."
        )

    if tx_status in NONTERMINAL_JOURNAL_STATES:
        drift_items.append(
            DriftItem(
                category="journal_recovery",
                severity="warning",
                target=f"{agents_root.relative_to(repo_root)}/transactions",
                summary=(
                    f"Local transaction journal is in '{tx_status}' state and "
                    "requires journal-first recovery before new mutations."
                ),
                recommended_operation="recover",
                auto_fixable=False,
            )
        )
    elif tx_status == "corrupt_journal":
        drift_items.append(
            DriftItem(
                category="journal_recovery",
                severity="error",
                target=f"{agents_root.relative_to(repo_root)}/transactions",
                summary="Local transaction journal is malformed.",
                recommended_operation="recover",
                auto_fixable=False,
            )
        )

    task_files: list[Path] = []
    if tasks_dir.is_dir():
        task_files = sorted(
            (p for p in tasks_dir.glob("*.md") if p.is_file()),
            key=lambda p: task_sort_key(p.stem),
        )

    task_records: list[tuple[Path, dict[str, Any], str]] = []
    for task_path in task_files:
        fm, body = parse_markdown_frontmatter(task_path)
        task_records.append((task_path, fm, body))

    max_task_state_rev = spec_state_rev or 0
    state_mutated = False

    for task_path, fm, body in task_records:
        raw_id = str(fm.get("task_id") or fm.get("id") or task_path.stem)
        short_id = raw_id.rsplit(":", 1)[-1]
        task_uses_state_key = "state" in fm or "status" not in fm
        c_state, l_status = normalize_task_state(fm)
        claimed_by = fm.get("claimed_by")
        claimed_at = fm.get("claimed_at")
        t_plan_rev = (
            int(fm["plan_revision"])
            if isinstance(fm.get("plan_revision"), int)
            else None
        )
        t_state_rev = (
            int(fm["state_revision"])
            if isinstance(fm.get("state_revision"), int)
            else None
        )
        if t_state_rev is not None and t_state_rev > max_task_state_rev:
            max_task_state_rev = t_state_rev
        last_commit = (
            str(fm.get("commit") or fm.get("last_functional_commit"))
            if isinstance(fm.get("commit") or fm.get("last_functional_commit"), str)
            else None
        )

        if c_state in {"closed", "skipped"} and (
            claimed_by is not None or claimed_at is not None
        ):
            drift_items.append(
                DriftItem(
                    category="cross_harness_claim_hygiene",
                    severity="warning",
                    target=f"tasks/{task_path.name}",
                    summary=(
                        f"Task {short_id} is '{c_state}' but retains claim metadata "
                        f"(claimed_by={claimed_by!r})."
                    ),
                    recommended_operation="reconcile",
                    auto_fixable=True,
                )
            )
            if apply_fixes:
                fm["claimed_by"] = None
                fm["claimed_at"] = None
                state_mutated = True
                applied_actions.append(
                    f"Cleared residual claim metadata on {c_state} task {short_id}."
                )

        elif c_state == "open" and (claimed_by is not None or claimed_at is not None):
            drift_items.append(
                DriftItem(
                    category="cross_harness_claim_hygiene",
                    severity="warning",
                    target=f"tasks/{task_path.name}",
                    summary=(
                        f"Task {short_id} is open with orphaned claim "
                        f"(claimed_by={claimed_by!r})."
                    ),
                    recommended_operation="release",
                    auto_fixable=True,
                )
            )
            if apply_fixes:
                fm["claimed_by"] = None
                fm["claimed_at"] = None
                state_mutated = True
                applied_actions.append(
                    f"Released orphaned claim on open task {short_id}."
                )

        elif (
            c_state == "in_progress"
            and current_harness
            and isinstance(claimed_by, str)
            and claimed_by != current_harness
            and tx_status not in NONTERMINAL_JOURNAL_STATES
        ):
            drift_items.append(
                DriftItem(
                    category="cross_harness_claim_hygiene",
                    severity="warning",
                    target=f"tasks/{task_path.name}",
                    summary=(
                        f"Task {short_id} is claimed by prior harness '{claimed_by}' "
                        f"while current session is '{current_harness}'."
                    ),
                    recommended_operation="release",
                    auto_fixable=True,
                )
            )
            if apply_fixes:
                if task_uses_state_key:
                    fm["state"] = "open"
                if "status" in fm:
                    fm["status"] = "todo"
                fm["claimed_by"] = None
                fm["claimed_at"] = None
                c_state, l_status = "open", "todo"
                claimed_by = None
                claimed_at = None
                state_mutated = True
                applied_actions.append(
                    f"Released stale cross-harness claim on task {short_id} for '{current_harness}'."
                )

        if (
            spec_plan_rev is not None
            and t_plan_rev is not None
            and t_plan_rev != spec_plan_rev
        ):
            drift_items.append(
                DriftItem(
                    category="revision_and_binding_alignment",
                    severity="warning",
                    target=f"tasks/{task_path.name}",
                    summary=(
                        f"Task {short_id} plan_revision ({t_plan_rev}) differs from "
                        f"spec.md plan_revision ({spec_plan_rev})."
                    ),
                    recommended_operation="reconcile",
                    auto_fixable=True,
                )
            )
            if apply_fixes:
                fm["plan_revision"] = spec_plan_rev
                state_mutated = True
                applied_actions.append(
                    f"Aligned task {short_id} plan_revision to {spec_plan_rev}."
                )

        if (
            last_commit
            and head_commit
            and not commit_exists_in_head(repo_root, last_commit)
        ):
            drift_items.append(
                DriftItem(
                    category="git_and_worktree_drift",
                    severity="error",
                    target=f"tasks/{task_path.name}",
                    summary=(
                        f"Task {short_id} references commit '{last_commit}' which is "
                        "not an ancestor of current HEAD."
                    ),
                    recommended_operation="reconcile",
                    auto_fixable=False,
                )
            )

        if c_state in {"open", "in_progress"}:
            matching_commit: str | None = None
            if (
                last_commit
                and head_commit
                and commit_exists_in_head(repo_root, last_commit)
            ):
                matching_commit = last_commit
            else:
                for sha, subject in commits:
                    mentioned = TASK_ID_MENTION_PATTERN.findall(subject)
                    if short_id in mentioned:
                        matching_commit = sha
                        break
            if matching_commit is not None:
                drift_items.append(
                    DriftItem(
                        category="git_and_worktree_drift",
                        severity="warning",
                        target=f"tasks/{task_path.name}",
                        summary=(
                            f"Task {short_id} is '{l_status}' but commit "
                            f"'{matching_commit}' in Git history already completes it."
                        ),
                        recommended_operation="reconcile",
                        auto_fixable=True,
                    )
                )
                if apply_fixes:
                    if task_uses_state_key:
                        fm["state"] = "closed"
                    if "status" in fm:
                        fm["status"] = "done"
                    fm["claimed_by"] = None
                    fm["claimed_at"] = None
                    if "commit" in fm or "last_functional_commit" not in fm:
                        fm["commit"] = matching_commit
                    if "last_functional_commit" in fm or "status" in fm:
                        fm["last_functional_commit"] = matching_commit
                    state_mutated = True
                    applied_actions.append(
                        f"Reconciled task {short_id} to closed/done at commit {matching_commit}."
                    )

    if spec_state_rev is not None and max_task_state_rev > spec_state_rev:
        drift_items.append(
            DriftItem(
                category="revision_and_binding_alignment",
                severity="warning",
                target="spec.md",
                summary=(
                    f"spec.md state_revision ({spec_state_rev}) trails task "
                    f"state_revision ({max_task_state_rev})."
                ),
                recommended_operation="reconcile",
                auto_fixable=True,
            )
        )
        if apply_fixes:
            state_mutated = True
            applied_actions.append(
                f"Synchronized spec.md state_revision from {spec_state_rev} to {max_task_state_rev}."
            )

    task_checklist_map: dict[str, tuple[str, str | None]] = {}
    for task_path, fm, _ in task_records:
        raw_id = str(fm.get("task_id") or fm.get("id") or task_path.stem)
        short_id = raw_id.rsplit(":", 1)[-1]
        c_state, _ = normalize_task_state(fm)
        raw_sha = fm.get("commit") or fm.get("last_functional_commit")
        task_checklist_map[short_id] = (
            c_state,
            str(raw_sha) if isinstance(raw_sha, str) else None,
        )

    reconciled_body = reconcile_spec_checklist_body(spec_body, task_checklist_map)
    if reconciled_body != spec_body:
        drift_items.append(
            DriftItem(
                category="revision_and_binding_alignment",
                severity="warning",
                target="spec.md",
                summary="spec.md Implementation Plan checklist markers differ from task states.",
                recommended_operation="reconcile",
                auto_fixable=True,
            )
        )
        if apply_fixes:
            spec_body = reconciled_body
            state_mutated = True
            applied_actions.append(
                "Synchronized spec.md Implementation Plan checklist markers with task states."
            )

    if apply_fixes and state_mutated:
        next_state_rev = max(max_task_state_rev, spec_state_rev or 0) + 1
        spec_fm["state_revision"] = next_state_rev
        spec_state_rev = next_state_rev
        active_in_prog = [
            str(fm.get("task_id") or fm.get("id") or p.stem).rsplit(":", 1)[-1]
            for p, fm, _ in task_records
            if normalize_task_state(fm)[0] == "in_progress"
        ]
        if "current_task" in spec_fm:
            spec_fm["current_task"] = active_in_prog[0] if active_in_prog else None
        spec_path.write_text(
            dump_markdown_frontmatter(spec_fm, spec_body), encoding="utf-8"
        )
        for task_path, fm, body in task_records:
            fm["state_revision"] = next_state_rev
            task_path.write_text(
                dump_markdown_frontmatter(fm, body), encoding="utf-8"
            )

    tasks: list[TaskSummary] = []
    task_counts: dict[str, int] = {
        "done": 0,
        "closed": 0,
        "in_progress": 0,
        "todo": 0,
        "open": 0,
        "blocked": 0,
        "skipped": 0,
    }
    closed_ids: set[str] = set()

    for task_path, fm, body in task_records:
        raw_id = str(fm.get("task_id") or fm.get("id") or task_path.stem)
        short_id = raw_id.rsplit(":", 1)[-1]
        c_state, l_status = normalize_task_state(fm)
        task_counts[c_state] = task_counts.get(c_state, 0) + 1
        if l_status != c_state:
            task_counts[l_status] = task_counts.get(l_status, 0) + 1
        if c_state in {"closed", "skipped"}:
            closed_ids.add(short_id)
            closed_ids.add(raw_id)
        raw_deps = fm.get("depends_on")
        deps = (
            [str(d).rsplit(":", 1)[-1] for d in raw_deps]
            if isinstance(raw_deps, list)
            else []
        )
        raw_sha = fm.get("commit") or fm.get("last_functional_commit")
        tasks.append(
            TaskSummary(
                task_id=short_id,
                title=extract_title(fm, body, short_id),
                state=c_state,
                status=l_status,
                priority=str(fm.get("priority") or "P2"),
                depends_on=deps,
                claimed_by=(
                    str(fm["claimed_by"]) if fm.get("claimed_by") is not None else None
                ),
                claimed_at=(
                    str(fm["claimed_at"]) if fm.get("claimed_at") is not None else None
                ),
                plan_revision=(
                    int(fm["plan_revision"])
                    if isinstance(fm.get("plan_revision"), int)
                    else None
                ),
                state_revision=(
                    int(fm["state_revision"])
                    if isinstance(fm.get("state_revision"), int)
                    else None
                ),
                commit=str(raw_sha) if isinstance(raw_sha, str) else None,
                path=str(task_path.relative_to(repo_root)),
            )
        )

    ready_tasks: list[str] = []
    in_progress_tasks: list[str] = []
    blocked_tasks: list[str] = []
    for item in tasks:
        if item.state == "in_progress":
            in_progress_tasks.append(item.task_id)
        elif item.state == "blocked":
            blocked_tasks.append(item.task_id)
        elif item.state == "open":
            if all(dep in closed_ids for dep in item.depends_on):
                ready_tasks.append(item.task_id)
            else:
                blocked_tasks.append(item.task_id)

    if tx_status in NONTERMINAL_JOURNAL_STATES:
        recommended_next = (
            f"Recover active journal under {agents_root.relative_to(repo_root)}/transactions "
            f"via flow-state recover before resuming {resolved_flow_id}."
        )
    elif in_progress_tasks:
        recommended_next = (
            f"Resume in-progress task {in_progress_tasks[0]} via "
            f"/flow:implement {resolved_flow_id}."
        )
    elif ready_tasks:
        recommended_next = (
            f"Claim and implement next ready task {ready_tasks[0]} via "
            f"/flow:implement {resolved_flow_id}."
        )
    elif (
        task_counts.get("closed", 0) + task_counts.get("skipped", 0) == len(tasks)
        and tasks
    ):
        recommended_next = (
            f"All {len(tasks)} tasks are closed/skipped; run /flow:finish {resolved_flow_id} "
            f"and /flow:archive {resolved_flow_id} (branch-local, no merge to main required)."
        )
    else:
        recommended_next = (
            f"Inspect blocked tasks or unresolved drift in {resolved_flow_id}."
        )

    return ReorientReport(
        flow_id=resolved_flow_id,
        flow_status=flow_status if not uses_state_key else str(spec_fm.get("state") or flow_status),
        configured_root=str(agents_root.relative_to(repo_root)),
        current_harness=current_harness,
        head_commit=head_commit,
        branch=branch,
        working_tree_clean=len(modified_paths) == 0,
        modified_paths=modified_paths,
        transaction_status=tx_status,
        pruned_journals=pruned_journals,
        plan_revision=spec_plan_rev,
        state_revision=spec_state_rev,
        plan_commit=spec_plan_commit,
        task_counts=task_counts,
        tasks=tasks,
        drift_items=drift_items,
        applied_actions=applied_actions,
        ready_tasks=ready_tasks,
        in_progress_tasks=in_progress_tasks,
        blocked_tasks=blocked_tasks,
        recommended_next_action=recommended_next,
    )


def format_text_report(report: ReorientReport) -> str:
    """Render a human-readable session reorientation and handoff report."""
    lines = [
        f"Flow Session Reorientation: {report.flow_id}",
        "",
        "Flow Overview:",
        f"- State: {report.flow_status}",
        f"- Root: {report.configured_root}",
        f"- Branch / HEAD: {report.branch or 'detached'} @ {report.head_commit or 'uncommitted'}",
        f"- Working tree: {'clean' if report.working_tree_clean else f'{len(report.modified_paths)} modified path(s)'}",
        f"- Local transaction: {report.transaction_status}",
        f"- Revisions: plan_revision={report.plan_revision}, state_revision={report.state_revision}",
        "",
        "Progress Summary:",
        (
            f"- closed: {report.task_counts.get('closed', 0)} | "
            f"in_progress: {report.task_counts.get('in_progress', 0)} | "
            f"ready: {len(report.ready_tasks)} | "
            f"blocked: {len(report.blocked_tasks)} | "
            f"skipped: {report.task_counts.get('skipped', 0)}"
        ),
    ]
    if report.drift_items:
        lines.extend(["", "Cross-Machine / Cross-Harness Drift:"])
        for item in report.drift_items:
            lines.append(
                f"- [{item.severity.upper()}] ({item.category}) {item.target}: "
                f"{item.summary} -> {item.recommended_operation}"
            )
    if report.applied_actions:
        lines.extend(["", "Applied Alignment Actions:"])
        for action in report.applied_actions:
            lines.append(f"- {action}")
    lines.extend(
        [
            "",
            "Next Actionable Handoff:",
            f"- Ready tasks: {', '.join(report.ready_tasks) if report.ready_tasks else 'none'}",
            f"- In-progress tasks: {', '.join(report.in_progress_tasks) if report.in_progress_tasks else 'none'}",
            f"- Recommended next step: {report.recommended_next_action}",
        ]
    )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser for tools/flow_state.py."""
    parser = argparse.ArgumentParser(
        prog="flow_state",
        description="Flow cross-session reorientation, snapshot, and journal compaction utility.",
    )
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    reorient_parser = subparsers.add_parser(
        "reorient",
        help="Inspect and optionally align Flow state across machines and harnesses.",
    )
    reorient_parser.add_argument(
        "flow_id",
        nargs="?",
        default=None,
        help="Optional flow_id to inspect (defaults to active flow).",
    )
    reorient_parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path.cwd(),
        help="Repository root directory.",
    )
    reorient_parser.add_argument(
        "--harness",
        default=None,
        help="Current harness identifier (e.g. antigravity, claude_code, codex_cli).",
    )
    reorient_parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply safe deterministic alignment fixes to spec.md and tasks/*.md.",
    )
    reorient_parser.add_argument(
        "--format",
        choices=("json", "text"),
        default="text",
        help="Output format (text or json).",
    )

    snapshot_parser = subparsers.add_parser(
        "snapshot",
        help="Emit a compact single-pass status snapshot for a flow.",
    )
    snapshot_parser.add_argument(
        "flow_id",
        nargs="?",
        default=None,
        help="Optional flow_id to snapshot.",
    )
    snapshot_parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path.cwd(),
        help="Repository root directory.",
    )

    prune_parser = subparsers.add_parser(
        "prune-journals",
        help="Prune obsolete terminal transaction journals for a flow.",
    )
    prune_parser.add_argument(
        "flow_id",
        nargs="?",
        default=None,
        help="Optional flow_id whose terminal journals should be pruned.",
    )
    prune_parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path.cwd(),
        help="Repository root directory.",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point for the flow_state CLI."""
    parser = build_parser()
    args = parser.parse_args(argv)
    repo_root = args.repo_root.resolve()

    if args.subcommand == "reorient":
        report = reorient_flow(
            repo_root,
            flow_id=args.flow_id,
            current_harness=args.harness,
            apply_fixes=args.apply,
        )
        if args.format == "json":
            print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
        else:
            print(format_text_report(report))
        return 0

    if args.subcommand == "snapshot":
        report = reorient_flow(repo_root, flow_id=args.flow_id, apply_fixes=False)
        print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
        return 0

    if args.subcommand == "prune-journals":
        agents_root = resolve_agents_root(repo_root)
        target_flow = resolve_flow_id(agents_root, args.flow_id)
        _, pruned = inspect_and_prune_transactions(
            agents_root, target_flow, prune_terminal=True
        )
        print(json.dumps({"flow_id": target_flow, "pruned_journals": pruned}))
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())

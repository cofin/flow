"""Audit and compact over-fragmented multi-chapter Flow specs into concise deliverable units."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from tools.validate import _split_frontmatter

__all__ = (
    "CompactionPlan",
    "CompactionResult",
    "audit_specs",
    "compact_specs",
    "main",
)

_PINNED_CHAPTER_STATES: frozenset[str] = frozenset({"completed", "closed", "deferred", "skipped"})
_SMALL_CHAPTER_THRESHOLD = 4
_CHECKLIST_SECTION_RE = re.compile(
    r"(^##\s+5\.\s+Implementation Plan[^\n]*\n)([\s\S]*?)(?=^##\s+|^\[\^|\Z)", re.MULTILINE
)
_SNAPSHOT_SECTION_RE = re.compile(
    r"(^##\s+6\.\s+Current State & Remaining Plan Snapshot[^\n]*\n)([\s\S]*?)(?=^##\s+|^\[\^|\Z)", re.MULTILINE
)


@dataclass(frozen=True, slots=True)
class CompactionPlan:
    """Identified mergeable chapter groups for a fragmented specification."""

    flow_id: str
    spec_path: str
    total_chapters: int
    collapse_to_single_chapter: bool
    merge_runs: tuple[tuple[str, ...], ...]
    reason: str

    def to_dict(self) -> dict[str, Any]:
        """Serialize compaction plan into JSON-compatible data."""
        return {
            "flow_id": self.flow_id,
            "spec_path": self.spec_path,
            "total_chapters": self.total_chapters,
            "collapse_to_single_chapter": self.collapse_to_single_chapter,
            "merge_runs": [list(run) for run in self.merge_runs],
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class CompactionResult:
    """Applied or dry-run compaction summary for one specification."""

    flow_id: str
    dry_run: bool
    before_chapters: int
    after_chapters: int
    collapsed_to_single_chapter: bool
    tasks_reindexed: int
    removed_chapters: tuple[str, ...]
    updated_files: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        """Serialize compaction receipt into JSON-compatible data."""
        return asdict(self) | {
            "removed_chapters": list(self.removed_chapters),
            "updated_files": list(self.updated_files),
        }


def _read_fm(path: Path) -> tuple[dict[str, Any], str]:
    """Read Markdown frontmatter and body cleanly."""
    raw = path.read_text(encoding="utf-8")
    fm, body = _split_frontmatter(raw)
    return (fm or {}), body


def _format_yaml_scalar(value: Any) -> str:
    """Format a scalar or shallow sequence YAML value."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, list):
        formatted = ", ".join(_format_yaml_scalar(item) for item in value)
        return f"[{formatted}]"
    text = str(value)
    if not text or any(ch in text for ch in (":", "#", "[", "]", "{", "}", "\n")) or text != text.strip():
        return json.dumps(text)
    return text


def _update_frontmatter_lines(raw_text: str, updates: dict[str, Any]) -> str:
    """Update top-level scalar/inline-list keys in existing YAML frontmatter in place."""
    normalized = raw_text.replace("\r\n", "\n")
    if not normalized.startswith("---\n"):
        return normalized
    end_idx = normalized.find("\n---\n", 4)
    if end_idx == -1:
        return normalized

    fm_lines = normalized[4:end_idx].splitlines()
    out_lines: list[str] = []
    seen: set[str] = set()
    skip_nested_for: str | None = None

    for line in fm_lines:
        stripped = line.strip()
        indent = len(line) - len(line.lstrip(" "))
        if skip_nested_for is not None:
            if indent > 0 or stripped.startswith("- "):
                continue
            skip_nested_for = None

        if indent == 0 and ":" in line and not stripped.startswith("-"):
            key, val_part = line.split(":", 1)
            clean_key = key.strip()
            if clean_key in updates:
                seen.add(clean_key)
                out_lines.append(f"{clean_key}: {_format_yaml_scalar(updates[clean_key])}")
                if not val_part.strip():
                    skip_nested_for = clean_key
                continue
        out_lines.append(line)

    for key, val in updates.items():
        if key not in seen:
            out_lines.append(f"{key}: {_format_yaml_scalar(val)}")

    return "---\n" + "\n".join(out_lines) + normalized[end_idx:]


def _expected_marker(state: str, commit: str = "") -> str:
    """Compute checklist marker matching Flow status rules."""
    clean = state.strip().lower()
    if clean in ("completed", "closed"):
        return f"[x] [{commit}]" if commit else "[x]"
    if clean in ("deferred", "skipped"):
        return "[-]"
    if clean in ("in_progress", "active"):
        return "[~]"
    if clean == "blocked":
        return "[!]"
    return "[ ]"


def _extract_footnotes(body: str) -> tuple[str, list[tuple[str, str]]]:
    """Split trailing [^id]: footnote definitions from body prose."""
    lines = body.splitlines()
    footnotes: list[tuple[str, str]] = []
    kept: list[str] = []
    for line in lines:
        m = re.match(r"^\[\^([^\]]+)\]:\s*(.*)$", line)
        if m:
            footnotes.append((m.group(1), m.group(2)))
        else:
            kept.append(line)
    return "\n".join(kept).rstrip() + "\n", footnotes


def _append_sources_into_spec(
    spec_text: str,
    extra_sources: list[dict[str, Any]],
    extra_footnotes: list[tuple[str, str]],
) -> str:
    """Merge non-duplicate source entries and footnotes into a surviving spec document."""
    fm, body = _split_frontmatter(spec_text)
    if fm is None:
        return spec_text

    existing_sources = fm.get("sources")
    source_list = list(existing_sources) if isinstance(existing_sources, list) else []
    known_ids = {str(s.get("id", "")).strip() for s in source_list if isinstance(s, dict)}

    added_yaml_lines: list[str] = []
    for item in extra_sources:
        if not isinstance(item, dict):
            continue
        sid = str(item.get("id", "")).strip()
        res = str(item.get("resource", "")).strip()
        title = str(item.get("title", "")).strip() or sid
        if not sid or not res or sid in known_ids:
            continue
        known_ids.add(sid)
        added_yaml_lines.extend(
            [
                f"  - id: {sid}",
                f"    resource: {_format_yaml_scalar(res)}",
                f"    title: {_format_yaml_scalar(title)}",
            ]
        )

    updated = spec_text.replace("\r\n", "\n")
    if added_yaml_lines:
        end_idx = updated.find("\n---\n", 4)
        if end_idx != -1:
            fm_part = updated[4:end_idx]
            fm_lines = fm_part.splitlines()
            insert_at = len(fm_lines)
            for idx, ln in enumerate(fm_lines):
                if ln.startswith("sources:"):
                    insert_at = idx + 1
                    while insert_at < len(fm_lines) and (
                        fm_lines[insert_at].startswith((" ", "\t", "- ")) or not fm_lines[insert_at].strip()
                    ):
                        insert_at += 1
                    break
            fm_lines[insert_at:insert_at] = added_yaml_lines
            updated = "---\n" + "\n".join(fm_lines) + updated[end_idx:]

    _, next_body = _split_frontmatter(updated)
    existing_fns = {m.group(1) for m in re.finditer(r"^\[\^([^\]]+)\]:", next_body, re.MULTILINE)}
    new_fn_lines = [
        f"[^{fid}]: {ftext}" for fid, ftext in extra_footnotes if fid in known_ids and fid not in existing_fns
    ]
    for item in extra_sources:
        if isinstance(item, dict):
            sid = str(item.get("id", "")).strip()
            res = str(item.get("resource", "")).strip()
            already = any(ln.startswith(f"[^{sid}]:") for ln in new_fn_lines)
            if sid in known_ids and sid not in existing_fns and not already:
                new_fn_lines.append(f"[^{sid}]: `{res}`")
    if new_fn_lines:
        updated = updated.rstrip() + "\n" + "\n".join(new_fn_lines) + "\n"
    return updated


def _ordered_chapter_dirs(flow_dir: Path, root_fm: dict[str, Any]) -> list[Path]:
    """Return ordered chapter directories under ``flow_dir/chapters``."""
    chapters_dir = flow_dir / "chapters"
    if not chapters_dir.is_dir():
        return []
    disk_map = {p.name: p for p in sorted(chapters_dir.iterdir()) if p.is_dir()}
    declared = root_fm.get("chapters")
    ordered: list[Path] = []
    if isinstance(declared, list):
        for name in declared:
            clean = str(name).strip()
            if clean in disk_map:
                ordered.append(disk_map.pop(clean))
    ordered.extend(disk_map.values())
    return ordered


def _build_compaction_plan(bundle_root: Path, flow_dir: Path) -> CompactionPlan | None:
    """Analyze one spec directory and return a compaction plan when chapters are over-fragmented."""
    root_spec = flow_dir / "spec.md"
    if not root_spec.is_file():
        return None
    root_fm, _ = _read_fm(root_spec)
    root_state = str(root_fm.get("state") or "").strip().lower()
    if root_state in _PINNED_CHAPTER_STATES or root_fm.get("paused") is True:
        return None

    ch_dirs = _ordered_chapter_dirs(flow_dir, root_fm)
    if len(ch_dirs) < 2:
        return None

    ch_meta: list[dict[str, Any]] = []
    depended_by_empirical: set[str] = set()
    for ch_dir in ch_dirs:
        ch_spec = ch_dir / "spec.md"
        if not ch_spec.is_file():
            return None
        ch_fm, _ = _read_fm(ch_spec)
        tasks_dir = ch_dir / "tasks"
        task_files = sorted(p for p in tasks_dir.glob("*.md") if p.name != "index.md") if tasks_dir.is_dir() else []
        ch_state = str(ch_fm.get("state") or "planned").strip().lower()
        p_status = str(ch_fm.get("planning_status") or "complete").strip().lower()
        raw_deps = ch_fm.get("depends_on_chapters")
        deps = [str(d).strip() for d in raw_deps] if isinstance(raw_deps, list) else []
        if p_status == "empirical_dependent":
            depended_by_empirical.update(deps)
        ch_meta.append(
            {
                "id": ch_dir.name,
                "state": ch_state,
                "planning_status": p_status,
                "task_count": len(task_files),
            }
        )

    runs: list[list[dict[str, Any]]] = []
    current_run: list[dict[str, Any]] = []
    for item in ch_meta:
        is_pinned = (
            item["state"] in _PINNED_CHAPTER_STATES
            or item["planning_status"] == "empirical_dependent"
            or item["id"] in depended_by_empirical
        )
        if is_pinned:
            if len(current_run) >= 2 and any(c["task_count"] <= _SMALL_CHAPTER_THRESHOLD for c in current_run):
                runs.append(current_run)
            current_run = []
        else:
            current_run.append(item)

    if len(current_run) >= 2 and any(c["task_count"] <= _SMALL_CHAPTER_THRESHOLD for c in current_run):
        runs.append(current_run)

    if not runs:
        return None

    collapse_to_single = len(runs) == 1 and len(runs[0]) == len(ch_meta)
    run_tuples = tuple(tuple(c["id"] for c in run) for run in runs)
    rel_spec = root_spec.relative_to(bundle_root).as_posix()
    return CompactionPlan(
        flow_id=flow_dir.name,
        spec_path=rel_spec,
        total_chapters=len(ch_meta),
        collapse_to_single_chapter=collapse_to_single,
        merge_runs=run_tuples,
        reason=(
            f"Found {sum(len(r) for r in run_tuples)} small non-empirical open chapter(s) suitable for consolidation"
        ),
    )


def audit_specs(bundle_root: Path) -> list[CompactionPlan]:
    """Scan ``bundle_root/specs`` for fragmented multi-chapter specs created under small task caps."""
    specs_dir = bundle_root / "specs"
    if not specs_dir.is_dir():
        return []
    plans: list[CompactionPlan] = []
    for flow_dir in sorted(p for p in specs_dir.iterdir() if p.is_dir()):
        plan = _build_compaction_plan(bundle_root, flow_dir)
        if plan is not None:
            plans.append(plan)
    return plans


def _rewrite_spec_checklist_and_snapshot(spec_text: str, checklist_lines: list[str], snapshot_line: str) -> str:
    """Update sections 5 (checklist) and 6 (snapshot) cleanly inside a spec body."""
    updated = spec_text
    block = "\n".join(checklist_lines) + "\n\n"

    def _replace_s5(match: re.Match[str]) -> str:
        existing_body = match.group(2)
        recovery_idx = existing_body.find("### ")
        suffix = existing_body[recovery_idx:] if recovery_idx != -1 else ""
        if suffix and not block.endswith("\n\n"):
            return f"{match.group(1)}\n{block}{suffix}"
        return f"{match.group(1)}\n{block}{suffix}"

    if _CHECKLIST_SECTION_RE.search(updated):
        updated = _CHECKLIST_SECTION_RE.sub(_replace_s5, updated, count=1)
    else:
        updated = updated.rstrip() + "\n\n## 5. Implementation Plan\n\n" + block

    if _SNAPSHOT_SECTION_RE.search(updated):
        updated = _SNAPSHOT_SECTION_RE.sub(lambda m: f"{m.group(1)}\n{snapshot_line}\n\n", updated, count=1)
    return updated


def compact_specs(
    bundle_root: Path,
    *,
    flow_id: str | None = None,
    dry_run: bool = False,
) -> list[CompactionResult]:
    """Consolidate fragmented open non-empirical chapters while preserving task states, deps, and SHAs."""
    plans = audit_specs(bundle_root)
    if flow_id:
        plans = [p for p in plans if p.flow_id == flow_id]

    results: list[CompactionResult] = []
    for plan in plans:
        flow_dir = bundle_root / "specs" / plan.flow_id
        root_spec_path = flow_dir / "spec.md"
        root_raw = root_spec_path.read_text(encoding="utf-8")
        root_fm, _ = _split_frontmatter(root_raw)
        if root_fm is None:
            continue

        updated_files: list[str] = []
        removed_chapters: list[str] = []
        total_reindexed = 0

        merged_map: dict[str, tuple[str, ...]] = {run[0]: run for run in plan.merge_runs}
        absorbed_set = {ch_id for run in plan.merge_runs for ch_id in run[1:]}
        old_chapters = _ordered_chapter_dirs(flow_dir, root_fm)

        id_remap: dict[str, str] = {}
        new_chapter_ids: list[str] = []
        chapter_summaries: dict[str, tuple[str, str, str]] = {}

        if plan.collapse_to_single_chapter:
            move_ops: list[dict[str, Any]] = []
            target_dir = flow_dir / "tasks"
            collected_sources: list[dict[str, Any]] = []
            collected_footnotes: list[tuple[str, str]] = []
            task_seq = 1
            for ch_dir in old_chapters:
                ch_raw = (ch_dir / "spec.md").read_text(encoding="utf-8")
                ch_fm, ch_body = _split_frontmatter(ch_raw)
                if ch_fm and isinstance(ch_fm.get("sources"), list):
                    collected_sources.extend(ch_fm["sources"])
                _, ch_fns = _extract_footnotes(ch_body)
                collected_footnotes.extend(ch_fns)
                t_dir = ch_dir / "tasks"
                for tf in sorted(p for p in t_dir.glob("*.md") if p.name != "index.md") if t_dir.is_dir() else []:
                    tfm, tbody = _read_fm(tf)
                    short = f"t{task_seq:02d}"
                    slug = tf.name.split("-", 1)[1] if "-" in tf.name else tf.name
                    new_name = f"{short}-{slug}"
                    new_id = f"{plan.flow_id}:{short}"
                    old_id = str(tfm.get("id") or tf.stem).strip()
                    old_stem = tf.name.split("-", 1)[0]
                    for alias in {old_id, f"{ch_dir.name}:{old_stem}", old_stem, tf.stem}:
                        id_remap[alias] = new_id
                    move_ops.append(
                        {
                            "src": tf,
                            "dst": target_dir / new_name,
                            "new_id": new_id,
                            "new_chapter_id": None,
                            "tfm": tfm,
                            "tbody": tbody,
                            "title": str(tfm.get("title") or new_name),
                            "state": str(tfm.get("state") or "pending").strip(),
                            "commit": str(tfm.get("commit") or "").strip(),
                            "rel_link": f"tasks/{new_name}",
                            "raw": tf.read_text(encoding="utf-8"),
                        }
                    )
                    task_seq += 1
                removed_chapters.append(ch_dir.name)
            total_reindexed = len(move_ops)

            if not dry_run:
                target_dir.mkdir(parents=True, exist_ok=True)
                for op in move_ops:
                    deps_raw = op["tfm"].get("depends_on")
                    new_deps = []
                    if isinstance(deps_raw, list):
                        for d in deps_raw:
                            mapped = id_remap.get(str(d).strip(), str(d).strip())
                            if mapped != op["new_id"] and mapped not in new_deps:
                                new_deps.append(mapped)
                    rewritten = _update_frontmatter_lines(
                        op["raw"],
                        {
                            "id": op["new_id"],
                            "chapter_id": None,
                            "depends_on": new_deps,
                        },
                    )
                    op["dst"].write_text(rewritten, encoding="utf-8")
                    updated_files.append(op["dst"].relative_to(bundle_root).as_posix())

                shutil.rmtree(flow_dir / "chapters")
                first_open = next(
                    (op["new_id"] for op in move_ops if op["state"] not in _PINNED_CHAPTER_STATES),
                    None,
                )
                checklist = [
                    f"- {_expected_marker(op['state'], op['commit'])} {op['new_id']} — {op['title']} ({op['rel_link']})"
                    for op in move_ops
                ]
                next_root = _append_sources_into_spec(root_raw, collected_sources, collected_footnotes)
                next_root = _update_frontmatter_lines(
                    next_root,
                    {
                        "has_chapters": False,
                        "chapters": [],
                        "current_chapter": None,
                        "last_reviewed_chapter": None,
                        "current_task": first_open,
                    },
                )
                next_root = re.sub(r"\[([^\]]+)\]\((?:\./)?chapters/[^)]+\)", r"\1", next_root)
                next_root = _rewrite_spec_checklist_and_snapshot(
                    next_root,
                    checklist,
                    f"Active single-chapter flow compacted into {total_reindexed} vertical-slice tasks.",
                )
                root_spec_path.write_text(next_root, encoding="utf-8")
                updated_files.append(root_spec_path.relative_to(bundle_root).as_posix())

            results.append(
                CompactionResult(
                    flow_id=plan.flow_id,
                    dry_run=dry_run,
                    before_chapters=len(old_chapters),
                    after_chapters=0,
                    collapsed_to_single_chapter=True,
                    tasks_reindexed=total_reindexed,
                    removed_chapters=tuple(removed_chapters),
                    updated_files=tuple(sorted(set(updated_files))),
                )
            )
            continue

        for ch_dir in old_chapters:
            cid = ch_dir.name
            if cid in absorbed_set:
                removed_chapters.append(cid)
                continue
            new_chapter_ids.append(cid)
            if cid not in merged_map:
                ch_fm, _ = _read_fm(ch_dir / "spec.md")
                chapter_summaries[cid] = (
                    str(ch_fm.get("title") or cid),
                    str(ch_fm.get("state") or "planned"),
                    str(ch_fm.get("last_reviewed_commit") or "").strip(),
                )
                continue

            run = merged_map[cid]
            target_ch_dir = flow_dir / "chapters" / cid
            target_tasks_dir = target_ch_dir / "tasks"
            target_raw = (target_ch_dir / "spec.md").read_text(encoding="utf-8")
            target_fm, _ = _split_frontmatter(target_raw)
            collected_sources = []
            collected_footnotes = []
            run_ops: list[dict[str, Any]] = []
            task_seq = 1

            for member_id in run:
                member_dir = flow_dir / "chapters" / member_id
                if member_id != cid:
                    mfm, mbody = _read_fm(member_dir / "spec.md")
                    if isinstance(mfm.get("sources"), list):
                        collected_sources.extend(mfm["sources"])
                    _, mfns = _extract_footnotes(mbody)
                    collected_footnotes.extend(mfns)
                t_dir = member_dir / "tasks"
                for tf in sorted(p for p in t_dir.glob("*.md") if p.name != "index.md") if t_dir.is_dir() else []:
                    tfm, tbody = _read_fm(tf)
                    short = f"t{task_seq:02d}"
                    slug = tf.name.split("-", 1)[1] if "-" in tf.name else tf.name
                    new_name = f"{short}-{slug}"
                    new_id = f"{plan.flow_id}:{cid}:{short}"
                    old_id = str(tfm.get("id") or tf.stem).strip()
                    old_stem = tf.name.split("-", 1)[0]
                    for alias in {old_id, f"{member_id}:{old_stem}", f"{plan.flow_id}:{old_stem}", old_stem, tf.stem}:
                        id_remap[alias] = new_id
                    run_ops.append(
                        {
                            "src": tf,
                            "dst": target_tasks_dir / new_name,
                            "new_id": new_id,
                            "new_chapter_id": cid,
                            "tfm": tfm,
                            "tbody": tbody,
                            "title": str(tfm.get("title") or new_name),
                            "state": str(tfm.get("state") or "pending").strip(),
                            "commit": str(tfm.get("commit") or "").strip(),
                            "rel_link": f"tasks/{new_name}",
                            "raw": tf.read_text(encoding="utf-8"),
                        }
                    )
                    task_seq += 1

            total_reindexed += len(run_ops)
            chapter_summaries[cid] = (
                str((target_fm or {}).get("title") or cid),
                str((target_fm or {}).get("state") or "planned"),
                str((target_fm or {}).get("last_reviewed_commit") or "").strip(),
            )

            if not dry_run:
                staging_outputs: list[tuple[Path, str]] = []
                for op in run_ops:
                    deps_raw = op["tfm"].get("depends_on")
                    new_deps = []
                    if isinstance(deps_raw, list):
                        for d in deps_raw:
                            mapped = id_remap.get(str(d).strip(), str(d).strip())
                            if mapped != op["new_id"] and mapped not in new_deps:
                                new_deps.append(mapped)
                    rewritten = _update_frontmatter_lines(
                        op["raw"],
                        {
                            "id": op["new_id"],
                            "chapter_id": cid,
                            "depends_on": new_deps,
                        },
                    )
                    staging_outputs.append((op["dst"], rewritten))

                for old_file in list(target_tasks_dir.glob("*.md")):
                    if old_file.name != "index.md":
                        old_file.unlink()
                target_tasks_dir.mkdir(parents=True, exist_ok=True)
                for dst_path, text in staging_outputs:
                    dst_path.write_text(text, encoding="utf-8")
                    updated_files.append(dst_path.relative_to(bundle_root).as_posix())

                for member_id in run[1:]:
                    shutil.rmtree(flow_dir / "chapters" / member_id)

                first_open = next(
                    (op["new_id"] for op in run_ops if op["state"] not in _PINNED_CHAPTER_STATES),
                    None,
                )
                ch_checklist = [
                    f"- {_expected_marker(op['state'], op['commit'])} {op['new_id']} — {op['title']} ({op['rel_link']})"
                    for op in run_ops
                ]
                next_ch = _append_sources_into_spec(target_raw, collected_sources, collected_footnotes)
                next_ch = _update_frontmatter_lines(next_ch, {"current_task": first_open})
                next_ch = _rewrite_spec_checklist_and_snapshot(
                    next_ch,
                    ch_checklist,
                    f"Compacted deliverable chapter holding {len(run_ops)} vertical-slice tasks.",
                )
                (target_ch_dir / "spec.md").write_text(next_ch, encoding="utf-8")
                updated_files.append((target_ch_dir / "spec.md").relative_to(bundle_root).as_posix())

        if not dry_run:
            idx_path = flow_dir / "chapters" / "index.md"
            idx_lines = [f"# Chapters: {root_fm.get('title') or plan.flow_id}", ""]
            root_checklist: list[str] = []
            for cid in new_chapter_ids:
                ctitle, cstate, csha = chapter_summaries[cid]
                idx_lines.append(f"- [{cid} — {ctitle}]({cid}/spec.md) — [{cstate}] Deliverable chapter.")
                root_checklist.append(f"- {_expected_marker(cstate, csha)} {cid} — {ctitle} (chapters/{cid}/spec.md)")
            idx_path.write_text("\n".join(idx_lines) + "\n", encoding="utf-8")
            updated_files.append(idx_path.relative_to(bundle_root).as_posix())

            curr_ch = str(root_fm.get("current_chapter") or "").strip()
            if curr_ch not in new_chapter_ids:
                curr_ch = next(
                    (cid for cid in new_chapter_ids if chapter_summaries[cid][1].lower() not in _PINNED_CHAPTER_STATES),
                    new_chapter_ids[0],
                )
            next_root = _update_frontmatter_lines(
                root_raw,
                {
                    "chapters": new_chapter_ids,
                    "current_chapter": curr_ch,
                },
            )
            for lead_cid, run in merged_map.items():
                for member_cid in run[1:]:
                    next_root = next_root.replace(f"chapters/{member_cid}/", f"chapters/{lead_cid}/")
            next_root = _rewrite_spec_checklist_and_snapshot(
                next_root,
                root_checklist,
                f"Active chapter `{curr_ch}` across {len(new_chapter_ids)} deliverable chapter(s).",
            )
            root_spec_path.write_text(next_root, encoding="utf-8")
            updated_files.append(root_spec_path.relative_to(bundle_root).as_posix())

        results.append(
            CompactionResult(
                flow_id=plan.flow_id,
                dry_run=dry_run,
                before_chapters=len(old_chapters),
                after_chapters=len(new_chapter_ids),
                collapsed_to_single_chapter=False,
                tasks_reindexed=total_reindexed,
                removed_chapters=tuple(removed_chapters),
                updated_files=tuple(sorted(set(updated_files))),
            )
        )

    return results


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for auditing or compacting over-fragmented Flow specs."""
    parser = argparse.ArgumentParser(description="Audit or compact over-fragmented Flow specifications.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for cmd_name in ("audit", "apply"):
        sub = subparsers.add_parser(cmd_name)
        sub.add_argument("--bundle", type=Path, default=Path(".agents/bundles"), help="Path to OKF bundle root.")
        sub.add_argument("--flow", type=str, default=None, help="Optional flow_id filter.")
        sub.add_argument("--json", action="store_true", help="Emit structured JSON output.")
        if cmd_name == "apply":
            sub.add_argument("--dry-run", action="store_true", help="Preview changes without modifying disk.")

    ns = parser.parse_args(argv)
    bundle_root = ns.bundle.resolve()
    if ns.command == "audit":
        plans = audit_specs(bundle_root)
        if ns.flow:
            plans = [p for p in plans if p.flow_id == ns.flow]
        payload = {"fragmented_specs": [p.to_dict() for p in plans], "count": len(plans)}
        if ns.json:
            print(json.dumps(payload, indent=2))
        else:
            sys.stdout.write(f"Fragmented specs: {len(plans)}\n")
            for p in plans:
                sys.stdout.write(f"  - {p.flow_id}: {p.reason} (collapse_single={p.collapse_to_single_chapter})\n")
        return 0

    results = compact_specs(bundle_root, flow_id=ns.flow, dry_run=bool(getattr(ns, "dry_run", False)))
    payload = {"compacted_specs": [r.to_dict() for r in results], "count": len(results)}
    if ns.json:
        print(json.dumps(payload, indent=2))
    else:
        sys.stdout.write(f"Compacted specs: {len(results)}\n")
        for r in results:
            sys.stdout.write(
                f"  - {r.flow_id}: chapters {r.before_chapters} -> {r.after_chapters}, tasks={r.tasks_reindexed}\n"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

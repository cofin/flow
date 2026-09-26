"""Flow completion and knowledge consolidation utility.

Extracts task discoveries, flow-level learnings, architectural decisions, and
promoted research into a structured 5-dimension synthesis manifest prior to
spec contraction, and enforces terminal task-state safety before bundle removal.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(os.environ.get("FLOW_REPO_ROOT", Path(__file__).resolve().parents[1]))


def _parse_yaml_frontmatter(content: str) -> tuple[dict[str, Any] | None, str]:
    """Parse YAML frontmatter and Markdown body from a document string."""
    content = content.replace("\r\n", "\n")
    if not content.startswith("---\n"):
        return None, content
    parts = content.split("---\n", 2)
    if len(parts) < 3:
        return None, content
    try:
        data = yaml.safe_load(parts[1])
        if isinstance(data, dict):
            return data, parts[2]
    except yaml.YAMLError:
        pass
    return None, content


def _extract_notes(body: str) -> str:
    """Extract the Notes & Discoveries or Learnings section from a task body."""
    pattern = re.compile(
        r"(?mi)^##\s+(?:Notes\s+&\s+Discoveries|Learnings)\b(.*?)(?=(?:^##\s+)|\Z)",
        re.DOTALL | re.MULTILINE,
    )
    match = pattern.search(body)
    if match:
        return match.group(1).strip()
    return ""


def consolidate_flow_learnings(flow_id: str, repo_root: Path = REPO_ROOT) -> Path:
    """Consolidate task notes, learnings.md, and research into extracted_learnings.md."""
    specs_dir = repo_root / ".agents" / "bundles" / "specs"
    flow_dir = specs_dir / flow_id
    if not flow_dir.is_dir():
        raise FileNotFoundError(f"Flow directory not found: {flow_dir}")

    tasks_dir = flow_dir / "tasks"
    notes_list: list[str] = []

    learnings_file = flow_dir / "learnings.md"
    if learnings_file.is_file():
        try:
            _, l_body = _parse_yaml_frontmatter(learnings_file.read_text(encoding="utf-8"))
            stripped = l_body.strip()
            if stripped:
                notes_list.append(f"### Flow Learnings ({flow_id})\n\n{stripped}\n")
        except OSError as exc:
            print(f"Warning: Failed to process {learnings_file}: {exc}", file=sys.stderr)

    research_dir = flow_dir / "research"
    if research_dir.is_dir():
        for research_file in sorted(research_dir.glob("*.md")):
            try:
                _, r_body = _parse_yaml_frontmatter(
                    research_file.read_text(encoding="utf-8")
                )
                stripped = r_body.strip()
                if stripped:
                    notes_list.append(
                        f"### Promoted Research: {research_file.name}\n\n{stripped}\n"
                    )
            except OSError as exc:
                print(
                    f"Warning: Failed to process {research_file}: {exc}",
                    file=sys.stderr,
                )

    if tasks_dir.is_dir():
        for task_file in sorted(tasks_dir.glob("*.md")):
            try:
                content = task_file.read_text(encoding="utf-8")
                metadata, body = _parse_yaml_frontmatter(content)
                if not metadata:
                    continue

                notes = _extract_notes(body)
                if not notes:
                    continue

                task_id = metadata.get("id", f"{flow_id}:{task_file.stem}")
                title = metadata.get("title", task_file.stem)
                state = metadata.get("state") or metadata.get("status") or "open"
                commit = metadata.get("commit")
                files = metadata.get("files", [])

                header = f"### Task {task_id}: {title} ({state})"
                if commit:
                    header += f" [{commit}]"

                section = [header]
                if files:
                    section.append(f"**Files**: {', '.join(files)}")
                section.append("")
                section.append(notes)
                section.append("")

                notes_list.append("\n".join(section))
            except Exception as exc:
                print(f"Warning: Failed to process {task_file}: {exc}", file=sys.stderr)

    extracted_path = flow_dir / "extracted_learnings.md"
    if not notes_list:
        print(
            f"No task notes found for flow '{flow_id}'; nothing written.",
            file=sys.stderr,
        )
        return extracted_path

    synthesis_checklist = (
        "## 5-Dimension Synthesis Checklist\n\n"
        "- [ ] Domain Model & Invariants (`knowledge/domains/<domain>.md`)\n"
        "- [ ] Architecture & Deep Module Seams (`knowledge/architecture/<area>.md`)\n"
        "- [ ] Idiomatic Patterns & Anti-Patterns (`knowledge/patterns/<topic>.md`)\n"
        "- [ ] Build, Verification & Testing Recipes (`knowledge/testing/<topic>.md` or `knowledge/workflow.md`)\n"
        "- [ ] Hard-Won Gotchas & Edge Cases (`knowledge/gotchas/<topic>.md`)\n\n"
    )
    extracted_content = (
        f"---\ntype: Learnings\n---\n\n# Extracted Learnings: {flow_id}\n\n"
        + synthesis_checklist
        + "\n---\n\n".join(notes_list)
    )
    extracted_path.write_text(extracted_content, encoding="utf-8")
    return extracted_path


def delete_flow_bundle(
    flow_id: str, repo_root: Path = REPO_ROOT, force: bool = False
) -> None:
    """Safely delete a completed flow bundle directory after verifying task states."""
    specs_dir = repo_root / ".agents" / "bundles" / "specs"
    flow_dir = specs_dir / flow_id
    if not flow_dir.is_dir():
        raise FileNotFoundError(f"Flow directory not found: {flow_dir}")

    if not force:
        tasks_dir = flow_dir / "tasks"
        if tasks_dir.is_dir():
            for task_file in tasks_dir.glob("*.md"):
                try:
                    content = task_file.read_text(encoding="utf-8")
                    metadata, _ = _parse_yaml_frontmatter(content)
                except OSError as exc:
                    raise ValueError(
                        f"Cannot delete flow '{flow_id}': task '{task_file.name}' is unreadable ({exc}). "
                        "Use --force to override."
                    ) from exc
                if metadata is None:
                    raise ValueError(
                        f"Cannot delete flow '{flow_id}': task '{task_file.name}' has invalid frontmatter. "
                        "Use --force to override."
                    )
                state = metadata.get("state") or metadata.get("status") or "open"
                if state not in ("closed", "skipped"):
                    raise ValueError(
                        f"Cannot delete flow '{flow_id}': task '{task_file.name}' is '{state}'. "
                        "Flow contains open or in-progress tasks. Use --force to override."
                    )

    shutil.rmtree(flow_dir)


def revert_flow_bundle_delete(flow_id: str, repo_root: Path = REPO_ROOT) -> None:
    """Restore a deleted flow bundle directory from Git HEAD."""
    target_rel_path = Path(".agents") / "bundles" / "specs" / flow_id

    try:
        subprocess.run(
            ["git", "checkout", "HEAD", "--", target_rel_path.as_posix()],
            cwd=str(repo_root),
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        print(f"Error reverting delete: {exc.stderr}", file=sys.stderr)
        raise RuntimeError(
            "Flow spec folder was not committed/tracked in Git. Cannot auto-restore."
        ) from exc


def main() -> None:
    """CLI entry point for flow_completion."""
    parser = argparse.ArgumentParser(description="Flow Completion & Archiving Utility")
    subparsers = parser.add_subparsers(dest="command", required=True)

    parser_cons = subparsers.add_parser(
        "consolidate",
        help="Consolidate task notes and discoveries into extracted_learnings.md",
    )
    parser_cons.add_argument("flow_id", help="The flow ID to process")

    parser_del = subparsers.add_parser(
        "delete", help="Safely delete a flow spec bundle directory"
    )
    parser_del.add_argument("flow_id", help="The flow ID to delete")
    parser_del.add_argument(
        "--force",
        action="store_true",
        help="Force deletion even if there are open tasks",
    )

    parser_rev = subparsers.add_parser(
        "revert-delete", help="Revert a deleted spec bundle directory via Git"
    )
    parser_rev.add_argument("flow_id", help="The flow ID to restore")

    args = parser.parse_args()

    try:
        if args.command == "consolidate":
            path = consolidate_flow_learnings(args.flow_id)
            print(f"Consolidated learnings written to {path}")
        elif args.command == "delete":
            delete_flow_bundle(args.flow_id, force=args.force)
            print(f"Successfully deleted spec bundle directory for flow: {args.flow_id}")
        elif args.command == "revert-delete":
            revert_flow_bundle_delete(args.flow_id)
            print(
                f"Successfully restored spec bundle directory for flow: {args.flow_id}"
            )
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

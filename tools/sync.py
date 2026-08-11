from __future__ import annotations
import datetime
import os
import re
from pathlib import Path
from typing import Any, Iterator
import yaml

REPO_ROOT = Path(os.environ.get("FLOW_REPO_ROOT", Path(__file__).resolve().parents[1]))

# Regex to match task checklist lines: "- [ ] Task 1.1: Setup spec [abc1234]"
TASK_LINE_PATTERN = re.compile(
    r"^(\s*-\s*\[([ ~x!-])\]\s*Task\s+([a-zA-Z0-9._-]+)\s*:\s*)(.*?)(?:\s*\[([a-fA-F0-9]{7,})\])?$",
    re.MULTILINE
)

def _validate_iso_timestamp(timestamp: str) -> bool:
    pattern = re.compile(
        r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?$"
    )
    return bool(pattern.match(timestamp))

def _parse_yaml_frontmatter(content: str) -> tuple[dict[str, Any] | None, int]:
    if not content.startswith("---\n"):
        return None, 0
    parts = content.split("---\n", 2)
    if len(parts) < 3:
        return None, 0
    try:
        data = yaml.safe_load(parts[1])
        if isinstance(data, dict):
            # Length of frontmatter block including delimiters
            frontmatter_len = len(parts[1]) + 8 # ---\n + \n---\n
            return data, frontmatter_len
    except yaml.YAMLError:
        pass
    return None, 0

def resolve_active_flow_dir(repo_root: Path = REPO_ROOT) -> Path | None:
    specs_dir = repo_root / ".agents" / "bundles" / "specs"
    if not specs_dir.is_dir():
        return None

    active_specs: list[tuple[Path, float]] = []
    for spec_dir in specs_dir.iterdir():
        if not spec_dir.is_dir():
            continue
        spec_file = spec_dir / "spec.md"
        if not spec_file.is_file():
            continue
        
        try:
            content = spec_file.read_text(encoding="utf-8")
            data, _ = _parse_yaml_frontmatter(content)
            if data and data.get("status") in ("planned", "active"):
                # Get the most recent mtime of any file in the spec directory
                mtimes = [p.stat().st_mtime for p in spec_dir.rglob("*") if p.is_file()]
                max_mtime = max(mtimes) if mtimes else spec_file.stat().st_mtime
                active_specs.append((spec_dir, max_mtime))
        except (OSError, ValueError):
            continue

    if not active_specs:
        return None
    
    if len(active_specs) == 1:
        return active_specs[0][0]
        
    # Sort by mtime descending (most recently modified first)
    active_specs.sort(key=lambda x: x[1], reverse=True)
    return active_specs[0][0]

def sync_flow_bundle(flow_dir: Path, repo_root: Path = REPO_ROOT) -> None:
    spec_file = flow_dir / "spec.md"
    if not spec_file.is_file():
        raise FileNotFoundError(f"Missing spec.md in flow directory: {flow_dir}")
        
    content = spec_file.read_text(encoding="utf-8")
    spec_data, fm_len = _parse_yaml_frontmatter(content)
    if spec_data is None:
        raise ValueError(f"Invalid YAML frontmatter in spec.md: {spec_file}")
        
    flow_id = spec_data.get("flow_id")
    if not flow_id:
        raise ValueError(f"Missing flow_id in spec.md frontmatter: {spec_file}")
        
    body = content[fm_len:]
    tasks_dir = flow_dir / "tasks"
    tasks_dir.mkdir(exist_ok=True)
    
    status_mapping_to_marker = {
        "open": " ",
        "in_progress": "~",
        "closed": "x",
        "blocked": "!",
        "skipped": "-"
    }
    
    status_marker_to_status = {
        " ": "open",
        "~": "in_progress",
        "x": "closed",
        "!": "blocked",
        "-": "skipped"
    }

    # Find and process task lines in spec.md body
    updated_body = body
    matches = list(TASK_LINE_PATTERN.finditer(body))
    
    # We will build replacements in reverse order to keep indices valid
    for match in reversed(matches):
        prefix_group = match.group(1) # e.g. "- [ ] Task 1.1: "
        marker_group = match.group(2) # e.g. " "
        short_id = match.group(3)     # e.g. "1.1"
        title = match.group(4).strip()
        sha = match.group(5)          # e.g. "abc1234"
        
        task_file = tasks_dir / f"{short_id}.md"
        task_id = f"{flow_id}:{short_id}"
        
        if not task_file.is_file():
            # Scaffold missing task file
            now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
            status = status_marker_to_status.get(marker_group, "open")
            
            task_fm = {
                "id": task_id,
                "status": status,
                "depends_on": [],
                "files": [],
                "tests": [],
                "created_at": now_iso,
                "updated_at": now_iso
            }
            if sha:
                task_fm["commit"] = sha
                
            task_fm_str = yaml.safe_dump(task_fm, default_flow_style=False, sort_keys=False)
            task_content = f"---\n{task_fm_str}---\n\n# Task {task_id}\n\n## Description\n{title}\n\n## Notes & Discoveries\n"
            task_file.write_text(task_content, encoding="utf-8")
            
            reconciled_marker = marker_group
            reconciled_sha = sha
        else:
            # Reconcile from task file
            task_content = task_file.read_text(encoding="utf-8")
            task_data, _ = _parse_yaml_frontmatter(task_content)
            if task_data is None:
                continue # Skip invalid task file
                
            task_status = task_data.get("status", "open")
            reconciled_marker = status_mapping_to_marker.get(task_status, " ")
            reconciled_sha = task_data.get("commit")
            
        # Reconstruct task line
        new_prefix = prefix_group.replace(f"[{marker_group}]", f"[{reconciled_marker}]")
        new_line = f"{new_prefix}{title}"
        if reconciled_sha:
            new_line += f" [{reconciled_sha}]"
            
        # Perform replacement in updated_body
        start, end = match.span()
        updated_body = updated_body[:start] + new_line + updated_body[end:]

    # Update updated_at timestamp in spec.md frontmatter
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
    spec_data["updated_at"] = now_iso
    
    new_fm_str = yaml.safe_dump(spec_data, default_flow_style=False, sort_keys=False)
    updated_content = f"---\n{new_fm_str}---\n{updated_body}"
    
    spec_file.write_text(updated_content, encoding="utf-8")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        flow_id = sys.argv[1]
        active_dir = REPO_ROOT / ".agents" / "bundles" / "specs" / flow_id
        if not active_dir.is_dir():
            print(f"Flow spec directory not found: {active_dir}", file=sys.stderr)
            sys.exit(1)
    else:
        active_dir = resolve_active_flow_dir(REPO_ROOT)
        
    if active_dir:
        print(f"Syncing flow bundle at: {active_dir.relative_to(REPO_ROOT)}")
        sync_flow_bundle(active_dir, REPO_ROOT)
        print("Sync complete.")
        sys.exit(0)
    else:
        print("No active flows found.", file=sys.stderr)
        sys.exit(1)

"""Generate maintainer/test-only priming diagnostics from the OKF bundles.

This repository-development oracle is retained for direct tests and diagnostics.
Installed hooks and plugins never invoke it, and it is not a consumer fallback.
"""

import argparse
import json
from pathlib import Path

SPEC_ACTIVE_STATES = ("planned", "active")
TASK_ACTIVE_STATES = ("open", "in_progress", "blocked")


def find_project_root() -> Path:
    curr = Path.cwd().resolve()
    for parent in [curr] + list(curr.parents):
        if (parent / ".agents").is_dir():
            return parent
    return curr


def parse_frontmatter(text: str) -> dict:
    fm = {}
    if not text.startswith("---\n"):
        return fm
    try:
        end = text.index("\n---\n", 4)
    except ValueError:
        return fm
    raw = text[4:end]
    for line in raw.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            fm[k.strip()] = v.strip().strip("'\"")
    return fm


def _state_of(fm: dict, default: str) -> str:
    return fm.get("state") or fm.get("status") or default


def strip_frontmatter(text: str) -> str:
    if not text.startswith("---\n"):
        return text
    try:
        end = text.index("\n---\n", 4)
    except ValueError:
        return text
    return text[end + len("\n---\n"):]


def parse_config(project_root: Path) -> tuple[Path, Path]:
    config_file = project_root / ".agents" / "config.json"
    bundles_dir = project_root / ".agents" / "bundles"
    knowledge_dir = bundles_dir / "knowledge"

    if config_file.is_file():
        try:
            data = json.loads(config_file.read_text(encoding="utf-8"))
            if "bundles_dir" in data:
                bundles_dir = project_root / data["bundles_dir"]
            if "knowledge_dir" in data:
                knowledge_dir = project_root / data["knowledge_dir"]
            elif "bundles_dir" in data:
                knowledge_dir = bundles_dir / "knowledge"
        except Exception:
            pass

    return bundles_dir, knowledge_dir


def extract_project_identity(product_dir: Path) -> str:
    file_path = product_dir / "product.md"
    if not file_path.is_file():
        return ""

    try:
        content = strip_frontmatter(file_path.read_text(encoding="utf-8"))
        lines = []
        for line in content.splitlines():
            line_str = line.strip()
            if not line_str or line_str.startswith("#"):
                continue
            lines.append(line_str)
            if len(lines) == 5:
                break
        return "\n".join(lines)
    except Exception:
        return ""


def extract_truths_from_file(filepath: Path) -> str:
    if not filepath.is_file():
        return ""
    try:
        content = strip_frontmatter(filepath.read_text(encoding="utf-8"))
        start_idx = content.find("<!-- truth: start -->")
        end_idx = content.find("<!-- truth: end -->")
        if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
            return content[start_idx + len("<!-- truth: start -->"):end_idx].strip()

        list_items = []
        for line in content.splitlines():
            line_str = line.strip()
            if line_str.startswith(("- ", "* ", "1. ")):
                list_items.append(line_str)
                if len(list_items) == 10:
                    break
        if list_items:
            return "\n".join(list_items)

        plain_text = "\n".join(line for line in content.splitlines() if not line.strip().startswith("#"))
        return plain_text[:200].strip()
    except Exception:
        return ""


def scan_active_flows_and_tasks(bundles_dir: Path, project_root: Path) -> list:
    specs_dir = bundles_dir / "specs"
    if not specs_dir.is_dir():
        return []

    active_flows = []

    for item in sorted(specs_dir.iterdir()):
        if not item.is_dir():
            continue
        spec_file = item / "spec.md"
        if not spec_file.is_file():
            continue

        try:
            content = spec_file.read_text(encoding="utf-8")
            fm = parse_frontmatter(content)
            state = _state_of(fm, "planned")
            if state in SPEC_ACTIVE_STATES:
                flow_id = fm.get("flow_id") or fm.get("id") or item.name
                flow_title = fm.get("title", flow_id)
                flow_desc = fm.get("description", "")

                tasks = []
                tasks_dir = item / "tasks"
                if tasks_dir.is_dir():
                    for task_file in sorted(tasks_dir.glob("*.md")):
                        try:
                            task_content = task_file.read_text(encoding="utf-8")
                            tfm = parse_frontmatter(task_content)
                            t_state = _state_of(tfm, "open")
                            if t_state in TASK_ACTIVE_STATES:
                                tasks.append({
                                    "id": tfm.get("id", task_file.stem),
                                    "title": tfm.get("title", task_file.stem),
                                    "state": t_state,
                                    "priority": tfm.get("priority", "P2"),
                                    "rel_path": str(task_file.relative_to(project_root))
                                })
                        except Exception:
                            pass

                active_flows.append({
                    "id": flow_id,
                    "title": flow_title,
                    "description": flow_desc,
                    "state": state,
                    "tasks": tasks,
                    "rel_path": str(spec_file.relative_to(project_root))
                })
        except Exception:
            pass

    return active_flows


def scan_custom_skills(bundles_dir: Path, project_root: Path) -> list:
    skills = []
    skill_roots = [
        project_root / ".agents" / "skills",
        bundles_dir / "skills"
    ]

    seen_names = set()

    for sroot in skill_roots:
        if not sroot.is_dir():
            continue
        for item in sorted(sroot.iterdir()):
            if not item.is_dir() or item.name in seen_names:
                continue
            skill_file = item / "SKILL.md"
            if skill_file.is_file():
                try:
                    content = skill_file.read_text(encoding="utf-8")
                    fm = parse_frontmatter(content)
                    name = fm.get("name", item.name)
                    desc = fm.get("description", "")
                    skills.append({
                        "name": name,
                        "description": desc,
                        "rel_path": str(skill_file.relative_to(project_root))
                    })
                    seen_names.add(item.name)
                except Exception:
                    pass
    return skills


def build_context(root: Path) -> str:
    bundles_dir, knowledge_dir = parse_config(root)

    identity = extract_project_identity(bundles_dir / "product")

    truths = []
    for filename in ("tech-stack.md", "workflow.md", "patterns.md"):
        if filename == "tech-stack.md":
            filepath = bundles_dir / "product" / filename
        else:
            filepath = knowledge_dir / filename
        if filepath.is_file():
            file_truths = extract_truths_from_file(filepath)
            if file_truths:
                truths.append(f"### {filename.capitalize()} Invariants\n{file_truths}")

    active_flows = scan_active_flows_and_tasks(bundles_dir, root)
    skills = scan_custom_skills(bundles_dir, root)

    md_blocks = []

    if identity:
        md_blocks.append(f"## Project Purpose\n{identity}")

    if truths:
        md_blocks.append("## Core Project Invariants\n" + "\n\n".join(truths))

    if active_flows:
        flow_lines = ["## Active Flows & Tasks"]
        for flow in active_flows:
            flow_lines.append(f"### Flow: [{flow['title']}]({flow['rel_path']}) ({flow['state']})")
            if flow['description']:
                flow_lines.append(f"*{flow['description']}*")
            if flow['tasks']:
                flow_lines.append("Pending Tasks:")
                for t in flow['tasks']:
                    flow_lines.append(f"- [{t['priority']}] [{t['title']}]({t['rel_path']}) ({t['state']})")
            else:
                flow_lines.append("No active tasks.")
        md_blocks.append("\n".join(flow_lines))

    if skills:
        skill_lines = ["## Custom Project Skills"]
        for s in skills:
            skill_lines.append(f"- **[{s['name']}]({s['rel_path']})**: {s['description']}")
        md_blocks.append("\n".join(skill_lines))

    return "\n\n".join(md_blocks) if md_blocks else "No project context resolved."


def main() -> None:
    parser = argparse.ArgumentParser(description="Flow Priming Context Generator")
    parser.add_argument("--legacy", action="store_true", help="Output legacy JSON format")
    parser.add_argument("--markdown", action="store_true", help="Output raw context markdown (oracle mode)")
    args = parser.parse_args()

    context_str = build_context(find_project_root())

    if args.markdown:
        print(context_str)
        return

    if args.legacy:
        output = {
            "additional_context": context_str
        }
    else:
        output = {
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": context_str
            }
        }

    print(json.dumps(output))


if __name__ == "__main__":
    main()

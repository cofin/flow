import json
from pathlib import Path
import tempfile

# We will test functions in tools.priming
# Since tools.priming doesn't exist yet, the import will fail during pytest collection.
# That is expected TDD behavior.

def test_parse_frontmatter() -> None:
    from tools.priming import parse_frontmatter
    
    # Standard frontmatter
    content = "---\nstatus: planned\ntitle: test-flow\n---\nbody content here"
    fm = parse_frontmatter(content)
    assert fm == {"status": "planned", "title": "test-flow"}

    # No frontmatter
    content_no_fm = "just body content"
    fm_no = parse_frontmatter(content_no_fm)
    assert fm_no == {}

    # Empty frontmatter
    content_empty = "---\n---\nbody"
    fm_empty = parse_frontmatter(content_empty)
    assert fm_empty == {}


def test_find_project_root() -> None:
    from tools.priming import find_project_root
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir).resolve()
        
        # Create a mock .agents folder
        (tmpdir_path / ".agents").mkdir()
        
        # Create nested subdirs
        nested = tmpdir_path / "foo" / "bar"
        nested.mkdir(parents=True)
        
        # Change cwd to nested dir and call find_project_root
        import os
        old_cwd = os.getcwd()
        os.chdir(str(nested))
        try:
            root = find_project_root()
            assert root == tmpdir_path
        finally:
            os.chdir(old_cwd)


def test_config_parsing() -> None:
    from tools.priming import parse_config
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir).resolve()
        agents_dir = tmp_path / ".agents"
        agents_dir.mkdir()
        
        # Case 1: Config file exists
        config_data = {
            "bundles_dir": "custom_specs",
            "knowledge_dir": "custom_knowledge"
        }
        (agents_dir / "config.json").write_text(json.dumps(config_data), encoding="utf-8")
        
        bundles, knowledge = parse_config(tmp_path)
        assert bundles == tmp_path / "custom_specs"
        assert knowledge == tmp_path / "custom_knowledge"
        
        # Case 2: Config file missing -> should fallback to defaults
        (agents_dir / "config.json").unlink()
        bundles_default, knowledge_default = parse_config(tmp_path)
        assert bundles_default == tmp_path / ".agents" / "bundles"
        assert knowledge_default == tmp_path / ".agents" / "bundles" / "knowledge"

def test_extract_project_identity() -> None:
    from tools.priming import extract_project_identity
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir).resolve()
        
        # Test Case 1: product.md under knowledge/product/product.md
        prod_dir = tmp_path / "product"
        prod_dir.mkdir()
        prod_content = """# Header
# Subheader

First line of identity.
Second line.

Third line.
Fourth line.
Fifth line.
Sixth line (should be ignored).
"""
        (prod_dir / "product.md").write_text(prod_content, encoding="utf-8")
        
        identity = extract_project_identity(tmp_path)
        lines = identity.splitlines()
        assert len(lines) == 5
        assert lines[0] == "First line of identity."
        assert lines[2] == "Third line."
        assert "Sixth line" not in identity

def test_extract_truths_from_file() -> None:
    from tools.priming import extract_truths_from_file
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir).resolve()
        file_path = tmp_path / "tech-stack.md"
        
        # Case 1: Markers present
        content = """# Tech Stack
<!-- truth: start -->
- Python 3.11
- Pytest
<!-- truth: end -->
Other content
"""
        file_path.write_text(content, encoding="utf-8")
        truths = extract_truths_from_file(file_path)
        assert truths == "- Python 3.11\n- Pytest"
        
        # Case 2: Markers missing, fallback to list items
        content_fallback = """# Workflow
Some intro text.
- Step 1
- Step 2
- Step 3
"""
        file_path.write_text(content_fallback, encoding="utf-8")
        truths_fb = extract_truths_from_file(file_path)
        assert "- Step 1" in truths_fb
        assert "- Step 3" in truths_fb

def test_scan_active_flows_and_tasks() -> None:
    from tools.priming import scan_active_flows_and_tasks
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir).resolve()
        specs_dir = tmp_path / "specs"
        specs_dir.mkdir()
        
        # Create an active flow
        flow_dir = specs_dir / "active-flow"
        flow_dir.mkdir()
        spec_content = """---
type: Spec
flow_id: active-flow
state: active
title: Active Flow Title
---
# Description
"""
        (flow_dir / "spec.md").write_text(spec_content, encoding="utf-8")

        # Create tasks directory
        tasks_dir = flow_dir / "tasks"
        tasks_dir.mkdir()

        task1 = """---
type: Task
id: active-flow:001
state: in_progress
title: Task 1 Title
---
"""
        task2 = """---
type: Task
id: active-flow:002
state: closed
title: Task 2 Title
---
"""
        (tasks_dir / "001-t1.md").write_text(task1, encoding="utf-8")
        (tasks_dir / "002-t2.md").write_text(task2, encoding="utf-8")

        # Create a completed flow (should be ignored)
        closed_flow = specs_dir / "completed-flow"
        closed_flow.mkdir()
        (closed_flow / "spec.md").write_text("---\ntype: Spec\nstate: completed\n---\n", encoding="utf-8")

        flows = scan_active_flows_and_tasks(tmp_path, tmp_path)
        
        assert len(flows) == 1
        assert flows[0]["id"] == "active-flow"
        assert flows[0]["title"] == "Active Flow Title"
        assert len(flows[0]["tasks"]) == 1
        assert flows[0]["tasks"][0]["id"] == "active-flow:001"
        assert flows[0]["tasks"][0]["title"] == "Task 1 Title"

def test_scan_custom_skills() -> None:
    from tools.priming import scan_custom_skills
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir).resolve()
        
        # Skill in .agents/skills/
        skills_dir1 = tmp_path / ".agents" / "skills" / "my-skill"
        skills_dir1.mkdir(parents=True)
        skill_content = """---
name: my-skill
description: Custom project skill description
---
# Workflow
"""
        (skills_dir1 / "SKILL.md").write_text(skill_content, encoding="utf-8")
        
        # Skill in bundles/skills/
        skills_dir2 = tmp_path / "bundles" / "skills" / "another-skill"
        skills_dir2.mkdir(parents=True)
        (skills_dir2 / "SKILL.md").write_text("---\nname: another-skill\ndescription: Another skill description\n---\n", encoding="utf-8")
        
        skills = scan_custom_skills(tmp_path / "bundles", tmp_path)
        assert len(skills) == 2
        names = [s["name"] for s in skills]
        assert "my-skill" in names
        assert "another-skill" in names


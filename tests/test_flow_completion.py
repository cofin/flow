from pathlib import Path
import pytest
from unittest.mock import patch, MagicMock
import shutil
import subprocess
import textwrap

from tools import flow_completion

def _write_okf_file(path: Path, frontmatter: str, content: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    dedented_fm = textwrap.dedent(frontmatter).strip()
    dedented_content = textwrap.dedent(content).strip()
    full_content = f"---\n{dedented_fm}\n---\n{dedented_content}"
    path.write_text(full_content, encoding="utf-8")

def test_consolidate(tmp_path: Path) -> None:
    # Setup directories
    spec_dir = tmp_path / ".agents" / "bundles" / "specs" / "test-flow"
    tasks_dir = spec_dir / "tasks"
    tasks_dir.mkdir(parents=True, exist_ok=True)
    
    # Task 1
    _write_okf_file(
        tasks_dir / "001-test.md",
        """
id: test-flow:001-test
status: closed
depends_on: []
files:
  - src/test.py
tests: []
created_at: 2026-08-11T12:00:00Z
updated_at: 2026-08-11T12:00:00Z
commit: abc1234
""",
        content="""
# Test Task 1

## Notes & Discoveries
- Discovery A from task 1.
- Discovery B from task 1.
"""
    )

    # Task 2 (uses "Learnings" header instead of "Notes & Discoveries")
    _write_okf_file(
        tasks_dir / "002-test.md",
        """
id: test-flow:002-test
status: closed
depends_on: []
files:
  - src/test2.py
tests: []
created_at: 2026-08-11T12:00:00Z
updated_at: 2026-08-11T12:00:00Z
commit: def5678
""",
        content="""
# Test Task 2

## Learnings
- Learning C from task 2.
"""
    )

    # Call consolidate function
    flow_completion.consolidate_flow_learnings("test-flow", repo_root=tmp_path)
    
    extracted_path = spec_dir / "extracted_learnings.md"
    assert extracted_path.is_file()
    
    output = extracted_path.read_text(encoding="utf-8")
    assert "test-flow:001-test" in output
    assert "Discovery A from task 1" in output
    assert "Discovery B from task 1" in output
    assert "test-flow:002-test" in output
    assert "Learning C from task 2" in output

def test_delete_safety(tmp_path: Path) -> None:
    spec_dir = tmp_path / ".agents" / "bundles" / "specs" / "test-flow"
    tasks_dir = spec_dir / "tasks"
    tasks_dir.mkdir(parents=True, exist_ok=True)
    
    # Write a spec file
    _write_okf_file(
        spec_dir / "spec.md",
        """
flow_id: test-flow
type: feature
status: active
created_at: 2026-08-11T12:00:00Z
updated_at: 2026-08-11T12:00:00Z
description: Test flow
"""
    )
    
    # Task 1: open
    _write_okf_file(
        tasks_dir / "001-test.md",
        """
id: test-flow:001-test
status: open
depends_on: []
files: []
tests: []
created_at: 2026-08-11T12:00:00Z
updated_at: 2026-08-11T12:00:00Z
"""
    )
    
    # Try deleting without force - should fail
    with pytest.raises(ValueError, match="contains open or in-progress tasks"):
        flow_completion.delete_flow_bundle("test-flow", repo_root=tmp_path, force=False)
        
    assert spec_dir.is_dir()
    
    # Delete with force - should succeed
    flow_completion.delete_flow_bundle("test-flow", repo_root=tmp_path, force=True)
    assert not spec_dir.exists()

def test_delete_success_all_closed(tmp_path: Path) -> None:
    spec_dir = tmp_path / ".agents" / "bundles" / "specs" / "test-flow"
    tasks_dir = spec_dir / "tasks"
    tasks_dir.mkdir(parents=True, exist_ok=True)
    
    _write_okf_file(
        spec_dir / "spec.md",
        """
flow_id: test-flow
type: feature
status: completed
created_at: 2026-08-11T12:00:00Z
updated_at: 2026-08-11T12:00:00Z
description: Test flow
"""
    )
    
    # Task 1: closed
    _write_okf_file(
        tasks_dir / "001-test.md",
        """
id: test-flow:001-test
status: closed
depends_on: []
files: []
tests: []
created_at: 2026-08-11T12:00:00Z
updated_at: 2026-08-11T12:00:00Z
"""
    )
    
    # Task 2: skipped
    _write_okf_file(
        tasks_dir / "002-test.md",
        """
id: test-flow:002-test
status: skipped
depends_on: []
files: []
tests: []
created_at: 2026-08-11T12:00:00Z
updated_at: 2026-08-11T12:00:00Z
"""
    )
    
    flow_completion.delete_flow_bundle("test-flow", repo_root=tmp_path, force=False)
    assert not spec_dir.exists()

def test_revert_delete(tmp_path: Path) -> None:
    with patch("subprocess.run") as mock_run:
        # Mock subprocess to simulate success
        mock_run.return_value = MagicMock(returncode=0)
        
        flow_completion.revert_flow_bundle_delete("test-flow", repo_root=tmp_path)
        
        # Should call git checkout
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert "git" in args
        assert "checkout" in args
        assert "HEAD" in args
        # The path should contain the spec directory path
        spec_rel_path = "bundles/specs/test-flow"
        assert any(spec_rel_path in str(arg) for arg in args)

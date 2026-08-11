from __future__ import annotations
import importlib.util
import json
import os
from pathlib import Path
import time
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SYNC_MODULE_PATH = REPO_ROOT / "tools" / "sync.py"

def _load_sync_module():
    spec = importlib.util.spec_from_file_location("sync_flow", SYNC_MODULE_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

sync_flow = _load_sync_module()

def _write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

def test_sync_auto_discovery_resolves_most_recent_active_spec(tmp_path: Path) -> None:
    # Set up specs dir
    specs_dir = tmp_path / ".agents" / "bundles" / "specs"
    
    # 1. Completed flow (should be ignored)
    _write_file(
        specs_dir / "flow-completed" / "spec.md",
        """---
flow_id: flow-completed
status: completed
type: feature
created_at: 2026-08-11T12:00:00Z
updated_at: 2026-08-11T12:00:00Z
description: Done
---
"""
    )
    
    # 2. First active flow (older modification)
    flow_active1_dir = specs_dir / "flow-active-1"
    _write_file(
        flow_active1_dir / "spec.md",
        """---
flow_id: flow-active-1
status: active
type: feature
created_at: 2026-08-11T12:00:00Z
updated_at: 2026-08-11T12:00:00Z
description: Active 1
---
"""
    )
    
    # Sleep to ensure timestamp difference
    time.sleep(0.1)
    
    # 3. Second active flow (newer modification)
    flow_active2_dir = specs_dir / "flow-active-2"
    _write_file(
        flow_active2_dir / "spec.md",
        """---
flow_id: flow-active-2
status: active
type: feature
created_at: 2026-08-11T12:00:00Z
updated_at: 2026-08-11T12:00:00Z
description: Active 2
---
"""
    )
    
    # Auto discovery should resolve to flow-active-2
    resolved_flow_dir = sync_flow.resolve_active_flow_dir(repo_root=tmp_path)
    assert resolved_flow_dir is not None
    assert resolved_flow_dir.name == "flow-active-2"


def test_sync_reconciles_status_markers_and_commits(tmp_path: Path) -> None:
    flow_dir = tmp_path / ".agents" / "bundles" / "specs" / "test-flow"
    
    # Create spec.md with tasks
    spec_content = """---
flow_id: test-flow
status: active
type: feature
created_at: 2026-08-11T12:00:00Z
updated_at: 2026-08-11T12:00:00Z
description: Test flow
---
# Flow Spec

## Implementation Plan

### Phase 1: Setup
- [ ] Task 1.1: First task
- [ ] Task 1.2: Second task
- [ ] Task 1.3: Third task
"""
    _write_file(flow_dir / "spec.md", spec_content)
    
    # Create task files with different statuses
    _write_file(
        flow_dir / "tasks" / "1.1.md",
        """---
id: test-flow:1.1
status: closed
commit: abc1234
depends_on: []
files: []
tests: []
created_at: 2026-08-11T12:00:00Z
updated_at: 2026-08-11T12:00:00Z
---
"""
    )
    
    _write_file(
        flow_dir / "tasks" / "1.2.md",
        """---
id: test-flow:1.2
status: in_progress
depends_on: [test-flow:1.1]
files: []
tests: []
created_at: 2026-08-11T12:00:00Z
updated_at: 2026-08-11T12:00:00Z
---
"""
    )
    
    # task 1.3 has no task file (should be auto-created as status: open)
    
    # Run sync
    sync_flow.sync_flow_bundle(flow_dir, repo_root=tmp_path)
    
    # Read spec.md and assert reconciled markers
    updated_spec = (flow_dir / "spec.md").read_text(encoding="utf-8")
    
    assert "- [x] Task 1.1: First task [abc1234]" in updated_spec
    assert "- [~] Task 1.2: Second task" in updated_spec
    assert "- [ ] Task 1.3: Third task" in updated_spec
    
    # Check that tasks/1.3.md was auto-created
    task_1_3_path = flow_dir / "tasks" / "1.3.md"
    assert task_1_3_path.is_file()
    task_1_3_content = task_1_3_path.read_text(encoding="utf-8")
    assert "id: test-flow:1.3" in task_1_3_content
    assert "status: open" in task_1_3_content


def test_sync_cli_with_flow_id_argument(tmp_path: Path) -> None:
    import subprocess
    import sys
    
    flow_dir = tmp_path / ".agents" / "bundles" / "specs" / "cli-flow"
    spec_content = """---
flow_id: cli-flow
status: active
type: feature
created_at: 2026-08-11T12:00:00Z
updated_at: 2026-08-11T12:00:00Z
description: CLI flow
---
# Flow Spec

## Implementation Plan

### Phase 1: Setup
- [ ] Task 1.1: First task
"""
    _write_file(flow_dir / "spec.md", spec_content)
    
    # Run tools/sync.py as CLI subprocess
    subprocess.run(
        [sys.executable, str(SYNC_MODULE_PATH), "cli-flow"],
        env={**os.environ, "FLOW_REPO_ROOT": str(tmp_path)},
        check=True,
        capture_output=True
    )
    
    # Check that task 1.1 file was auto-scaffolded
    task_file = flow_dir / "tasks" / "1.1.md"
    assert task_file.is_file()
    assert "id: cli-flow:1.1" in task_file.read_text(encoding="utf-8")


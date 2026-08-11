from __future__ import annotations
import importlib.util
import json
import os
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
STATUS_MODULE_PATH = REPO_ROOT / "tools" / "status.py"

def _load_status_module():
    spec = importlib.util.spec_from_file_location("status_flow", STATUS_MODULE_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

status_flow = _load_status_module()

def _write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

def test_status_dashboard_aggregates_metrics_correctly(tmp_path: Path) -> None:
    specs_dir = tmp_path / ".agents" / "bundles" / "specs"
    flow_dir = specs_dir / "test-flow"
    
    # 1. Spec
    _write_file(
        flow_dir / "spec.md",
        """---
flow_id: test-flow
status: active
type: feature
created_at: 2026-08-11T12:00:00Z
updated_at: 2026-08-11T12:00:00Z
description: Test flow
---
# Spec
"""
    )
    
    # 2. Closed task (1.1)
    _write_file(
        flow_dir / "tasks" / "1.1.md",
        """---
id: test-flow:1.1
status: closed
depends_on: []
files: []
tests: []
created_at: 2026-08-11T12:00:00Z
updated_at: 2026-08-11T12:00:00Z
---
# Task 1.1

## Notes & Discoveries
- [2026-08-11 12:00] Note A
"""
    )
    
    # 3. In Progress task (1.2)
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
# Task 1.2

## Notes & Discoveries
- [2026-08-11 12:10] Note B
"""
    )
    
    # 4. Open task, blocked on 1.2 (1.3)
    _write_file(
        flow_dir / "tasks" / "1.3.md",
        """---
id: test-flow:1.3
status: open
depends_on: [test-flow:1.2]
files: []
tests: []
created_at: 2026-08-11T12:00:00Z
updated_at: 2026-08-11T12:00:00Z
---
# Task 1.3
"""
    )
    
    # 5. Open task, ready (1.4)
    _write_file(
        flow_dir / "tasks" / "1.4.md",
        """---
id: test-flow:1.4
status: open
depends_on: []
files: []
tests: []
created_at: 2026-08-11T12:00:00Z
updated_at: 2026-08-11T12:00:00Z
---
# Task 1.4
"""
    )

    # 6. Skipped task (1.5)
    _write_file(
        flow_dir / "tasks" / "1.5.md",
        """---
id: test-flow:1.5
status: skipped
depends_on: []
files: []
tests: []
created_at: 2026-08-11T12:00:00Z
updated_at: 2026-08-11T12:00:00Z
---
# Task 1.5
"""
    )

    dashboard = status_flow.generate_status_dashboard(repo_root=tmp_path)
    
    # Reconciled specs count
    assert dashboard["active_flows_count"] == 1
    flow_info = dashboard["flows"]["test-flow"]
    
    # Metrics check
    assert flow_info["total_tasks"] == 5 # 1.1, 1.2, 1.3, 1.4, 1.5
    assert flow_info["closed_count"] == 1
    assert flow_info["skipped_count"] == 1
    # progress = closed / (total - skipped) * 100 = 1 / 4 * 100 = 25%
    assert flow_info["progress_percentage"] == 25.0
    
    # Queues check
    assert flow_info["active_tasks"] == ["test-flow:1.2"]
    assert flow_info["ready_queue"] == ["test-flow:1.4"] # 1.3 is blocked on 1.2
    assert flow_info["blocked_queue"] == ["test-flow:1.3"]
    
    # Notes check
    notes = dashboard["recent_notes"]
    assert len(notes) == 2
    assert notes[0]["text"] == "Note B"
    assert notes[0]["task_id"] == "test-flow:1.2"
    assert notes[1]["text"] == "Note A"
    assert notes[1]["task_id"] == "test-flow:1.1"

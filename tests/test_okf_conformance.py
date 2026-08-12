"""A canonical OKF v0.2 bundle must pass the validator end-to-end.

Fixture-based: the repo's own .agents/bundles/ is local-only dogfooding and is
never committed, so conformance is proven against a generated bundle instead.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
VALIDATE_MODULE_PATH = REPO_ROOT / "tools" / "validate.py"


def _load_validate_module():
    spec = importlib.util.spec_from_file_location("validate_flow", VALIDATE_MODULE_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


validate = _load_validate_module()


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _build_canonical_bundle(root: Path) -> Path:
    bundles = root / ".agents" / "bundles"
    _write(bundles / "index.md", '---\nokf_version: "0.2"\n---\n\n# Bundle\n')
    _write(bundles / "log.md", "# Bundle Log\n\n## 2026-08-12\n\n**Creation** Initial bundle.\n")
    _write(
        bundles / "knowledge" / "patterns.md",
        "---\ntype: Pattern\ntitle: Patterns\n---\n\n# Patterns\n",
    )
    flow_dir = bundles / "specs" / "demo-flow"
    _write(
        flow_dir / "spec.md",
        """---
type: Spec
flow_id: demo-flow
title: Demo Flow
state: active
created_at: 2026-08-11T12:00:00Z
updated_at: 2026-08-11T12:00:00Z
---
# Demo Flow

## Implementation Plan

### Phase 1
- [x] Task 1.1: Done task [abc1234]
- [ ] Task 1.2: Open task
""",
    )
    _write(
        flow_dir / "tasks" / "1.1.md",
        """---
type: Task
id: demo-flow:1.1
title: Done task
state: closed
depends_on: []
files: []
tests: []
created_at: 2026-08-11T12:00:00Z
updated_at: 2026-08-11T12:00:00Z
commit: abc1234
---
# Task 1.1

## Notes & Discoveries
- [2026-08-11 12:00] Example note.
""",
    )
    _write(
        flow_dir / "tasks" / "1.2.md",
        """---
type: Task
id: demo-flow:1.2
title: Open task
state: open
depends_on: ["1.1"]
files: []
tests: []
created_at: 2026-08-11T12:00:00Z
updated_at: 2026-08-11T12:00:00Z
commit: null
---
# Task 1.2
""",
    )
    return bundles


def test_canonical_bundle_root_passes(tmp_path: Path) -> None:
    _build_canonical_bundle(tmp_path)
    assert validate.validate_okf_bundle_root(tmp_path) == []


def test_canonical_spec_bundle_passes(tmp_path: Path) -> None:
    bundles = _build_canonical_bundle(tmp_path)
    bundle_dirs = list(validate.iter_okf_bundles(tmp_path))
    assert bundle_dirs == [bundles / "specs" / "demo-flow"]
    violations = validate.validate_okf_bundle(bundle_dirs[0], tmp_path)
    assert violations == [], "\n".join(str(v) for v in violations)


def test_missing_okf_version_is_flagged(tmp_path: Path) -> None:
    _build_canonical_bundle(tmp_path)
    (tmp_path / ".agents" / "bundles" / "index.md").write_text("# Bundle\n", encoding="utf-8")
    violations = validate.validate_okf_bundle_root(tmp_path)
    assert any("okf_version" in v.message for v in violations)


def test_workflow_state_in_status_is_flagged(tmp_path: Path) -> None:
    bundles = _build_canonical_bundle(tmp_path)
    task = bundles / "specs" / "demo-flow" / "tasks" / "1.2.md"
    task.write_text(task.read_text(encoding="utf-8").replace("state: open", "status: open"), encoding="utf-8")
    violations = validate.validate_okf_bundle(bundles / "specs" / "demo-flow", tmp_path)
    assert any("OKF lifecycle" in v.message for v in violations)

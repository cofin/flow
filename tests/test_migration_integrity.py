"""Regression coverage for brownfield Flow migration integrity."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = REPO_ROOT / "tests" / "fixtures" / "migrations"


def _load_validate_module():
    path = REPO_ROOT / "tools" / "validate.py"
    spec = importlib.util.spec_from_file_location("validate_flow_migrations", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


validate = _load_validate_module()


def test_beekeeper_partial_reports_each_failed_postcondition() -> None:
    result = validate.validate_migration_integrity(FIXTURES / "beekeeper-partial")
    messages = "\n".join(violation.message for violation in result.violations)

    for expected in (
        "active legacy spec has no migrated bundle destination",
        "legacy and bundle product authorities coexist",
        "legacy and bundle workflow authorities coexist",
        "legacy and bundle knowledge authorities coexist",
        "operational content references legacy path",
        "operational skill is installed under .agents/bundles/skills",
        "setup claims completion while migration postconditions fail",
        "setup retains contradictory Beads backend authority",
        "bundle log claims migration completion while postconditions fail",
        "migration inventory omits live source",
        "semantic mapping is missing",
    ):
        assert expected in messages

    assert {item.disposition for item in result.inventory} <= {
        "migrate",
        "synthesize",
        "remove_after_verify",
        "preserve_local_policy",
    }
    assert {item.source for item in result.inventory} >= {
        ".agents/specs/beekeeper-convergence",
        ".agents/specs/queues-prerequisites",
        ".agents/product.md",
        ".agents/workflow.md",
        ".agents/knowledge",
        ".agents/bundles/skills/flow-memory-keeper",
        ".agents/beads.json",
    }


def test_beekeeper_corrected_is_lossless_and_single_authority() -> None:
    result = validate.validate_migration_integrity(FIXTURES / "beekeeper-corrected")

    assert result.violations == [], "\n".join(str(item) for item in result.violations)
    assert [item.source for item in result.inventory] == sorted(
        item.source for item in result.inventory
    )
    assert len({item.source for item in result.inventory}) == len(result.inventory)
    assert {item.disposition for item in result.inventory} == {
        "migrate",
        "synthesize",
        "remove_after_verify",
        "preserve_local_policy",
    }


def test_scope_aware_scan_allows_migration_evidence_but_not_live_instructions() -> None:
    partial = FIXTURES / "beekeeper-partial"
    research = partial / ".agents" / "bundles" / "research" / "migration.md"
    operational = partial / "AGENTS.md"

    assert validate.validate_migration_path_references(research, partial) == []
    assert validate.validate_migration_path_references(operational, partial) == []
    violations = validate.validate_migration_path_references(
        operational, partial, allow_negative_fixture=False
    )
    assert any("operational content references legacy path" in item.message for item in violations)


def test_migration_fixture_scope_passes_as_a_regression_suite() -> None:
    completed = subprocess.run(
        [sys.executable, "tools/validate.py", "--scope", "migration-fixtures"],
        cwd=REPO_ROOT,
        capture_output=True,
        check=False,
        text=True,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "beekeeper-partial" in completed.stdout
    assert "beekeeper-corrected" in completed.stdout

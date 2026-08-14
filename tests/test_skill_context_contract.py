from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
AUDIT_PATH = REPO_ROOT / "tools" / "audit-skill-contracts.py"
REVIEWER_AUTHORITIES = {
    "architecture-critic": ("persona.md", "checklist.md"),
    "challenge": ("challenge-strategy.md",),
    "consensus": ("consensus-strategy.md", "stance-rotation.md"),
    "deepthink": ("reasoning-strategy.md", "confidence-tracking.md"),
    "devils-advocate": ("persona.md", "checklist.md"),
    "docgen": ("docgen-strategy.md", "component-template.md"),
    "performance-analyst": ("persona.md", "checklist.md"),
    "perspectives": ("critical-thinking.md", "stances.md"),
    "security-auditor": ("persona.md", "checklist.md"),
    "tracer": ("tracing-strategy.md", "trace-modes.md"),
}


def _copy_audit_tree(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    for directory in ("agents", "contracts", "skills"):
        shutil.copytree(REPO_ROOT / directory, root / directory)
    workflow = root / "templates" / "agent" / "workflow.md"
    workflow.parent.mkdir(parents=True)
    shutil.copy2(REPO_ROOT / "templates" / "agent" / "workflow.md", workflow)
    return root


def _run_audit(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(AUDIT_PATH), "--repo-root", str(root)],
        check=False,
        capture_output=True,
        text=True,
    )


def _append_lines(path: Path, target_lines: int) -> None:
    lines = path.read_text(encoding="utf-8").splitlines()
    lines.extend("budget filler" for _ in range(target_lines - len(lines)))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _substantive_lines(path: Path) -> set[str]:
    lines = set()
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = " ".join(raw_line.split())
        if len(line) >= 60 and not line.startswith(("#", "<", "```", "- [")):
            lines.add(line.casefold())
    return lines


def _reviewer_authority_violations(root: Path) -> list[str]:
    violations = []
    for skill_name, reference_names in REVIEWER_AUTHORITIES.items():
        skill = root / "skills" / skill_name / "SKILL.md"
        skill_text = skill.read_text(encoding="utf-8")
        skill_lines = _substantive_lines(skill)
        for reference_name in reference_names:
            relative_reference = f"references/{reference_name}"
            reference = skill.parent / relative_reference
            if f"({relative_reference})" not in skill_text:
                violations.append(
                    f"{skill.relative_to(root)} does not directly link {relative_reference}"
                )
            duplicates = sorted(skill_lines & _substantive_lines(reference))
            for duplicate in duplicates:
                violations.append(
                    f"{skill.relative_to(root)} duplicates {reference.relative_to(root)}: "
                    f"{duplicate}"
                )
    return violations


def test_repository_skill_context_contract_passes() -> None:
    result = _run_audit(REPO_ROOT)

    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout == "Skill context contracts pass.\n"


def test_reviewer_authority_map_is_direct_and_singular() -> None:
    assert _reviewer_authority_violations(REPO_ROOT) == []


def test_reviewer_authority_check_rejects_duplicate_detail(tmp_path: Path) -> None:
    root = _copy_audit_tree(tmp_path)
    skill = root / "skills" / "architecture-critic" / "SKILL.md"
    persona = skill.parent / "references" / "persona.md"
    duplicated = next(
        line
        for line in persona.read_text(encoding="utf-8").splitlines()
        if len(line.strip()) >= 60 and not line.startswith("#")
    )
    skill.write_text(
        skill.read_text(encoding="utf-8") + f"\n{duplicated}\n",
        encoding="utf-8",
    )

    violations = _reviewer_authority_violations(root)

    assert any("duplicates" in violation for violation in violations)


def test_audit_rejects_over_budget_skill(tmp_path: Path) -> None:
    root = _copy_audit_tree(tmp_path)
    _append_lines(root / "skills" / "flow" / "SKILL.md", 510)

    result = _run_audit(root)

    assert result.returncode == 1
    assert "SKILL body must be below 500 lines" in result.stdout


def test_audit_rejects_over_budget_agent(tmp_path: Path) -> None:
    root = _copy_audit_tree(tmp_path)
    _append_lines(root / "agents" / "code-reviewer.md", 125)

    result = _run_audit(root)

    assert result.returncode == 1
    assert "canonical agent prompt must be below 120 lines" in result.stdout


def test_audit_rejects_over_budget_consumer_workflow(tmp_path: Path) -> None:
    root = _copy_audit_tree(tmp_path)
    _append_lines(root / "templates" / "agent" / "workflow.md", 251)

    result = _run_audit(root)

    assert result.returncode == 1
    assert "consumer workflow must be at most 250 lines" in result.stdout


def test_audit_rejects_long_reference_without_contents(tmp_path: Path) -> None:
    root = _copy_audit_tree(tmp_path)
    reference = root / "skills" / "flow" / "references" / "setup.md"
    reference.write_text(
        reference.read_text(encoding="utf-8").replace("## Contents\n", "", 1),
        encoding="utf-8",
    )

    result = _run_audit(root)

    assert result.returncode == 1
    assert "reference over 100 lines requires a Contents section" in result.stdout


def test_audit_rejects_indirect_only_reference(tmp_path: Path) -> None:
    root = _copy_audit_tree(tmp_path)
    skill = root / "skills" / "apilookup" / "SKILL.md"
    skill.write_text(
        skill.read_text(encoding="utf-8")
        .replace(
            "See `references/lookup-strategy.md` for the full decision tree. Key principles:\n",
            "Use the full decision tree when escalation is required. Key principles:\n",
        )
        .replace(
            "- **[Lookup Strategy](references/lookup-strategy.md)** — Detailed three-tier resolution instructions\n",
            "",
        ),
        encoding="utf-8",
    )
    bridge = root / "skills" / "apilookup" / "references" / "registry-schema.md"
    bridge.write_text(
        bridge.read_text(encoding="utf-8")
        + "\nSee [Lookup Strategy](lookup-strategy.md).\n",
        encoding="utf-8",
    )

    result = _run_audit(root)

    assert result.returncode == 1
    assert (
        "reference must be directly linked from a triggering SKILL.md" in result.stdout
    )


def test_audit_rejects_duplicate_lifecycle_owner(tmp_path: Path) -> None:
    root = _copy_audit_tree(tmp_path)
    planning = root / "skills" / "flow-planning" / "SKILL.md"
    planning.write_text(
        planning.read_text(encoding="utf-8").replace(
            "operations=prd,plan,refine,revise,research,task",
            "operations=setup,prd,plan,refine,revise,research,task",
        ),
        encoding="utf-8",
    )

    result = _run_audit(root)

    assert result.returncode == 1
    assert "operation 'setup' has duplicate lifecycle owners" in result.stdout


def test_audit_rejects_missing_shared_contract(tmp_path: Path) -> None:
    root = _copy_audit_tree(tmp_path)
    contract = root / "contracts" / "flow.yaml"
    contract.write_text(
        contract.read_text(encoding="utf-8").replace(
            "  - {id: quality-review-v1, source: skills/flow/references/review.md, runtime_dependency: agent_file_tools_only}\n",
            "",
        ),
        encoding="utf-8",
    )

    result = _run_audit(root)

    assert result.returncode == 1
    assert "required shared contract 'quality-review-v1' is missing" in result.stdout

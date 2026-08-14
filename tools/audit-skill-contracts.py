#!/usr/bin/env python3
"""Audit progressive-disclosure and Flow lifecycle ownership contracts."""

from __future__ import annotations

import argparse
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

import yaml


SKILL_BODY_LIMIT = 500
REFERENCE_CONTENTS_THRESHOLD = 100
AGENT_PROMPT_LIMIT = 120
CONSUMER_WORKFLOW_LIMIT = 250
EXPECTED_LIFECYCLE_OWNERSHIP = {
    "flow": (),
    "flow-setup": ("setup",),
    "flow-planning": ("prd", "plan", "refine", "revise", "research", "task"),
    "flow-execution": ("implement",),
    "flow-sync-status": ("sync", "status", "refresh"),
    "flow-completion": (
        "review",
        "finish",
        "archive",
        "revert",
        "docs",
        "cleanup",
        "validate",
    ),
}
REQUIRED_SHARED_CONTRACTS = {
    "flow-state-v1",
    "quality-review-v1",
    "structured-choice-v1",
    "worksheet-execution-v1",
}
FORBIDDEN_LIVE_TERMS = (
    ".agents/workflow.md",
    ".agents/tech-stack.md",
    ".agents/knowledge-base.md",
    ".agents/archive/",
    "implement_state.json",
)
LINK_PATTERN = re.compile(r"\[[^]]+\]\(([^)]+)\)")
LIFECYCLE_PATTERN = re.compile(
    r"<!-- lifecycle-ownership: owner=([a-z-]+); operations=([a-z,-]*) -->"
)


def _line_count(path: Path) -> int:
    return len(path.read_text(encoding="utf-8").splitlines())


def _body_line_count(path: Path) -> int:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != "---":
        return len(lines)
    try:
        end = lines.index("---", 1)
    except ValueError:
        return len(lines)
    return len(lines[end + 1 :])


def _relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _load_contract(path: Path) -> tuple[dict[str, Any], list[str]]:
    try:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        return {}, [f"contracts/flow.yaml: cannot load contract: {exc}"]
    if not isinstance(loaded, dict):
        return {}, ["contracts/flow.yaml: contract must be a mapping"]
    return loaded, []


def _audit_budgets(root: Path) -> list[str]:
    violations: list[str] = []
    for path in sorted((root / "skills").glob("*/SKILL.md")):
        count = _body_line_count(path)
        if count >= SKILL_BODY_LIMIT:
            violations.append(
                f"{_relative(path, root)}: SKILL body must be below "
                f"{SKILL_BODY_LIMIT} lines (found {count})"
            )
    for path in sorted((root / "agents").glob("*.md")):
        count = _body_line_count(path)
        if count >= AGENT_PROMPT_LIMIT:
            violations.append(
                f"{_relative(path, root)}: canonical agent prompt must be below "
                f"{AGENT_PROMPT_LIMIT} lines (found {count})"
            )
    workflow = root / "templates" / "agent" / "workflow.md"
    if workflow.is_file() and _line_count(workflow) > CONSUMER_WORKFLOW_LIMIT:
        violations.append(
            f"{_relative(workflow, root)}: consumer workflow must be at most "
            f"{CONSUMER_WORKFLOW_LIMIT} lines (found {_line_count(workflow)})"
        )
    return violations


def _direct_reference_links(root: Path) -> set[Path]:
    direct: set[Path] = set()
    for skill in sorted((root / "skills").glob("*/SKILL.md")):
        for raw_target in LINK_PATTERN.findall(skill.read_text(encoding="utf-8")):
            target = raw_target.split("#", 1)[0].strip("<>")
            if not target or "://" in target:
                continue
            resolved = (skill.parent / target).resolve()
            if resolved.is_file():
                direct.add(resolved)
    return direct


def _audit_references(root: Path) -> list[str]:
    violations: list[str] = []
    direct = _direct_reference_links(root)
    references = sorted((root / "skills").glob("*/references/**/*.md"))
    for path in references:
        text = path.read_text(encoding="utf-8")
        count = len(text.splitlines())
        if count > REFERENCE_CONTENTS_THRESHOLD and not re.search(
            r"^## Contents\s*$", text, re.MULTILINE
        ):
            violations.append(
                f"{_relative(path, root)}: reference over "
                f"{REFERENCE_CONTENTS_THRESHOLD} lines requires a Contents section"
            )
        if path.resolve() not in direct:
            violations.append(
                f"{_relative(path, root)}: reference must be directly linked from a "
                "triggering SKILL.md"
            )
    return violations


def _declared_lifecycle_ownership(
    root: Path,
) -> tuple[dict[str, tuple[str, ...]], list[str]]:
    declared: dict[str, tuple[str, ...]] = {}
    violations: list[str] = []
    for skill_name in EXPECTED_LIFECYCLE_OWNERSHIP:
        path = root / "skills" / skill_name / "SKILL.md"
        text = path.read_text(encoding="utf-8") if path.is_file() else ""
        match = LIFECYCLE_PATTERN.search(text)
        if match is None:
            violations.append(
                f"skills/{skill_name}/SKILL.md: missing lifecycle ownership declaration"
            )
            continue
        owner, raw_operations = match.groups()
        if owner != skill_name:
            violations.append(
                f"skills/{skill_name}/SKILL.md: lifecycle declaration owner is {owner!r}"
            )
        operations = tuple(filter(None, raw_operations.split(",")))
        declared[skill_name] = operations
    return declared, violations


def _audit_lifecycle(root: Path, contract: dict[str, Any]) -> list[str]:
    violations: list[str] = []
    declared, declaration_violations = _declared_lifecycle_ownership(root)
    violations.extend(declaration_violations)
    operation_owners: dict[str, list[str]] = defaultdict(list)
    for owner, operations in declared.items():
        for operation in operations:
            operation_owners[operation].append(owner)
    for operation, owners in sorted(operation_owners.items()):
        if len(owners) > 1:
            violations.append(
                f"operation {operation!r} has duplicate lifecycle owners: "
                + ", ".join(owners)
            )
    for owner, expected in EXPECTED_LIFECYCLE_OWNERSHIP.items():
        if declared.get(owner) != expected:
            violations.append(
                f"skills/{owner}/SKILL.md: operations must be {list(expected)!r}"
            )

    commands = contract.get("commands")
    if not isinstance(commands, list):
        return violations + ["contracts/flow.yaml: commands must be a list"]
    command_owners: dict[str, str] = {}
    for command in commands:
        if not isinstance(command, dict):
            continue
        command_id = command.get("id")
        owner = command.get("lifecycle_owner")
        if isinstance(command_id, str) and command_id.startswith("flow/"):
            command_owners[command_id.removeprefix("flow/")] = str(owner)
    expected_command_owners = {
        operation: owner
        for owner, operations in EXPECTED_LIFECYCLE_OWNERSHIP.items()
        for operation in operations
    }
    if command_owners != expected_command_owners:
        violations.append(
            "contracts/flow.yaml: command lifecycle owners must match the canonical map"
        )
    return violations


def _audit_shared_contracts(root: Path, contract: dict[str, Any]) -> list[str]:
    violations: list[str] = []
    records = contract.get("shared_contracts")
    by_id = (
        {
            record.get("id"): record
            for record in records
            if isinstance(record, dict) and isinstance(record.get("id"), str)
        }
        if isinstance(records, list)
        else {}
    )
    for contract_id in sorted(REQUIRED_SHARED_CONTRACTS):
        if contract_id not in by_id:
            violations.append(
                f"contracts/flow.yaml: required shared contract {contract_id!r} is missing"
            )
            continue
        source = by_id[contract_id].get("source")
        if not isinstance(source, str) or not (root / source).is_file():
            violations.append(
                f"contracts/flow.yaml: shared contract {contract_id!r} has no live source"
            )
    commands = contract.get("commands")
    if isinstance(commands, list):
        for command in commands:
            if not isinstance(command, dict):
                continue
            for contract_id in command.get("shared_contracts", []):
                if contract_id not in by_id:
                    violations.append(
                        f"contracts/flow.yaml: command {command.get('id')!r} references "
                        f"undefined shared contract {contract_id!r}"
                    )
    return violations


def _audit_stale_live_terms(root: Path) -> list[str]:
    violations: list[str] = []
    paths = list((root / "skills").glob("flow*/SKILL.md"))
    paths.extend((root / "skills" / "flow" / "references").glob("*.md"))
    legacy_prd = re.compile(r"\.agents/(?:specs|bundles/specs)/[^\s`)]+/prd\.md")
    for path in sorted(paths):
        text = path.read_text(encoding="utf-8")
        for term in FORBIDDEN_LIVE_TERMS:
            if term in text:
                violations.append(
                    f"{_relative(path, root)}: stale live term {term!r} is forbidden"
                )
        if legacy_prd.search(text):
            violations.append(
                f"{_relative(path, root)}: bare prd.md flow artifact is forbidden"
            )
    return violations


def audit(root: Path) -> list[str]:
    contract, violations = _load_contract(root / "contracts" / "flow.yaml")
    violations.extend(_audit_budgets(root))
    violations.extend(_audit_references(root))
    violations.extend(_audit_lifecycle(root, contract))
    violations.extend(_audit_shared_contracts(root, contract))
    violations.extend(_audit_stale_live_terms(root))
    return violations


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--repo-root", type=Path, default=Path(__file__).resolve().parents[1]
    )
    args = parser.parse_args()
    violations = audit(args.repo_root.resolve())
    if violations:
        print("Skill context contract violations:")
        for violation in violations:
            print(f"  - {violation}")
        return 1
    print("Skill context contracts pass.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

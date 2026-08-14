"""Contract and test-only traces for the mandatory quality gate."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any

import pytest
import yaml

from tools.flow_contract import load_contract


REPO_ROOT = Path(__file__).resolve().parents[1]
REVIEW_PATH = REPO_ROOT / "skills" / "flow" / "references" / "review.md"
CONTRACT_PATH = REPO_ROOT / "contracts" / "flow.yaml"
INSTALLED_WORKFLOWS = tuple((REPO_ROOT / "agents").rglob("*.md")) + tuple(
    (REPO_ROOT / "skills").rglob("*.md")
)


def _marked_yaml(path: Path, name: str) -> dict[str, Any]:
    content = path.read_text(encoding="utf-8")
    match = re.search(
        rf"<!-- {re.escape(name)}: start -->\s*```yaml\s*(.*?)\s*```\s*"
        rf"<!-- {re.escape(name)}: end -->",
        content,
        re.DOTALL,
    )
    assert match is not None, f"missing {name} block in {path}"
    parsed = yaml.safe_load(match.group(1))
    assert isinstance(parsed, dict)
    return parsed


@dataclass(frozen=True)
class Finding:
    finding_id: str
    severity: str


@dataclass(frozen=True)
class QualityReport:
    reviewer: str
    base_commit: str
    head_commit: str
    debloat_source: str
    findings: tuple[Finding, ...]


@dataclass(frozen=True)
class GateResult:
    outcome: str
    next_steps: tuple[str, ...]


def _select_debloat_source(
    contract: dict[str, Any], *, consumer: bool, packaged: bool
) -> str:
    available = {
        ".agents/skills/debloat/SKILL.md": consumer,
        "skills/debloat/SKILL.md": packaged,
    }
    for source in contract["skill_resolution"]["order"]:
        if source == "inline_fallback" or available[source]:
            return contract["skill_resolution"]["report_values"][source]
    raise AssertionError("quality review must always resolve a debloat policy")


def _evaluate_finish(
    contract: dict[str, Any],
    *,
    base_commit: str,
    head_commit: str,
    verification_range: tuple[str, str],
    code_review_range: tuple[str, str],
    report: QualityReport | None,
    waivers: tuple[dict[str, str], ...] = (),
) -> GateResult:
    exact_range = (base_commit, head_commit)
    if report is None:
        return GateResult("blocked", ("dispatch_quality_review",))
    if verification_range != exact_range or code_review_range != exact_range:
        return GateResult("blocked", ("rerun_verification", "rerun_code_review"))
    if (report.base_commit, report.head_commit) != exact_range:
        return GateResult("blocked", ("dispatch_fresh_quality_review",))

    required = set(contract["waiver"]["required"])
    valid_waivers = {
        waiver["finding_id"]
        for waiver in waivers
        if set(waiver) == required
        and (waiver["base_commit"], waiver["head_commit"]) == exact_range
    }
    blockers = tuple(
        finding.finding_id
        for finding in report.findings
        if finding.severity in contract["blocking_severities"]
        and finding.finding_id not in valid_waivers
    )
    if blockers:
        return GateResult(
            "blocked",
            (
                "revise_remediation_task",
                "execute_remediation",
                "rerun_verification",
                "rerun_code_review",
                "dispatch_fresh_quality_review",
            ),
        )
    return GateResult("ready", ("finish",))


def _evaluate_archive(
    contract: dict[str, Any],
    *,
    candidate_range: tuple[str, str],
    reviewed_manifest: bytes,
    current_manifest: bytes,
    report: QualityReport | None,
) -> GateResult:
    if reviewed_manifest != current_manifest:
        return GateResult("blocked", ("render_new_candidate", "review_fresh_range"))
    result = _evaluate_finish(
        contract,
        base_commit=candidate_range[0],
        head_commit=candidate_range[1],
        verification_range=candidate_range,
        code_review_range=candidate_range,
        report=report,
    )
    if result.outcome == "ready":
        return GateResult("ready", ("archive",))
    return result


@pytest.fixture(scope="module")
def quality_contract() -> dict[str, Any]:
    contract = _marked_yaml(REVIEW_PATH, "quality-review-contract")
    assert contract["contract"] == "quality-review-v1"
    return contract


@pytest.mark.parametrize(
    ("consumer", "packaged", "expected"),
    [
        (True, True, "consumer_skill"),
        (False, True, "packaged_skill"),
        (False, False, "inline_fallback"),
    ],
)
def test_debloat_skill_resolution_is_ordered_and_total(
    quality_contract: dict[str, Any],
    consumer: bool,
    packaged: bool,
    expected: str,
) -> None:
    assert (
        _select_debloat_source(
            quality_contract, consumer=consumer, packaged=packaged
        )
        == expected
    )


def test_contract_and_agent_make_quality_review_read_only_and_mandatory(
    quality_contract: dict[str, Any],
) -> None:
    flow = load_contract(CONTRACT_PATH)
    reviewer = flow.agents["quality-reviewer"]

    assert quality_contract["mandatory_dispatch"] is True
    assert quality_contract["dispatch_after"] == "code_review"
    assert quality_contract["report"]["exact_keys"] == [
        "reviewer",
        "base_commit",
        "head_commit",
        "debloat_source",
        "findings",
    ]
    assert reviewer.invariant_ids == (
        "quality-review-mandatory-v1",
        "quality-review-read-only-v1",
        "quality-findings-evidence-v1",
        "quality-behavior-preservation-v1",
        "quality-test-gate-debloat-v1",
        "quality-review-range-v1",
        "quality-no-opportunism-v1",
        "git-no-tags-v1",
    )
    assert all(
        "file_write" not in requirements
        for requirements in reviewer.tool_requirements.values()
    )
    assert reviewer.generation.outputs["opencode"].edit_permission == "deny"
    assert flow.commands["flow/finish"].completion_gates == (
        "verification",
        "code_review",
        "quality_review",
        "finish",
    )
    assert flow.commands["flow/archive"].completion_gates == (
        "archive_candidate",
        "verification",
        "code_review",
        "quality_review",
        "archive",
    )


def test_finish_gate_requires_dispatch_and_exact_fresh_range(
    quality_contract: dict[str, Any],
) -> None:
    base, head = "a" * 40, "b" * 40
    no_review = _evaluate_finish(
        quality_contract,
        base_commit=base,
        head_commit=head,
        verification_range=(base, head),
        code_review_range=(base, head),
        report=None,
    )
    stale = _evaluate_finish(
        quality_contract,
        base_commit=base,
        head_commit=head,
        verification_range=(base, head),
        code_review_range=(base, head),
        report=QualityReport(
            "quality-reviewer", base, "c" * 40, "packaged_skill", ()
        ),
    )

    assert no_review == GateResult("blocked", ("dispatch_quality_review",))
    assert stale == GateResult("blocked", ("dispatch_fresh_quality_review",))
    assert quality_contract["one_commit_range"]["base_commit"] == "parent_of_head"


def test_blocking_finding_routes_remediation_and_requires_all_fresh_gates(
    quality_contract: dict[str, Any],
) -> None:
    base, old_head, new_head = "a" * 40, "b" * 40, "c" * 40
    finding = Finding("Q-001", "Important")
    initial = QualityReport(
        "quality-reviewer", base, old_head, "consumer_skill", (finding,)
    )
    blocked = _evaluate_finish(
        quality_contract,
        base_commit=base,
        head_commit=old_head,
        verification_range=(base, old_head),
        code_review_range=(base, old_head),
        report=initial,
    )
    stale_after_remediation = _evaluate_finish(
        quality_contract,
        base_commit=base,
        head_commit=new_head,
        verification_range=(base, new_head),
        code_review_range=(base, new_head),
        report=initial,
    )
    ready = _evaluate_finish(
        quality_contract,
        base_commit=base,
        head_commit=new_head,
        verification_range=(base, new_head),
        code_review_range=(base, new_head),
        report=QualityReport(
            "quality-reviewer", base, new_head, "consumer_skill", ()
        ),
    )

    assert blocked.next_steps == (
        "revise_remediation_task",
        "execute_remediation",
        "rerun_verification",
        "rerun_code_review",
        "dispatch_fresh_quality_review",
    )
    assert stale_after_remediation == GateResult(
        "blocked", ("dispatch_fresh_quality_review",)
    )
    assert ready == GateResult("ready", ("finish",))


def test_waiver_is_finding_specific_fresh_and_never_replaces_dispatch(
    quality_contract: dict[str, Any],
) -> None:
    base, head = "a" * 40, "b" * 40
    waiver = {
        "finding_id": "Q-001",
        "rationale": "The duplicate is required by the public wire contract.",
        "approval_text": "Waive Q-001 for this exact range.",
        "approved_at": "2026-08-14T20:00:00Z",
        "compensating_evidence": "Both wire variants pass interoperability tests.",
        "base_commit": base,
        "head_commit": head,
    }
    report = QualityReport(
        "quality-reviewer",
        base,
        head,
        "inline_fallback",
        (Finding("Q-001", "Important"), Finding("Q-002", "Important")),
    )

    one_unwaived = _evaluate_finish(
        quality_contract,
        base_commit=base,
        head_commit=head,
        verification_range=(base, head),
        code_review_range=(base, head),
        report=report,
        waivers=(waiver,),
    )
    waived = _evaluate_finish(
        quality_contract,
        base_commit=base,
        head_commit=head,
        verification_range=(base, head),
        code_review_range=(base, head),
        report=QualityReport(
            "quality-reviewer",
            base,
            head,
            "inline_fallback",
            (Finding("Q-001", "Important"),),
        ),
        waivers=(waiver,),
    )
    attempted_no_review_waiver = _evaluate_finish(
        quality_contract,
        base_commit=base,
        head_commit=head,
        verification_range=(base, head),
        code_review_range=(base, head),
        report=None,
        waivers=(waiver,),
    )

    assert one_unwaived.outcome == "blocked"
    assert waived == GateResult("ready", ("finish",))
    assert attempted_no_review_waiver == GateResult(
        "blocked", ("dispatch_quality_review",)
    )


def test_archive_candidate_manifest_and_report_are_byte_and_range_bound(
    quality_contract: dict[str, Any],
) -> None:
    candidate = ("a" * 40, "b" * 40)
    report = QualityReport(
        "quality-reviewer", *candidate, "packaged_skill", ()
    )

    assert _evaluate_archive(
        quality_contract,
        candidate_range=candidate,
        reviewed_manifest=b"knowledge\nlog\ndelete spec\n",
        current_manifest=b"knowledge changed\nlog\ndelete spec\n",
        report=report,
    ) == GateResult("blocked", ("render_new_candidate", "review_fresh_range"))
    assert _evaluate_archive(
        quality_contract,
        candidate_range=candidate,
        reviewed_manifest=b"knowledge\nlog\ndelete spec\n",
        current_manifest=b"knowledge\nlog\ndelete spec\n",
        report=report,
    ) == GateResult("ready", ("archive",))


def test_installed_workflows_have_no_quality_evaluator_runtime() -> None:
    forbidden = ("test_quality_gate", "_evaluate_finish", "_evaluate_archive")
    violations = {
        str(path.relative_to(REPO_ROOT)): token
        for path in INSTALLED_WORKFLOWS
        for token in forbidden
        if token in path.read_text(encoding="utf-8")
    }
    assert not violations
    assert not (REPO_ROOT / "tools" / "quality_gate.py").exists()

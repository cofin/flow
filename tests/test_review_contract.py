from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_review_requires_ordered_correctness_and_quality_on_identical_range() -> None:
    review = (ROOT / "skills/flow/references/review.md").read_text()
    code_reviewer = (ROOT / "agents/code-reviewer.md").read_text()
    quality_reviewer = (ROOT / "agents/quality-reviewer.md").read_text()

    assert "dispatch_after: code_review" in review
    assert "same exact `base_commit..head_commit`" in review
    assert "correctness" in code_reviewer.lower()
    assert "exact" in quality_reviewer.lower()
    assert "read-only" in quality_reviewer.lower()


def test_quality_report_schema_and_severity_gate_are_complete() -> None:
    review = (ROOT / "skills/flow/references/review.md").read_text()
    reviewer = (ROOT / "agents/quality-reviewer.md").read_text()
    required_fields = {
        "finding_id",
        "severity",
        "file",
        "symbol",
        "evidence",
        "preserved_invariant",
        "remediation_target",
        "reverification",
    }

    assert "blocking_severities: [Critical, Important]" in review
    assert "name: QualityReport" in review
    for field in required_fields:
        assert field in review
        assert field in reviewer
    assert "Critical" in reviewer and "Important" in reviewer and "Minor" in reviewer

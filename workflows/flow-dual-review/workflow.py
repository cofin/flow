"""Orchestrate parallel zero-context code and quality reviews for a Flow Git range."""

review_schema = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": ["PASS", "NEEDS_WORK"]},
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "severity": {"type": "string"},
                    "file": {"type": "string"},
                    "summary": {"type": "string"},
                },
                "required": ["severity", "file", "summary"],
            },
        },
    },
    "required": ["verdict", "findings"],
}

git_range = str(args.get("git_range", "main..HEAD"))
spec_path = str(args.get("spec_path", ""))
spec_clause = f" against {spec_path}" if spec_path else ""

phase("Zero-Context Dual Review")
log(f"Dispatching @code-reviewer and @quality-reviewer on {git_range}{spec_clause}")

reviewers = [
    (
        "code-reviewer",
        "Correctness & Spec Review",
        f"Review exact Git range `{git_range}`{spec_clause} for correctness, spec conformance, and SUT test integrity.",
    ),
    (
        "quality-reviewer",
        "Quality & Debloat Review",
        f"Review exact Git range `{git_range}`{spec_clause} for dead code, prose sediment, OKF hygiene, and test strength.",
    ),
]

reports = await parallel(
    reviewers,
    lambda item: agent(
        item[2],
        schema=review_schema,
        role=item[1],
        type_name=item[0],
        workspace="inherit",
        model="inherit",
    ),
)

phase("Adjudication Summary")
combined = {
    "git_range": git_range,
    "spec_path": spec_path,
    "code_review": reports[0],
    "quality_review": reports[1],
}
log(f"Code review verdict: {reports[0]['verdict']} ({len(reports[0]['findings'])} finding(s))")
log(f"Quality review verdict: {reports[1]['verdict']} ({len(reports[1]['findings'])} finding(s))")
print(combined)

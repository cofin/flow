"""End-to-end acceptance trace for the Flow continuity contract.

This composes the focused migration, state, harness, hook, and quality contracts
without introducing a consumer runtime helper.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
from types import ModuleType

from tools.flow_contract import load_contract, parse_request, select_transport


REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = REPO_ROOT / "tests" / "fixtures" / "migrations"


def _load_module(name: str, relative: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, REPO_ROOT / relative)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _choice(choice_id: str) -> dict[str, str]:
    return {
        "id": choice_id,
        "label": choice_id.title(),
        "description": f"Select {choice_id} for this scenario.",
    }


def _request(mode: str, choices: tuple[str, ...]) -> dict[str, object]:
    request: dict[str, object] = {
        "contract_id": "structured-choice-v1",
        "decision_id": "continuity_e2e",
        "selection_mode": mode,
        "question": "Choose the continuity scenario.",
        "disabled_choice_policy": "omit",
        "choices": [_choice(choice) for choice in choices],
        "recommended_choice_id": choices[0] if choices else None,
        "allow_custom": mode != "open",
        "min_selections": None,
        "max_selections": None,
        "free_form_reason": None,
        "input_guidance": None,
    }
    if mode == "multi_select":
        request.update(min_selections=1, max_selections=len(choices))
    if mode == "open":
        request.update(
            choices=[],
            recommended_choice_id=None,
            allow_custom=False,
            free_form_reason="revision_details",
            input_guidance="Describe the required revision.",
        )
    return request


def test_continuity_saga_rejects_injected_stale_quality_evidence() -> None:
    migration = _load_module("continuity_migration", "tests/test_migration_integrity.py")
    state = _load_module("continuity_state", "tests/test_state_operations.py")
    quality = _load_module("continuity_quality", "tests/test_quality_gate.py")

    partial = migration.validate.validate_migration_integrity(
        FIXTURES / "beekeeper-partial"
    )
    corrected = migration.validate.validate_migration_integrity(
        FIXTURES / "beekeeper-corrected"
    )
    assert partial.violations
    assert corrected.violations == []
    assert {item.disposition for item in corrected.inventory} == {
        "migrate",
        "synthesize",
        "remove_after_verify",
        "preserve_local_policy",
    }

    state_contract = state._contract(state.SKILL_PATH)
    assert set(state_contract["operations"]) == state.OPERATIONS
    for operation in (
        "create",
        "status",
        "activate",
        "checkpoint",
        "claim",
        "note",
        "discover",
        "release",
        "block",
        "unblock",
        "close",
        "skip",
        "reopen",
        "revise",
        "reconcile",
        "complete",
        "archive",
        "recover",
    ):
        assert operation in state_contract["operations"]

    contract = load_contract(REPO_ROOT / "contracts" / "flow.yaml")
    for mode, choices in (
        ("binary", ("approve", "revise")),
        ("single_select", ("approve", "revise", "refine")),
        ("multi_select", ("source", "tests", "docs", "ci")),
        ("open", ()),
    ):
        request = parse_request(contract, _request(mode, choices))
        for host, capability in contract.harnesses.items():
            transport = select_transport(
                contract,
                host,
                request,
                tool_available=True,
                tool_allowed=True,
            )
            if transport.transport == "native":
                assert transport.fallback_reasons == ()
                assert transport.tool_name == capability.verified_tool

    codex_multi = select_transport(
        contract,
        "codex_cli",
        parse_request(contract, _request("multi_select", ("a", "b", "c", "d"))),
        tool_available=True,
        tool_allowed=True,
    )
    assert codex_multi.fallback_reasons == (
        "mode_unsupported",
        "choice_count_unsupported",
        "bounds_unsupported",
    )

    hooks = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted((REPO_ROOT / "hooks").glob("hooks-*.json"))
    ]
    assert hooks
    for entrypoint in (REPO_ROOT / "hooks").glob("session-start.*"):
        assert "child_process" not in entrypoint.read_text(encoding="utf-8")

    quality_contract = quality._marked_yaml(
        quality.REVIEW_PATH, "quality-review-contract"
    )
    base, stale_head, current_head = "a" * 40, "b" * 40, "c" * 40
    injected_stale = quality._evaluate_finish(
        quality_contract,
        base_commit=base,
        head_commit=current_head,
        verification_range=(base, current_head),
        code_review_range=(base, current_head),
        report=quality.QualityReport(
            "quality-reviewer", base, stale_head, "packaged_skill", ()
        ),
    )
    assert injected_stale == quality.GateResult(
        "blocked", ("dispatch_fresh_quality_review",)
    )

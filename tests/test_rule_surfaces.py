"""Semantic and generation tests for cross-harness Flow rule adapters."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys

import pytest
import yaml

from tools.flow_contract import parse_request, select_transport

REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = REPO_ROOT / "contracts" / "flow.yaml"
CORE_PATH = REPO_ROOT / "rules" / "flow-core.md"
GENERATED_PATTERN = re.compile(r"generated-sha256: ([0-9a-f]{64})")
METADATA_PATTERN = re.compile(r"<!-- flow-rule-adapter: (\{.*\}) -->")


def _generator():
    path = REPO_ROOT / "tools" / "sync-rule-surfaces.py"
    spec = importlib.util.spec_from_file_location("sync_rule_surfaces", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _markdown_record(content: str) -> dict[str, object]:
    match = METADATA_PATTERN.search(content)
    assert match is not None
    return json.loads(match.group(1))


def _javascript_record(content: str) -> dict[str, object]:
    payload = content.split("// flow-rule-adapter:start\n", 1)[1].split(
        "\n// flow-rule-adapter:end", 1
    )[0]
    prefix = "const FLOW_RULE_ADAPTER = Object.freeze("
    assert payload.startswith(prefix) and payload.endswith(");")
    return json.loads(payload[len(prefix) : -2])


def _request(mode: str, count: int = 2) -> dict[str, object]:
    choices = [
        {
            "id": f"choice_{index}",
            "label": f"Choice {index}",
            "description": f"Use choice {index} for this repository decision.",
        }
        for index in range(count)
    ]
    return {
        "contract_id": "structured-choice-v1",
        "decision_id": f"rule-{mode}-{count}",
        "selection_mode": mode,
        "question": "Which repository-specific option should Flow use?",
        "disabled_choice_policy": "omit",
        "choices": choices,
        "recommended_choice_id": choices[0]["id"] if choices else None,
        "allow_custom": mode != "open",
        "min_selections": 1 if mode == "multi_select" else None,
        "max_selections": min(2, count) if mode == "multi_select" else None,
        "free_form_reason": "revision_details" if mode == "open" else None,
        "input_guidance": "Describe the exact revision." if mode == "open" else None,
    }


def test_core_rule_is_bounded_versioned_and_contract_linked() -> None:
    generator = _generator()
    core = generator.load_core_rule(CORE_PATH)
    assert core.rule_id == "flow-operational-v1"
    assert core.revision == 1
    assert len(core.body) <= 3_000
    assert core.shared_contracts == (
        "flow-state-v1",
        "structured-choice-v1",
        "worksheet-execution-v1",
        "quality-review-v1",
    )
    assert set(core.host_activation) == {
        "antigravity",
        "claude_code",
        "codex_cli",
        "opencode",
        "cursor",
        "vscode_copilot",
        "openclaw",
    }
    assert "Never create, move, force-update, or delete Git tags" in core.body
    assert "recursively nested knowledge" in core.body


def test_rule_generation_is_deterministic_and_removes_legacy_authority(
    tmp_path: Path,
) -> None:
    generator = _generator()
    expected = generator.render_surfaces(CONTRACT_PATH, CORE_PATH, tmp_path)
    assert set(expected) == {
        ".cursor/rules/flow.mdc",
        ".github/copilot-instructions.md",
        ".opencode/plugins/flow.js",
        "rules/flow-antigravity.md",
        "templates/agent/flow-instructions.md",
    }
    legacy = tmp_path / "rules" / "flow_antigravity.md"
    legacy.parent.mkdir(parents=True)
    legacy.write_text("retired\n", encoding="utf-8")
    first = generator.write_surfaces(CONTRACT_PATH, CORE_PATH, tmp_path)
    snapshot = {path: path.read_bytes() for path in first}
    second = generator.write_surfaces(CONTRACT_PATH, CORE_PATH, tmp_path)
    assert first == second
    assert snapshot == {path: path.read_bytes() for path in second}
    assert not legacy.exists()
    assert generator.check_surfaces(CONTRACT_PATH, CORE_PATH, tmp_path) == []


def test_generated_metadata_is_bound_to_source_revision_and_hashes() -> None:
    generator = _generator()
    expected = generator.render_surfaces(CONTRACT_PATH, CORE_PATH, REPO_ROOT)
    records = []
    for relative, content in expected.items():
        generated = GENERATED_PATTERN.search(content)
        assert generated is not None
        digest = generated.group(1)
        assert (
            digest == hashlib.sha256(content.replace(digest, "").encode()).hexdigest()
        )
        record = (
            _javascript_record(content)
            if relative.endswith(".js")
            else _markdown_record(content)
        )
        records.append(record)
    canonical_hashes = {record["canonical_sha256"] for record in records}
    contract_hashes = {record["contract_sha256"] for record in records}
    assert canonical_hashes == {hashlib.sha256(CORE_PATH.read_bytes()).hexdigest()}
    assert contract_hashes == {hashlib.sha256(CONTRACT_PATH.read_bytes()).hexdigest()}
    assert {record["rule_revision"] for record in records} == {1}
    assert all(record["git_tags"] == "forbidden" for record in records)
    assert all(record["automatic_push"] is False for record in records)


def test_rule_records_preserve_exact_host_capabilities_from_contract() -> None:
    generator = _generator()
    contract = generator.load_contract(CONTRACT_PATH)
    records = generator.semantic_records(CONTRACT_PATH, CORE_PATH)
    for harness_id, capability in contract.harnesses.items():
        record = records[harness_id]["question_capability"]
        assert record == {
            "transport": capability.transport,
            "tool": capability.verified_tool,
            "permission_check": capability.permission_check,
            "supported_modes": list(capability.supported_modes),
            "choice_min": capability.choice_min,
            "choice_max": capability.choice_max,
            "multi_select": capability.multi_select,
            "bounds_enforcement": capability.bounds_enforcement,
            "custom_answer_behavior": capability.custom_answer_behavior,
            "disabled_choice_policy": capability.disabled_choice_policy,
            "sequential_fallback": capability.sequential_fallback,
        }


def test_antigravity_native_and_fallback_transport_scenarios() -> None:
    generator = _generator()
    contract = generator.load_contract(CONTRACT_PATH)
    multi = parse_request(contract, _request("multi_select", 4))
    allowed = select_transport(
        contract, "antigravity", multi, tool_available=True, tool_allowed=True
    )
    absent = select_transport(
        contract, "antigravity", multi, tool_available=False, tool_allowed=True
    )
    denied = select_transport(
        contract, "antigravity", multi, tool_available=True, tool_allowed=False
    )
    assert (allowed.transport, allowed.tool_name, allowed.fallback_reasons) == (
        "native",
        "ask_question",
        (),
    )
    assert absent.fallback_reasons == ("tool_absent",)
    assert denied.fallback_reasons == ("tool_denied",)

    open_request = parse_request(contract, _request("open", 0))
    incompatible = select_transport(
        contract,
        "antigravity",
        open_request,
        tool_available=True,
        tool_allowed=True,
    )
    assert incompatible.transport == "sequential_text"
    assert incompatible.fallback_reasons == (
        "mode_unsupported",
        "choice_count_unsupported",
    )


def test_exact_host_limits_select_native_or_sequential_transport() -> None:
    generator = _generator()
    contract = generator.load_contract(CONTRACT_PATH)
    four_choice_single = parse_request(contract, _request("single_select", 4))
    codex_four = select_transport(
        contract,
        "codex_cli",
        four_choice_single,
        tool_available=True,
        tool_allowed=True,
    )
    assert codex_four.fallback_reasons == ("choice_count_unsupported",)

    multi = parse_request(contract, _request("multi_select", 4))
    codex_multi = select_transport(
        contract, "codex_cli", multi, tool_available=True, tool_allowed=True
    )
    assert codex_multi.fallback_reasons == (
        "mode_unsupported",
        "choice_count_unsupported",
        "bounds_unsupported",
    )
    for harness_id, tool in (
        ("claude_code", "AskUserQuestion"),
        ("opencode", "question"),
    ):
        native = select_transport(
            contract, harness_id, multi, tool_available=True, tool_allowed=True
        )
        assert (native.transport, native.tool_name) == ("native", tool)
    for harness_id in ("cursor", "vscode_copilot", "openclaw"):
        fallback = select_transport(
            contract, harness_id, multi, tool_available=False, tool_allowed=False
        )
        assert (fallback.tool_name, fallback.fallback_reasons) == (
            None,
            ("tool_absent",),
        )


def test_view_contract_preserves_selection_and_refinement_semantics() -> None:
    generator = _generator()
    records = generator.semantic_records(CONTRACT_PATH, CORE_PATH)
    interaction = records["antigravity"]["interaction_contract"]
    assert interaction["id"] == "structured-choice-v1"
    assert interaction["choice_keys"] == ["id", "label", "description"]
    assert interaction["recommended_choice"] == "first_with_suffix"
    assert interaction["recommended_suffix"] == " (Recommended)"
    assert interaction["custom_label"] == "Other"
    assert interaction["one_decision_at_a_time"] is True
    assert interaction["pre_quality"] == ["revise", "refine"]
    assert interaction["post_quality"] == ["approve", "revise", "refine"]

    surfaces = generator.render_surfaces(CONTRACT_PATH, CORE_PATH, REPO_ROOT)
    for relative in (
        "rules/flow-antigravity.md",
        ".cursor/rules/flow.mdc",
        ".github/copilot-instructions.md",
    ):
        text = surfaces[relative]
        assert "Other - enter a custom response" in text
        assert "(Recommended)" in text
        assert "Before quality" in text and "after quality" in text


def test_opencode_javascript_is_parseable_and_maps_only_verified_question(
    tmp_path: Path,
) -> None:
    generator = _generator()
    content = generator.render_surfaces(CONTRACT_PATH, CORE_PATH, REPO_ROOT)[
        ".opencode/plugins/flow.js"
    ]
    record = _javascript_record(content)
    assert record["host"] == "opencode"
    assert record["question_capability"]["tool"] == "question"
    assert "ask_question" not in content
    prompt = content.split("const FLOW_RULE_PROMPT = ", 1)[1].split(";\n", 1)[0]
    assert len(json.loads(prompt)) <= 512
    assert "journal-first direct-read continuity contract" in json.loads(prompt)
    path = tmp_path / "flow.js"
    path.write_text(content, encoding="utf-8")
    result = subprocess.run(
        ["node", "--check", path], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stderr


def test_check_reports_an_isolated_stale_surface_without_writing(
    tmp_path: Path,
) -> None:
    generator = _generator()
    paths = generator.write_surfaces(CONTRACT_PATH, CORE_PATH, tmp_path)
    victim = next(path for path in paths if path.name == "flow-antigravity.md")
    victim.write_text(victim.read_text(encoding="utf-8") + "isolated mutation\n")
    assert generator.check_surfaces(CONTRACT_PATH, CORE_PATH, tmp_path) == [
        "stale rule output: rules/flow-antigravity.md"
    ]
    assert victim.read_text(encoding="utf-8").endswith("isolated mutation\n")


@pytest.mark.parametrize(
    "mutation",
    [
        lambda data: data.update(revision=0),
        lambda data: data["host_activation"].pop("openclaw"),
        lambda data: data["shared_contracts"].remove("structured-choice-v1"),
    ],
)
def test_core_semantic_source_rejects_incomplete_metadata(
    tmp_path: Path, mutation
) -> None:
    generator = _generator()
    source = CORE_PATH.read_text(encoding="utf-8")
    _, frontmatter, body = source.split("---\n", 2)
    data = yaml.safe_load(frontmatter)
    mutation(data)
    core = tmp_path / "flow-core.md"
    core.write_text(
        "---\n" + yaml.safe_dump(data, sort_keys=False) + "---\n" + body,
        encoding="utf-8",
    )
    with pytest.raises(generator.ContractError):
        generator.semantic_records(CONTRACT_PATH, core)

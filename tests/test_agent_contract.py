"""Behavior tests for generated host-agent adapters."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tomllib

from tools.flow_contract import load_contract

REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = REPO_ROOT / "contracts" / "flow.yaml"


def _generator():
    path = REPO_ROOT / "tools" / "sync-agent-surfaces.py"
    spec = importlib.util.spec_from_file_location("sync_agent_surfaces", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _adapter_record(relative: str, content: str) -> dict[str, object]:
    if relative.endswith(".toml"):
        parsed = tomllib.loads(content)
        return json.loads(parsed["developer_instructions"])
    fenced = content.split("```json\n", 1)[1].split("\n```", 1)[0]
    return json.loads(fenced)


def test_agent_records_are_canonical_and_typed() -> None:
    contract = load_contract(CONTRACT_PATH)
    canonical_ids = {path.stem for path in (REPO_ROOT / "agents").glob("*.md")}
    assert set(contract.agents) == canonical_ids
    for agent in contract.agents.values():
        assert agent.canonical_source == f"agents/{agent.id}.md"
        assert agent.supported_host_adapters
        assert agent.generation.outputs
        assert agent.interaction_requirement in {"none", "structured_choice_optional"}
        if agent.interaction_requirement == "structured_choice_optional":
            assert "structured-choice-v1" in agent.invariant_ids

    quality = contract.agents["quality-reviewer"]
    assert quality.canonical_source == "agents/quality-reviewer.md"
    assert all(
        "file_write" not in requirements
        for requirements in quality.tool_requirements.values()
    )
    assert quality.generation.outputs["opencode"].edit_permission == "deny"


def test_agent_rendering_is_deterministic_and_adapter_only(tmp_path: Path) -> None:
    generator = _generator()
    expected = generator.render_surfaces(CONTRACT_PATH, tmp_path)
    assert expected
    assert all("generated-sha256:" in content for content in expected.values())
    records = [_adapter_record(path, content) for path, content in expected.items()]
    assert all(record["kind"] == "flow_agent_adapter" for record in records)
    assert all(
        record["canonical_source"] == f"agents/{record['canonical_id']}.md"
        for record in records
    )
    assert all(record["git_tags"] == "forbidden" for record in records)
    assert all(record["invariant_ids"] for record in records)
    antigravity = _adapter_record(
        "templates/antigravity/agents/plan-generator.md",
        expected["templates/antigravity/agents/plan-generator.md"],
    )
    assert antigravity["question_capability"] == {
        "bounds_enforcement": "agent_validated",
        "choice_max": 4,
        "choice_min": 2,
        "custom_answer_behavior": "native_custom_input",
        "disabled_choice_policy": "omit",
        "evidence": "Antigravity allowed-tool contract for ask_question",
        "multi_select": True,
        "mutual_exclusion": True,
        "permission_check": "declared_and_allowed",
        "sequential_fallback": True,
        "supported_modes": ["binary", "single_select", "multi_select"],
        "tool": "ask_question",
        "transport": "conditional_native",
    }
    paths = generator.write_surfaces(CONTRACT_PATH, tmp_path)
    assert {path.relative_to(tmp_path) for path in paths} == {
        Path(path) for path in expected
    }
    assert generator.check_surfaces(CONTRACT_PATH, tmp_path) == []


def test_agent_check_reports_missing_outputs_without_writing(tmp_path: Path) -> None:
    generator = _generator()
    expected = generator.render_surfaces(CONTRACT_PATH, tmp_path)
    missing = generator.check_surfaces(CONTRACT_PATH, tmp_path)
    assert missing == [f"missing agent output: {path}" for path in expected]
    assert list(tmp_path.rglob("*")) == []


def test_write_is_scoped_to_the_explicit_output_root(tmp_path: Path) -> None:
    generator = _generator()
    expected = generator.render_surfaces(CONTRACT_PATH, tmp_path)
    paths = generator.write_surfaces(CONTRACT_PATH, tmp_path)
    assert paths
    assert all(path.is_relative_to(tmp_path) for path in paths)
    assert {path.relative_to(tmp_path) for path in paths} == {
        Path(path) for path in expected
    }
    victim = paths[0]
    victim.write_text("hand edited\n", encoding="utf-8")
    assert generator.check_surfaces(CONTRACT_PATH, tmp_path) == [
        f"stale agent output: {victim.relative_to(tmp_path)}"
    ]

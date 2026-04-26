from __future__ import annotations

import tomllib
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_command_prompt(relative_path: str) -> str:
    command = tomllib.loads((REPO_ROOT / relative_path).read_text(encoding="utf-8"))
    return command["prompt"]


def _load_agent_text(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def test_gemini_prd_command_delegates_with_plan_mode() -> None:
    prompt = _load_command_prompt("commands/flow/prd.toml")

    assert "enter_plan_mode" in prompt
    assert "@prd-orchestrator" in prompt
    assert "@flow:" not in prompt


def test_gemini_prd_orchestrator_manages_full_plan_mode_lifecycle() -> None:
    agent = _load_agent_text("agents/prd-orchestrator.md")

    assert "enter_plan_mode" in agent
    assert "exit_plan_mode" in agent
    assert "Stay in Plan Mode" in agent


def test_gemini_plan_command_delegates_with_plan_mode() -> None:
    prompt = _load_command_prompt("commands/flow/plan.toml")

    assert "enter_plan_mode" in prompt
    assert "@plan-generator" in prompt
    assert "@flow:" not in prompt


def test_gemini_implement_command_delegates_to_slug_executor() -> None:
    prompt = _load_command_prompt("commands/flow/implement.toml")

    assert "@executor" in prompt
    assert "@flow:" not in prompt


def test_gemini_plan_generator_manages_full_plan_mode_lifecycle() -> None:
    agent = _load_agent_text("agents/plan-generator.md")

    assert "enter_plan_mode" in agent
    assert "exit_plan_mode" in agent
    assert "Stay in Plan Mode" in agent


def test_opencode_templates_reference_native_plan_mode() -> None:
    for relative_path in (
        "templates/opencode/commands/flow-prd.md",
        "templates/opencode/commands/flow-plan.md",
    ):
        assert "Native Plan Mode" in _load_agent_text(relative_path)


def test_gemini_docs_reference_supported_plan_settings() -> None:
    gemini_doc = (REPO_ROOT / "GEMINI.md").read_text(encoding="utf-8")
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    combined = f"{gemini_doc}\n{readme}"

    assert "general.plan.enabled" in combined
    assert "general.plan.modelRouting" in combined
    assert "undocumented `autoEnter` behavior" in combined

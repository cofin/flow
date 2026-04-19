from __future__ import annotations

import tomllib
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_command_prompt(relative_path: str) -> str:
    command = tomllib.loads((REPO_ROOT / relative_path).read_text(encoding="utf-8"))
    return command["prompt"]


def test_gemini_prd_command_explicitly_manages_plan_mode() -> None:
    prompt = _load_command_prompt("commands/flow/prd.toml")

    assert "enter_plan_mode" in prompt
    assert "exit_plan_mode" in prompt
    assert "Remain in Plan Mode" in prompt


def test_gemini_plan_command_explicitly_manages_plan_mode() -> None:
    prompt = _load_command_prompt("commands/flow/plan.toml")

    assert "enter_plan_mode" in prompt
    assert "exit_plan_mode" in prompt
    assert "Remain in Plan Mode" in prompt


def test_gemini_docs_reference_supported_plan_settings() -> None:
    gemini_doc = (REPO_ROOT / "GEMINI.md").read_text(encoding="utf-8")
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    combined = f"{gemini_doc}\n{readme}"

    assert "general.plan.enabled" in combined
    assert "general.plan.modelRouting" in combined
    assert "undocumented `autoEnter` behavior" in combined

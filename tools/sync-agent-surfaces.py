#!/usr/bin/env python3
"""Generate thin host-agent adapters from ``contracts/flow.yaml``."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:  # Direct ``python tools/...`` execution.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.flow_contract import (  # noqa: E402
    AgentOutput,
    AgentRecord,
    ContractError,
    FlowContract,
    load_contract,
)

GENERATED_MARKER = "generated-sha256:"
_HASH_PLACEHOLDER = "__FLOW_GENERATED_SHA256__"


def _digest(payload: str) -> str:
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _record(
    contract: FlowContract, agent: AgentRecord, harness_id: str
) -> dict[str, object]:
    capability = contract.harnesses[harness_id]
    return {
        "kind": "flow_agent_adapter",
        "canonical_id": agent.id,
        "canonical_source": agent.canonical_source,
        "host": harness_id,
        "invariant_ids": list(agent.invariant_ids),
        "interaction_requirement": agent.interaction_requirement,
        "tool_capability_requirements": list(agent.tool_requirements[harness_id]),
        "question_capability": {
            "transport": capability.transport,
            "tool": capability.verified_tool,
            "permission_check": capability.permission_check,
            "supported_modes": list(capability.supported_modes),
            "choice_min": capability.choice_min,
            "choice_max": capability.choice_max,
            "mutual_exclusion": capability.mutual_exclusion,
            "multi_select": capability.multi_select,
            "bounds_enforcement": capability.bounds_enforcement,
            "custom_answer_behavior": capability.custom_answer_behavior,
            "disabled_choice_policy": capability.disabled_choice_policy,
            "sequential_fallback": capability.sequential_fallback,
            "evidence": capability.evidence,
        },
        "git_tags": contract.git_policy.tags,
        "instruction": "Read and follow the canonical agent source directly.",
    }


def _body(contract: FlowContract, agent: AgentRecord, harness_id: str) -> str:
    return json.dumps(
        _record(contract, agent, harness_id),
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )


def _stamp(content: str) -> str:
    digest = _digest(content.replace(_HASH_PLACEHOLDER, ""))
    return content.replace(_HASH_PLACEHOLDER, digest)


def _render_codex(
    contract: FlowContract, agent: AgentRecord, output: AgentOutput, harness_id: str
) -> str:
    body = _body(contract, agent, harness_id)
    nicknames = ", ".join(
        json.dumps(item) for item in agent.generation.nickname_candidates
    )
    return _stamp(
        "# Generated from contracts/flow.yaml\n"
        f"# {GENERATED_MARKER} {_HASH_PLACEHOLDER}\n"
        f"name = {json.dumps(agent.id)}\n"
        f"description = {json.dumps(agent.generation.description)}\n"
        f"nickname_candidates = [{nicknames}]\n"
        f"developer_instructions = {json.dumps(body)}\n"
    )


def _render_opencode(
    contract: FlowContract, agent: AgentRecord, output: AgentOutput, harness_id: str
) -> str:
    body = _body(contract, agent, harness_id)
    return _stamp(
        "---\n"
        f"name: {agent.id}\n"
        f"description: {json.dumps(agent.generation.description)}\n"
        f"mode: {output.mode}\n"
        "permission:\n"
        f"  edit: {output.edit_permission}\n"
        f"  bash: {output.bash_permission}\n"
        f"  webfetch: {output.web_permission}\n"
        "---\n\n"
        f"<!-- Generated from contracts/flow.yaml; {GENERATED_MARKER} {_HASH_PLACEHOLDER} -->\n\n"
        f"```json\n{body}\n```\n"
    )


def _render_vscode(
    contract: FlowContract,
    agent: AgentRecord,
    _output: AgentOutput,
    harness_id: str,
) -> str:
    body = _body(contract, agent, harness_id)
    return _stamp(
        "---\n"
        f"name: {agent.id}\n"
        f"description: {json.dumps(agent.generation.description)}\n"
        "---\n\n"
        f"<!-- Generated from contracts/flow.yaml; {GENERATED_MARKER} {_HASH_PLACEHOLDER} -->\n\n"
        f"```json\n{body}\n```\n"
    )


def _render_antigravity(
    contract: FlowContract,
    agent: AgentRecord,
    _output: AgentOutput,
    harness_id: str,
) -> str:
    body = _body(contract, agent, harness_id)
    return _stamp(
        "---\n"
        f"name: {agent.id}\n"
        f"description: {json.dumps(agent.generation.description)}\n"
        "subagent: true\n"
        "mainAgent: false\n"
        "model: inherit\n"
        "commandExecutionPolicy: off\n"
        "---\n\n"
        f"<!-- Generated from contracts/flow.yaml; {GENERATED_MARKER} {_HASH_PLACEHOLDER} -->\n\n"
        f"```json\n{body}\n```\n"
    )


def render_surfaces(contract_path: Path, _output_root: Path) -> dict[str, str]:
    """Return deterministic repository-relative agent outputs."""
    contract = load_contract(contract_path)
    rendered: dict[str, str] = {}
    renderers = {
        "antigravity_markdown": _render_antigravity,
        "codex_toml": _render_codex,
        "opencode_markdown": _render_opencode,
        "vscode_markdown": _render_vscode,
    }
    for agent in contract.agents.values():
        for harness_id, output in agent.generation.outputs.items():
            rendered[output.path] = renderers[output.format](
                contract, agent, output, harness_id
            )
    return dict(sorted(rendered.items()))


def write_surfaces(contract_path: Path, output_root: Path) -> list[Path]:
    """Write generated outputs beneath the explicit output root."""
    paths: list[Path] = []
    for relative, content in render_surfaces(contract_path, output_root).items():
        target = output_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        paths.append(target)
    return paths


def check_surfaces(contract_path: Path, output_root: Path) -> list[str]:
    """Return missing/stale diagnostics without mutating the output tree."""
    diagnostics: list[str] = []
    for relative, expected in render_surfaces(contract_path, output_root).items():
        target = output_root / relative
        if not target.is_file():
            diagnostics.append(f"missing agent output: {relative}")
        elif target.read_text(encoding="utf-8") != expected:
            diagnostics.append(f"stale agent output: {relative}")
    return diagnostics


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    parser.add_argument("--contract", type=Path, default=Path("contracts/flow.yaml"))
    parser.add_argument("--output-root", type=Path, default=Path.cwd())
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    try:
        if args.write:
            paths = write_surfaces(args.contract, args.output_root)
            print(f"wrote {len(paths)} agent outputs")
            return 0
        diagnostics = check_surfaces(args.contract, args.output_root)
    except ContractError as exc:
        print(f"agent surface generation failed: {exc}", file=sys.stderr)
        return 1
    if diagnostics:
        print("Agent surfaces are stale:")
        for diagnostic in diagnostics:
            print(f"  - {diagnostic}")
        return 1
    print("Agent surfaces are current.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

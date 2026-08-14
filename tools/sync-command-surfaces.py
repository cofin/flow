#!/usr/bin/env python3
"""Generate thin host command adapters from ``contracts/flow.yaml``."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:  # Direct ``python tools/...`` execution.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.flow_contract import (  # noqa: E402
    CommandRecord,
    ContractError,
    FlowContract,
    load_contract,
)

GENERATED_MARKER = "generated-sha256:"
_HASH_PLACEHOLDER = "__FLOW_GENERATED_SHA256__"


def _digest(payload: str) -> str:
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _adapter_record(
    contract: FlowContract, command: CommandRecord, harness_id: str
) -> dict[str, object]:
    invocation = command.invocations[harness_id]
    capability = contract.harnesses[harness_id]
    return {
        "kind": "flow_command_adapter",
        "canonical_id": command.id,
        "host": harness_id,
        "lifecycle_owner": command.lifecycle_owner,
        "procedure_source": command.procedure_source,
        "agent": command.agent,
        "argument_schema": {
            "syntax": command.argument_schema.syntax,
            "required": list(command.argument_schema.required),
            "optional": list(command.argument_schema.optional),
        },
        "mutability": command.mutability,
        "interaction_mode": command.interaction_mode,
        "question_capability": command.question_capability,
        "question_transport": capability.transport,
        "question_tool": capability.verified_tool,
        "question_permission_check": capability.permission_check,
        "supported_selection_modes": list(capability.supported_modes),
        "choice_min": capability.choice_min,
        "choice_max": capability.choice_max,
        "mutual_exclusion": capability.mutual_exclusion,
        "multi_select": capability.multi_select,
        "bounds_enforcement": capability.bounds_enforcement,
        "custom_answer_behavior": capability.custom_answer_behavior,
        "disabled_choice_policy": capability.disabled_choice_policy,
        "sequential_fallback": capability.sequential_fallback,
        "capability_evidence": capability.evidence,
        "shared_contracts": list(command.shared_contracts),
        "state_operations": list(command.state_operations),
        "plan_capability": command.plan_capability,
        "completion_gates": list(command.completion_gates),
        "runtime_dependency": command.runtime_dependency,
        "invocation": invocation.spelling,
        "fallback": invocation.fallback,
        "git_tags": contract.git_policy.tags,
        "instruction": "Load the lifecycle owner and follow the canonical procedure source directly.",
    }


def _payload(contract: FlowContract, command: CommandRecord, harness_id: str) -> str:
    return json.dumps(
        _adapter_record(contract, command, harness_id),
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )


def _stamp(content: str) -> str:
    digest = _digest(content.replace(_HASH_PLACEHOLDER, ""))
    return content.replace(_HASH_PLACEHOLDER, digest)


def _markdown_adapter(
    contract: FlowContract, command: CommandRecord, harness_id: str
) -> str:
    payload = _payload(contract, command, harness_id)
    description = f"Run the canonical {command.id} Flow lifecycle."
    return _stamp(
        "---\n"
        f"description: {json.dumps(description)}\n"
        "---\n\n"
        f"<!-- Generated from contracts/flow.yaml; {GENERATED_MARKER} {_HASH_PLACEHOLDER} -->\n\n"
        f"```json\n{payload}\n```\n"
    )


def _toml_adapter(contract: FlowContract, command: CommandRecord) -> str:
    payload = _payload(contract, command, "codex_cli")
    description = f"Run the canonical {command.id} Flow lifecycle."
    return _stamp(
        "# Generated from contracts/flow.yaml\n"
        f"# {GENERATED_MARKER} {_HASH_PLACEHOLDER}\n"
        f"description = {json.dumps(description)}\n"
        f"prompt = {json.dumps(payload)}\n"
    )


def render_surfaces(contract_path: Path, _output_root: Path) -> dict[str, str]:
    """Return deterministic repository-relative command outputs."""
    contract = load_contract(contract_path)
    rendered: dict[str, str] = {}
    for command in contract.commands.values():
        name = command.id.removeprefix("flow/")
        rendered[f"commands/flow-{name}.md"] = _markdown_adapter(
            contract, command, "claude_code"
        )
        rendered[f"commands/flow/{name}.toml"] = _toml_adapter(contract, command)
        rendered[f"templates/opencode/commands/flow-{name}.md"] = _markdown_adapter(
            contract, command, "opencode"
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
            diagnostics.append(f"missing command output: {relative}")
        elif target.read_text(encoding="utf-8") != expected:
            diagnostics.append(f"stale command output: {relative}")
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
            print(f"wrote {len(paths)} command outputs")
            return 0
        diagnostics = check_surfaces(args.contract, args.output_root)
    except ContractError as exc:
        print(f"command surface generation failed: {exc}", file=sys.stderr)
        return 1
    if diagnostics:
        print("Command surfaces are stale:")
        for diagnostic in diagnostics:
            print(f"  - {diagnostic}")
        return 1
    print("Command surfaces are current.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

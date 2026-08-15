#!/usr/bin/env python3
"""Generate host rule adapters from the canonical Flow operational rule."""

from __future__ import annotations

import argparse
import hashlib
import json
import posixpath
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

if __package__ in {None, ""}:  # Direct ``python tools/...`` execution.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.flow_contract import ContractError, FlowContract, load_contract  # noqa: E402

CANONICAL_SOURCE = Path("rules/flow-core.md")
CONTRACT_SOURCE = Path("contracts/flow.yaml")
LEGACY_SURFACES = (Path("rules/flow_antigravity.md"),)
GENERATED_MARKER = "generated-sha256:"
_HASH_PLACEHOLDER = "__FLOW_GENERATED_SHA256__"
_FRONTMATTER = re.compile(r"\A---\n(?P<data>.*?)\n---\n(?P<body>.*)\Z", re.DOTALL)


@dataclass(frozen=True)
class CoreRule:
    rule_id: str
    revision: int
    shared_contracts: tuple[str, ...]
    lifecycle_skills: tuple[str, ...]
    host_activation: dict[str, str]
    body: str
    sha256: str


def _digest(payload: str) -> str:
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _strings(value: Any, context: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise ContractError(f"{context} must be a non-empty list")
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise ContractError(f"{context} must contain non-empty strings")
    return tuple(value)


def load_core_rule(path: Path) -> CoreRule:
    """Parse the bounded canonical rule semantic source."""
    source = path.read_text(encoding="utf-8")
    match = _FRONTMATTER.fullmatch(source)
    if match is None:
        raise ContractError("canonical rule requires YAML frontmatter")
    data = yaml.safe_load(match.group("data"))
    if not isinstance(data, dict):
        raise ContractError("canonical rule frontmatter must be a mapping")
    expected = {
        "rule_id",
        "revision",
        "shared_contracts",
        "lifecycle_skills",
        "host_activation",
    }
    if set(data) != expected:
        raise ContractError("canonical rule frontmatter keys are not canonical")
    if data["rule_id"] != "flow-operational-v1":
        raise ContractError("canonical rule_id must be flow-operational-v1")
    revision = data["revision"]
    if not isinstance(revision, int) or isinstance(revision, bool) or revision < 1:
        raise ContractError("canonical rule revision must be a positive integer")
    shared = _strings(data["shared_contracts"], "shared_contracts")
    lifecycle = _strings(data["lifecycle_skills"], "lifecycle_skills")
    activation = data["host_activation"]
    if not isinstance(activation, dict) or any(
        not isinstance(key, str) or not isinstance(value, str) or not value.strip()
        for key, value in activation.items()
    ):
        raise ContractError("host_activation must map hosts to non-empty text")
    body = match.group("body").strip() + "\n"
    if not body.startswith("# Flow Operational Rule\n"):
        raise ContractError("canonical rule requires its stable title")
    if len(body) > 3_000:
        raise ContractError("canonical rule exceeds the 3000-character budget")
    return CoreRule(
        data["rule_id"],
        revision,
        shared,
        lifecycle,
        dict(activation),
        body,
        _digest(source),
    )


def _adapter_record(
    contract: FlowContract, core: CoreRule, harness_id: str, contract_sha256: str
) -> dict[str, object]:
    capability = contract.harnesses[harness_id]
    return {
        "kind": "flow_rule_adapter",
        "rule_id": core.rule_id,
        "rule_revision": core.revision,
        "canonical_source": CANONICAL_SOURCE.as_posix(),
        "canonical_sha256": core.sha256,
        "contract_source": CONTRACT_SOURCE.as_posix(),
        "contract_sha256": contract_sha256,
        "host": harness_id,
        "activation": core.host_activation[harness_id],
        "shared_contracts": list(core.shared_contracts),
        "lifecycle_skills": list(core.lifecycle_skills),
        "question_capability": {
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
        },
        "interaction_contract": {
            "id": contract.interaction.id,
            "procedure_source": contract.interaction.procedure_source,
            "choice_keys": list(contract.interaction.choice_keys),
            "fallback_reason_order": list(contract.interaction.fallback_reason_order),
            "pre_quality": list(contract.interaction.planning_gates["pre_quality"]),
            "post_quality": list(contract.interaction.planning_gates["post_quality"]),
            "recommended_choice": "first_with_suffix",
            "recommended_suffix": " (Recommended)",
            "custom_label": "Other",
            "one_decision_at_a_time": True,
        },
        "git_tags": contract.git_policy.tags,
        "automatic_push": False,
        "nested_knowledge": True,
    }


def semantic_records(
    contract_path: Path, core_path: Path
) -> dict[str, dict[str, object]]:
    """Build the single normalized record consumed by every host renderer."""
    contract = load_contract(contract_path)
    core = load_core_rule(core_path)
    if tuple(core.host_activation) != tuple(contract.harnesses):
        raise ContractError(
            "canonical rule host activation order must match the contract"
        )
    if core.shared_contracts != tuple(contract.shared_contracts):
        raise ContractError("canonical rule shared contracts must match the contract")
    contract_sha256 = _digest(contract_path.read_text(encoding="utf-8"))
    return {
        harness_id: _adapter_record(contract, core, harness_id, contract_sha256)
        for harness_id in contract.harnesses
    }


def _metadata(record: dict[str, object]) -> str:
    return json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _stamp(content: str) -> str:
    digest = _digest(content.replace(_HASH_PLACEHOLDER, ""))
    return content.replace(_HASH_PLACEHOLDER, digest)


def _body_for(core: CoreRule, relative: str) -> str:
    parent = posixpath.dirname(relative) or "."
    skills = posixpath.relpath("skills", start=parent)
    return core.body.replace("../skills/", f"{skills}/")


def _choice_view(record: dict[str, object]) -> str:
    capability = record["question_capability"]
    assert isinstance(capability, dict)
    tool = capability["tool"]
    if tool is None:
        transport = (
            "No native question tool is verified for this host. Render every request "
            "sequentially in text and wait for its answer before continuing."
        )
    else:
        modes = ", ".join(capability["supported_modes"])
        usage = "MUST use" if record["host"] == "antigravity" else "Use"
        transport = (
            f"Inspect current tool declarations and permission before asking. {usage} `{tool}` "
            f"only when it is declared, allowed, and compatible with modes {modes}, "
            f"{capability['choice_min']}-{capability['choice_max']} domain choices, custom "
            "input, omit-disabled, and any required agent-validated bounds. If absent, "
            "denied, or incompatible, render the same request sequentially in text and "
            "wait for its answer. Stop and surface any other tool error."
        )
    return (
        "## Structured decision view\n\n"
        f"{transport}\n\n"
        "For `binary`, `single_select`, and `multi_select`, show only enabled domain "
        "choices (2-4 within the host limit), put the recommended choice first with "
        "a space and `(Recommended)`, include each concise description, include "
        "multi-select bounds, and finish with `Other - enter a custom response`. For "
        "`open`, show only its input guidance and use sequential text. Never invent a "
        "tool, argument, mode, slash command, or batch interaction. Before quality, "
        "offer only Revise/Refine; after quality, offer Approve/Revise/Refine.\n"
    )


def _cross_harness_view(records: dict[str, dict[str, object]]) -> str:
    lines = ["## Structured decision transport", ""]
    for harness_id, record in records.items():
        capability = record["question_capability"]
        assert isinstance(capability, dict)
        tool = capability["tool"]
        if tool is None:
            detail = "sequential text only; no verified native question tool"
        else:
            modes = ", ".join(capability["supported_modes"])
            detail = (
                f"conditionally use `{tool}` for {modes} with "
                f"{capability['choice_min']}-{capability['choice_max']} choices; "
                "fall back sequentially when absent, denied, or incompatible"
            )
        lines.append(f"- `{harness_id}`: {record['activation']} {detail}.")
    lines.extend(
        [
            "",
            "Every renderer preserves omit-disabled, recommended-first "
            "`(Recommended)`, concise descriptions, custom/Other, zero-choice "
            "open input, selection bounds, and the pre/post-quality action sets "
            "from `structured-choice-v1`. Ask and await one decision at a time.",
            "",
        ]
    )
    return "\n".join(lines)


def _markdown(
    core: CoreRule,
    record: dict[str, object],
    relative: str,
    *,
    frontmatter: str | None = None,
    view: str | None = None,
) -> str:
    header = ""
    if frontmatter is not None:
        header = f"---\n{frontmatter.rstrip()}\n---\n\n"
    body = _body_for(core, relative)
    title, remainder = body.split("\n", 1)
    remainder = remainder.strip()
    return _stamp(
        header
        + f"<!-- Generated from rules/flow-core.md and contracts/flow.yaml; {GENERATED_MARKER} {_HASH_PLACEHOLDER} -->\n"
        + f"<!-- flow-rule-adapter: {_metadata(record)} -->\n\n"
        + title
        + "\n\n"
        + f"Activation: {record['activation']}\n\n"
        + remainder
        + "\n\n"
        + (view if view is not None else _choice_view(record))
    )


def _opencode(core: CoreRule, record: dict[str, object], relative: str) -> str:
    del core, relative
    capability = record["question_capability"]
    interaction = record["interaction_contract"]
    assert isinstance(capability, dict) and isinstance(interaction, dict)
    modes = "/".join(capability["supported_modes"])
    prompt = (
        f"Flow rule v{record['rule_revision']} is {record['canonical_source']}. When "
        ".agents exists, rules precede skills; load the router/lifecycle skill and "
        "the journal-first direct-read continuity contract in "
        "skills/flow/references/state.md. For "
        f"{interaction['id']}, inspect allowed tools and use verified "
        f"{capability['tool']} only for compatible {modes} requests with "
        f"{capability['choice_min']}-{capability['choice_max']} choices, recommended "
        "first, Other, omitted disabled choices, and valid bounds; otherwise ask "
        "sequentially. Read nested knowledge. Never auto-push or mutate Git tags."
    )
    if len(prompt) > 512:
        raise ContractError("OpenCode static rule exceeds the 512-character budget")
    return _stamp(
        "/** Generated from rules/flow-core.md and contracts/flow.yaml. */\n"
        f"// {GENERATED_MARKER} {_HASH_PLACEHOLDER}\n"
        "// flow-rule-adapter:start\n"
        f"const FLOW_RULE_ADAPTER = Object.freeze({_metadata(record)});\n"
        "// flow-rule-adapter:end\n"
        f"const FLOW_RULE_PROMPT = {json.dumps(prompt, ensure_ascii=False)};\n\n"
        "function isFlowDisabledByManagedConfig(ctx) {\n"
        "  const managed = ctx?.config?.managedConfig ?? ctx?.config?.managed ?? null;\n"
        "  if (!managed) return false;\n"
        "  if (managed.disabledPlugins?.includes('flow')) return true;\n"
        "  return Boolean(managed.allowedPlugins && !managed.allowedPlugins.includes('flow'));\n"
        "}\n\n"
        "export default async (ctx) => {\n"
        "  if (isFlowDisabledByManagedConfig(ctx)) return {};\n\n"
        "  return {\n"
        "    'experimental.chat.system.transform': async (_input, output) => {\n"
        "      output.system.push(FLOW_RULE_PROMPT);\n"
        "    },\n"
        "  };\n"
        "};\n"
    )


def render_surfaces(
    contract_path: Path, core_path: Path, _output_root: Path
) -> dict[str, str]:
    """Return deterministic repository-relative rule outputs."""
    core = load_core_rule(core_path)
    records = semantic_records(contract_path, core_path)
    antigravity = records["antigravity"]
    cursor = records["cursor"]
    vscode = records["vscode_copilot"]
    opencode = records["opencode"]
    generic = dict(records["openclaw"])
    generic["host"] = "cross_harness"
    generic["activation"] = (
        "Use the supported host instruction surface and then native Flow skills."
    )
    generic["host_capabilities"] = {
        host: record["question_capability"] for host, record in records.items()
    }
    generic["host_activation"] = {
        host: record["activation"] for host, record in records.items()
    }
    rendered = {
        "rules/flow-antigravity.md": _markdown(
            core,
            antigravity,
            "rules/flow-antigravity.md",
            frontmatter=(
                "trigger: model_decision\n"
                "description: Flow operational and structured-decision rules evaluated before skills."
            ),
        ),
        "templates/agent/flow-instructions.md": _markdown(
            core,
            generic,
            "templates/agent/flow-instructions.md",
            view=_cross_harness_view(records),
        ),
        ".cursor/rules/flow.mdc": _markdown(
            core,
            cursor,
            ".cursor/rules/flow.mdc",
            frontmatter=(
                "description: Use Flow for context-driven development in repositories with .agents.\n"
                "alwaysApply: true"
            ),
        ),
        ".github/copilot-instructions.md": _markdown(
            core, vscode, ".github/copilot-instructions.md"
        ),
        ".opencode/plugins/flow.js": _opencode(
            core, opencode, ".opencode/plugins/flow.js"
        ),
    }
    return dict(sorted(rendered.items()))


def write_surfaces(
    contract_path: Path, core_path: Path, output_root: Path
) -> list[Path]:
    """Write generated outputs and remove the retired underscore rule."""
    paths: list[Path] = []
    for relative, content in render_surfaces(
        contract_path, core_path, output_root
    ).items():
        target = output_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        paths.append(target)
    for relative in LEGACY_SURFACES:
        legacy = output_root / relative
        if legacy.is_file():
            legacy.unlink()
    return paths


def check_surfaces(
    contract_path: Path, core_path: Path, output_root: Path
) -> list[str]:
    """Return stale/missing/legacy diagnostics without mutating the output tree."""
    diagnostics: list[str] = []
    for relative, expected in render_surfaces(
        contract_path, core_path, output_root
    ).items():
        target = output_root / relative
        if not target.is_file():
            diagnostics.append(f"missing rule output: {relative}")
        elif target.read_text(encoding="utf-8") != expected:
            diagnostics.append(f"stale rule output: {relative}")
    for relative in LEGACY_SURFACES:
        if (output_root / relative).exists():
            diagnostics.append(
                f"legacy rule output must be removed: {relative.as_posix()}"
            )
    return diagnostics


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    parser.add_argument("--contract", type=Path, default=CONTRACT_SOURCE)
    parser.add_argument("--core", type=Path, default=CANONICAL_SOURCE)
    parser.add_argument("--output-root", type=Path, default=Path.cwd())
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    try:
        if args.write:
            paths = write_surfaces(args.contract, args.core, args.output_root)
            print(f"wrote {len(paths)} rule outputs")
            return 0
        diagnostics = check_surfaces(args.contract, args.core, args.output_root)
    except (ContractError, OSError, yaml.YAMLError) as exc:
        print(f"rule surface generation failed: {exc}", file=sys.stderr)
        return 1
    if diagnostics:
        print("Rule surfaces are stale:")
        for diagnostic in diagnostics:
            print(f"  - {diagnostic}")
        return 1
    print("Rule surfaces are current.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import json
import re
from pathlib import Path

from tools.flow_contract import load_contract


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT = load_contract(REPO_ROOT / "contracts" / "flow.yaml")
PUBLIC_DOCS = (
    "README.md",
    "AGENTS.md",
    "docs/antigravity.md",
    "docs/harness-conformance-matrix.md",
    "docs/multi-harness-plugin-patterns.md",
    ".codex/INSTALL.md",
    ".opencode/INSTALL.md",
)
MANUAL_INSTALL_COMMAND = re.compile(r"^\s*(?:git\s+clone|ln\s+-s\w*|cp\s+-[Rr])\b", re.MULTILINE)
LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def _table(document: str, heading: str) -> tuple[list[str], list[list[str]]]:
    section = document.split(f"## {heading}\n", 1)[1].split("\n## ", 1)[0]
    lines = [line for line in section.splitlines() if line.startswith("|")]
    header = [cell.strip() for cell in lines[0].strip("|").split("|")]
    rows = [
        [cell.strip().replace("`", "") for cell in line.strip("|").split("|")]
        for line in lines[2:]
    ]
    return header, rows


def test_legacy_cli_files_are_removed_from_shipped_repo() -> None:
    for relative_path in ("GEMINI.md", "gemini-extension.json", ".geminiignore"):
        assert not (REPO_ROOT / relative_path).exists()


def test_multi_harness_installer_is_removed_from_shipped_repo() -> None:
    assert not (REPO_ROOT / "tools" / "install.sh").exists()


def test_public_install_docs_use_native_install_surfaces() -> None:
    forbidden_names = (
        "Gemini CLI",
        "gemini extensions",
        "gemini-extension.json",
        "GEMINI.md",
        "tools/install.sh",
    )
    for relative_path in PUBLIC_DOCS:
        text = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
        assert MANUAL_INSTALL_COMMAND.search(text) is None, relative_path
        for token in forbidden_names:
            assert token not in text, f"{relative_path} still advertises {token!r}"


def test_public_doc_local_links_resolve() -> None:
    for relative_path in PUBLIC_DOCS:
        path = REPO_ROOT / relative_path
        for target in LINK.findall(path.read_text(encoding="utf-8")):
            if target.startswith(("http://", "https://", "#", "mailto:")):
                continue
            local = target.split("#", 1)[0]
            if local:
                assert (path.parent / local).resolve().exists(), (relative_path, target)


def test_capability_matrix_projects_the_contract() -> None:
    document = (REPO_ROOT / "docs" / "harness-conformance-matrix.md").read_text(encoding="utf-8")
    header, rows = _table(document, "Capability matrix")
    assert header == [
        "Harness ID",
        "Activation",
        "Command surface",
        "Native question tool",
        "Availability check",
        "Supported modes",
        "Domain choices",
        "Custom answer",
        "Sequential fallback",
        "Plan capability",
        "Recovery routing",
        "State sidecar",
        "Quality gate",
    ]
    by_id = {row[0]: row for row in rows}
    assert set(by_id) == set(CONTRACT.harnesses)
    for harness_id, capability in CONTRACT.harnesses.items():
        row = by_id[harness_id]
        assert row[2] == capability.command_surface
        assert row[3] == (capability.verified_tool or "null")
        assert row[4] == capability.permission_check
        assert row[5] == (",".join(capability.supported_modes) or "none")
        expected_choices = (
            f"{capability.choice_min}-{capability.choice_max}"
            if capability.choice_min is not None
            else "n/a"
        )
        assert row[6] == expected_choices
        assert row[7] == capability.custom_answer_behavior
        assert row[8] == str(capability.sequential_fallback).lower()
        assert row[9] == capability.plan_capability
        assert "direct Markdown read" in row[10]
        assert row[11] == "flow-reconciler with file tools"
        assert "mandatory fresh quality review" in row[12]


def test_invocation_matrix_projects_every_contract_spelling() -> None:
    document = (REPO_ROOT / "docs" / "harness-conformance-matrix.md").read_text(encoding="utf-8")
    header, rows = _table(document, "Exact command spellings")
    assert header == ["Operation", *CONTRACT.harnesses]
    by_id = {row[0]: row[1:] for row in rows}
    assert set(by_id) == set(CONTRACT.commands)
    for command_id, command in CONTRACT.commands.items():
        assert by_id[command_id] == [
            command.invocations[harness_id].spelling
            for harness_id in CONTRACT.harnesses
        ]


def test_manifests_and_templates_do_not_advertise_unsupported_commands() -> None:
    codex = json.loads((REPO_ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
    claude = json.loads((REPO_ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    assert "commands" not in codex
    assert {Path(path).stem for path in claude["agents"]} == set(CONTRACT.agents)

    opencode_templates = {
        path.stem.removeprefix("flow-")
        for path in (REPO_ROOT / "templates" / "opencode" / "commands").glob("flow-*.md")
    }
    assert opencode_templates == {
        command_id.removeprefix("flow/") for command_id in CONTRACT.commands
    }


def test_public_operational_discovery_uses_the_consumer_skill_root() -> None:
    for relative_path in PUBLIC_DOCS:
        text = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
        assert ".agents/bundles/skills/" not in text
    assert ".agents/skills/" in (REPO_ROOT / "README.md").read_text(encoding="utf-8")

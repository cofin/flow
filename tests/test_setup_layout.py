from __future__ import annotations

import re
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]


def _read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def _flow_contract() -> dict[str, object]:
    loaded = yaml.safe_load(_read("contracts/flow.yaml"))
    assert isinstance(loaded, dict)
    return loaded


def _command(command_id: str) -> dict[str, object]:
    commands = _flow_contract()["commands"]
    assert isinstance(commands, list)
    return next(command for command in commands if command["id"] == command_id)


def _migration_contract() -> dict[str, object]:
    text = _read("skills/flow/references/setup.md")
    match = re.search(
        r"```yaml\n(?P<contract>contract: setup-migration-v1\n.*?)\n```",
        text,
        re.DOTALL,
    )
    assert match is not None
    loaded = yaml.safe_load(match.group("contract"))
    assert isinstance(loaded, dict)
    return loaded


def test_setup_has_one_parsed_lifecycle_owner_and_procedure() -> None:
    setup = _command("flow/setup")

    assert setup["lifecycle_owner"] == "flow-setup"
    assert setup["procedure_source"] == "skills/flow/references/setup.md"
    assert setup["completion_gates"] == ["setup_validation", "migration_integrity"]
    assert setup["runtime_dependency"] == "agent_file_tools_only"


def test_setup_migration_contract_has_structured_paths_and_resume_state() -> None:
    migration = _migration_contract()

    assert migration["contract"] == "setup-migration-v1"
    assert migration["version"] == 1
    assert migration["items"] == [
        {
            "source": "<repository-relative path>",
            "destination": "<repository-relative path>",
            "disposition": "migrate|synthesize|remove_after_verify|preserve_local_policy",
        }
    ]
    assert migration["knowledge_paths"] == [
        {
            "source_root": "<legacy knowledge root>",
            "destination_root": "<configured bundle knowledge root>",
            "relative_paths": ["<unique sorted recursive paths>"],
        }
    ]
    assert migration["progress"] == {
        "last_successful_step": "inventory|mapping_approved|destination_writes|postconditions|complete",
        "resume_operation": "<exact next setup operation or null>",
    }


def test_setup_postconditions_are_complete_and_fail_closed() -> None:
    text = _read("skills/flow/references/setup.md")
    section = text.split("#### Fail-closed completion and resume", 1)[1].split(
        "### 0.1.1b", 1
    )[0]
    labels = re.findall(r"^\d+\. ([^:]+):", section, re.MULTILINE)

    assert labels == [
        "plan integrity",
        "continuity",
        "contradiction",
        "single authority",
        "archive contraction",
        "skill-root authority",
        "source/destination count equality",
    ]
    assert "Setup remains incomplete if any check fails." in section


def test_setup_never_mutates_git_tags() -> None:
    git_policy = _flow_contract()["git_policy"]
    assert git_policy == {
        "tags": "forbidden",
        "allowed_local_operations": ["notes", "branches", "worktrees"],
    }
    for relative_path in (
        "skills/flow-setup/SKILL.md",
        "skills/flow/references/setup.md",
    ):
        assert "git tag" not in _read(relative_path).lower()

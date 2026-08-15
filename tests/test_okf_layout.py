from __future__ import annotations

import json
from pathlib import Path
import tomllib

from tools.flow_contract import load_contract


REPO_ROOT = Path(__file__).resolve().parents[1]


def _adapter(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".toml":
        return json.loads(tomllib.loads(text)["prompt"])
    return json.loads(text.split("```json\n", 1)[1].split("\n```", 1)[0])


def test_flow_archive_adapters_route_to_the_canonical_okf_contract() -> None:
    contract = load_contract(REPO_ROOT / "contracts" / "flow.yaml")
    archive = contract.commands["flow/archive"]
    assert archive.procedure_source == "skills/flow/references/archive.md"
    assert archive.runtime_dependency == "agent_file_tools_only"
    assert archive.state_operations == ("note", "archive")
    assert archive.completion_gates == (
        "archive_candidate",
        "verification",
        "code_review",
        "quality_review",
        "archive",
    )
    assert (REPO_ROOT / archive.procedure_source).is_file()

    adapters = (
        REPO_ROOT / "commands" / "flow-archive.md",
        REPO_ROOT / "commands" / "flow" / "archive.toml",
        REPO_ROOT / "templates" / "opencode" / "commands" / "flow-archive.md",
    )
    for path in adapters:
        record = _adapter(path)
        assert record["canonical_id"] == archive.id
        assert record["procedure_source"] == archive.procedure_source
        assert record["runtime_dependency"] == archive.runtime_dependency
        assert tuple(record["state_operations"]) == archive.state_operations
        assert tuple(record["completion_gates"]) == archive.completion_gates

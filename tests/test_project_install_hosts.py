from __future__ import annotations

import importlib.util
import json
from copy import deepcopy
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parents[1]
MODULE_PATH = REPO_ROOT / "tools" / "install-project-flow.py"
SPEC = importlib.util.spec_from_file_location("install_project_flow_hosts", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
INSTALLER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(INSTALLER)


@pytest.mark.parametrize(
    ("host", "present", "absent"),
    [
        ("antigravity", ".agents/agents/executor.md", ".claude/commands/flow-setup.md"),
        (
            "claude_code",
            ".claude/commands/flow-setup.md",
            ".opencode/commands/flow-setup.md",
        ),
        ("codex_cli", ".codex/agents/executor.toml", ".claude/commands/flow-setup.md"),
        ("cursor", ".agents/flow/agents/researcher.md", ".codex/agents/executor.toml"),
        (
            "opencode",
            ".opencode/commands/flow-setup.md",
            ".claude/commands/flow-setup.md",
        ),
        (
            "openclaw",
            ".agents/flow/agents/researcher.md",
            ".opencode/commands/flow-setup.md",
        ),
        (
            "vscode_copilot",
            ".github/agents/executor.agent.md",
            ".claude/commands/flow-setup.md",
        ),
    ],
)
def test_clean_plugin_free_host_gets_complete_selected_surface(
    tmp_path: Path, host: str, present: str, absent: str
) -> None:
    project = tmp_path / host
    project.mkdir()
    result = INSTALLER.install_project_flow(
        project, source_root=REPO_ROOT, mode="install", host=host
    )
    assert result.action == "installed"
    assert (project / present).is_file()
    assert not (project / absent).exists()
    graph = INSTALLER._load_install_graph(REPO_ROOT)
    closure = INSTALLER._graph_closure(graph, host)
    nodes = graph["nodes"]
    expected = {}
    for node_id in closure:
        expected.update(INSTALLER._node_files(REPO_ROOT, node_id, nodes[node_id]))
    state = json.loads((project / ".agents/setup-state.json").read_text())
    installed = {entry["path"] for entry in state["project_install"]["managed_files"]}
    assert installed == set(expected)
    assert "skill:okf" in closure
    assert (project / ".agents/skills/okf/SKILL.md").is_file()
    assert any(node_id.startswith("agent:") for node_id in closure)
    if host == "codex_cli":
        assert "host:codex-agents" in closure
        assert any(path.endswith(".toml") for path in installed)

    unreachable = set(nodes).difference(closure)
    for node_id in unreachable:
        paths = INSTALLER._node_files(REPO_ROOT, node_id, nodes[node_id])
        assert installed.isdisjoint(paths), f"unreachable node installed: {node_id}"

    researcher = (project / ".agents/flow/agents/researcher.md").read_text()
    assert "structured-result-v1" in researcher
    assert state["project_install"]["active_host"] == host

    completion = (project / ".agents/skills/flow-completion/SKILL.md").read_text()
    review = (project / ".agents/skills/flow/references/review.md").read_text()
    sync_status = (project / ".agents/skills/flow-sync-status/SKILL.md").read_text()
    assert "quality-completion-v1" in completion
    for required in ("exact_range_required", "QualityReport"):
        assert required in review
    assert review.index("correctness review") < review.index("quality review")
    for required in (
        "flow-sync-status-routing",
        "typed_reconcile_request",
        "typed_read_only_status_request",
        "flow-state",
    ):
        assert required in sync_status
    assert INSTALLER.CUSTOM_START in completion and INSTALLER.CUSTOM_END in completion
    assert INSTALLER.CUSTOM_START in sync_status and INSTALLER.CUSTOM_END in sync_status


def test_generated_template_gate_reports_missing_stale_and_unmanaged(
    tmp_path: Path,
) -> None:
    generator_path = REPO_ROOT / "tools/sync-standalone-skill-templates.py"
    spec = importlib.util.spec_from_file_location(
        "standalone_generator", generator_path
    )
    assert spec is not None and spec.loader is not None
    generator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(generator)
    output = tmp_path / "skills"
    generator.write_templates(REPO_ROOT, output)
    assert generator.check_templates(REPO_ROOT, output) == []

    customized = output / "flow-completion" / "SKILL.md"
    customized.write_text(
        customized.read_text().replace(
            generator.CUSTOM_END, "run project audit\n" + generator.CUSTOM_END
        )
    )
    generator.write_templates(REPO_ROOT, output)
    assert "run project audit" in customized.read_text()
    assert generator.check_templates(REPO_ROOT, output) == []

    missing = output / "flow" / "SKILL.md"
    missing.unlink()
    assert any(
        "missing standalone skill template: flow/SKILL.md" in item
        for item in generator.check_templates(REPO_ROOT, output)
    )
    generator.write_templates(REPO_ROOT, output)
    stale = output / "flow" / "SKILL.md"
    stale.write_text("stale\n")
    assert any(
        "stale standalone skill template: flow/SKILL.md" in item
        for item in generator.check_templates(REPO_ROOT, output)
    )
    generator.write_templates(REPO_ROOT, output)
    unmanaged = output / "flow" / "unmanaged.md"
    unmanaged.write_text("unexpected\n")
    assert any(
        "unmanaged standalone skill template: flow/unmanaged.md" in item
        for item in generator.check_templates(REPO_ROOT, output)
    )


def test_installer_refuses_stale_generated_graph_node_before_writes(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    canonical = source / "skills/example/SKILL.md"
    generated = source / "templates/agent/skills/example/SKILL.md"
    canonical.parent.mkdir(parents=True)
    generated.parent.mkdir(parents=True)
    canonical.write_text("canonical\n")
    generated.write_text("stale\n")
    graph = {
        "version": 1,
        "roots": ["skill:example"],
        "nodes": {
            "skill:example": {
                "source": "templates/agent/skills/example",
                "destination": ".agents/skills/example",
                "canonical": "skills/example",
                "dependencies": [],
            }
        },
        "hosts": {"cursor": []},
    }
    with pytest.raises(
        INSTALLER.InstallError, match="stale generated standalone node: skill:example"
    ):
        INSTALLER._standalone_files(source, "cursor", graph=graph)


def test_declared_graph_is_complete_and_all_non_host_nodes_are_reachable() -> None:
    graph = INSTALLER._load_install_graph(REPO_ROOT)
    nodes = graph["nodes"]
    all_closures = {
        host: set(INSTALLER._graph_closure(graph, host)) for host in graph["hosts"]
    }
    reachable = set().union(*all_closures.values())

    assert set(graph["roots"]) == {"skill:flow"}
    assert set(nodes).issubset(reachable)
    assert "skill:okf" in reachable
    assert any(node_id.startswith("agent:") for node_id in reachable)
    codex_files = {
        path
        for node_id in all_closures["codex_cli"]
        for path in INSTALLER._node_files(REPO_ROOT, node_id, nodes[node_id])
    }
    assert any(path.endswith(".toml") for path in codex_files)


def test_declared_graph_refuses_missing_and_cyclic_edges() -> None:
    graph = INSTALLER._load_install_graph(REPO_ROOT)
    missing = deepcopy(graph)
    del missing["nodes"]["skill:okf"]
    with pytest.raises(INSTALLER.InstallError, match="missing or invalid.*skill:okf"):
        INSTALLER._graph_closure(missing, "cursor")

    cyclic = deepcopy(graph)
    cyclic["nodes"]["skill:flow-state"]["dependencies"] = ["skill:flow"]
    with pytest.raises(INSTALLER.InstallError, match="cyclic standalone dependency"):
        INSTALLER._graph_closure(cyclic, "cursor")


def test_unsupported_host_and_duplicate_authority_refuse_without_writes(
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    with pytest.raises(INSTALLER.InstallError, match="unsupported active host"):
        INSTALLER.install_project_flow(
            project, source_root=REPO_ROOT, mode="install", host="unknown"
        )
    assert not (project / ".agents").exists()

    collision = project / ".agents/skills/flow/SKILL.md"
    collision.parent.mkdir(parents=True)
    collision.write_text("another authority\n")
    with pytest.raises(INSTALLER.InstallError, match="unmanaged target collision"):
        INSTALLER.install_project_flow(
            project, source_root=REPO_ROOT, mode="install", host="cursor"
        )
    assert collision.read_text() == "another authority\n"

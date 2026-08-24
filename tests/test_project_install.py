from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

MODULE_PATH = Path(__file__).parents[1] / "tools" / "install-project-flow.py"
SPEC = importlib.util.spec_from_file_location("install_project_flow", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
INSTALLER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(INSTALLER)
InstallError = INSTALLER.InstallError
install_project_flow = INSTALLER.install_project_flow


def _write_source(root: Path) -> None:
    (root / "skills" / "flow" / "references").mkdir(parents=True)
    (root / "skills" / "flow" / "SKILL.md").write_text(
        "[Setup](references/setup.md)\n", encoding="utf-8"
    )
    (root / "skills" / "flow" / "references" / "setup.md").write_text(
        "before\n<!-- project-customization: start -->\n"
        "<!-- project-customization: end -->\nafter\n",
        encoding="utf-8",
    )
    graph = {
        "version": 1,
        "roots": ["skill:flow"],
        "nodes": {
            "skill:flow": {
                "source": "skills/flow",
                "destination": ".agents/skills/flow",
                "dependencies": [],
            }
        },
        "hosts": {host: [] for host in INSTALLER.HOST_MARKERS},
    }
    graph_path = root / INSTALLER.INSTALL_GRAPH_PATH
    graph_path.parent.mkdir(parents=True)
    graph_path.write_text(json.dumps(graph), encoding="utf-8")


def _state(project: Path) -> dict[str, object]:
    return json.loads((project / ".agents" / "setup-state.json").read_text())


def test_default_skip_does_not_create_or_change_an_install(tmp_path: Path) -> None:
    source = tmp_path / "source"
    project = tmp_path / "project"
    _write_source(source)
    project.mkdir()

    result = install_project_flow(project, source_root=source)
    assert result.action == "skipped"
    assert not (project / ".agents").exists()

    installed = install_project_flow(
        project, source_root=source, mode="install", host="codex_cli"
    )
    before = (project / ".agents" / "setup-state.json").read_bytes()
    assert installed.action == "installed"
    assert install_project_flow(project, source_root=source).action == "skipped"
    assert (project / ".agents" / "setup-state.json").read_bytes() == before


def test_install_requires_one_active_host_and_records_exact_inventory(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    project = tmp_path / "project"
    _write_source(source)
    (project / ".claude").mkdir(parents=True)
    (project / ".codex").mkdir()

    with pytest.raises(InstallError, match="active host is ambiguous"):
        install_project_flow(project, source_root=source, mode="install")

    result = install_project_flow(
        project, source_root=source, mode="install", host="codex_cli"
    )
    state = _state(project)["project_install"]
    assert result.action == "installed"
    assert state["mode"] == "standalone"
    assert state["active_host"] == "codex_cli"
    assert len(state["canonical_contract_hash"]) == 64
    assert state["managed_files"] == sorted(
        state["managed_files"], key=lambda entry: entry["path"]
    )
    for entry in state["managed_files"]:
        path = entry["path"]
        assert not path.startswith("/") and ".." not in Path(path).parts
        assert len(entry["content_hash"]) == 64


def test_graph_sources_and_edges_fail_before_writes(
    tmp_path: Path,
) -> None:
    for source_value, message in (
        ("skills/missing", "missing standalone dependency source"),
        ("../outside", "escapes canonical skills root"),
    ):
        source = tmp_path / source_value.replace("/", "-").replace("..", "escape")
        project = source / "project"
        _write_source(source)
        graph_path = source / INSTALLER.INSTALL_GRAPH_PATH
        graph = json.loads(graph_path.read_text())
        graph["nodes"]["skill:flow"]["source"] = source_value
        graph_path.write_text(json.dumps(graph))
        project.mkdir()
        with pytest.raises(InstallError, match=message):
            install_project_flow(
                project, source_root=source, mode="install", host="codex_cli"
            )
        assert not (project / ".agents").exists()

    source = tmp_path / "cycle"
    _write_source(source)
    graph_path = source / INSTALLER.INSTALL_GRAPH_PATH
    graph = json.loads(graph_path.read_text())
    graph["nodes"]["skill:other"] = {
        "source": "skills/flow",
        "destination": ".agents/skills/other",
        "dependencies": ["skill:flow"],
    }
    graph["nodes"]["skill:flow"]["dependencies"] = ["skill:other"]
    graph_path.write_text(json.dumps(graph))
    project = source / "project"
    project.mkdir()
    with pytest.raises(InstallError, match="cyclic standalone dependency"):
        install_project_flow(
            project, source_root=source, mode="install", host="codex_cli"
        )
    assert not (project / ".agents").exists()


def test_install_conflicts_and_global_plugin_transition_are_confirmed(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    project = tmp_path / "project"
    _write_source(source)
    collision = project / ".agents" / "skills" / "flow" / "SKILL.md"
    collision.parent.mkdir(parents=True)
    collision.write_text("mine\n")

    with pytest.raises(InstallError, match="unmanaged target collision"):
        install_project_flow(
            project, source_root=source, mode="install", host="codex_cli"
        )
    assert collision.read_text() == "mine\n"

    collision.unlink()
    with pytest.raises(InstallError, match="global Flow plugin"):
        install_project_flow(
            project,
            source_root=source,
            mode="install",
            host="codex_cli",
            global_plugin_detected=True,
        )
    result = install_project_flow(
        project,
        source_root=source,
        mode="install",
        host="codex_cli",
        global_plugin_detected=True,
        confirm_global_plugin=True,
    )
    assert "disable the global Flow plugin" in result.guidance


def test_update_preserves_bounded_customization_and_rejects_stale_hashes(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    project = tmp_path / "project"
    _write_source(source)
    project.mkdir()
    install_project_flow(project, source_root=source, mode="install", host="codex_cli")
    target = project / ".agents" / "skills" / "flow" / "references" / "setup.md"
    target.write_text(
        "before\n<!-- project-customization: start -->\nmy policy\n"
        "<!-- project-customization: end -->\nafter\n"
    )
    canonical = source / "skills" / "flow" / "references" / "setup.md"
    canonical.write_text(
        "new before\n<!-- project-customization: start -->\n"
        "<!-- project-customization: end -->\nnew after\n"
    )
    install_project_flow(project, source_root=source, mode="update", host="codex_cli")
    assert target.read_text() == (
        "new before\n<!-- project-customization: start -->\nmy policy\n"
        "<!-- project-customization: end -->\nnew after\n"
    )
    assert (
        install_project_flow(
            project, source_root=source, mode="update", host="codex_cli"
        ).action
        == "unchanged"
    )

    target.write_text(target.read_text().replace("new after", "unmanaged edit"))
    with pytest.raises(InstallError, match="stale managed hash"):
        install_project_flow(
            project, source_root=source, mode="update", host="codex_cli"
        )
    assert "unmanaged edit" in target.read_text()


def test_install_update_and_uninstall_are_idempotent_and_path_confirmed(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    project = tmp_path / "project"
    _write_source(source)
    project.mkdir()
    first = install_project_flow(
        project, source_root=source, mode="install", host="codex_cli"
    )
    second = install_project_flow(
        project, source_root=source, mode="install", host="codex_cli"
    )
    assert first.action == "installed"
    assert second.action == "unchanged"

    custom = ".agents/skills/flow/references/setup.md"
    target = project / custom
    target.write_text(
        target.read_text().replace(
            "<!-- project-customization: end -->",
            "keep me\n<!-- project-customization: end -->",
        )
    )
    result = install_project_flow(project, source_root=source, mode="uninstall")
    assert result.action == "confirmation_required"
    assert result.confirmation_paths == (custom,)
    assert target.exists()
    assert not (project / ".agents" / "skills" / "flow" / "SKILL.md").exists()

    result = install_project_flow(
        project,
        source_root=source,
        mode="uninstall",
        confirm_customized=(custom,),
    )
    assert result.action == "uninstalled"
    assert not target.exists()
    assert (
        install_project_flow(project, source_root=source, mode="uninstall").action
        == "unchanged"
    )


def test_write_fault_rolls_back_the_entire_install(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source"
    project = tmp_path / "project"
    _write_source(source)
    project.mkdir()
    real_replace = INSTALLER.os.replace
    calls = 0

    def fail_second_replace(source_path: str, target_path: Path) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("injected write fault")
        real_replace(source_path, target_path)

    monkeypatch.setattr(INSTALLER.os, "replace", fail_second_replace)
    with pytest.raises(OSError, match="injected write fault"):
        install_project_flow(
            project, source_root=source, mode="install", host="codex_cli"
        )
    assert not (project / ".agents").exists()


def test_graph_update_fault_restores_files_and_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source"
    project = tmp_path / "project"
    _write_source(source)
    project.mkdir()
    install_project_flow(project, source_root=source, mode="install", host="cursor")
    target = project / ".agents/skills/flow/references/setup.md"
    state_path = project / ".agents/setup-state.json"
    target_before = target.read_bytes()
    state_before = state_path.read_bytes()
    (source / "skills/flow/references/setup.md").write_text("updated\n")
    real_replace = INSTALLER.os.replace
    calls = 0

    def fail_state_replace(source_path: str, target_path: Path) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("injected update fault")
        real_replace(source_path, target_path)

    monkeypatch.setattr(INSTALLER.os, "replace", fail_state_replace)
    with pytest.raises(OSError, match="injected update fault"):
        install_project_flow(project, source_root=source, mode="update", host="cursor")
    assert target.read_bytes() == target_before
    assert state_path.read_bytes() == state_before


def test_graph_uninstall_fault_restores_deleted_files_and_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source"
    project = tmp_path / "project"
    _write_source(source)
    project.mkdir()
    install_project_flow(project, source_root=source, mode="install", host="cursor")
    skill = project / ".agents/skills/flow/SKILL.md"
    reference = project / ".agents/skills/flow/references/setup.md"
    state_path = project / ".agents/setup-state.json"
    state_before = state_path.read_bytes()

    def fail_state_replace(_source_path: str, _target_path: Path) -> None:
        raise OSError("injected uninstall fault")

    monkeypatch.setattr(INSTALLER.os, "replace", fail_state_replace)
    with pytest.raises(OSError, match="injected uninstall fault"):
        install_project_flow(project, source_root=source, mode="uninstall")
    assert skill.is_file()
    assert reference.is_file()
    assert state_path.read_bytes() == state_before


def test_graph_update_removes_only_unchanged_retired_nodes(tmp_path: Path) -> None:
    source = tmp_path / "source"
    project = tmp_path / "project"
    _write_source(source)
    extra = source / "skills/extra/SKILL.md"
    extra.parent.mkdir(parents=True)
    extra.write_text("generated\n")
    graph_path = source / INSTALLER.INSTALL_GRAPH_PATH
    graph = json.loads(graph_path.read_text())
    graph["nodes"]["skill:extra"] = {
        "source": "skills/extra",
        "destination": ".agents/skills/extra",
        "dependencies": [],
    }
    graph["nodes"]["skill:flow"]["dependencies"] = ["skill:extra"]
    graph_path.write_text(json.dumps(graph))
    project.mkdir()
    install_project_flow(project, source_root=source, mode="install", host="cursor")
    installed_extra = project / ".agents/skills/extra/SKILL.md"
    assert installed_extra.is_file()

    graph["nodes"]["skill:flow"]["dependencies"] = []
    del graph["nodes"]["skill:extra"]
    graph_path.write_text(json.dumps(graph))
    result = install_project_flow(
        project, source_root=source, mode="update", host="cursor"
    )
    assert result.action == "updated"
    assert not installed_extra.exists()


def test_graph_update_refuses_customized_retired_nodes_without_writes(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    project = tmp_path / "project"
    _write_source(source)
    extra = source / "skills/extra/SKILL.md"
    extra.parent.mkdir(parents=True)
    extra.write_text(
        "<!-- project-customization: start -->\n<!-- project-customization: end -->\n"
    )
    graph_path = source / INSTALLER.INSTALL_GRAPH_PATH
    graph = json.loads(graph_path.read_text())
    graph["nodes"]["skill:extra"] = {
        "source": "skills/extra",
        "destination": ".agents/skills/extra",
        "dependencies": [],
    }
    graph["nodes"]["skill:flow"]["dependencies"] = ["skill:extra"]
    graph_path.write_text(json.dumps(graph))
    project.mkdir()
    install_project_flow(project, source_root=source, mode="install", host="cursor")
    installed_extra = project / ".agents/skills/extra/SKILL.md"
    installed_extra.write_text(
        "<!-- project-customization: start -->\nkeep\n"
        "<!-- project-customization: end -->\n"
    )
    state_before = (project / ".agents/setup-state.json").read_bytes()

    graph["nodes"]["skill:flow"]["dependencies"] = []
    del graph["nodes"]["skill:extra"]
    graph_path.write_text(json.dumps(graph))
    with pytest.raises(InstallError, match="requires uninstall confirmation"):
        install_project_flow(project, source_root=source, mode="update", host="cursor")
    assert "keep" in installed_extra.read_text()
    assert (project / ".agents/setup-state.json").read_bytes() == state_before


def test_install_refuses_a_symlinked_managed_parent_without_writes(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    project = tmp_path / "project"
    external = tmp_path / "external"
    _write_source(source)
    project.mkdir()
    external.mkdir()
    (project / ".agents").symlink_to(external, target_is_directory=True)

    with pytest.raises(InstallError, match="symlinked managed path refused"):
        install_project_flow(
            project, source_root=source, mode="install", host="cursor"
        )

    assert list(external.iterdir()) == []


@pytest.mark.parametrize("mode", ["update", "uninstall"])
@pytest.mark.parametrize("link_kind", ["file", "parent"])
def test_lifecycle_refuses_managed_symlinks_without_writes(
    tmp_path: Path, mode: str, link_kind: str
) -> None:
    source = tmp_path / "source"
    project = tmp_path / "project"
    external = tmp_path / "external-skill.md"
    _write_source(source)
    project.mkdir()
    install_project_flow(project, source_root=source, mode="install", host="cursor")
    target = project / ".agents/skills/flow/SKILL.md"
    if link_kind == "file":
        external.write_bytes(target.read_bytes())
        target.unlink()
        target.symlink_to(external)
        linked_path = target
    else:
        external = tmp_path / "external-flow"
        target.parent.rename(external)
        target.parent.symlink_to(external, target_is_directory=True)
        linked_path = target.parent
    external_file = external if external.is_file() else external / "SKILL.md"
    state = (project / ".agents/setup-state.json").read_bytes()
    external_before = external_file.read_bytes()

    with pytest.raises(InstallError, match="symlinked managed path refused"):
        install_project_flow(project, source_root=source, mode=mode, host="cursor")

    assert linked_path.is_symlink()
    assert external_file.read_bytes() == external_before
    assert (project / ".agents/setup-state.json").read_bytes() == state


def test_retired_node_cleanup_refuses_a_symlink_without_writes(tmp_path: Path) -> None:
    source = tmp_path / "source"
    project = tmp_path / "project"
    _write_source(source)
    extra = source / "skills/extra/SKILL.md"
    extra.parent.mkdir(parents=True)
    extra.write_text("generated\n")
    graph_path = source / INSTALLER.INSTALL_GRAPH_PATH
    graph = json.loads(graph_path.read_text())
    graph["nodes"]["skill:extra"] = {
        "source": "skills/extra",
        "destination": ".agents/skills/extra",
        "dependencies": [],
    }
    graph["nodes"]["skill:flow"]["dependencies"] = ["skill:extra"]
    graph_path.write_text(json.dumps(graph))
    project.mkdir()
    install_project_flow(project, source_root=source, mode="install", host="cursor")
    target = project / ".agents/skills/extra/SKILL.md"
    external = tmp_path / "external-extra.md"
    external.write_bytes(target.read_bytes())
    target.unlink()
    target.symlink_to(external)
    state = (project / ".agents/setup-state.json").read_bytes()
    graph["nodes"]["skill:flow"]["dependencies"] = []
    del graph["nodes"]["skill:extra"]
    graph_path.write_text(json.dumps(graph))

    with pytest.raises(InstallError, match="symlinked managed path refused"):
        install_project_flow(project, source_root=source, mode="update", host="cursor")

    assert target.is_symlink()
    assert external.read_text() == "generated\n"
    assert (project / ".agents/setup-state.json").read_bytes() == state

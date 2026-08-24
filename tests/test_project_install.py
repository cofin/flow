from __future__ import annotations

import hashlib
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


def test_dependency_closure_fails_before_writes_for_invalid_links(
    tmp_path: Path,
) -> None:
    for invalid, message in (
        ("[missing](references/missing.md)\n", "missing dependency"),
        ("[escape](../../../outside.md)\n", "escapes canonical skills root"),
    ):
        source = tmp_path / hashlib.sha256(invalid.encode()).hexdigest()
        project = source / "project"
        (source / "skills" / "flow").mkdir(parents=True)
        (source / "skills" / "flow" / "SKILL.md").write_text(invalid)
        project.mkdir()
        with pytest.raises(InstallError, match=message):
            install_project_flow(
                project, source_root=source, mode="install", host="codex_cli"
            )
        assert not (project / ".agents").exists()

    source = tmp_path / "cycle"
    project = source / "project"
    (source / "skills" / "flow").mkdir(parents=True)
    (source / "skills" / "flow" / "SKILL.md").write_text("[a](a.md)\n")
    (source / "skills" / "flow" / "a.md").write_text("[root](SKILL.md)\n")
    project.mkdir()
    with pytest.raises(InstallError, match="cyclic dependency"):
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

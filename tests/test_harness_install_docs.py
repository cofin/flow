from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PUBLIC_DOCS = (
    "README.md",
    "AGENTS.md",
    "docs/antigravity.md",
    "docs/harness-conformance-matrix.md",
    "docs/multi-harness-plugin-patterns.md",
    ".codex/INSTALL.md",
    ".opencode/INSTALL.md",
)


def test_legacy_cli_files_are_removed_from_shipped_repo() -> None:
    for relative_path in ("GEMINI.md", "gemini-extension.json", ".geminiignore"):
        assert not (REPO_ROOT / relative_path).exists()


def test_multi_harness_installer_is_removed_from_shipped_repo() -> None:
    assert not (REPO_ROOT / "tools" / "install.sh").exists()


def test_public_install_docs_do_not_advertise_legacy_or_manual_clone_symlink_installs() -> None:
    forbidden = (
        "Gemini CLI",
        "gemini extensions",
        "gemini-extension.json",
        "GEMINI.md",
        "tools/install.sh",
        "ln -sf",
        "git clone https://github.com/cofin/flow",
    )

    for relative_path in PUBLIC_DOCS:
        text = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in text, f"{relative_path} still advertises {token!r}"



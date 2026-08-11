from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

def test_flow_archive_is_beads_free_and_uses_okf_paths() -> None:
    target_files = [
        "commands/flow-archive.md",
        "commands/flow/archive.toml",
        "skills/flow/references/archive.md",
        "templates/opencode/commands/flow-archive.md",
    ]
    for rel_path in target_files:
        file_path = REPO_ROOT / rel_path
        assert file_path.is_file(), f"{rel_path} does not exist"
        text = file_path.read_text(encoding="utf-8")
        
        # Assert Beads-free
        assert "bd " not in text.lower(), f"Beads command found in {rel_path}"
        assert "beads" not in text.lower(), f"Beads reference found in {rel_path}"
        
        # Assert old layout path references are removed
        assert ".agents/specs/" not in text, f"Old spec path found in {rel_path}"
        assert ".agents/patterns.md" not in text, f"Old patterns path found in {rel_path}"
        assert ".agents/knowledge/" not in text, f"Old knowledge path found in {rel_path}"
        assert ".agents/flows.md" not in text, f"Old flows registry found in {rel_path}"
        assert ".agents/archive/" not in text, f"Old archive directory found in {rel_path}"
        
        # Assert new layout paths are referenced
        assert ".agents/bundles/specs/" in text or ".agents/bundles/knowledge/" in text

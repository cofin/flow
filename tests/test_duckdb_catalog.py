"""Public-seam tests for the derived DuckDB knowledge catalog and hybrid retrieval."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from tools.catalog.embedder import (
    DeterministicHashEmbedder,
    EmbeddingGemmaProvider,
    NullEmbeddingProvider,
    truncate_and_normalize,
)
from tools.catalog.models import CatalogSearchHit
from tools.catalog.service import CatalogService


def _seed_okf_workspace(workspace_root: Path, *, repo_name: str = "acme-platform") -> Path:
    """Create a multi-document OKF v0.2 workspace with real source citations and links."""
    ws = workspace_root / repo_name
    bundles = ws / ".agents" / "bundles"
    patterns_dir = bundles / "knowledge" / "patterns"
    decisions_dir = bundles / "knowledge" / "decisions"
    spec_ch_dir = bundles / "specs" / "multi-tenant-isolation" / "chapters" / "ch02-session-guard"
    src_db = ws / "src" / "db"

    patterns_dir.mkdir(parents=True)
    decisions_dir.mkdir(parents=True)
    spec_ch_dir.mkdir(parents=True)
    src_db.mkdir(parents=True)

    (src_db / "pool.py").write_text(
        "class ConnectionPool:\n    def checkout(self) -> None: ...\n    def release(self) -> None: ...\n",
        encoding="utf-8",
    )
    (ws / ".agents" / "setup-state.json").write_text(
        '{"setup_status": "complete", "bundle_root": ".agents/bundles", "okf_version": "0.2"}\n',
        encoding="utf-8",
    )
    (bundles / "index.md").write_text(
        '---\nokf_version: "0.2"\nbundle: acme-platform\n---\n\n# Acme Bundle\n',
        encoding="utf-8",
    )
    (patterns_dir / "pool-reset.md").write_text(
        "---\n"
        "type: Pattern\n"
        "title: Connection Pool Reset Invariants\n"
        "description: Guarantees clean session state before returning pooled connections.\n"
        "status: stable\n"
        "tags: [database, connection-pool, tenancy]\n"
        "verified:\n"
        "  - by: human:cofin\n"
        "    at: 2026-11-07\n"
        "sources:\n"
        "  - id: pool-checkout\n"
        "    resource: src/db/pool.py::ConnectionPool.checkout\n"
        "    title: Pool checkout\n"
        "  - id: pool-release\n"
        "    resource: src/db/pool.py::ConnectionPool.release\n"
        "    title: Pool release\n"
        "---\n\n"
        "<!-- truth: start -->\n"
        "- Bind tenant context via `SET LOCAL app.current_tenant` inside active transactions[^pool-checkout].\n"
        "- Execute `RESET ALL` before returning session-pinned connections to the pool[^pool-release].\n"
        "<!-- truth: end -->\n\n"
        "See [ADR-004](../decisions/adr-004-tenant-gucs.md) for transaction-scoped GUC rationale.\n\n"
        "[^pool-checkout]: src/db/pool.py::ConnectionPool.checkout\n"
        "[^pool-release]: src/db/pool.py::ConnectionPool.release\n",
        encoding="utf-8",
    )
    (decisions_dir / "adr-004-tenant-gucs.md").write_text(
        "---\n"
        "type: Decision\n"
        "title: ADR-004 Transaction-Scoped Tenant GUCs\n"
        "description: Uses SET LOCAL inside transaction blocks for PgBouncer compatibility.\n"
        "status: stable\n"
        "tags: [postgres, pgbouncer, tenancy]\n"
        "verified:\n"
        "  - by: agent:code-reviewer\n"
        "    at: 2026-11-07\n"
        "sources:\n"
        "  - id: missing-ref\n"
        "    resource: src/db/deleted_module.py::legacy_hook\n"
        "    title: Deleted hook\n"
        "---\n\n"
        "<!-- truth: start -->\n"
        "- Never issue session-level `SET app.current_tenant` on transaction-pooled connections[^missing-ref].\n"
        "<!-- truth: end -->\n\n"
        "Broken reference to [missing doc](../patterns/nonexistent.md).\n\n"
        "[^missing-ref]: src/db/deleted_module.py::legacy_hook\n",
        encoding="utf-8",
    )
    (bundles / "specs" / "multi-tenant-isolation" / "spec.md").write_text(
        "---\n"
        "type: Spec\n"
        "flow_id: multi-tenant-isolation\n"
        "title: Multi-Tenant Session Isolation\n"
        "description: Enforces tenant isolation across pooled database sessions.\n"
        "status: draft\n"
        "state: active\n"
        "has_chapters: true\n"
        "current_chapter: ch02-session-guard\n"
        "---\n\n"
        "References [Connection Pool Reset Invariants](../../knowledge/patterns/pool-reset.md).\n",
        encoding="utf-8",
    )
    (spec_ch_dir / "spec.md").write_text(
        "---\n"
        "type: Spec\n"
        "chapter_id: ch02-session-guard\n"
        "title: Chapter 02 Session Guard\n"
        "description: ASGI middleware binding tenant context.\n"
        "status: draft\n"
        "state: active\n"
        "---\n\n"
        "Applies [pool-reset](../../../../knowledge/patterns/pool-reset.md).\n",
        encoding="utf-8",
    )
    return ws


@pytest.mark.parametrize("target_dim", [128, 256, 512])
def test_matryoshka_truncate_and_l2_renormalize(target_dim: int) -> None:
    """Verify Matryoshka dimension truncation re-normalizes vectors to unit L2 length."""
    raw_vector = [float(i + 1) for i in range(768)]
    truncated = truncate_and_normalize(raw_vector, target_dim)
    assert len(truncated) == target_dim
    norm_sq = sum(val * val for val in truncated)
    assert norm_sq == pytest.approx(1.0, rel=1e-5)


def test_embedding_gemma_prompt_formatting() -> None:
    """Verify EmbeddingGemma applies canonical query and title-aware document task prefixes."""
    assert (
        EmbeddingGemmaProvider.format_query("connection pool leak")
        == "task: search result | query: connection pool leak"
    )
    assert (
        EmbeddingGemmaProvider.format_document("Pool Reset", "Execute RESET ALL.")
        == "title: Pool Reset | text: Execute RESET ALL."
    )
    assert EmbeddingGemmaProvider.format_document("", "Body only.") == "title: none | text: Body only."


@pytest.mark.parametrize("mode", ["bm25", "semantic", "hybrid"])
def test_catalog_service_search_modes_and_caching(tmp_path: Path, mode: str) -> None:
    """Verify BM25, semantic vector, and hybrid RRF retrieval plus SHA-256 embedding cache reuse."""
    ws = _seed_okf_workspace(tmp_path)
    db_path = tmp_path / "catalog.duckdb"
    embedder = DeterministicHashEmbedder(dimensions=256)
    service = CatalogService(db_path=db_path, embedder=embedder)

    first_stats = service.index_workspaces([ws])
    assert first_stats.entries_indexed == 4
    first_embed_calls = embedder.embed_calls
    assert first_embed_calls > 0

    second_stats = service.index_workspaces([ws])
    assert second_stats.entries_unchanged == 4
    assert embedder.embed_calls == first_embed_calls

    hits: list[CatalogSearchHit] = service.search("connection pool reset session", mode=mode, limit=5)
    assert len(hits) >= 1
    top_ids = [hit.concept_id for hit in hits]
    assert "knowledge/patterns/pool-reset" in top_ids

    pool_hit = next(hit for hit in hits if hit.concept_id == "knowledge/patterns/pool-reset")
    assert pool_hit.trust_tier == "human-reviewed"
    assert pool_hit.truth_block is not None
    assert "RESET ALL" in pool_hit.truth_block


def test_catalog_reverse_provenance_graph_and_drift_checks(tmp_path: Path) -> None:
    """Verify reverse code-citation lookup, inbound graph edges, read-only serving, and drift detection."""
    ws = _seed_okf_workspace(tmp_path)
    db_path = tmp_path / "catalog.duckdb"
    service = CatalogService(db_path=db_path, embedder=NullEmbeddingProvider())
    service.index_workspaces([ws])

    provenance_hits = service.find_provenance("src/db/pool.py")
    assert len(provenance_hits) == 1
    assert provenance_hits[0].concept_id == "knowledge/patterns/pool-reset"
    assert provenance_hits[0].truth_block is not None

    detail = service.get_entry_detail(provenance_hits[0].entry_id)
    assert detail is not None
    assert len(detail.sources) == 2
    assert all(src.resource_exists for src in detail.sources)
    inbound_concepts = {edge.from_entry_id.split(":", 1)[1] for edge in detail.referenced_by}
    assert "specs/multi-tenant-isolation/spec" in inbound_concepts

    drift = service.check_drift()
    assert len(drift.broken_links) == 1
    assert drift.broken_links[0].target == "../patterns/nonexistent.md"
    assert len(drift.missing_sources) == 1
    assert drift.missing_sources[0].target == "src/db/deleted_module.py::legacy_hook"


def test_catalog_cli_json_and_stdio_server(tmp_path: Path) -> None:
    """Verify the flow-catalog CLI supports one-shot JSON commands and persistent serve-stdio RPC."""
    ws = _seed_okf_workspace(tmp_path)
    db_path = tmp_path / "cli-catalog.duckdb"

    idx_proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "tools.catalog.cli",
            "--db",
            str(db_path),
            "--embedder",
            "deterministic",
            "index",
            str(ws),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    assert '"entries_indexed":4' in idx_proc.stdout.replace(" ", "")

    rpc_input = (
        '{"id": 1, "method": "search", "params": {"query": "PgBouncer SET LOCAL", "mode": "hybrid"}}\n'
        '{"id": 2, "method": "provenance", "params": {"file_path": "src/db/pool.py"}}\n'
    )
    stdio_proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "tools.catalog.cli",
            "--db",
            str(db_path),
            "--embedder",
            "deterministic",
            "serve-stdio",
        ],
        input=rpc_input,
        capture_output=True,
        text=True,
        check=True,
    )
    lines = [ln for ln in stdio_proc.stdout.strip().splitlines() if ln.strip()]
    assert len(lines) == 2
    assert '"id":1' in lines[0].replace(" ", "")
    assert "adr-004-tenant-gucs" in lines[0]
    assert '"id":2' in lines[1].replace(" ", "")
    assert "pool-reset" in lines[1]


def test_catalog_supports_kcmd_bundle_exclusions_and_extra_parent_links(tmp_path: Path) -> None:
    """``CatalogService`` indexes ``bundle/`` layouts, enforces exclusions, and links ``extra.resource.parent``."""
    ws = tmp_path / "kcmd-repo"
    bundle = ws / "bundle"
    (bundle / "documents").mkdir(parents=True)
    (bundle / "agents").mkdir(parents=True)
    (bundle / "private").mkdir(parents=True)
    (bundle / "noexport").mkdir(parents=True)
    (bundle / "noexport" / ".kc-no-export").write_text("", encoding="utf-8")

    (ws / "catalog.yaml").write_text(
        "scope: kb.team-proj.us-central1.ctx\nlayout: okf\ncatalog_exclude:\n  - bundle/private/**\n",
        encoding="utf-8",
    )
    (bundle / "index.md").write_text("---\nokf_version: '0.2'\n---\n\n# Root\n", encoding="utf-8")
    (bundle / "agents" / "guide.md").write_text(
        "---\ntype: ContextSet\ntitle: Root Guide\ndescription: Agent entry point.\n---\n\n# Root Guide\n",
        encoding="utf-8",
    )
    (bundle / "documents" / "spanner.md").write_text(
        "---\n"
        "type: Knowledge\n"
        "title: Spanner Schema Guide\n"
        "description: Spanner table sharding guidance.\n"
        "extra:\n"
        "  resource:\n"
        "    parent: projects/team-proj/locations/us-central1/entryGroups/ctx/entries/agents/guide\n"
        "---\n\n# Spanner Schema Guide\n\nAvoid hotspot keys.\n",
        encoding="utf-8",
    )
    (bundle / "documents" / "unpublished.md").write_text(
        "---\ntype: Knowledge\ntitle: Hidden\ndescription: Excluded.\ncatalog_publish: false\n---\n\nSecret.\n",
        encoding="utf-8",
    )
    (bundle / "private" / "glob_skip.md").write_text(
        "---\ntype: Knowledge\ntitle: Private\ndescription: Glob skipped.\n---\n\nHidden.\n",
        encoding="utf-8",
    )
    (bundle / "noexport" / "marker_skip.md").write_text(
        "---\ntype: Knowledge\ntitle: Marker Skip\ndescription: Marker skipped.\n---\n\nHidden.\n",
        encoding="utf-8",
    )

    db_path = tmp_path / "kcmd.duckdb"
    service = CatalogService(db_path=db_path, embedder=NullEmbeddingProvider())
    stats = service.index_workspaces([ws])
    assert stats.workspaces_indexed == 1
    assert stats.entries_indexed == 2

    hits = service.search("hotspot keys", mode="bm25")
    assert len(hits) == 1
    assert hits[0].concept_id == "documents/spanner"

    detail = service.get_entry_detail(hits[0].entry_id)
    assert detail is not None
    assert any(
        edge.edge_kind == "parent" and edge.to_entry_id and edge.to_entry_id.endswith(":agents/guide")
        for edge in detail.outbound_links
    )

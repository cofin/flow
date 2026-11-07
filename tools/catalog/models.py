"""Domain value models for the derived local DuckDB knowledge catalog."""

from __future__ import annotations

import msgspec

__all__ = (
    "CatalogDriftIssue",
    "CatalogDriftReport",
    "CatalogEntry",
    "CatalogEntryDetail",
    "CatalogFacetBucket",
    "CatalogFacets",
    "CatalogIndexStats",
    "CatalogLinkEdge",
    "CatalogSearchHit",
    "CatalogSourceRef",
    "CatalogStatus",
    "CatalogWorkspace",
)


class CatalogWorkspace(msgspec.Struct, frozen=True, gc=False):
    """Indexed repository workspace metadata."""

    workspace_id: str
    repo_name: str
    root_path: str
    bundle_root: str
    okf_version: str
    indexed_at: str


class CatalogSourceRef(msgspec.Struct, frozen=True, gc=False):
    """Primary-source code or document citation attached to a catalog entry."""

    entry_id: str
    source_id: str
    resource: str
    file_path: str | None = None
    symbol_name: str | None = None
    title: str | None = None
    resource_exists: bool = True


class CatalogLinkEdge(msgspec.Struct, frozen=True, gc=False):
    """Directed link edge between two OKF concepts or spec artifacts."""

    from_entry_id: str
    to_target: str
    to_entry_id: str | None = None
    edge_kind: str = "reference"
    target_exists: bool = True


class CatalogEntry(msgspec.Struct, frozen=True, gc=False):
    """Normalized OKF bundle or specification entry stored in DuckDB."""

    entry_id: str
    workspace_id: str
    rel_path: str
    concept_id: str
    concept_type: str
    title: str
    description: str
    status: str
    state: str | None
    trust_tier: str
    verified_by: str | None
    verified_at: str | None
    tags: tuple[str, ...]
    truth_block: str | None
    body_markdown: str
    frontmatter_json: str
    content_sha256: str
    mtime_ms: int
    file_size: int


class CatalogSearchHit(msgspec.Struct, frozen=True, gc=False):
    """Ranked search or reverse-provenance hit projected from DuckDB."""

    entry_id: str
    workspace_id: str
    rel_path: str
    concept_id: str
    concept_type: str
    title: str
    description: str
    trust_tier: str
    truth_block: str | None = None
    status: str = "draft"
    state: str | None = None
    bm25_score: float | None = None
    semantic_score: float | None = None
    rrf_score: float = 0.0


class CatalogEntryDetail(msgspec.Struct, frozen=True, gc=False):
    """Complete catalog entry payload with outbound citations and inbound references."""

    entry: CatalogEntry
    sources: tuple[CatalogSourceRef, ...]
    outbound_links: tuple[CatalogLinkEdge, ...]
    referenced_by: tuple[CatalogLinkEdge, ...]


class CatalogFacetBucket(msgspec.Struct, frozen=True, gc=False):
    """Count bucket for a catalog filter dimension."""

    value: str
    count: int


class CatalogFacets(msgspec.Struct, frozen=True, gc=False):
    """Aggregated facet counts across indexed workspaces, concept types, and trust tiers."""

    workspaces: tuple[CatalogFacetBucket, ...]
    concept_types: tuple[CatalogFacetBucket, ...]
    trust_tiers: tuple[CatalogFacetBucket, ...]


class CatalogDriftIssue(msgspec.Struct, frozen=True, gc=False):
    """Single broken cross-concept link or missing source-code citation."""

    entry_id: str
    workspace_id: str
    rel_path: str
    title: str
    issue_kind: str
    target: str


class CatalogDriftReport(msgspec.Struct, frozen=True, gc=False):
    """Drift verification summary across all indexed OKF entries."""

    broken_links: tuple[CatalogDriftIssue, ...]
    missing_sources: tuple[CatalogDriftIssue, ...]


class CatalogIndexStats(msgspec.Struct, frozen=True, gc=False):
    """Incremental synchronization summary emitted after indexing workspaces."""

    workspaces_indexed: int
    entries_indexed: int
    entries_unchanged: int
    entries_removed: int
    embeddings_computed: int
    embeddings_reused: int
    embedder_model: str
    embedding_dim: int
    fts_enabled: bool
    vss_enabled: bool


class CatalogStatus(msgspec.Struct, frozen=True, gc=False):
    """Health and capability summary for the local DuckDB catalog."""

    db_path: str
    exists: bool
    workspace_count: int
    entry_count: int
    embedding_count: int
    embedder_model: str
    embedding_dim: int
    fts_enabled: bool
    vss_enabled: bool

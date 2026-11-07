"""Derived local DuckDB knowledge catalog built with SQLSpec and EmbeddingGemma."""

from __future__ import annotations

from tools.catalog.embedder import (
    DEFAULT_EMBEDDING_DIMENSIONS,
    DEFAULT_GEMMA_MODEL,
    DeterministicHashEmbedder,
    EmbeddingGemmaProvider,
    EmbeddingProvider,
    FastEmbedProvider,
    NullEmbeddingProvider,
    resolve_embedding_provider,
    truncate_and_normalize,
)
from tools.catalog.models import (
    CatalogDriftIssue,
    CatalogDriftReport,
    CatalogEntry,
    CatalogEntryDetail,
    CatalogFacetBucket,
    CatalogFacets,
    CatalogIndexStats,
    CatalogLinkEdge,
    CatalogSearchHit,
    CatalogSourceRef,
    CatalogStatus,
    CatalogWorkspace,
)
from tools.catalog.service import CatalogService, OkfMarkdownDocument, OkfMarkdownParser, default_catalog_db_path

__all__ = (
    "DEFAULT_EMBEDDING_DIMENSIONS",
    "DEFAULT_GEMMA_MODEL",
    "CatalogDriftIssue",
    "CatalogDriftReport",
    "CatalogEntry",
    "CatalogEntryDetail",
    "CatalogFacetBucket",
    "CatalogFacets",
    "CatalogIndexStats",
    "CatalogLinkEdge",
    "CatalogSearchHit",
    "CatalogService",
    "CatalogSourceRef",
    "CatalogStatus",
    "CatalogWorkspace",
    "DeterministicHashEmbedder",
    "EmbeddingGemmaProvider",
    "EmbeddingProvider",
    "FastEmbedProvider",
    "NullEmbeddingProvider",
    "OkfMarkdownDocument",
    "OkfMarkdownParser",
    "default_catalog_db_path",
    "resolve_embedding_provider",
    "truncate_and_normalize",
)

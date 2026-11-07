"""Embedding provider abstractions and EmbeddingGemma-300m ONNX integration."""

from __future__ import annotations

import hashlib
import importlib
import math
import os
import re
from collections.abc import Sequence
from typing import Any, Protocol, runtime_checkable

__all__ = (
    "DEFAULT_EMBEDDING_DIMENSIONS",
    "DEFAULT_GEMMA_MODEL",
    "DeterministicHashEmbedder",
    "EmbeddingGemmaProvider",
    "EmbeddingProvider",
    "FastEmbedProvider",
    "NullEmbeddingProvider",
    "resolve_embedding_provider",
    "truncate_and_normalize",
)

DEFAULT_GEMMA_MODEL = "google/embeddinggemma-300m"
DEFAULT_EMBEDDING_DIMENSIONS = 256
_TOKEN_RE = re.compile(r"[a-z0-9_]{2,}")


@runtime_checkable
class EmbeddingProvider(Protocol):
    """Protocol implemented by local and test-time text embedding backends."""

    @property
    def model_name(self) -> str:
        """Return the canonical model identifier recorded in DuckDB."""
        ...

    @property
    def dimensions(self) -> int:
        """Return the output vector width stored in ``FLOAT[D]`` columns."""
        ...

    @property
    def enabled(self) -> bool:
        """Return True when semantic vector indexing and search are active."""
        ...

    def embed_documents(self, items: Sequence[tuple[str, str]]) -> list[list[float]]:
        """Embed ``(title, text)`` document pairs into L2-normalized vectors."""
        ...

    def embed_query(self, query: str) -> list[float]:
        """Embed a search query into an L2-normalized vector."""
        ...


def truncate_and_normalize(vector: Sequence[float], target_dim: int) -> list[float]:
    """Slice a Matryoshka embedding to ``target_dim`` and re-normalize to unit L2 length."""
    if target_dim <= 0:
        msg = f"target_dim must be positive, got {target_dim}"
        raise ValueError(msg)
    sliced = [float(val) for val in vector[:target_dim]]
    if len(sliced) < target_dim:
        sliced.extend(0.0 for _ in range(target_dim - len(sliced)))
    norm = math.sqrt(sum(val * val for val in sliced))
    if norm <= 1e-12:
        return sliced
    return [val / norm for val in sliced]


class NullEmbeddingProvider:
    """No-op embedder used when semantic vector indexing is disabled."""

    def __init__(self, dimensions: int = DEFAULT_EMBEDDING_DIMENSIONS) -> None:
        self._dimensions = dimensions

    @property
    def model_name(self) -> str:
        """Return sentinel model identifier for disabled embeddings."""
        return "none"

    @property
    def dimensions(self) -> int:
        """Return configured vector column width."""
        return self._dimensions

    @property
    def enabled(self) -> bool:
        """Return False so callers skip vector computation."""
        return False

    def embed_documents(self, items: Sequence[tuple[str, str]]) -> list[list[float]]:
        """Return an empty vector batch when embeddings are disabled."""
        _ = items
        return []

    def embed_query(self, query: str) -> list[float]:
        """Return a zero vector when embeddings are disabled."""
        _ = query
        return [0.0] * self._dimensions


class DeterministicHashEmbedder:
    """Hermetic feature-hashing embedder for offline tests and air-gapped environments."""

    def __init__(self, dimensions: int = DEFAULT_EMBEDDING_DIMENSIONS) -> None:
        self._dimensions = dimensions
        self.embed_calls = 0

    @property
    def model_name(self) -> str:
        """Return deterministic hash model identifier."""
        return f"deterministic-hash-{self._dimensions}"

    @property
    def dimensions(self) -> int:
        """Return hash projection vector width."""
        return self._dimensions

    @property
    def enabled(self) -> bool:
        """Return True because hash vectors support cosine retrieval."""
        return True

    def embed_documents(self, items: Sequence[tuple[str, str]]) -> list[list[float]]:
        """Project ``(title, text)`` pairs into signed L2-normalized token hash vectors."""
        self.embed_calls += len(items)
        return [self._hash_text(f"{title} {title} {body}") for title, body in items]

    def embed_query(self, query: str) -> list[float]:
        """Project ``query`` into the same signed L2-normalized token hash space."""
        return self._hash_text(query)

    def _hash_text(self, text: str) -> list[float]:
        """Compute a signed CountSketch vector over lowercased lexical tokens."""
        vec = [0.0] * self._dimensions
        tokens = _TOKEN_RE.findall(text.lower())
        for token in tokens:
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
            bucket = int.from_bytes(digest[:4], "little") % self._dimensions
            sign = 1.0 if (digest[4] & 1) == 0 else -1.0
            vec[bucket] += sign
        return truncate_and_normalize(vec, self._dimensions)


class EmbeddingGemmaProvider:
    """Local EmbeddingGemma-300m ONNX embedder with asymmetric retrieval prefixes and MRL."""

    QUANTIZED_MODEL_NAME = "google/embeddinggemma-300m-q8"
    NATIVE_DIMENSIONS = 768

    def __init__(
        self,
        *,
        dimensions: int = DEFAULT_EMBEDDING_DIMENSIONS,
        quantized: bool = False,
        cache_dir: str | None = None,
    ) -> None:
        if dimensions not in (128, 256, 512, 768):
            msg = f"EmbeddingGemma Matryoshka dimensions must be one of 128, 256, 512, or 768; got {dimensions}"
            raise ValueError(msg)
        self._dimensions = dimensions
        self._quantized = quantized
        self._cache_dir = cache_dir
        self._model: Any = None

    @property
    def model_name(self) -> str:
        """Return model identifier scoped by quantization variant and MRL dimension."""
        base = self.QUANTIZED_MODEL_NAME if self._quantized else DEFAULT_GEMMA_MODEL
        return f"{base}:mrl-{self._dimensions}"

    @property
    def dimensions(self) -> int:
        """Return configured Matryoshka vector width."""
        return self._dimensions

    @property
    def enabled(self) -> bool:
        """Return True because EmbeddingGemma produces semantic vectors."""
        return True

    @staticmethod
    def format_query(query: str) -> str:
        """Format a retrieval query with EmbeddingGemma's asymmetric search task prefix."""
        cleaned = query.strip()
        return f"task: search result | query: {cleaned}"

    @staticmethod
    def format_document(title: str, text: str) -> str:
        """Format a document with EmbeddingGemma's title-aware retrieval prompt."""
        clean_title = title.strip() or "none"
        return f"title: {clean_title} | text: {text.strip()}"

    def embed_documents(self, items: Sequence[tuple[str, str]]) -> list[list[float]]:
        """Embed ``(title, text)`` documents with title prefixes and MRL normalization."""
        if not items:
            return []
        prompts = [self.format_document(title, body) for title, body in items]
        return self._encode_batch(prompts)

    def embed_query(self, query: str) -> list[float]:
        """Embed ``query`` with the retrieval task prefix and MRL normalization."""
        encoded = self._encode_batch([self.format_query(query)])
        return encoded[0] if encoded else [0.0] * self._dimensions

    def _encode_batch(self, prompts: list[str]) -> list[list[float]]:
        """Run ONNX inference via fastembed and truncate/re-normalize each output vector."""
        model = self._ensure_model()
        raw_vectors = list(model.embed(prompts))
        return [truncate_and_normalize([float(x) for x in vec], self._dimensions) for vec in raw_vectors]

    def _ensure_model(self) -> Any:
        """Lazily initialize the fastembed TextEmbedding session on first vector computation."""
        if self._model is not None:
            return self._model
        fastembed_mod = importlib.import_module("fastembed")
        text_embedding_cls = fastembed_mod.TextEmbedding
        common_types = importlib.import_module("fastembed.common.types")
        pooling_type = common_types.PoolingType

        target_name = DEFAULT_GEMMA_MODEL
        if self._quantized:
            target_name = self.QUANTIZED_MODEL_NAME
            supported = {entry["model"] for entry in text_embedding_cls.list_supported_models()}
            if target_name not in supported:
                text_embedding_cls.add_custom_model(
                    model=target_name,
                    pooling=pooling_type.MEAN,
                    normalization=True,
                    sources={"hf": "onnx-community/embeddinggemma-300m-ONNX"},
                    dim=self.NATIVE_DIMENSIONS,
                    model_file="onnx/model_quantized.onnx",
                    additional_files=["onnx/model_quantized.onnx_data"],
                )
        kwargs: dict[str, Any] = {"model_name": target_name}
        if self._cache_dir:
            kwargs["cache_dir"] = self._cache_dir
        self._model = text_embedding_cls(**kwargs)
        return self._model


class FastEmbedProvider:
    """Generic fastembed ONNX provider for models such as ``BAAI/bge-small-en-v1.5``."""

    def __init__(
        self,
        model_name: str = "BAAI/bge-small-en-v1.5",
        *,
        dimensions: int = 384,
        cache_dir: str | None = None,
    ) -> None:
        self._raw_model_name = model_name
        self._dimensions = dimensions
        self._cache_dir = cache_dir
        self._model: Any = None

    @property
    def model_name(self) -> str:
        """Return configured fastembed model name."""
        return self._raw_model_name

    @property
    def dimensions(self) -> int:
        """Return vector dimensionality."""
        return self._dimensions

    @property
    def enabled(self) -> bool:
        """Return True because fastembed produces dense vectors."""
        return True

    def embed_documents(self, items: Sequence[tuple[str, str]]) -> list[list[float]]:
        """Embed ``(title, text)`` pairs via ``passage_embed``."""
        if not items:
            return []
        model = self._ensure_model()
        texts = [f"{title}\n\n{body}".strip() for title, body in items]
        raw = list(model.passage_embed(texts))
        return [truncate_and_normalize([float(x) for x in vec], self._dimensions) for vec in raw]

    def embed_query(self, query: str) -> list[float]:
        """Embed ``query`` via ``query_embed``."""
        model = self._ensure_model()
        raw = list(model.query_embed([query]))
        if not raw:
            return [0.0] * self._dimensions
        return truncate_and_normalize([float(x) for x in raw[0]], self._dimensions)

    def _ensure_model(self) -> Any:
        """Lazily construct the underlying fastembed TextEmbedding instance."""
        if self._model is not None:
            return self._model
        fastembed_mod = importlib.import_module("fastembed")
        kwargs: dict[str, Any] = {"model_name": self._raw_model_name}
        if self._cache_dir:
            kwargs["cache_dir"] = self._cache_dir
        self._model = fastembed_mod.TextEmbedding(**kwargs)
        return self._model


def resolve_embedding_provider(
    backend: str | None = None,
    *,
    dimensions: int | None = None,
) -> EmbeddingProvider:
    """Resolve an ``EmbeddingProvider`` from CLI flags or ``FLOW_CATALOG_*`` environment variables."""
    chosen = (backend or os.environ.get("FLOW_CATALOG_EMBEDDER") or "gemma").strip().lower()
    raw_dim = dimensions or int(os.environ.get("FLOW_CATALOG_EMBED_DIM", str(DEFAULT_EMBEDDING_DIMENSIONS)))
    cache_dir = os.environ.get("FLOW_CATALOG_MODEL_CACHE")
    quantized = os.environ.get("FLOW_CATALOG_GEMMA_QUANTIZED", "0").strip().lower() in {"1", "true", "yes"}

    if chosen in {"none", "off", "disabled", "bm25"}:
        return NullEmbeddingProvider(dimensions=raw_dim)
    if chosen in {"deterministic", "hash"}:
        return DeterministicHashEmbedder(dimensions=raw_dim)
    if chosen in {"gemma", "embeddinggemma", DEFAULT_GEMMA_MODEL.lower()}:
        return EmbeddingGemmaProvider(dimensions=raw_dim, quantized=quantized, cache_dir=cache_dir)
    if chosen in {"bge", "bge-small", "baai/bge-small-en-v1.5"}:
        bge_dim = dimensions or int(os.environ.get("FLOW_CATALOG_EMBED_DIM", "384"))
        return FastEmbedProvider("BAAI/bge-small-en-v1.5", dimensions=bge_dim, cache_dir=cache_dir)
    return FastEmbedProvider(backend or DEFAULT_GEMMA_MODEL, dimensions=raw_dim, cache_dir=cache_dir)

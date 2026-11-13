"""DuckDB-backed hybrid knowledge catalog service built on SQLSpec."""

from __future__ import annotations

import datetime as dt
import fnmatch
import hashlib
import json
import os
import re
from collections import Counter
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from sqlspec import SQLFileLoader, SQLSpec
from sqlspec.adapters.duckdb import DuckDBConfig
from sqlspec.utils.serializers import to_json

from tools.catalog.embedder import (
    EmbeddingProvider,
    resolve_embedding_provider,
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

__all__ = (
    "CatalogService",
    "OkfMarkdownDocument",
    "OkfMarkdownParser",
    "default_catalog_db_path",
)

_SQL_DIR = Path(__file__).resolve().parent / "sql"
_FRONTMATTER_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n?(.*)\Z", re.DOTALL)
_TRUTH_BLOCK_RE = re.compile(r"<!--\s*truth:\s*start\s*-->\s*(.*?)\s*<!--\s*truth:\s*end\s*-->", re.DOTALL)
_MD_LINK_RE = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
_HEADING_RE = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)
_TOKEN_RE = re.compile(r"[a-z0-9_]{2,}")
_STOPWORDS = frozenset(
    {
        "all",
        "and",
        "are",
        "for",
        "from",
        "has",
        "into",
        "not",
        "only",
        "that",
        "the",
        "their",
        "then",
        "this",
        "use",
        "uses",
        "via",
        "when",
        "with",
    }
)


def default_catalog_db_path() -> Path:
    """Resolve the disposable local DuckDB catalog path from env or user cache directory."""
    override = os.environ.get("FLOW_CATALOG_DB")
    if override:
        return Path(override).expanduser().resolve()
    xdg_cache = os.environ.get("XDG_CACHE_HOME")
    base = Path(xdg_cache).expanduser() if xdg_cache else (Path.home() / ".cache")
    return (base / "flow" / "catalog.duckdb").resolve()


class OkfMarkdownDocument:
    """Parsed representation of a single OKF Markdown concept or specification file."""

    def __init__(
        self,
        *,
        entry: CatalogEntry,
        sources: tuple[CatalogSourceRef, ...],
        links: tuple[CatalogLinkEdge, ...],
        term_counts: dict[str, int],
    ) -> None:
        self.entry = entry
        self.sources = sources
        self.links = links
        self.term_counts = term_counts


class OkfMarkdownParser:
    """Parser for OKF v0.2 YAML frontmatter, truth blocks, citations, and graph edges."""

    @classmethod
    def should_index_file(cls, rel_to_bundle: Path, raw_text: str) -> bool:
        """Determine whether a bundle Markdown file represents a catalogable concept or spec."""
        posix_rel = rel_to_bundle.as_posix()
        if posix_rel in {"index.md", "log.md"}:
            return False
        frontmatter, _ = cls._split_frontmatter(raw_text)
        raw_publish = frontmatter.get("catalog_publish")
        if raw_publish is False or str(raw_publish).strip().lower() == "false":
            return False
        if rel_to_bundle.stem == "index" and "type" not in frontmatter:
            return False
        top_dir = rel_to_bundle.parts[0] if len(rel_to_bundle.parts) > 1 else ""
        return bool(
            top_dir in {"knowledge", "specs", "research", "decisions", "agents", "assets", "documents"}
            or "type" in frontmatter
        )

    @classmethod
    def parse_file(
        cls,
        *,
        workspace_id: str,
        workspace_root: Path,
        bundle_root: Path,
        file_path: Path,
        raw_bytes: bytes,
        mtime_ms: int,
    ) -> OkfMarkdownDocument:
        """Parse ``file_path`` into a ``CatalogEntry``, citations, links, and lexical terms."""
        raw_text = raw_bytes.decode("utf-8", errors="replace")
        content_sha256 = hashlib.sha256(raw_bytes).hexdigest()
        frontmatter, body = cls._split_frontmatter(raw_text)

        rel_to_ws = file_path.relative_to(workspace_root).as_posix()
        rel_to_bundle = file_path.relative_to(bundle_root)
        concept_id = rel_to_bundle.with_suffix("").as_posix()
        entry_id = f"{workspace_id}:{concept_id}"

        concept_type = cls._infer_concept_type(frontmatter, rel_to_bundle)
        title = str(frontmatter.get("title") or cls._extract_heading(body) or file_path.stem)
        description = str(frontmatter.get("description") or "").strip()
        status = str(frontmatter.get("status") or "draft").strip()
        raw_state = frontmatter.get("state")
        state = str(raw_state).strip() if raw_state else None
        trust_tier, verified_by, verified_at = cls._resolve_trust(frontmatter, status)
        tags = cls._normalize_tags(frontmatter.get("tags"))
        truth_block = cls._extract_truth_block(body)

        searchable_text = "\n".join(
            part for part in (title, description, " ".join(tags), truth_block or "", body) if part
        )
        tokens = cls.tokenize(searchable_text)
        term_counts = dict(Counter(tokens))
        doc_len = max(sum(term_counts.values()), 1)

        entry = CatalogEntry(
            entry_id=entry_id,
            workspace_id=workspace_id,
            rel_path=rel_to_ws,
            concept_id=concept_id,
            concept_type=concept_type,
            title=title,
            description=description,
            status=status,
            state=state,
            trust_tier=trust_tier,
            verified_by=verified_by,
            verified_at=verified_at,
            tags=tags,
            truth_block=truth_block,
            body_markdown=body.strip(),
            frontmatter_json=to_json(frontmatter),
            content_sha256=content_sha256,
            mtime_ms=mtime_ms,
            file_size=len(raw_bytes),
        )
        sources = cls._extract_sources(entry_id=entry_id, workspace_root=workspace_root, frontmatter=frontmatter)
        links = cls._extract_links(
            entry_id=entry_id,
            workspace_id=workspace_id,
            bundle_root=bundle_root,
            file_path=file_path,
            body=body,
        )
        _ = doc_len
        return OkfMarkdownDocument(entry=entry, sources=sources, links=links, term_counts=term_counts)

    @staticmethod
    def tokenize(text: str) -> list[str]:
        """Tokenize text into normalized lowercase lexical terms excluding trivial stopwords."""
        return [tok for tok in _TOKEN_RE.findall(text.lower()) if tok not in _STOPWORDS]

    @classmethod
    def _split_frontmatter(cls, raw_text: str) -> tuple[dict[str, Any], str]:
        """Split YAML frontmatter and Markdown body without external YAML dependencies."""
        match = _FRONTMATTER_RE.match(raw_text)
        if not match:
            return {}, raw_text
        yaml_block, body = match.group(1), match.group(2)
        return cls._parse_yaml_subset(yaml_block), body

    @classmethod
    def _parse_yaml_subset(cls, yaml_block: str) -> dict[str, Any]:
        """Parse flat scalars, inline arrays, string lists, and object lists from OKF frontmatter."""
        result: dict[str, Any] = {}
        lines = yaml_block.splitlines()
        idx = 0
        total = len(lines)

        while idx < total:
            line = lines[idx]
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or ":" not in line or line[0].isspace():
                idx += 1
                continue

            key_part, raw_val = line.split(":", 1)
            key = key_part.strip()
            val = raw_val.strip()

            if val:
                result[key] = cls._parse_scalar_or_inline_list(val)
                idx += 1
                continue

            items: list[Any] = []
            idx += 1
            while idx < total:
                sub = lines[idx]
                sub_stripped = sub.strip()
                if not sub_stripped or sub_stripped.startswith("#"):
                    idx += 1
                    continue
                if not sub[0].isspace():
                    break
                if sub_stripped.startswith("- "):
                    remainder = sub_stripped[2:].strip()
                    if ":" in remainder and not remainder.startswith(('"', "'")):
                        obj: dict[str, Any] = {}
                        sub_k, sub_v = remainder.split(":", 1)
                        obj[sub_k.strip()] = cls._parse_scalar_or_inline_list(sub_v.strip())
                        item_indent = len(sub) - len(sub.lstrip())
                        idx += 1
                        while idx < total:
                            nested = lines[idx]
                            nested_stripped = nested.strip()
                            if not nested_stripped or nested_stripped.startswith("#"):
                                idx += 1
                                continue
                            nested_indent = len(nested) - len(nested.lstrip())
                            if nested_indent <= item_indent or nested_stripped.startswith("- "):
                                break
                            if ":" in nested_stripped:
                                nk, nv = nested_stripped.split(":", 1)
                                obj[nk.strip()] = cls._parse_scalar_or_inline_list(nv.strip())
                            idx += 1
                        items.append(obj)
                        continue
                    items.append(cls._parse_scalar_or_inline_list(remainder))
                idx += 1
            result[key] = items
        return result

    @staticmethod
    def _parse_scalar_or_inline_list(raw: str) -> Any:
        """Convert a YAML scalar or inline bracketed list into native Python values."""
        if raw.startswith("[") and raw.endswith("]"):
            inner = raw[1:-1].strip()
            if not inner:
                return []
            return [part.strip().strip("\"'") for part in inner.split(",") if part.strip()]
        unquoted = raw.strip("\"'")
        lower = unquoted.lower()
        if lower == "true":
            return True
        if lower == "false":
            return False
        if lower in {"null", "none", "~"}:
            return None
        return unquoted

    @staticmethod
    def _infer_concept_type(frontmatter: dict[str, Any], rel_to_bundle: Path) -> str:
        """Resolve the OKF concept type from frontmatter or directory conventions."""
        declared = frontmatter.get("type")
        if isinstance(declared, str) and declared.strip():
            return declared.strip()
        parts = rel_to_bundle.parts
        if parts and parts[0] == "specs":
            return "Spec"
        if len(parts) >= 2 and parts[1] == "decisions":
            return "Decision"
        if len(parts) >= 2 and parts[1] == "patterns":
            return "Pattern"
        if parts and parts[0] == "research":
            return "Research"
        return "Concept"

    @staticmethod
    def _extract_heading(body: str) -> str | None:
        """Extract the first top-level Markdown heading when frontmatter omits ``title``."""
        match = _HEADING_RE.search(body)
        return match.group(1).strip() if match else None

    @staticmethod
    def _extract_truth_block(body: str) -> str | None:
        """Extract concatenated ``<!-- truth: start -->`` invariants when present."""
        blocks = [m.strip() for m in _TRUTH_BLOCK_RE.findall(body) if m.strip()]
        return "\n".join(blocks) if blocks else None

    @staticmethod
    def _resolve_trust(frontmatter: dict[str, Any], status: str) -> tuple[str, str | None, str | None]:
        """Classify trust tier and primary verifier metadata from OKF ``verified`` records."""
        verified = frontmatter.get("verified")
        if isinstance(verified, list):
            for record in verified:
                if isinstance(record, dict):
                    verifier = str(record.get("by") or "").strip()
                    timestamp = str(record.get("at") or "").strip() or None
                    if verifier.startswith("human:"):
                        return "human-reviewed", verifier, timestamp
            for record in verified:
                if isinstance(record, dict):
                    verifier = str(record.get("by") or "").strip()
                    timestamp = str(record.get("at") or "").strip() or None
                    if verifier.startswith("agent:"):
                        return "agent-verified", verifier, timestamp
        if status.lower() in {"stable", "accepted", "completed"}:
            return "verified", None, None
        return "draft", None, None

    @staticmethod
    def _normalize_tags(raw_tags: Any) -> tuple[str, ...]:
        """Normalize frontmatter tags into an immutable tuple of strings."""
        if isinstance(raw_tags, list):
            return tuple(str(item).strip() for item in raw_tags if str(item).strip())
        if isinstance(raw_tags, str) and raw_tags.strip():
            return tuple(part.strip() for part in raw_tags.split(",") if part.strip())
        return ()

    @staticmethod
    def _extract_sources(
        *,
        entry_id: str,
        workspace_root: Path,
        frontmatter: dict[str, Any],
    ) -> tuple[CatalogSourceRef, ...]:
        """Extract structured primary-source citations and verify local file/symbol existence."""
        raw_sources = frontmatter.get("sources")
        if not isinstance(raw_sources, list):
            return ()
        refs: list[CatalogSourceRef] = []
        seen_ids: set[str] = set()
        for idx, item in enumerate(raw_sources):
            if not isinstance(item, dict):
                continue
            resource = str(item.get("resource") or "").strip()
            if not resource:
                continue
            source_id = str(item.get("id") or f"src-{idx + 1}").strip()
            if source_id in seen_ids:
                source_id = f"{source_id}-{idx + 1}"
            seen_ids.add(source_id)
            title = str(item.get("title") or "").strip() or None

            if resource.startswith(("http://", "https://")):
                refs.append(
                    CatalogSourceRef(
                        entry_id=entry_id,
                        source_id=source_id,
                        resource=resource,
                        file_path=None,
                        symbol_name=None,
                        title=title,
                        resource_exists=True,
                    )
                )
                continue

            if "::" in resource:
                raw_file, symbol_name = resource.split("::", 1)
                clean_file = raw_file.strip().lstrip("./")
                clean_sym: str | None = symbol_name.strip() or None
            else:
                clean_file = resource.strip().lstrip("./")
                clean_sym = None

            candidate = (workspace_root / clean_file).resolve()
            exists = candidate.exists()
            if exists and clean_sym and candidate.is_file():
                leaf_symbol = clean_sym.rsplit(".", 1)[-1]
                file_text = candidate.read_text(encoding="utf-8", errors="ignore")
                exists = leaf_symbol in file_text

            refs.append(
                CatalogSourceRef(
                    entry_id=entry_id,
                    source_id=source_id,
                    resource=resource,
                    file_path=clean_file,
                    symbol_name=clean_sym,
                    title=title,
                    resource_exists=exists,
                )
            )
        return tuple(refs)

    @staticmethod
    def _extract_links(
        *,
        entry_id: str,
        workspace_id: str,
        bundle_root: Path,
        file_path: Path,
        body: str,
    ) -> tuple[CatalogLinkEdge, ...]:
        """Extract outbound Markdown links and resolve relative bundle concept targets."""
        edges: list[CatalogLinkEdge] = []
        seen_targets: set[str] = set()
        bundle_resolved = bundle_root.resolve()

        for raw_target in _MD_LINK_RE.findall(body):
            target = raw_target.strip().split()[0]
            if not target or target.startswith(("#", "http://", "https://", "mailto:", "sidecar://", "file://")):
                continue
            clean_rel = target.split("#", 1)[0]
            if not clean_rel or clean_rel in seen_targets:
                continue
            seen_targets.add(clean_rel)

            resolved = (file_path.parent / clean_rel).resolve()
            target_exists = resolved.exists()
            to_entry_id: str | None = None
            if resolved.suffix.lower() == ".md":
                is_within_bundle = False
                rel_concept = ""
                try:
                    rel_concept_path = resolved.relative_to(bundle_resolved)
                    rel_concept = rel_concept_path.with_suffix("").as_posix()
                    is_within_bundle = True
                except ValueError:
                    is_within_bundle = False
                if is_within_bundle and rel_concept not in {"index", "log"}:
                    to_entry_id = f"{workspace_id}:{rel_concept}"

            edges.append(
                CatalogLinkEdge(
                    from_entry_id=entry_id,
                    to_target=clean_rel,
                    to_entry_id=to_entry_id,
                    edge_kind="reference",
                    target_exists=target_exists,
                )
            )
        return tuple(edges)

    @classmethod
    def parse_catalog_yaml(cls, catalog_path: Path) -> list[str]:
        """Extract ``catalog_exclude`` / ``exclude`` globs from ``catalog.yaml``."""
        if not catalog_path.is_file():
            return []
        raw_text = catalog_path.read_text(encoding="utf-8", errors="ignore")
        parsed = cls._parse_yaml_subset(raw_text)
        raw_excludes = parsed.get("catalog_exclude") if "catalog_exclude" in parsed else parsed.get("exclude")
        if not isinstance(raw_excludes, list):
            return []
        return [str(pat).strip().lstrip("/") for pat in raw_excludes if str(pat).strip()]

    @staticmethod
    def is_kc_excluded(
        md_path: Path,
        bundle_root: Path,
        workspace_root: Path,
        excludes: Sequence[str],
    ) -> bool:
        """Return True when a ``.kc-no-export`` marker or glob excludes ``md_path``."""
        cur = md_path.parent.resolve()
        bundle_res = bundle_root.resolve()
        while True:
            if (cur / ".kc-no-export").exists():
                return True
            if cur == bundle_res or cur.parent == cur:
                break
            cur = cur.parent
        if not excludes:
            return False
        rel_bundle = md_path.relative_to(bundle_root).as_posix()
        rel_ws = (
            md_path.relative_to(workspace_root).as_posix() if md_path.is_relative_to(workspace_root) else rel_bundle
        )
        return any(fnmatch.fnmatch(rel_bundle, pat) or fnmatch.fnmatch(rel_ws, pat) for pat in excludes)

    @classmethod
    def extract_extra_parent(cls, raw_text: str) -> str | None:
        """Read nested ``extra.resource.parent`` from ``kcmd --format okf`` frontmatter."""
        lines = raw_text.splitlines()
        if not lines or lines[0].strip() != "---":
            return None
        yaml_lines: list[str] = []
        for line in lines[1:]:
            if line.strip() in {"---", "..."}:
                break
            yaml_lines.append(line)
        stack: list[tuple[int, str]] = []
        for line in yaml_lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or stripped.startswith("-"):
                continue
            indent = len(line) - len(line.lstrip())
            if ":" not in stripped:
                continue
            key, val = stripped.split(":", 1)
            key = key.strip()
            val = val.strip().strip("\"'")
            while stack and stack[-1][0] >= indent:
                stack.pop()
            if not val:
                stack.append((indent, key))
                continue
            path_keys = [item[1] for item in stack] + [key]
            if path_keys == ["extra", "resource", "parent"] and val:
                return val
        return None

    @staticmethod
    def load_links_yaml(links_path: Path) -> dict[str, list[tuple[str, str]]]:
        """Parse ``kcmd`` ``_links.yaml`` edges mapping source slug/path to ``(target, kind)`` tuples."""
        if not links_path.is_file():
            return {}
        edges_by_source: dict[str, list[tuple[str, str]]] = {}
        current: dict[str, str] = {}

        def _flush() -> None:
            src = current.get("source") or current.get("from") or ""
            tgt = current.get("target") or current.get("to") or ""
            kind = current.get("kind") or current.get("type") or "related"
            if src and tgt:
                edges_by_source.setdefault(src.strip().strip("/"), []).append((tgt.strip().strip("/"), kind.strip()))
            current.clear()

        for raw_line in links_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            stripped = raw_line.strip()
            if not stripped or stripped.startswith("#") or stripped in {"links:", "edges:"}:
                continue
            if stripped.startswith("- "):
                _flush()
                stripped = stripped[2:].strip()
            if ":" in stripped:
                k, v = stripped.split(":", 1)
                current[k.strip()] = v.strip().strip("\"'")
        _flush()
        return edges_by_source

    @staticmethod
    def build_kcmd_edges(
        *,
        entry_id: str,
        concept_id: str,
        workspace_id: str,
        bundle_root: Path,
        raw_text: str,
        links_map: dict[str, list[tuple[str, str]]],
    ) -> tuple[CatalogLinkEdge, ...]:
        """Build ``CatalogLinkEdge`` rows from ``extra.resource.parent`` and ``_links.yaml``."""
        edges: list[CatalogLinkEdge] = []
        extra_parent = OkfMarkdownParser.extract_extra_parent(raw_text)
        candidates: list[tuple[str, str]] = []
        if extra_parent:
            candidates.append((extra_parent, "parent"))
        for key in (concept_id, f"{concept_id}.md"):
            candidates.extend(links_map.get(key, []))

        for raw_target, kind in candidates:
            clean = raw_target.strip()
            if not clean:
                continue
            if "/entries/" in clean:
                entry_slug = clean.split("/entries/", 1)[1].strip("/")
                to_entry = f"{workspace_id}:{entry_slug}" if (bundle_root / f"{entry_slug}.md").is_file() else None
                exists = to_entry is not None
            else:
                target_no_ext = clean[:-3] if clean.endswith(".md") else clean
                candidate_file = bundle_root / f"{target_no_ext}.md"
                exists = candidate_file.is_file()
                to_entry = f"{workspace_id}:{target_no_ext}" if exists else None
            edges.append(
                CatalogLinkEdge(
                    from_entry_id=entry_id,
                    to_target=clean,
                    to_entry_id=to_entry,
                    edge_kind=kind,
                    target_exists=exists,
                )
            )
        return tuple(edges)


class CatalogService:
    """SQLSpec + DuckDB hybrid BM25 and vector knowledge catalog service."""

    def __init__(
        self,
        *,
        db_path: Path | str | None = None,
        embedder: EmbeddingProvider | None = None,
        memory_limit: str = "512MB",
        threads: int = 2,
    ) -> None:
        self._db_path = Path(db_path).expanduser().resolve() if db_path else default_catalog_db_path()
        self._embedder = embedder if embedder is not None else resolve_embedding_provider()
        self._memory_limit = os.environ.get("FLOW_CATALOG_MEMORY_LIMIT", memory_limit)
        self._threads = int(os.environ.get("FLOW_CATALOG_THREADS", str(threads)))
        self._loader = SQLFileLoader()
        self._loader.load_sql(_SQL_DIR / "catalog.sql")
        self._fts_loaded = False
        self._vss_loaded = False

    @property
    def db_path(self) -> Path:
        """Return resolved filesystem path of the local DuckDB catalog file."""
        return self._db_path

    @property
    def embedder(self) -> EmbeddingProvider:
        """Return active ``EmbeddingProvider`` instance."""
        return self._embedder

    def index_workspaces(self, workspace_roots: Sequence[Path | str]) -> CatalogIndexStats:
        """Incrementally synchronize one or more repository ``.agents/bundles`` trees into DuckDB."""
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        db = SQLSpec()
        cfg = self._make_config(read_only=False)
        db.add_config(cfg)

        workspaces_indexed = 0
        entries_indexed = 0
        entries_unchanged = 0
        entries_removed = 0
        embeddings_computed = 0
        embeddings_reused = 0
        fts_enabled = False
        vss_enabled = False

        try:
            with db.provide_session(cfg) as session:
                fts_enabled, vss_enabled = self._probe_extensions(session, allow_install=True)
                self._ensure_schema(session)

                for raw_root in workspace_roots:
                    ws_root = Path(raw_root).expanduser().resolve()
                    bundle_root = self._locate_bundle_root(ws_root)
                    if bundle_root is None:
                        continue

                    workspaces_indexed += 1
                    workspace_id = self._derive_workspace_id(ws_root)
                    okf_version = self._read_okf_version(ws_root, bundle_root)
                    now_iso = dt.datetime.now(dt.UTC).isoformat()

                    ws_model = CatalogWorkspace(
                        workspace_id=workspace_id,
                        repo_name=ws_root.name,
                        root_path=str(ws_root),
                        bundle_root=bundle_root.relative_to(ws_root).as_posix(),
                        okf_version=okf_version,
                        indexed_at=now_iso,
                    )
                    session.execute(
                        "INSERT OR REPLACE INTO workspaces "
                        "(workspace_id, repo_name, root_path, bundle_root, okf_version, indexed_at) "
                        "VALUES (:workspace_id, :repo_name, :root_path, :bundle_root, :okf_version, :indexed_at)",
                        {
                            "workspace_id": ws_model.workspace_id,
                            "repo_name": ws_model.repo_name,
                            "root_path": ws_model.root_path,
                            "bundle_root": ws_model.bundle_root,
                            "okf_version": ws_model.okf_version,
                            "indexed_at": ws_model.indexed_at,
                        },
                    )

                    existing_rows = session.select(
                        self._loader.get_sql("select-workspace-manifest"),
                        {"workspace_id": workspace_id},
                    )
                    existing_by_rel = {str(r["rel_path"]): r for r in existing_rows}
                    seen_rel_paths: set[str] = set()
                    changed_docs: list[OkfMarkdownDocument] = []
                    kc_excludes = [
                        *OkfMarkdownParser.parse_catalog_yaml(ws_root / "catalog.yaml"),
                        *OkfMarkdownParser.parse_catalog_yaml(bundle_root / "catalog.yaml"),
                    ]
                    links_yaml_map = OkfMarkdownParser.load_links_yaml(bundle_root / "_links.yaml")

                    for md_file in sorted(bundle_root.rglob("*.md")):
                        if not md_file.is_file():
                            continue
                        if OkfMarkdownParser.is_kc_excluded(md_file, bundle_root, ws_root, kc_excludes):
                            continue
                        rel_to_bundle = md_file.relative_to(bundle_root)
                        raw_bytes = md_file.read_bytes()
                        raw_text = raw_bytes.decode("utf-8", errors="replace")
                        if not OkfMarkdownParser.should_index_file(rel_to_bundle, raw_text):
                            continue

                        rel_to_ws = md_file.relative_to(ws_root).as_posix()
                        seen_rel_paths.add(rel_to_ws)
                        stat = md_file.stat()
                        mtime_ms = int(stat.st_mtime_ns // 1_000_000)
                        file_size = int(stat.st_size)

                        prior = existing_by_rel.get(rel_to_ws)
                        if (
                            prior is not None
                            and int(prior["mtime_ms"]) == mtime_ms
                            and int(prior["file_size"]) == file_size
                        ):
                            entries_unchanged += 1
                            continue

                        parsed = OkfMarkdownParser.parse_file(
                            workspace_id=workspace_id,
                            workspace_root=ws_root,
                            bundle_root=bundle_root,
                            file_path=md_file,
                            raw_bytes=raw_bytes,
                            mtime_ms=mtime_ms,
                        )
                        extra_edges = OkfMarkdownParser.build_kcmd_edges(
                            entry_id=parsed.entry.entry_id,
                            concept_id=parsed.entry.concept_id,
                            workspace_id=workspace_id,
                            bundle_root=bundle_root,
                            raw_text=raw_text,
                            links_map=links_yaml_map,
                        )
                        if extra_edges:
                            parsed = OkfMarkdownDocument(
                                entry=parsed.entry,
                                sources=parsed.sources,
                                links=(*parsed.links, *extra_edges),
                                term_counts=parsed.term_counts,
                            )
                        if prior is not None and str(prior["content_sha256"]) == parsed.entry.content_sha256:
                            session.execute(
                                "UPDATE entries SET mtime_ms = :mtime_ms, file_size = :file_size "
                                "WHERE entry_id = :entry_id",
                                {
                                    "mtime_ms": mtime_ms,
                                    "file_size": file_size,
                                    "entry_id": parsed.entry.entry_id,
                                },
                            )
                            self._replace_sources_and_links(session, parsed)
                            entries_unchanged += 1
                            continue

                        changed_docs.append(parsed)

                    stale_entry_ids = [
                        str(row["entry_id"])
                        for rel_path, row in existing_by_rel.items()
                        if rel_path not in seen_rel_paths
                    ]
                    for stale_id in stale_entry_ids:
                        self._delete_entry(session, stale_id)
                        entries_removed += 1

                    for doc in changed_docs:
                        self._upsert_document(session, doc)
                        entries_indexed += 1

                    if self._embedder.enabled:
                        comp, reused = self._sync_workspace_embeddings(session, workspace_id)
                        embeddings_computed += comp
                        embeddings_reused += reused

                session.execute(self._loader.get_sql("refresh-corpus-stats"))
                if fts_enabled and (entries_indexed > 0 or entries_removed > 0):
                    fts_enabled = self._rebuild_fts_index(session)
                if vss_enabled and embeddings_computed > 0:
                    self._ensure_hnsw_index(session)
        finally:
            cfg.close_pool()

        self._fts_loaded = fts_enabled
        self._vss_loaded = vss_enabled
        return CatalogIndexStats(
            workspaces_indexed=workspaces_indexed,
            entries_indexed=entries_indexed,
            entries_unchanged=entries_unchanged,
            entries_removed=entries_removed,
            embeddings_computed=embeddings_computed,
            embeddings_reused=embeddings_reused,
            embedder_model=self._embedder.model_name,
            embedding_dim=self._embedder.dimensions,
            fts_enabled=fts_enabled,
            vss_enabled=vss_enabled,
        )

    def search(
        self,
        query: str,
        *,
        mode: str = "hybrid",
        workspace_id: str | None = None,
        concept_type: str | None = None,
        trust_tier: str | None = None,
        limit: int = 20,
    ) -> list[CatalogSearchHit]:
        """Execute BM25, cosine vector, or hybrid Reciprocal Rank Fusion search in read-only mode."""
        cleaned = query.strip()
        if not cleaned or not self._db_path.exists():
            return []

        normalized_mode = mode.strip().lower()
        if normalized_mode not in {"bm25", "semantic", "hybrid"}:
            msg = f"Unsupported search mode '{mode}'. Expected 'bm25', 'semantic', or 'hybrid'."
            raise ValueError(msg)

        query_terms = OkfMarkdownParser.tokenize(cleaned)
        if not query_terms:
            query_terms = [cleaned.lower()]

        db = SQLSpec()
        cfg = self._make_config(read_only=True)
        db.add_config(cfg)
        try:
            with db.provide_session(cfg) as session:
                fts_ready, _ = self._probe_extensions(session, allow_install=False)
                fts_schema_exists = fts_ready and self._has_fts_index(session)
                has_vectors = self._embedder.enabled and self._has_model_embeddings(session)
                vec_slot = self._vec_slot()

                common_params: dict[str, Any] = {
                    "workspace_id": workspace_id,
                    "concept_type": concept_type,
                    "trust_tier": trust_tier,
                    "limit_rows": max(1, min(limit, 100)),
                }

                if normalized_mode == "bm25" or not has_vectors:
                    if fts_schema_exists:
                        stmt = self._loader.get_sql("search-fts-bm25")
                        return session.select(
                            stmt,
                            {**common_params, "query_text": cleaned},
                            schema_type=CatalogSearchHit,
                        )
                    stmt = self._loader.get_sql("search-sql-bm25")
                    return session.select(
                        stmt,
                        {**common_params, "query_terms": query_terms},
                        schema_type=CatalogSearchHit,
                    )

                query_vec = self._embedder.embed_query(cleaned)
                if normalized_mode == "semantic":
                    stmt = self._loader.get_sql("search-semantic", vec_type=vec_slot)
                    return session.select(
                        stmt,
                        {
                            **common_params,
                            "query_vec": query_vec,
                            "model_name": self._embedder.model_name,
                        },
                        schema_type=CatalogSearchHit,
                    )

                if fts_schema_exists:
                    stmt = self._loader.get_sql("search-hybrid-fts-rrf", vec_type=vec_slot)
                    return session.select(
                        stmt,
                        {
                            **common_params,
                            "query_text": cleaned,
                            "query_vec": query_vec,
                            "model_name": self._embedder.model_name,
                        },
                        schema_type=CatalogSearchHit,
                    )

                stmt = self._loader.get_sql("search-hybrid-sql-rrf", vec_type=vec_slot)
                return session.select(
                    stmt,
                    {
                        **common_params,
                        "query_terms": query_terms,
                        "query_vec": query_vec,
                        "model_name": self._embedder.model_name,
                    },
                    schema_type=CatalogSearchHit,
                )
        finally:
            cfg.close_pool()

    def find_provenance(
        self,
        file_path: str,
        *,
        workspace_id: str | None = None,
        limit: int = 20,
    ) -> list[CatalogSearchHit]:
        """Look up OKF concepts and truth blocks whose ``sources`` cite ``file_path``."""
        cleaned = file_path.strip().lstrip("./")
        if not cleaned or not self._db_path.exists():
            return []

        db = SQLSpec()
        cfg = self._make_config(read_only=True)
        db.add_config(cfg)
        try:
            with db.provide_session(cfg) as session:
                stmt = self._loader.get_sql("find-provenance")
                return session.select(
                    stmt,
                    {
                        "file_path": cleaned,
                        "suffix_pattern": f"%/{cleaned}",
                        "prefix_pattern": f"{cleaned}::%",
                        "workspace_id": workspace_id,
                        "limit_rows": max(1, min(limit, 100)),
                    },
                    schema_type=CatalogSearchHit,
                )
        finally:
            cfg.close_pool()

    def get_entry_detail(self, entry_id: str) -> CatalogEntryDetail | None:
        """Fetch a complete catalog entry with citations, outbound links, and inbound backlinks."""
        if not self._db_path.exists():
            return None

        db = SQLSpec()
        cfg = self._make_config(read_only=True)
        db.add_config(cfg)
        try:
            with db.provide_session(cfg) as session:
                entry = session.select_one_or_none(
                    self._loader.get_sql("select-entry-by-id"),
                    {"entry_id": entry_id},
                    schema_type=CatalogEntry,
                )
                if entry is None:
                    return None
                sources = session.select(
                    self._loader.get_sql("select-entry-sources"),
                    {"entry_id": entry_id},
                    schema_type=CatalogSourceRef,
                )
                outbound = session.select(
                    self._loader.get_sql("select-outbound-links"),
                    {"entry_id": entry_id},
                    schema_type=CatalogLinkEdge,
                )
                inbound = session.select(
                    self._loader.get_sql("select-inbound-links"),
                    {"entry_id": entry_id},
                    schema_type=CatalogLinkEdge,
                )
                return CatalogEntryDetail(
                    entry=entry,
                    sources=tuple(sources),
                    outbound_links=tuple(outbound),
                    referenced_by=tuple(inbound),
                )
        finally:
            cfg.close_pool()

    def list_facets(self) -> CatalogFacets:
        """Return workspace, concept-type, and trust-tier facet counts."""
        if not self._db_path.exists():
            return CatalogFacets(workspaces=(), concept_types=(), trust_tiers=())

        db = SQLSpec()
        cfg = self._make_config(read_only=True)
        db.add_config(cfg)
        try:
            with db.provide_session(cfg) as session:
                workspaces = session.select(
                    self._loader.get_sql("select-workspace-facets"),
                    schema_type=CatalogFacetBucket,
                )
                concept_types = session.select(
                    self._loader.get_sql("select-type-facets"),
                    schema_type=CatalogFacetBucket,
                )
                trust_tiers = session.select(
                    self._loader.get_sql("select-trust-facets"),
                    schema_type=CatalogFacetBucket,
                )
                return CatalogFacets(
                    workspaces=tuple(workspaces),
                    concept_types=tuple(concept_types),
                    trust_tiers=tuple(trust_tiers),
                )
        finally:
            cfg.close_pool()

    def check_drift(self, *, workspace_id: str | None = None) -> CatalogDriftReport:
        """Query broken cross-concept links and missing local code citations."""
        if not self._db_path.exists():
            return CatalogDriftReport(broken_links=(), missing_sources=())

        db = SQLSpec()
        cfg = self._make_config(read_only=True)
        db.add_config(cfg)
        try:
            with db.provide_session(cfg) as session:
                broken_links = session.select(
                    self._loader.get_sql("select-broken-links"),
                    {"workspace_id": workspace_id},
                    schema_type=CatalogDriftIssue,
                )
                missing_sources = session.select(
                    self._loader.get_sql("select-missing-sources"),
                    {"workspace_id": workspace_id},
                    schema_type=CatalogDriftIssue,
                )
                return CatalogDriftReport(
                    broken_links=tuple(broken_links),
                    missing_sources=tuple(missing_sources),
                )
        finally:
            cfg.close_pool()

    def get_status(self) -> CatalogStatus:
        """Inspect catalog database counts and loaded DuckDB extension status."""
        if not self._db_path.exists():
            return CatalogStatus(
                db_path=str(self._db_path),
                exists=False,
                workspace_count=0,
                entry_count=0,
                embedding_count=0,
                embedder_model=self._embedder.model_name,
                embedding_dim=self._embedder.dimensions,
                fts_enabled=False,
                vss_enabled=False,
            )

        db = SQLSpec()
        cfg = self._make_config(read_only=True)
        db.add_config(cfg)
        try:
            with db.provide_session(cfg) as session:
                fts_ready, vss_ready = self._probe_extensions(session, allow_install=False)
                ws_count = int(session.select_value("SELECT COUNT(*) FROM workspaces") or 0)
                entry_count = int(session.select_value("SELECT COUNT(*) FROM entries") or 0)
                emb_count = int(session.select_value("SELECT COUNT(*) FROM entry_embeddings") or 0)
                return CatalogStatus(
                    db_path=str(self._db_path),
                    exists=True,
                    workspace_count=ws_count,
                    entry_count=entry_count,
                    embedding_count=emb_count,
                    embedder_model=self._embedder.model_name,
                    embedding_dim=self._embedder.dimensions,
                    fts_enabled=fts_ready,
                    vss_enabled=vss_ready,
                )
        finally:
            cfg.close_pool()

    def _make_config(self, *, read_only: bool) -> DuckDBConfig:
        """Create a resource-bounded ``DuckDBConfig`` for read-only or transactional write use."""
        conn_params: dict[str, Any] = {
            "database": str(self._db_path),
            "read_only": read_only,
        }
        if not read_only:
            conn_params["memory_limit"] = self._memory_limit
            conn_params["threads"] = self._threads
        return DuckDBConfig(connection_config=conn_params)

    def _vec_slot(self) -> str:
        """Return validated DuckDB fixed-size vector type literal for SQLFileLoader slots."""
        dim = int(self._embedder.dimensions)
        if dim <= 0 or dim > 4096:
            msg = f"Invalid embedding dimension: {dim}"
            raise ValueError(msg)
        return f"FLOAT[{dim}]"

    def _probe_extensions(self, session: Any, *, allow_install: bool) -> tuple[bool, bool]:
        """Inspect and optionally load/install DuckDB ``fts`` and ``vss`` extensions safely."""
        rows = session.select(
            "SELECT extension_name, installed, loaded FROM duckdb_extensions() WHERE extension_name IN ('fts', 'vss')"
        )
        state = {str(r["extension_name"]): (bool(r["installed"]), bool(r["loaded"])) for r in rows}
        offline = os.environ.get("FLOW_OFFLINE", "0").strip().lower() in {"1", "true", "yes"}
        auto_install = (
            allow_install
            and not offline
            and os.environ.get("FLOW_CATALOG_INSTALL_EXTENSIONS", "0").strip().lower() in {"1", "true", "yes"}
        )

        fts_ok = self._activate_extension(session, "fts", state.get("fts", (False, False)), auto_install)
        vss_ok = self._activate_extension(session, "vss", state.get("vss", (False, False)), auto_install)
        return fts_ok, vss_ok

    @staticmethod
    def _activate_extension(
        session: Any,
        ext_name: str,
        ext_state: tuple[bool, bool],
        auto_install: bool,
    ) -> bool:
        """Load an installed DuckDB extension or optionally install it without leaking exceptions."""
        installed, loaded = ext_state
        if loaded:
            return True
        if not installed and not auto_install:
            return False

        activated = False
        try:
            if not installed and auto_install:
                session.execute(f"INSTALL {ext_name}")
            session.execute(f"LOAD {ext_name}")
            activated = True
        except Exception:
            activated = False
        return activated

    def _ensure_schema(self, session: Any) -> None:
        """Initialize catalog tables and recreate fixed-width vector tables if dimension changed."""
        vec_slot = self._vec_slot()
        session.execute_script(self._loader.get_sql("init-schema", vec_type=vec_slot))

        prev_dim_raw = session.select_value_or_none(
            "SELECT meta_value FROM catalog_meta WHERE meta_key = 'embedding_dim'"
        )
        current_dim_str = str(self._embedder.dimensions)
        if prev_dim_raw is not None and str(prev_dim_raw) != current_dim_str:
            session.execute("DROP TABLE IF EXISTS entry_embeddings")
            session.execute("DROP TABLE IF EXISTS embedding_cache")
            session.execute_script(self._loader.get_sql("init-schema", vec_type=vec_slot))

        session.execute(
            "INSERT OR REPLACE INTO catalog_meta (meta_key, meta_value) VALUES ('embedding_dim', :dim)",
            {"dim": current_dim_str},
        )
        session.execute(
            "INSERT OR REPLACE INTO catalog_meta (meta_key, meta_value) VALUES ('embedder_model', :model)",
            {"model": self._embedder.model_name},
        )

    @staticmethod
    def _locate_bundle_root(workspace_root: Path) -> Path | None:
        """Resolve OKF bundle root from ``setup-state.json``, ``.agents/bundles``, or ``catalog.yaml`` + ``bundle/``."""
        setup_file = workspace_root / ".agents" / "setup-state.json"
        if setup_file.is_file():
            try:
                raw = json.loads(setup_file.read_text(encoding="utf-8"))
                configured = str(raw.get("bundle_root") or "").strip()
                if configured:
                    candidate = (workspace_root / configured).resolve()
                    if candidate.is_dir():
                        return candidate
            except (json.JSONDecodeError, OSError):
                pass
        default_bundle = workspace_root / ".agents" / "bundles"
        if default_bundle.is_dir():
            return default_bundle
        kcmd_bundle = workspace_root / "bundle"
        if kcmd_bundle.is_dir() and (
            (workspace_root / "catalog.yaml").is_file() or (kcmd_bundle / "index.md").is_file()
        ):
            return kcmd_bundle
        return None

    @staticmethod
    def _derive_workspace_id(workspace_root: Path) -> str:
        """Build a stable workspace slug combining repository directory name and short path hash."""
        short_hash = hashlib.sha256(str(workspace_root).encode("utf-8")).hexdigest()[:8]
        safe_name = re.sub(r"[^a-z0-9_-]+", "-", workspace_root.name.lower()).strip("-") or "workspace"
        return f"{safe_name}-{short_hash}"

    @staticmethod
    def _read_okf_version(workspace_root: Path, bundle_root: Path) -> str:
        """Extract ``okf_version`` from ``bundle_root/index.md`` when present."""
        index_md = bundle_root / "index.md"
        if index_md.is_file():
            fm, _ = OkfMarkdownParser._split_frontmatter(index_md.read_text(encoding="utf-8", errors="ignore"))
            ver = fm.get("okf_version")
            if ver:
                return str(ver)
        _ = workspace_root
        return "0.2"

    def _delete_entry(self, session: Any, entry_id: str) -> None:
        """Delete an entry and its dependent term, citation, link, and vector rows."""
        params = {"entry_id": entry_id}
        session.execute("DELETE FROM entry_terms WHERE entry_id = :entry_id", params)
        session.execute("DELETE FROM entry_sources WHERE entry_id = :entry_id", params)
        session.execute("DELETE FROM entry_links WHERE from_entry_id = :entry_id", params)
        session.execute("DELETE FROM entry_embeddings WHERE entry_id = :entry_id", params)
        session.execute("DELETE FROM entries WHERE entry_id = :entry_id", params)

    def _upsert_document(self, session: Any, doc: OkfMarkdownDocument) -> None:
        """Write an ``OkfMarkdownDocument`` and its inverted lexical terms into DuckDB."""
        e = doc.entry
        doc_len = max(sum(doc.term_counts.values()), 1)
        session.execute(
            "INSERT OR REPLACE INTO entries ("
            "entry_id, workspace_id, rel_path, concept_id, concept_type, title, description, "
            "status, state, trust_tier, verified_by, verified_at, tags, truth_block, body_markdown, "
            "frontmatter_json, content_sha256, mtime_ms, file_size, doc_len"
            ") VALUES ("
            ":entry_id, :workspace_id, :rel_path, :concept_id, :concept_type, :title, :description, "
            ":status, :state, :trust_tier, :verified_by, :verified_at, :tags, :truth_block, :body_markdown, "
            ":frontmatter_json, :content_sha256, :mtime_ms, :file_size, :doc_len"
            ")",
            {
                "entry_id": e.entry_id,
                "workspace_id": e.workspace_id,
                "rel_path": e.rel_path,
                "concept_id": e.concept_id,
                "concept_type": e.concept_type,
                "title": e.title,
                "description": e.description,
                "status": e.status,
                "state": e.state,
                "trust_tier": e.trust_tier,
                "verified_by": e.verified_by,
                "verified_at": e.verified_at,
                "tags": list(e.tags),
                "truth_block": e.truth_block,
                "body_markdown": e.body_markdown,
                "frontmatter_json": e.frontmatter_json,
                "content_sha256": e.content_sha256,
                "mtime_ms": e.mtime_ms,
                "file_size": e.file_size,
                "doc_len": doc_len,
            },
        )
        session.execute("DELETE FROM entry_terms WHERE entry_id = :entry_id", {"entry_id": e.entry_id})
        if doc.term_counts:
            term_rows = [{"entry_id": e.entry_id, "term": term, "tf": tf} for term, tf in doc.term_counts.items()]
            session.execute_many(
                "INSERT INTO entry_terms (entry_id, term, tf) VALUES (:entry_id, :term, :tf)",
                term_rows,
            )
        self._replace_sources_and_links(session, doc)

    @staticmethod
    def _replace_sources_and_links(session: Any, doc: OkfMarkdownDocument) -> None:
        """Refresh ``entry_sources`` and ``entry_links`` rows for ``doc``."""
        entry_id = doc.entry.entry_id
        session.execute("DELETE FROM entry_sources WHERE entry_id = :entry_id", {"entry_id": entry_id})
        if doc.sources:
            src_rows = [
                {
                    "entry_id": s.entry_id,
                    "source_id": s.source_id,
                    "resource": s.resource,
                    "file_path": s.file_path,
                    "symbol_name": s.symbol_name,
                    "title": s.title,
                    "resource_exists": s.resource_exists,
                }
                for s in doc.sources
            ]
            session.execute_many(
                "INSERT INTO entry_sources "
                "(entry_id, source_id, resource, file_path, symbol_name, title, resource_exists) "
                "VALUES (:entry_id, :source_id, :resource, :file_path, :symbol_name, :title, :resource_exists)",
                src_rows,
            )

        session.execute("DELETE FROM entry_links WHERE from_entry_id = :entry_id", {"entry_id": entry_id})
        if doc.links:
            link_rows = [
                {
                    "from_entry_id": edge.from_entry_id,
                    "to_target": edge.to_target,
                    "to_entry_id": edge.to_entry_id,
                    "edge_kind": edge.edge_kind,
                    "target_exists": edge.target_exists,
                }
                for edge in doc.links
            ]
            session.execute_many(
                "INSERT INTO entry_links "
                "(from_entry_id, to_target, to_entry_id, edge_kind, target_exists) "
                "VALUES (:from_entry_id, :to_target, :to_entry_id, :edge_kind, :target_exists)",
                link_rows,
            )

    def _sync_workspace_embeddings(self, session: Any, workspace_id: str) -> tuple[int, int]:
        """Populate missing ``entry_embeddings`` via SHA-256 ``embedding_cache`` deduplication."""
        model_name = self._embedder.model_name
        dim = self._embedder.dimensions

        missing_rows = session.select(
            self._loader.get_sql("select-missing-workspace-embeddings"),
            {"workspace_id": workspace_id, "model_name": model_name, "dim": dim},
        )
        if not missing_rows:
            return 0, 0

        reused = 0
        to_compute_shas: dict[str, tuple[str, str]] = {}
        for row in missing_rows:
            sha = str(row["content_sha256"])
            cached = row["cached_vec"]
            if cached is not None:
                session.execute(
                    "INSERT OR REPLACE INTO entry_embeddings (entry_id, model_name, embedding_dim, embedding) "
                    "VALUES (:entry_id, :model_name, :dim, :vec)",
                    {
                        "entry_id": str(row["entry_id"]),
                        "model_name": model_name,
                        "dim": dim,
                        "vec": list(cached),
                    },
                )
                reused += 1
            elif sha not in to_compute_shas:
                doc_text = "\n\n".join(
                    part
                    for part in (
                        str(row["description"] or ""),
                        str(row["truth_block"] or ""),
                        str(row["body_markdown"] or ""),
                    )
                    if part
                )
                to_compute_shas[sha] = (str(row["title"]), doc_text)

        computed = 0
        if to_compute_shas:
            ordered_shas = list(to_compute_shas.keys())
            batch_inputs = [to_compute_shas[sha] for sha in ordered_shas]
            vectors = self._embedder.embed_documents(batch_inputs)
            computed = len(vectors)
            sha_to_vec = dict(zip(ordered_shas, vectors, strict=True))

            for sha, vec in sha_to_vec.items():
                session.execute(
                    "INSERT OR REPLACE INTO embedding_cache "
                    "(content_sha256, model_name, embedding_dim, embedding) "
                    "VALUES (:sha, :model_name, :dim, :vec)",
                    {"sha": sha, "model_name": model_name, "dim": dim, "vec": vec},
                )

            for row in missing_rows:
                if row["cached_vec"] is not None:
                    continue
                sha = str(row["content_sha256"])
                vec = sha_to_vec[sha]
                session.execute(
                    "INSERT OR REPLACE INTO entry_embeddings "
                    "(entry_id, model_name, embedding_dim, embedding) "
                    "VALUES (:entry_id, :model_name, :dim, :vec)",
                    {
                        "entry_id": str(row["entry_id"]),
                        "model_name": model_name,
                        "dim": dim,
                        "vec": vec,
                    },
                )

        return computed, reused

    @staticmethod
    def _rebuild_fts_index(session: Any) -> bool:
        """Rebuild DuckDB's native ``fts`` inverted index when the extension is loaded."""
        created = False
        try:
            session.execute(
                "PRAGMA create_fts_index("
                "'entries', 'entry_id', 'title', 'description', 'truth_block', 'body_markdown', "
                "overwrite = 1"
                ")"
            )
            created = True
        except Exception:
            created = False
        return created

    @staticmethod
    def _ensure_hnsw_index(session: Any) -> None:
        """Create an experimental HNSW cosine index when DuckDB's ``vss`` extension is active."""
        try:
            session.execute("SET hnsw_enable_experimental_persistence = true")
            session.execute(
                "CREATE INDEX IF NOT EXISTS idx_entry_embeddings_hnsw "
                "ON entry_embeddings USING HNSW (embedding) WITH (metric = 'cosine')"
            )
        except Exception:
            return

    @staticmethod
    def _has_fts_index(session: Any) -> bool:
        """Return True when ``fts_main_entries`` schema exists in the catalog."""
        cnt = session.select_value_or_none(
            "SELECT COUNT(*) FROM information_schema.schemata WHERE schema_name = 'fts_main_entries'"
        )
        return bool(cnt and int(cnt) > 0)

    def _has_model_embeddings(self, session: Any) -> bool:
        """Return True when ``entry_embeddings`` contains rows for the active embedding model."""
        cnt = session.select_value_or_none(
            "SELECT COUNT(*) FROM entry_embeddings WHERE model_name = :model_name",
            {"model_name": self._embedder.model_name},
        )
        return bool(cnt and int(cnt) > 0)

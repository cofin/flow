"""Command-line and persistent stdio JSON-RPC interface for the DuckDB catalog."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from sqlspec.utils.serializers import from_json, to_json

from tools.catalog.embedder import resolve_embedding_provider
from tools.catalog.service import CatalogService, default_catalog_db_path

__all__ = (
    "CatalogCliDispatcher",
    "build_parser",
    "main",
)


class CatalogCliDispatcher:
    """Dispatches CLI subcommands and line-delimited stdio JSON-RPC requests."""

    def __init__(self, service: CatalogService) -> None:
        self._service = service

    def execute_method(self, method: str, params: dict[str, Any]) -> Any:
        """Execute a named catalog operation and return a JSON-serializable model or list."""
        if method == "ping":
            return {"ok": True, "db_path": str(self._service.db_path)}
        if method == "status":
            return self._service.get_status()
        if method == "index":
            raw_workspaces = params.get("workspaces") or []
            if isinstance(raw_workspaces, str):
                raw_workspaces = [raw_workspaces]
            return self._service.index_workspaces([Path(p) for p in raw_workspaces])
        if method == "search":
            return self._service.search(
                str(params.get("query") or ""),
                mode=str(params.get("mode") or "hybrid"),
                workspace_id=params.get("workspace_id"),
                concept_type=params.get("concept_type"),
                trust_tier=params.get("trust_tier"),
                limit=int(params.get("limit") or 20),
            )
        if method == "provenance":
            return self._service.find_provenance(
                str(params.get("file_path") or ""),
                workspace_id=params.get("workspace_id"),
                limit=int(params.get("limit") or 20),
            )
        if method == "entry":
            return self._service.get_entry_detail(str(params.get("entry_id") or ""))
        if method == "facets":
            return self._service.list_facets()
        if method == "drift":
            return self._service.check_drift(workspace_id=params.get("workspace_id"))
        msg = f"Unknown catalog RPC method: {method}"
        raise ValueError(msg)

    def serve_stdio(self) -> int:
        """Process line-delimited JSON-RPC requests from stdin until EOF."""
        for raw_line in sys.stdin:
            line = raw_line.strip()
            if not line:
                continue
            req_id: Any = None
            response: dict[str, Any]
            try:
                payload = from_json(line)
                if not isinstance(payload, dict):
                    msg = "Expected JSON object request"
                    raise TypeError(msg)
                req_id = payload.get("id")
                method = str(payload.get("method") or "")
                params = payload.get("params") or {}
                if not isinstance(params, dict):
                    msg = "Expected object for 'params'"
                    raise TypeError(msg)
                result = self.execute_method(method, params)
                response = {"id": req_id, "result": result}
            except Exception as exc:
                response = {"id": req_id, "error": {"message": str(exc)}}
            sys.stdout.write(f"{to_json(response)}\n")
            sys.stdout.flush()
        return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the ``flow-catalog`` CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="flow-catalog",
        description="Local SQLSpec + DuckDB hybrid BM25 and EmbeddingGemma knowledge catalog.",
    )
    parser.add_argument(
        "--db",
        default=str(default_catalog_db_path()),
        help="Path to the disposable DuckDB catalog file.",
    )
    parser.add_argument(
        "--embedder",
        default=None,
        help="Embedding backend ('gemma', 'bge', 'deterministic', or 'none').",
    )
    parser.add_argument(
        "--dim",
        type=int,
        default=None,
        help="Matryoshka or output vector dimensionality (default: 256).",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    p_index = sub.add_parser("index", help="Incrementally synchronize repository OKF bundles.")
    p_index.add_argument("workspaces", nargs="+", help="One or more repository root directories.")

    p_search = sub.add_parser("search", help="Run BM25, semantic vector, or hybrid RRF search.")
    p_search.add_argument("query", help="Search query text.")
    p_search.add_argument("--mode", choices=("hybrid", "bm25", "semantic"), default="hybrid")
    p_search.add_argument("--workspace", default=None, dest="workspace_id")
    p_search.add_argument("--type", default=None, dest="concept_type")
    p_search.add_argument("--trust", default=None, dest="trust_tier")
    p_search.add_argument("--limit", type=int, default=20)

    p_prov = sub.add_parser("provenance", help="Find OKF concepts citing a source file path.")
    p_prov.add_argument("file_path", help="Workspace-relative source file path.")
    p_prov.add_argument("--workspace", default=None, dest="workspace_id")
    p_prov.add_argument("--limit", type=int, default=20)

    p_entry = sub.add_parser("entry", help="Fetch full entry detail, citations, and graph links.")
    p_entry.add_argument("entry_id", help="Catalog entry identifier (<workspace_id>:<concept_id>).")

    sub.add_parser("facets", help="List workspace, concept-type, and trust-tier counts.")

    p_drift = sub.add_parser("drift", help="Report broken links and missing source citations.")
    p_drift.add_argument("--workspace", default=None, dest="workspace_id")

    sub.add_parser("status", help="Show catalog database and DuckDB extension status.")
    sub.add_parser("serve-stdio", help="Run persistent line-delimited JSON-RPC worker over stdio.")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Entrypoint for the ``flow-catalog`` console script and ``python -m tools.catalog``."""
    parser = build_parser()
    args = parser.parse_args(argv)

    embedder = resolve_embedding_provider(args.embedder, dimensions=args.dim)
    service = CatalogService(db_path=Path(args.db), embedder=embedder)
    dispatcher = CatalogCliDispatcher(service)

    if args.command == "serve-stdio":
        return dispatcher.serve_stdio()

    params: dict[str, Any] = {}
    if args.command == "index":
        params = {"workspaces": args.workspaces}
    elif args.command == "search":
        params = {
            "query": args.query,
            "mode": args.mode,
            "workspace_id": args.workspace_id,
            "concept_type": args.concept_type,
            "trust_tier": args.trust_tier,
            "limit": args.limit,
        }
    elif args.command == "provenance":
        params = {
            "file_path": args.file_path,
            "workspace_id": args.workspace_id,
            "limit": args.limit,
        }
    elif args.command == "entry":
        params = {"entry_id": args.entry_id}
    elif args.command == "drift":
        params = {"workspace_id": args.workspace_id}

    try:
        output = dispatcher.execute_method(args.command, params)
    except Exception as exc:
        sys.stderr.write(f"{to_json({'error': str(exc)})}\n")
        return 1

    sys.stdout.write(f"{to_json(output)}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

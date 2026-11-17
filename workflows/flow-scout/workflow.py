"""Run parallel read-only subsystem research with federated knowledge search and task boundary hints."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys

_WF_PARENT = Path(__file__).resolve().parent.parent if "__file__" in globals() else Path.cwd() / "workflows"
if str(_WF_PARENT) not in sys.path:
    sys.path.insert(0, str(_WF_PARENT))

from flow_common import (
    acquire_runtime_lease,
    git_porcelain,
    prefetch_seeds,
    release_runtime_lease,
    resolve_dynamic_route,
    resolve_plugin_root,
    run_node_cli,
)

DIGEST_SCHEMA = {
    "type": "object",
    "properties": {
        "subsystem": {"type": "string"},
        "symbols_and_exact_signatures": {"type": "array", "items": {"type": "string"}},
        "seams_and_dependency_categories": {"type": "array", "items": {"type": "string"}},
        "canonical_tests_and_fixtures": {"type": "array", "items": {"type": "string"}},
        "edge_cases_and_gotchas": {"type": "array", "items": {"type": "string"}},
        "affected_docs_and_okf_chapters": {"type": "array", "items": {"type": "string"}},
        "recommended_tasks": {"type": "array", "items": {"type": "string"}},
        "open_design_forks": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "subsystem",
        "symbols_and_exact_signatures",
        "seams_and_dependency_categories",
        "canonical_tests_and_fixtures",
        "edge_cases_and_gotchas",
        "affected_docs_and_okf_chapters",
        "recommended_tasks",
        "open_design_forks",
    ],
}

subsystems = list(args.get("subsystems", []))
federated_query = str(args.get("query") or "").strip()
planes = list(args.get("planes") or ["local", "siblings"])
harness = str(args.get("harness") or os.environ.get("FLOW_HARNESS") or "agy")
plugin_root = resolve_plugin_root(args.get("plugin_root"))

balanced_route = resolve_dynamic_route(plugin_root, "implementation", harness=harness)
light_route = resolve_dynamic_route(plugin_root, "narrow_fetch", harness=harness)
preferred_model = str(args.get("scout_model") or os.environ.get("FLOW_SCOUT_MODEL") or balanced_route["runtime_target"])
narrow_model_arg = str(args.get("narrow_model") or light_route["runtime_target"]).strip()
scout_agent = str(args.get("scout_agent") or os.environ.get("FLOW_SCOUT_AGENT") or "self")
narrow_agent = str(args.get("narrow_agent") or os.environ.get("FLOW_SCOUT_NARROW_AGENT") or scout_agent)
timeout_seconds = int(args.get("timeout_seconds", 300))

federated_hits: list[dict] = []
if federated_query:
    _, fed_out, _, _ = run_node_cli(
        plugin_root,
        ["catalog", "search", "--query", federated_query, "--mode", "federated", "--planes", ",".join(planes), "--root", str(Path.cwd())],
    )
    if isinstance(fed_out, dict):
        federated_hits = list(fed_out.get("hits", []))[:12]


async def _run_scout(item: dict) -> dict:
    """Run one read-only subsystem researcher with prefetched seeds and task boundary hints."""
    name = str(item.get("name", "subsystem"))
    paths = [str(p) for p in item.get("paths", [])]
    focus = str(item.get("focus", "")).strip()
    allow_lite = bool(item.get("narrow_fetch", False)) and len(paths) <= 3
    selected_agent = narrow_agent if allow_lite else scout_agent
    active_model = narrow_model_arg if allow_lite else preferred_model
    seeds = prefetch_seeds(paths, globals().get("call_tool"), max_files=4, end_line=100)
    seed_block = f"\nPre-read seed excerpts:\n{json.dumps(seeds, ensure_ascii=False)}" if seeds else ""
    fed_block = f"\nFederated catalog matches:\n{json.dumps(federated_hits[:5], ensure_ascii=False)}" if federated_hits else ""
    prompt = (
        f"Research subsystem `{name}` across paths {paths}. Focus: {focus or 'contracts, tests, and task boundaries'}.\n"
        "Stay read-only. Recommend separate-file `<=250` LOC tasks in `recommended_tasks`."
        f"{seed_block}{fed_block}"
    )
    digest = await with_budget(
        agent(
            prompt,
            schema=DIGEST_SCHEMA,
            role=f"Researcher {name}",
            type_name=selected_agent,
            workspace="inherit",
            model=active_model,
        ),
        max_tokens=260000,
        timeout=timeout_seconds,
    )
    return {"subsystem": name, "status": "completed", "agent_used": selected_agent, "model_used": active_model, "digest": digest}


before_status = git_porcelain()
phase("Parallel Subsystem Research")
log(f"Dispatching {len(subsystems)} read-only researcher(s) across planes {planes}")
_wf_lease = acquire_runtime_lease()
try:
    results = await parallel(subsystems, _run_scout) if subsystems else []
finally:
    release_runtime_lease(_wf_lease)

after_status = git_porcelain()
print(
    json.dumps(
        {
            "git_status_unchanged": before_status == after_status,
            "federated_hits": federated_hits,
            "subsystems": results,
            "tokens": tokens_used(),
        }
    )
)

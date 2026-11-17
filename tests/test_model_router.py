"""Public-seam tests for DynamicModelCatalog, DecisionEngine, AdaptiveModelRouter, and HarnessProfileMaterializer."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

from tools.validate import REPO_ROOT

NODE_BIN = shutil.which("node")
INVENTORY_MOD = (REPO_ROOT / "sidecars" / "studio" / "models" / "inventory.mjs").as_uri()
ROUTING_MOD = (REPO_ROOT / "sidecars" / "studio" / "models" / "routing.mjs").as_uri()
PROFILES_MOD = (REPO_ROOT / "sidecars" / "studio" / "models" / "profiles.mjs").as_uri()
FLOW_CLI = REPO_ROOT / "sidecars" / "studio" / "flow-cli.mjs"


def _run_node(js: str, *, env: dict[str, str] | None = None) -> dict[str, Any]:
    """Execute an ES module snippet via Node.js and parse the trailing JSON line."""
    assert NODE_BIN is not None
    proc = subprocess.run(
        [NODE_BIN, "--input-type=module", "-e", js],
        env={**os.environ, **(env or {})},
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return json.loads(proc.stdout.strip().splitlines()[-1])


@pytest.mark.skipif(NODE_BIN is None, reason="node binary required")
@pytest.mark.parametrize(
    ("raw_val", "expected"),
    (
        (77, 0.77),
        ("77%", 0.77),
        ("0.54", 0.54),
        (0.25, 0.25),
        (1, 1.0),
        ("0%", 0.0),
        (-5, 0.0),
        (150, 1.0),
        (None, None),
        ("", None),
        (True, None),
    ),
)
def test_normalize_quota_fraction_formats(raw_val: Any, expected: float | None) -> None:
    """Verify percentage strings, integers, and fractional floats normalize cleanly onto 0..1."""
    js = (
        f"import {{ normalizeQuotaFraction }} from {json.dumps(INVENTORY_MOD)};"
        f"process.stdout.write(JSON.stringify({{ v: normalizeQuotaFraction({json.dumps(raw_val)}) }}) + '\\n');"
    )
    assert _run_node(js)["v"] == expected


@pytest.mark.skipif(NODE_BIN is None, reason="node binary required")
def test_adaptive_model_router_enforces_strong_floor_cost_efficiency_and_vendor_diversity(tmp_path: Path) -> None:
    """Verify continuous utility scoring, strong-model degradation flagging, and second-vendor review routing."""
    inventory = [
        {
            "model": "gemini-pro-primary",
            "displayName": "Gemini Pro Coordinator",
            "vendor": "google",
            "model_role": "pro",
            "quota_remaining": "80%",
            "reasoning": True,
            "supported_efforts": ["high", "xhigh"],
            "cost_input": 1.25,
            "cost_output": 10.0,
        },
        {
            "model": "claude-opus-adv",
            "displayName": "Claude Opus",
            "vendor": "anthropic",
            "model_role": "strong",
            "quota_remaining": "75%",
            "reasoning": True,
            "supported_efforts": ["high", "xhigh"],
            "cost_input": 5.0,
            "cost_output": 25.0,
        },
        {
            "model": "gemini-flash-worker",
            "displayName": "Gemini Flash Thinking",
            "vendor": "google",
            "model_role": "flash",
            "quota_remaining": "85%",
            "reasoning": True,
            "supported_efforts": ["medium", "high"],
            "cost_input": 0.15,
            "cost_output": 0.6,
        },
        {
            "model": "gemini-flash-lite",
            "displayName": "Gemini Flash Lite",
            "vendor": "google",
            "model_role": "light",
            "quota_remaining": "99%",
            "reasoning": False,
            "supported_efforts": ["default"],
            "cost_input": 0.05,
            "cost_output": 0.2,
        },
    ]
    exhausted_strong = [
        {
            "model": "gemini-pro-primary",
            "vendor": "google",
            "model_role": "pro",
            "quota_remaining": "0%",
            "reasoning": True,
            "supported_efforts": ["xhigh"],
        },
        {
            "model": "gemini-flash-lite",
            "vendor": "google",
            "model_role": "light",
            "quota_remaining": "95%",
            "reasoning": False,
            "supported_efforts": ["default"],
        },
    ]

    js = (
        f"import {{ DynamicModelCatalog }} from {json.dumps(INVENTORY_MOD)};"
        f"import {{ AdaptiveModelRouter }} from {json.dumps(ROUTING_MOD)};"
        f"const catalog = new DynamicModelCatalog({{ projectRoot: {json.dumps(str(tmp_path))} }});"
        f"const cands = await catalog.discoverHarnessCatalog("
        f"{{ harness: 'agy', customInventory: {json.dumps(inventory)} }});"
        f"const lowCands = await catalog.discoverHarnessCatalog("
        f"{{ harness: 'agy', customInventory: {json.dumps(exhausted_strong)} }});"
        "const router = new AdaptiveModelRouter();"
        "const plan = router.select(cands, { taskKind: 'planning', risk: 'high' });"
        "const adv = router.select(cands, {"
        "  taskKind: 'adversarial', risk: 'high', authorVendor: 'google', requireVendorDiversity: true"
        "});"
        "const syncRoute = router.select(cands, { taskKind: 'sync', risk: 'low' });"
        "const degradedPlan = router.select(lowCands, { taskKind: 'planning', risk: 'high' });"
        "process.stdout.write(JSON.stringify({ plan, adv, syncRoute, degradedPlan }) + '\\n');"
    )
    out = _run_node(js, env={"FLOW_RUNTIME_DIR": str(tmp_path / "rt")})

    assert out["plan"]["degraded"] is False
    assert out["plan"]["capability_index"] >= 0.8
    assert out["plan"]["role"] == "strong"
    assert len(out["plan"]["fallback_chain"]) >= 2

    assert out["adv"]["model"] == "claude-opus-adv"
    assert out["adv"]["vendor"] == "anthropic"

    assert out["syncRoute"]["model"] == "gemini-flash-lite"
    assert out["syncRoute"]["role"] == "light"

    assert out["degradedPlan"]["degraded"] is True
    assert "strong-model floor" in out["degradedPlan"]["degraded_reason"]
    assert out["degradedPlan"]["model"] == "gemini-flash-lite"


@pytest.mark.skipif(NODE_BIN is None, reason="node binary required")
def test_decision_engine_escalates_on_retries_and_handles_http_confidence(tmp_path: Path) -> None:
    """Verify DecisionEngine escalates lane/replan on failed attempts and adjusts low-confidence HTTP scores."""
    js = (
        f"import {{ DecisionEngine }} from {json.dumps(ROUTING_MOD)};"
        "const builtin = new DecisionEngine();"
        "const fast = await builtin.evaluate("
        "{ taskKind: 'implementation', filesCount: 1, estimatedLoc: 40, failedAttempts: 0 });"
        "const escalated = await builtin.evaluate("
        "{ taskKind: 'implementation', filesCount: 3, estimatedLoc: 150, failedAttempts: 3 });"
        "const httpEngine = new DecisionEngine({"
        "  provider: 'remote-http',"
        "  endpoint: 'http://127.0.0.1:9999/v1/decide',"
        "  fetchImpl: async () => ({"
        "    ok: true,"
        "    json: async () => ({ answers: {"
        "      execution_lane: 'small_swarm', complexity_rubric: 2.0, confidence: 0.4,"
        "      should_replan: true, needs_adversarial: true, needs_strong_review: true"
        "    } })"
        "  })"
        "});"
        "const remote = await httpEngine.evaluate({ taskKind: 'planning', filesCount: 6, estimatedLoc: 320 });"
        "process.stdout.write(JSON.stringify({ fast, escalated, remote }) + '\\n');"
    )
    out = _run_node(js, env={"FLOW_RUNTIME_DIR": str(tmp_path / "rt")})

    assert out["fast"]["execution_lane"] == "inline_fast_path"
    assert out["fast"]["should_replan"] is False
    assert out["escalated"]["should_replan"] is True
    assert out["escalated"]["needs_strong_review"] is True
    assert out["escalated"]["complexity_rubric"] > out["fast"]["complexity_rubric"]
    assert out["remote"]["provider"] == "remote-http"
    assert out["remote"]["complexity_rubric"] == pytest.approx(2.75)
    assert out["remote"]["needs_adversarial"] is True


@pytest.mark.skipif(NODE_BIN is None, reason="node binary required")
@pytest.mark.parametrize(
    ("harness", "target", "expected_glob"),
    (
        ("claude", "ide", ".claude/agents/flow-model-*.md"),
        ("codex", "ide", ".codex/agents/flow-model-*.toml"),
        ("cursor", "ide", ".cursor/agents/flow-model-*.md"),
        ("vscode", "ide", ".github/agents/flow-model-*.agent.md"),
        ("vscode", "copilot-cli", ".github/agents/flow-model-*.agent.md"),
    ),
)
def test_harness_profile_materializer_generates_native_tier_files(
    tmp_path: Path,
    harness: str,
    target: str,
    expected_glob: str,
) -> None:
    """Verify HarnessProfileMaterializer emits valid native tier profiles and gitexclude rules across harnesses."""
    (tmp_path / ".git" / "info").mkdir(parents=True)
    inventory = [
        {
            "model": "tier-pro",
            "vendor": "anthropic",
            "model_role": "pro",
            "reasoning": True,
            "supported_efforts": ["high", "xhigh"],
        },
        {
            "model": "tier-flash",
            "vendor": "anthropic",
            "model_role": "flash",
            "reasoning": True,
            "supported_efforts": ["medium", "high"],
        },
        {
            "model": "tier-lite",
            "vendor": "anthropic",
            "model_role": "light",
            "reasoning": False,
            "supported_efforts": ["default"],
        },
    ]
    js = (
        f"import {{ DynamicModelCatalog }} from {json.dumps(INVENTORY_MOD)};"
        f"import {{ HarnessProfileMaterializer }} from {json.dumps(PROFILES_MOD)};"
        f"const cat = new DynamicModelCatalog({{ projectRoot: {json.dumps(str(tmp_path))} }});"
        f"const cands = await cat.discoverHarnessCatalog("
        f"{{ harness: {json.dumps(harness)}, customInventory: {json.dumps(inventory)} }});"
        f"const written = HarnessProfileMaterializer.materialize("
        f"{json.dumps(str(tmp_path))}, cands, "
        f"{{ harness: {json.dumps(harness)}, target: {json.dumps(target)} }});"
        "process.stdout.write(JSON.stringify({ written }) + '\\n');"
    )
    out = _run_node(js, env={"FLOW_RUNTIME_DIR": str(tmp_path / "rt")})

    assert set(out["written"].keys()) == {"strong", "standard", "fast", "light"}
    files = sorted(tmp_path.glob(expected_glob))
    assert len(files) == 4
    exclude_text = (tmp_path / ".git" / "info" / "exclude").read_text(encoding="utf-8")
    assert ".claude/agents/flow-model-*" in exclude_text

    strong_text = Path(out["written"]["strong"]).read_text(encoding="utf-8")
    assert "tier-pro" in strong_text
    if harness == "vscode" and target == "copilot-cli":
        assert "model: tier-pro" in strong_text
    elif harness == "vscode":
        assert 'model: ["tier-pro"' in strong_text


@pytest.mark.skipif(NODE_BIN is None, reason="node binary required")
def test_flow_cli_models_inspect_route_and_materialize(tmp_path: Path) -> None:
    """Verify sidecars/studio/flow-cli.mjs models inspect/route/materialize return valid JSON end-to-end."""
    assert NODE_BIN is not None
    inv_file = tmp_path / "inv.json"
    inv_file.write_text(
        json.dumps(
            [
                {
                    "model": "opus-model",
                    "vendor": "anthropic",
                    "model_role": "strong",
                    "reasoning": True,
                    "supported_efforts": ["xhigh"],
                },
                {
                    "model": "sonnet-model",
                    "vendor": "anthropic",
                    "model_role": "flash",
                    "reasoning": True,
                    "supported_efforts": ["medium"],
                },
            ]
        ),
        encoding="utf-8",
    )
    env = {**os.environ, "FLOW_RUNTIME_DIR": str(tmp_path / "rt")}

    inspect_proc = subprocess.run(
        [
            NODE_BIN,
            str(FLOW_CLI),
            "models",
            "inspect",
            "--harness",
            "claude",
            "--models-file",
            str(inv_file),
            "--ws",
            str(tmp_path),
        ],
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    inspected = json.loads(inspect_proc.stdout)
    assert inspected["harness"] == "claude"
    assert inspected["candidate_count"] >= 2

    route_proc = subprocess.run(
        [
            NODE_BIN,
            str(FLOW_CLI),
            "models",
            "route",
            "--harness",
            "claude",
            "--kind",
            "semantic_validation",
            "--risk",
            "high",
            "--models-file",
            str(inv_file),
            "--ws",
            str(tmp_path),
        ],
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    routed = json.loads(route_proc.stdout)
    assert routed["runtime_target"] == "opus-model"
    assert routed["decision"]["needs_strong_review"] is True

    mat_proc = subprocess.run(
        [
            NODE_BIN,
            str(FLOW_CLI),
            "models",
            "materialize",
            "--harness",
            "codex",
            "--models-file",
            str(inv_file),
            "--ws",
            str(tmp_path),
        ],
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    materialized = json.loads(mat_proc.stdout)
    assert "strong" in materialized["written"]
    assert Path(materialized["written"]["strong"]).is_file()

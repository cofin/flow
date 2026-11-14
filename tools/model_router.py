"""Quota-aware model routing, ephemeral runtime agent pinning, and disjoint small-swarm gating."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

__all__ = (
    "DEFAULT_PRO_QUOTA_FLOOR",
    "DEFAULT_SWARM_QUOTA_FLOOR",
    "DisjointPlan",
    "ModelCandidate",
    "ResolvedRoleModel",
    "ResolutionReport",
    "SwarmAssignment",
    "check_chapter_disjoint",
    "classify_model",
    "load_local_model_config",
    "main",
    "materialize_runtime_agents",
    "parse_models_input",
    "parse_quota_percent",
    "resolve_models",
)

DEFAULT_PRO_QUOTA_FLOOR = 25.0
DEFAULT_SWARM_QUOTA_FLOOR = 25.0
MAX_SWARM_WRITERS = 3
MAX_SWARM_WORKERS = 4

_CLOSED_TASK_STATES: frozenset[str] = frozenset({"completed", "closed", "deferred", "skipped"})
_EFFORT_SCORES: dict[str, int] = {
    "xhigh": 4,
    "extra_high": 4,
    "max": 4,
    "high": 3,
    "medium": 2,
    "default": 1,
    "standard": 1,
    "low": 0,
    "lite": 0,
}
_FRONTIER_FAMILIES: frozenset[str] = frozenset({"frontier_pro", "claude_frontier"})
_QUOTA_LINE_RE = re.compile(
    r"^(?:[-*]\s+)?`?(?P<model>[A-Za-z0-9._:/-]+)`?(?:\s+\((?P<label>[^)]+)\))?.*?(?P<quota>\d+(?:\.\d+)?)\s*%",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class ModelCandidate:
    """Normalized model inventory entry with inferred family, thinking tier, and remaining quota."""

    model: str
    display_name: str
    family: str
    thinking: str
    thinking_score: int
    quota: float | None
    placeholder: str | None = None
    priority: int = 0
    explicit_tier: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Serialize model candidate metadata into a JSON-compatible mapping."""
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ResolvedRoleModel:
    """Selected model and ordered fallback chain for a single orchestration role."""

    role: str
    model: str
    runtime_target: str
    family: str
    thinking: str
    quota: float | None
    degraded: bool
    reason: str
    fallback_chain: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        """Serialize resolved role routing details to JSON-compatible form."""
        data = asdict(self)
        data["fallback_chain"] = list(self.fallback_chain)
        return data


@dataclass(frozen=True, slots=True)
class ResolutionReport:
    """Complete role-to-model routing plan, degraded flags, and swarm quota gate result."""

    pro_quota_floor: float
    swarm_quota_floor: float
    planning_quality: str
    degraded_reason: str | None
    small_swarm_quota_ok: bool
    swarm_quota_reason: str
    roles: dict[str, ResolvedRoleModel]

    def to_dict(self) -> dict[str, Any]:
        """Serialize resolution report to JSON-compatible form."""
        return {
            "pro_quota_floor": self.pro_quota_floor,
            "swarm_quota_floor": self.swarm_quota_floor,
            "planning_quality": self.planning_quality,
            "degraded_reason": self.degraded_reason,
            "small_swarm_quota_ok": self.small_swarm_quota_ok,
            "swarm_quota_reason": self.swarm_quota_reason,
            "roles": {key: value.to_dict() for key, value in self.roles.items()},
        }


@dataclass(frozen=True, slots=True)
class SwarmAssignment:
    """Task assignment for one share writer in bounded chapter swarm mode."""

    worker_name: str
    task_ids: tuple[str, ...]
    task_paths: tuple[str, ...]
    owned_paths: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        """Serialize writer assignment to JSON-compatible form."""
        return {
            "worker_name": self.worker_name,
            "task_ids": list(self.task_ids),
            "task_paths": list(self.task_paths),
            "owned_paths": list(self.owned_paths),
        }


@dataclass(frozen=True, slots=True)
class DisjointPlan:
    """Disjointness and quota check result determining small_swarm vs chapter_batch mode."""

    mode: str
    reason: str
    writer_count: int
    verifier_count: int
    total_workers: int
    ready_task_ids: tuple[str, ...]
    conflicts: tuple[str, ...]
    assignments: tuple[SwarmAssignment, ...]

    def to_dict(self) -> dict[str, Any]:
        """Serialize disjoint execution plan to JSON-compatible form."""
        return {
            "mode": self.mode,
            "reason": self.reason,
            "writer_count": self.writer_count,
            "verifier_count": self.verifier_count,
            "total_workers": self.total_workers,
            "ready_task_ids": list(self.ready_task_ids),
            "conflicts": list(self.conflicts),
            "assignments": [item.to_dict() for item in self.assignments],
        }


def parse_quota_percent(raw_value: Any) -> float | None:
    """Normalize integer, percentage string, or fractional remaining quota onto ``0..100``."""
    if raw_value is None or isinstance(raw_value, bool):
        return None
    if isinstance(raw_value, (int, float)):
        num = float(raw_value)
        if num < 0:
            return 0.0
        if 0.0 < num < 1.0:
            return round(num * 100.0, 2)
        return min(round(num, 2), 100.0)
    text = str(raw_value).strip()
    if not text:
        return None
    has_pct = text.endswith("%")
    cleaned = text[:-1].strip() if has_pct else text
    try:
        num = float(cleaned)
    except ValueError:
        return None
    if num < 0:
        return 0.0
    if not has_pct and 0.0 < num < 1.0 and "." in cleaned:
        return round(num * 100.0, 2)
    return min(round(num, 2), 100.0)


def load_local_model_config(
    project_root: Path | None = None,
    config_path: Path | None = None,
) -> dict[str, Any]:
    """Load optional local user model configuration and project ``setup-state.json`` overrides."""
    merged: dict[str, Any] = {
        "pro_quota_floor": DEFAULT_PRO_QUOTA_FLOOR,
        "swarm_quota_floor": DEFAULT_SWARM_QUOTA_FLOOR,
        "models": {},
    }
    candidates: list[Path] = []
    if config_path is not None:
        candidates.append(config_path)
    else:
        env_cfg = os.environ.get("FLOW_MODELS_CONFIG", "").strip()
        if env_cfg:
            candidates.append(Path(env_cfg).expanduser())
        else:
            candidates.append(Path.home() / ".config" / "flow" / "models.json")

    for cand in candidates:
        if cand.is_file():
            try:
                loaded = json.loads(cand.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                loaded = {}
            if isinstance(loaded, dict):
                _merge_routing_dict(merged, loaded)

    if project_root is not None:
        setup_path = project_root / ".agents" / "setup-state.json"
        if setup_path.is_file():
            try:
                setup_data = json.loads(setup_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                setup_data = {}
            if isinstance(setup_data, dict) and isinstance(setup_data.get("model_routing"), dict):
                _merge_routing_dict(merged, setup_data["model_routing"])

    return merged


def _merge_routing_dict(target: dict[str, Any], source: dict[str, Any]) -> None:
    """Merge local or project model routing settings into ``target``."""
    for key in ("pro_quota_floor", "swarm_quota_floor"):
        val = source.get(key)
        if isinstance(val, (int, float)) and not isinstance(val, bool):
            target[key] = float(val)
    src_models = source.get("models")
    if isinstance(src_models, dict):
        dest_models = target.setdefault("models", {})
        for model_id, entry in src_models.items():
            if isinstance(model_id, str) and isinstance(entry, dict):
                dest_models[model_id] = dict(entry)


def _infer_thinking_tier(model_id: str, display_name: str, override: dict[str, Any]) -> str:
    """Infer thinking level from local override metadata, model slug, or display name."""
    explicit = str(override.get("thinking") or "").strip().lower()
    if explicit in _EFFORT_SCORES:
        return explicit
    combined = f"{model_id} {display_name}".lower()
    if any(token in combined for token in ("xhigh", "x-high", "extra high", "extra-high", "extra_high")):
        return "xhigh"
    if any(token in combined for token in ("-high", "(high)", " high")):
        return "high"
    if any(token in combined for token in ("-medium", "(medium)", " medium")):
        return "medium"
    if any(token in combined for token in ("lite", "haiku", "-low", "(low)")):
        return "low"
    return "default"


def _infer_family(model_id: str, display_name: str, override: dict[str, Any], thinking: str) -> str:
    """Infer capability family cleanly from local overrides or public naming conventions."""
    explicit = str(override.get("family") or "").strip().lower()
    if explicit:
        return explicit
    combined = f"{model_id} {display_name}".lower()
    if "opus" in combined:
        return "claude_frontier"
    if "sonnet" in combined:
        return "claude_balanced"
    if "haiku" in combined or "flash_lite" in combined or "flash-lite" in combined:
        return "claude_light" if "haiku" in combined else "fast_flash"
    if "flash-next" in combined or "flash_next" in combined or "flash next" in combined:
        return "fast_flash"
    if "flash" in combined:
        return "thinking_flash" if thinking in ("xhigh", "high", "medium") else "fast_flash"
    if any(token in combined for token in ("coordinator", "auto", "pro", "frontier")):
        return "frontier_pro"
    if thinking in ("xhigh", "high", "medium"):
        return "thinking_flash"
    return "unknown"


def classify_model(
    raw_entry: dict[str, Any] | str,
    config: dict[str, Any] | None = None,
) -> ModelCandidate:
    """Normalize a raw model record using local configuration overrides and public conventions."""
    cfg_models = (config or {}).get("models", {})
    if isinstance(raw_entry, str):
        model_id = raw_entry.strip()
        display_name = model_id
        quota: float | None = None
        entry_placeholder = None
        entry_priority = 0
        raw_family = ""
        raw_thinking = ""
    else:
        model_id = str(raw_entry.get("model") or raw_entry.get("id") or raw_entry.get("name") or "").strip()
        display_name = str(raw_entry.get("display_name") or raw_entry.get("label") or model_id).strip()
        quota = parse_quota_percent(
            raw_entry.get("quota")
            if "quota" in raw_entry
            else raw_entry.get("quota_remaining", raw_entry.get("remaining_quota"))
        )
        entry_placeholder = raw_entry.get("placeholder")
        entry_priority = int(raw_entry.get("priority", 0) or 0)
        raw_family = str(raw_entry.get("family") or "").strip()
        raw_thinking = str(raw_entry.get("thinking") or "").strip()

    override = dict(cfg_models.get(model_id, {}))
    if raw_family and "family" not in override:
        override["family"] = raw_family
    if raw_thinking and "thinking" not in override:
        override["thinking"] = raw_thinking

    thinking = _infer_thinking_tier(model_id, display_name, override)
    family = _infer_family(model_id, display_name, override, thinking)
    placeholder_raw = override.get("placeholder") or entry_placeholder
    placeholder = str(placeholder_raw).strip() if placeholder_raw else None
    priority = int(override.get("priority", entry_priority) or 0)
    explicit_tier = bool(override.get("family") or raw_family)

    return ModelCandidate(
        model=model_id,
        display_name=display_name,
        family=family,
        thinking=thinking,
        thinking_score=_EFFORT_SCORES.get(thinking, 1),
        quota=quota,
        placeholder=placeholder,
        priority=priority,
        explicit_tier=explicit_tier,
    )


def parse_models_input(raw_text: str, config: dict[str, Any] | None = None) -> list[ModelCandidate]:
    """Parse JSON arrays, ``{\"models\": [...]}`` objects, or plain model quota lines."""
    stripped = raw_text.strip()
    if not stripped:
        return []
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        parsed = None

    if isinstance(parsed, dict) and isinstance(parsed.get("models"), list):
        return [classify_model(item, config) for item in parsed["models"] if item]
    if isinstance(parsed, list):
        return [classify_model(item, config) for item in parsed if item]

    results: list[ModelCandidate] = []
    for line in stripped.splitlines():
        cand = line.strip()
        if not cand:
            continue
        match = _QUOTA_LINE_RE.match(cand)
        if match:
            results.append(
                classify_model(
                    {
                        "model": match.group("model"),
                        "display_name": match.group("label") or match.group("model"),
                        "quota": float(match.group("quota")),
                    },
                    config,
                )
            )
    return results


def _candidate_quota_value(candidate: ModelCandidate) -> float:
    """Return numeric remaining quota or a neutral positive score when quota telemetry is absent."""
    return 100.0 if candidate.quota is None else candidate.quota


def _pick_frontier_role(
    role: str,
    candidates: list[ModelCandidate],
    pro_floor: float,
    override_model: str | None,
) -> ResolvedRoleModel:
    """Pick highest-quota frontier Pro model above floor, falling back to high-thinking Flash."""
    if override_model:
        matched = next((c for c in candidates if c.model == override_model), None)
        cand = matched or classify_model(override_model)
        degraded = cand.family not in _FRONTIER_FAMILIES or (cand.quota is not None and cand.quota < pro_floor)
        reason = f"explicit override {override_model!r}"
        return ResolvedRoleModel(
            role=role,
            model=cand.model,
            runtime_target=cand.placeholder or cand.model,
            family=cand.family,
            thinking=cand.thinking,
            quota=cand.quota,
            degraded=degraded,
            reason=reason,
            fallback_chain=(cand.model,),
        )

    frontier_above = [
        c for c in candidates if c.family in _FRONTIER_FAMILIES and _candidate_quota_value(c) >= pro_floor
    ]
    frontier_above.sort(
        key=lambda c: (c.priority, _candidate_quota_value(c), c.thinking_score),
        reverse=True,
    )
    if frontier_above:
        winner = frontier_above[0]
        backups = [c.model for c in frontier_above[1:]]
        thinking_backups = _rank_flash_candidates(candidates, prefer_fast=False)
        backups.extend(c.model for c in thinking_backups if c.model not in backups)
        q_str = "n/a" if winner.quota is None else f"{winner.quota:.0f}%"
        return ResolvedRoleModel(
            role=role,
            model=winner.model,
            runtime_target=winner.placeholder or winner.model,
            family=winner.family,
            thinking=winner.thinking,
            quota=winner.quota,
            degraded=False,
            reason=f"frontier model {winner.model!r} meets {pro_floor:.0f}% quota floor (quota={q_str})",
            fallback_chain=tuple(backups),
        )

    flash_ranked = _rank_flash_candidates(candidates, prefer_fast=False)
    if flash_ranked:
        winner = flash_ranked[0]
        flash_backups = tuple(c.model for c in flash_ranked[1:])
        return ResolvedRoleModel(
            role=role,
            model=winner.model,
            runtime_target=winner.placeholder or winner.model,
            family=winner.family,
            thinking=winner.thinking,
            quota=winner.quota,
            degraded=True,
            reason=(
                f"all frontier models below {pro_floor:.0f}% quota floor; "
                f"falling back to {winner.model!r} (thinking={winner.thinking})"
            ),
            fallback_chain=flash_backups,
        )

    return ResolvedRoleModel(
        role=role,
        model="inherit",
        runtime_target="inherit",
        family="unknown",
        thinking="default",
        quota=None,
        degraded=False,
        reason="no candidate inventory available; defaulting to inherit",
        fallback_chain=("flash",),
    )


def _rank_flash_candidates(candidates: list[ModelCandidate], *, prefer_fast: bool) -> list[ModelCandidate]:
    """Order Flash and balanced worker/scout candidates by role fitness and remaining quota."""
    if prefer_fast:
        pool = [
            c for c in candidates if c.family in ("fast_flash", "thinking_flash", "claude_balanced", "claude_light")
        ]
        pool.sort(
            key=lambda c: (
                c.family == "fast_flash",
                c.thinking != "low",
                c.priority,
                _candidate_quota_value(c),
                c.thinking_score,
            ),
            reverse=True,
        )
        return pool

    pool = [c for c in candidates if c.family in ("thinking_flash", "claude_balanced", "fast_flash")]
    pool.sort(
        key=lambda c: (
            c.family == "thinking_flash",
            c.thinking_score,
            c.thinking != "low",
            c.priority,
            _candidate_quota_value(c),
        ),
        reverse=True,
    )
    return pool


def _pick_worker_role(
    role: str,
    candidates: list[ModelCandidate],
    *,
    prefer_fast: bool,
    prefer_pro: bool,
    pro_floor: float,
    override_model: str | None,
) -> ResolvedRoleModel:
    """Pick high/extra-thinking Flash for execution, verification, or scouts (or Pro when requested)."""
    if override_model:
        matched = next((c for c in candidates if c.model == override_model), None)
        cand = matched or classify_model(override_model)
        return ResolvedRoleModel(
            role=role,
            model=cand.model,
            runtime_target=cand.placeholder or cand.model,
            family=cand.family,
            thinking=cand.thinking,
            quota=cand.quota,
            degraded=False,
            reason=f"explicit override {override_model!r}",
            fallback_chain=(cand.model,),
        )

    if prefer_pro:
        frontier_choice = _pick_frontier_role(role, candidates, pro_floor, None)
        if not frontier_choice.degraded and frontier_choice.family in _FRONTIER_FAMILIES:
            return frontier_choice

    ranked = _rank_flash_candidates(candidates, prefer_fast=prefer_fast)
    if ranked:
        winner = ranked[0]
        backups = tuple(c.model for c in ranked[1:])
        q_str = "n/a" if winner.quota is None else f"{winner.quota:.0f}%"
        return ResolvedRoleModel(
            role=role,
            model=winner.model,
            runtime_target=winner.placeholder or winner.model,
            family=winner.family,
            thinking=winner.thinking,
            quota=winner.quota,
            degraded=False,
            reason=f"selected {winner.family} {winner.model!r} (thinking={winner.thinking}, quota={q_str})",
            fallback_chain=backups,
        )

    default_alias = "flash_lite" if prefer_fast else "flash"
    return ResolvedRoleModel(
        role=role,
        model=default_alias,
        runtime_target=default_alias,
        family="fast_flash" if prefer_fast else "thinking_flash",
        thinking="low" if prefer_fast else "high",
        quota=None,
        degraded=False,
        reason=f"no candidate inventory available; defaulting to {default_alias!r}",
        fallback_chain=(default_alias,),
    )


def resolve_models(
    candidates: list[ModelCandidate],
    *,
    config: dict[str, Any] | None = None,
    pro_quota_floor: float | None = None,
    swarm_quota_floor: float | None = None,
    prefer_pro_review: bool = False,
    overrides: dict[str, str] | None = None,
) -> ResolutionReport:
    """Resolve role-to-model routing decisions with quota floors and swarm eligibility."""
    cfg = config or {}
    pro_floor = float(
        pro_quota_floor if pro_quota_floor is not None else cfg.get("pro_quota_floor", DEFAULT_PRO_QUOTA_FLOOR)
    )
    flash_floor = float(
        swarm_quota_floor if swarm_quota_floor is not None else cfg.get("swarm_quota_floor", DEFAULT_SWARM_QUOTA_FLOOR)
    )
    explicit = overrides or {}

    roles: dict[str, ResolvedRoleModel] = {}
    for role in ("coordinator", "planner", "spec_reviewer"):
        env_key = f"FLOW_{role.upper()}_MODEL"
        ov = explicit.get(role) or os.environ.get(env_key, "").strip() or None
        roles[role] = _pick_frontier_role(role, candidates, pro_floor, ov)

    exec_override = explicit.get("executor") or os.environ.get("FLOW_EXECUTOR_MODEL", "").strip() or None
    roles["executor"] = _pick_worker_role(
        "executor",
        candidates,
        prefer_fast=False,
        prefer_pro=False,
        pro_floor=pro_floor,
        override_model=exec_override,
    )
    rev_override = explicit.get("reviewer") or os.environ.get("FLOW_REVIEWER_MODEL", "").strip() or None
    for role in ("verifier", "code_reviewer", "quality_reviewer"):
        ov = explicit.get(role) or rev_override
        roles[role] = _pick_worker_role(
            role,
            candidates,
            prefer_fast=False,
            prefer_pro=prefer_pro_review,
            pro_floor=pro_floor,
            override_model=ov,
        )

    scout_override = explicit.get("scout") or os.environ.get("FLOW_SCOUT_MODEL", "").strip() or None
    roles["scout_heavy"] = _pick_worker_role(
        "scout_heavy",
        candidates,
        prefer_fast=False,
        prefer_pro=False,
        pro_floor=pro_floor,
        override_model=explicit.get("scout_heavy") or scout_override,
    )
    roles["scout_narrow"] = _pick_worker_role(
        "scout_narrow",
        candidates,
        prefer_fast=True,
        prefer_pro=False,
        pro_floor=pro_floor,
        override_model=explicit.get("scout_narrow") or scout_override,
    )

    planning_degraded = roles["planner"].degraded or roles["coordinator"].degraded
    degraded_reason = (
        roles["planner"].reason
        if roles["planner"].degraded
        else (roles["coordinator"].reason if roles["coordinator"].degraded else None)
    )

    exec_quota = roles["executor"].quota
    verifier_quota = roles["verifier"].quota
    if exec_quota is not None and exec_quota <= flash_floor:
        swarm_ok = False
        swarm_reason = (
            f"worker Flash model {roles['executor'].model!r} quota {exec_quota:.0f}% "
            f"is at or below {flash_floor:.0f}% swarm floor; using chapter_batch"
        )
    elif verifier_quota is not None and verifier_quota <= flash_floor:
        swarm_ok = False
        swarm_reason = (
            f"verifier model {roles['verifier'].model!r} quota {verifier_quota:.0f}% "
            f"is at or below {flash_floor:.0f}% swarm floor; using chapter_batch"
        )
    else:
        swarm_ok = True
        q_label = "n/a" if exec_quota is None else f"{exec_quota:.0f}%"
        swarm_reason = f"worker model {roles['executor'].model!r} quota ({q_label}) exceeds {flash_floor:.0f}% floor"

    return ResolutionReport(
        pro_quota_floor=pro_floor,
        swarm_quota_floor=flash_floor,
        planning_quality="degraded" if planning_degraded else "standard",
        degraded_reason=degraded_reason,
        small_swarm_quota_ok=swarm_ok,
        swarm_quota_reason=swarm_reason,
        roles=roles,
    )


def materialize_runtime_agents(report: ResolutionReport, out_dir: Path) -> dict[str, str]:
    """Write ephemeral conversation-scoped ``runtime-<role>/agent.json`` profiles into ``out_dir``."""
    out_dir.mkdir(parents=True, exist_ok=True)
    created: dict[str, str] = {}
    for role_name, resolved in report.roles.items():
        if resolved.runtime_target == "inherit":
            continue
        slug = f"runtime-{role_name.replace('_', '-')}"
        profile_dir = out_dir / slug
        profile_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "name": slug,
            "role": role_name,
            "model": resolved.runtime_target,
            "requested_model": resolved.model,
            "disable_model_selection": True,
        }
        target_file = profile_dir / "agent.json"
        target_file.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        created[role_name] = str(target_file)
    return created


def _split_frontmatter(text: str) -> tuple[dict[str, Any] | None, str]:
    """Parse leading YAML frontmatter into scalar and string-list values."""
    normalized = text.replace("\r\n", "\n")
    if not normalized.startswith("---\n"):
        return None, normalized
    end_idx = normalized.find("\n---\n", 4)
    if end_idx == -1:
        return None, normalized
    raw_yaml = normalized[4:end_idx]
    body = normalized[end_idx + 5 :]
    result: dict[str, Any] = {}
    current_key: str | None = None
    for raw_line in raw_yaml.splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        line = raw_line.strip()
        if indent == 0 and ":" in line and not line.startswith("-"):
            key, val_part = line.split(":", 1)
            current_key = key.strip()
            val = val_part.strip()
            if not val:
                result[current_key] = []
            elif val.startswith("[") and val.endswith("]"):
                inner = val[1:-1].strip()
                result[current_key] = (
                    [item.strip().strip("'\"") for item in inner.split(",") if item.strip()] if inner else []
                )
            else:
                result[current_key] = val.strip("'\"")
        elif current_key is not None and line.startswith("- "):
            existing = result.setdefault(current_key, [])
            if isinstance(existing, list):
                existing.append(line[2:].strip().strip("'\""))
    return result, body


def _normalize_declared_paths(fm: dict[str, Any]) -> tuple[str, ...]:
    """Extract normalized write-target repository paths from task ``files:`` and ``tests:``."""
    paths: list[str] = []
    for key in ("files", "tests"):
        raw = fm.get(key)
        if not isinstance(raw, list):
            continue
        for item in raw:
            cleaned = str(item).split("::", 1)[0].strip().strip("/")
            if not cleaned or cleaned.startswith(".agents/bundles"):
                continue
            if cleaned not in paths:
                paths.append(cleaned)
    return tuple(paths)


def check_chapter_disjoint(
    bundle_root: Path,
    flow_id: str,
    chapter_id: str,
    *,
    harness: str = "agy",
    flash_quota: float | None = None,
    swarm_quota_floor: float = DEFAULT_SWARM_QUOTA_FLOOR,
) -> DisjointPlan:
    """Determine whether active chapter tasks qualify for bounded disjoint ``small_swarm`` execution."""
    if harness.strip().lower() not in ("agy", "antigravity"):
        return DisjointPlan(
            mode="chapter_batch",
            reason=f"harness {harness!r} executes chapter batches sequentially rather than native swarm",
            writer_count=0,
            verifier_count=0,
            total_workers=0,
            ready_task_ids=(),
            conflicts=(),
            assignments=(),
        )

    if flash_quota is not None and flash_quota <= swarm_quota_floor:
        return DisjointPlan(
            mode="chapter_batch",
            reason=f"worker Flash quota {flash_quota:.0f}% <= {swarm_quota_floor:.0f}% swarm floor",
            writer_count=0,
            verifier_count=0,
            total_workers=0,
            ready_task_ids=(),
            conflicts=(),
            assignments=(),
        )

    tasks_dir = bundle_root / "specs" / flow_id / "chapters" / chapter_id / "tasks"
    if not tasks_dir.is_dir():
        return DisjointPlan(
            mode="chapter_batch",
            reason=f"chapter tasks directory missing: {tasks_dir}",
            writer_count=0,
            verifier_count=0,
            total_workers=0,
            ready_task_ids=(),
            conflicts=(),
            assignments=(),
        )

    task_files = sorted(p for p in tasks_dir.glob("*.md") if p.name != "index.md")
    parsed_tasks: list[dict[str, Any]] = []
    closed_ids: set[str] = set()

    for tf in task_files:
        fm, _ = _split_frontmatter(tf.read_text(encoding="utf-8"))
        if fm is None:
            continue
        stem_id = tf.name.split("-", 1)[0]
        tid = str(fm.get("id") or stem_id).strip()
        state = str(fm.get("state") or "pending").strip().lower()
        deps_raw = fm.get("depends_on")
        deps = [str(d).strip() for d in deps_raw] if isinstance(deps_raw, list) else []
        if state in _CLOSED_TASK_STATES:
            closed_ids.update({tid, stem_id, tid.split(":")[-1]})
            continue
        parsed_tasks.append(
            {
                "id": tid,
                "stem": stem_id,
                "rel_path": f"tasks/{tf.name}",
                "deps": deps,
                "owned_paths": _normalize_declared_paths(fm),
            }
        )

    if len(parsed_tasks) < 2:
        return DisjointPlan(
            mode="chapter_batch",
            reason=f"chapter has {len(parsed_tasks)} open task(s); requires 2-4 disjoint tasks for small_swarm",
            writer_count=0,
            verifier_count=0,
            total_workers=0,
            ready_task_ids=tuple(item["id"] for item in parsed_tasks),
            conflicts=(),
            assignments=(),
        )

    if len(parsed_tasks) > MAX_SWARM_WORKERS:
        return DisjointPlan(
            mode="chapter_batch",
            reason=f"chapter has {len(parsed_tasks)} open tasks exceeding 4-task cap; use chapter_batch",
            writer_count=0,
            verifier_count=0,
            total_workers=0,
            ready_task_ids=(),
            conflicts=(),
            assignments=(),
        )

    ready_tasks: list[dict[str, Any]] = []
    for item in parsed_tasks:
        unresolved_deps = [d for d in item["deps"] if d and d not in closed_ids]
        if not unresolved_deps:
            ready_tasks.append(item)

    if len(ready_tasks) < 2:
        return DisjointPlan(
            mode="chapter_batch",
            reason="fewer than 2 open tasks have satisfied dependencies for parallel execution",
            writer_count=0,
            verifier_count=0,
            total_workers=0,
            ready_task_ids=tuple(item["id"] for item in ready_tasks),
            conflicts=(),
            assignments=(),
        )

    undeclared = [item["id"] for item in ready_tasks if not item["owned_paths"]]
    if undeclared:
        return DisjointPlan(
            mode="chapter_batch",
            reason=f"tasks missing explicit files/tests write declarations cannot prove disjointness: {undeclared}",
            writer_count=0,
            verifier_count=0,
            total_workers=0,
            ready_task_ids=tuple(item["id"] for item in ready_tasks),
            conflicts=(),
            assignments=(),
        )

    path_owners: dict[str, list[str]] = {}
    for item in ready_tasks:
        for rel_p in item["owned_paths"]:
            path_owners.setdefault(rel_p, []).append(item["id"])
    conflicts = tuple(
        sorted(f"{path} ({', '.join(owners)})" for path, owners in path_owners.items() if len(owners) > 1)
    )
    if conflicts:
        return DisjointPlan(
            mode="chapter_batch",
            reason="overlapping files/tests across chapter tasks; falling back to sequential chapter_batch",
            writer_count=0,
            verifier_count=0,
            total_workers=0,
            ready_task_ids=tuple(item["id"] for item in ready_tasks),
            conflicts=conflicts,
            assignments=(),
        )

    buckets: list[list[dict[str, Any]]] = [[item] for item in ready_tasks[:MAX_SWARM_WRITERS]]
    for extra_idx, extra_task in enumerate(ready_tasks[MAX_SWARM_WRITERS:]):
        buckets[extra_idx % MAX_SWARM_WRITERS].append(extra_task)

    assignments = tuple(
        SwarmAssignment(
            worker_name=f"writer-{idx}",
            task_ids=tuple(t["id"] for t in group),
            task_paths=tuple(t["rel_path"] for t in group),
            owned_paths=tuple(p for t in group for p in t["owned_paths"]),
        )
        for idx, group in enumerate(buckets, start=1)
    )
    writer_count = len(assignments)
    verifier_count = 1
    return DisjointPlan(
        mode="small_swarm",
        reason=(
            f"disjoint write sets across {len(ready_tasks)} ready tasks and Flash quota above {swarm_quota_floor:.0f}%"
        ),
        writer_count=writer_count,
        verifier_count=verifier_count,
        total_workers=writer_count + verifier_count,
        ready_task_ids=tuple(item["id"] for item in ready_tasks),
        conflicts=(),
        assignments=assignments,
    )


def _read_models_source(path_arg: str) -> str:
    """Read raw models JSON or quota text from file path or stdin ('-')."""
    if path_arg == "-":
        return sys.stdin.read()
    return Path(path_arg).read_text(encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    """Run quota-aware model resolution, runtime profile generation, or chapter disjoint checks."""
    parser = argparse.ArgumentParser(description="Flow quota-aware model router and disjointness gate.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    for cmd_name in ("inspect", "resolve", "materialize-agents"):
        sub = subparsers.add_parser(cmd_name)
        sub.add_argument("--models-json", default="", help="Path to models JSON/text ('-' for stdin).")
        sub.add_argument("--project", default=".", help="Workspace root containing optional .agents/setup-state.json.")
        sub.add_argument("--config", default="", help="Optional path to local models.json config.")
        sub.add_argument(
            "--pro-quota-floor",
            type=float,
            default=None,
            help="Minimum quota percentage for Pro planning roles.",
        )
        sub.add_argument(
            "--swarm-quota-floor",
            type=float,
            default=None,
            help="Strict quota percentage floor for Flash swarms.",
        )
        sub.add_argument("--prefer-pro-review", action="store_true", help="Prefer Pro review models when >= floor.")
        if cmd_name == "materialize-agents":
            sub.add_argument("--out-dir", required=True, help="Target runtime .agents/agents directory.")

    disjoint_parser = subparsers.add_parser("check-disjoint")
    disjoint_parser.add_argument("--bundle", default=".agents/bundles", help="Path to OKF bundle root.")
    disjoint_parser.add_argument("--flow", required=True, help="Flow slug under specs/.")
    disjoint_parser.add_argument("--chapter", required=True, help="Chapter directory slug.")
    disjoint_parser.add_argument("--harness", default="agy", help="Host harness name.")
    disjoint_parser.add_argument(
        "--flash-quota",
        type=float,
        default=None,
        help="Live worker Flash remaining quota percent.",
    )
    disjoint_parser.add_argument("--swarm-quota-floor", type=float, default=DEFAULT_SWARM_QUOTA_FLOOR)

    ns = parser.parse_args(argv)
    if ns.command == "check-disjoint":
        plan = check_chapter_disjoint(
            Path(ns.bundle),
            ns.flow,
            ns.chapter,
            harness=ns.harness,
            flash_quota=ns.flash_quota,
            swarm_quota_floor=ns.swarm_quota_floor,
        )
        print(json.dumps(plan.to_dict(), indent=2))
        return 0

    project_root = Path(ns.project).resolve()
    cfg_path = Path(ns.config).expanduser() if ns.config else None
    cfg = load_local_model_config(project_root=project_root, config_path=cfg_path)
    raw_models = _read_models_source(ns.models_json) if ns.models_json else ""
    candidates = parse_models_input(raw_models, cfg)
    report = resolve_models(
        candidates,
        config=cfg,
        pro_quota_floor=ns.pro_quota_floor,
        swarm_quota_floor=ns.swarm_quota_floor,
        prefer_pro_review=bool(getattr(ns, "prefer_pro_review", False)),
    )
    if ns.command == "materialize-agents":
        written = materialize_runtime_agents(report, Path(ns.out_dir))
        print(json.dumps({"materialized": written, "resolution": report.to_dict()}, indent=2))
        return 0

    print(json.dumps(report.to_dict(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

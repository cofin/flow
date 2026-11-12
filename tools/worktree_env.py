"""Git worktree environment bootstrap, shared-vs-main bundle routing, and fallback sync."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import stat
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

__all__ = (
    "LINKED_ENV_ARTIFACTS",
    "WorktreeEnvironment",
    "bootstrap_worktree",
    "inspect_worktree",
    "is_link_or_junction",
    "main",
    "resolve_git_main_worktree",
    "sync_main_bundle_to_worktree",
    "sync_worktree_bundle_to_main",
)

LINKED_ENV_ARTIFACTS: tuple[str, ...] = (
    ".venv",
    "node_modules",
    "uv.toml",
    ".npmrc",
    ".python-version",
)

_SKIP_SYNC_NAMES: frozenset[str] = frozenset(
    {
        "worktrees",
        "scratch",
        "studio-live-state.json",
    }
)


@dataclass(frozen=True, slots=True)
class WorktreeEnvironment:
    """Resolved Git worktree and Flow bundle routing metadata."""

    project_dir: str
    main_worktree: str | None
    is_linked_worktree: bool
    has_flow: bool
    ignore_policy: str
    bundle_rel: str
    target_agents_dir: str | None
    target_bundle_dir: str | None
    routing_mode: str
    bundle_writable: bool
    linked_artifacts: tuple[str, ...]
    warnings: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        """Serialize environment status to a JSON-compatible dictionary."""
        data = asdict(self)
        data["linked_artifacts"] = list(self.linked_artifacts)
        data["warnings"] = list(self.warnings)
        return data


def resolve_git_main_worktree(project_dir: Path) -> Path | None:
    """Return the primary Git checkout root for ``project_dir``, or ``None`` if not in Git."""
    resolved_proj = project_dir.resolve()
    git_bin = shutil.which("git")
    if git_bin is None:
        return None

    proc = subprocess.run(
        [git_bin, "-C", str(resolved_proj), "rev-parse", "--git-common-dir"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if proc.returncode != 0:
        return None

    raw_common = proc.stdout.strip()
    if not raw_common:
        return None

    common_path = Path(raw_common)
    if not common_path.is_absolute():
        common_path = (resolved_proj / common_path).resolve()
    else:
        common_path = common_path.resolve()

    if common_path.name == ".git":
        return common_path.parent
    if common_path.parent.name == ".git":
        return common_path.parent.parent
    return common_path.parent


def is_link_or_junction(path: Path) -> bool:
    """Return True when ``path`` is a POSIX symlink or Windows symlink/NTFS junction."""
    if path.is_symlink():
        return True
    is_junction = getattr(os.path, "isjunction", None)
    if callable(is_junction) and bool(is_junction(path)):
        return True
    if os.name == "nt":
        try:
            st = os.lstat(path)
            reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x0400)
            return bool(getattr(st, "st_file_attributes", 0) & reparse_flag)
        except OSError:
            return False
    return False


def inspect_worktree(project_dir: Path) -> WorktreeEnvironment:
    """Inspect ``project_dir`` without mutating symlinks on disk."""
    return _evaluate_worktree(project_dir, create_links=False)


def bootstrap_worktree(project_dir: Path) -> WorktreeEnvironment:
    """Inspect ``project_dir`` and create missing ``.venv``/``node_modules``/``.agents`` links in worktrees."""
    return _evaluate_worktree(project_dir, create_links=True)


def sync_main_bundle_to_worktree(project_dir: Path) -> dict[str, Any]:
    """Seed an isolated linked worktree's ``.agents`` directory from the primary checkout when unsymlinked."""
    resolved_proj = project_dir.resolve()
    main_wt = resolve_git_main_worktree(resolved_proj)
    if main_wt is None or main_wt == resolved_proj:
        raise ValueError(f"{resolved_proj} is not a linked Git worktree")

    src_agents = main_wt / ".agents"
    dst_agents = resolved_proj / ".agents"
    if not src_agents.exists():
        raise FileNotFoundError(f"No primary checkout .agents directory at {src_agents}")
    if is_link_or_junction(dst_agents) and dst_agents.resolve() == src_agents.resolve():
        return {
            "status": "noop_already_symlinked",
            "main_worktree": str(main_wt),
            "copied_files": [],
            "merged_catalogs": [],
        }

    return _merge_bundle_trees(src_agents, dst_agents, str(main_wt))


def sync_worktree_bundle_to_main(project_dir: Path) -> dict[str, Any]:
    """Merge non-conflicting bundle artifacts from an isolated worktree copy back into the main checkout."""
    resolved_proj = project_dir.resolve()
    main_wt = resolve_git_main_worktree(resolved_proj)
    if main_wt is None or main_wt == resolved_proj:
        raise ValueError(f"{resolved_proj} is not a linked Git worktree")

    src_agents = resolved_proj / ".agents"
    dst_agents = main_wt / ".agents"
    if not src_agents.exists():
        raise FileNotFoundError(f"No worktree .agents directory at {src_agents}")
    if is_link_or_junction(src_agents) and src_agents.resolve() == dst_agents.resolve():
        return {
            "status": "noop_already_symlinked",
            "main_worktree": str(main_wt),
            "copied_files": [],
            "merged_catalogs": [],
        }

    return _merge_bundle_trees(src_agents, dst_agents, str(main_wt))


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for inspecting, bootstrapping, or syncing Git worktree environments."""
    parser = argparse.ArgumentParser(description="Inspect or bootstrap Flow Git worktree symlinks and bundle routing.")
    parser.add_argument("--project", type=Path, default=Path.cwd(), help="Target workspace or worktree directory.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--status", action="store_true", help="Inspect worktree state without creating symlinks.")
    mode.add_argument(
        "--bootstrap",
        action="store_true",
        help="Create missing .venv/node_modules and local-only .agents symlinks in linked worktrees.",
    )
    mode.add_argument(
        "--seed-from-main",
        "--from-main",
        dest="seed_from_main",
        action="store_true",
        help="Seed isolated worktree .agents files from the primary checkout.",
    )
    mode.add_argument(
        "--sync-to-main",
        "--to-main",
        dest="sync_to_main",
        action="store_true",
        help="Merge isolated worktree .agents changes back into the primary checkout.",
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON output.")
    args = parser.parse_args(argv)

    if args.seed_from_main or args.sync_to_main:
        try:
            report = (
                sync_main_bundle_to_worktree(args.project)
                if args.seed_from_main
                else sync_worktree_bundle_to_main(args.project)
            )
        except (FileNotFoundError, ValueError) as exc:
            sys.stderr.write(f"ERROR: {exc}\n")
            return 1
        if args.json:
            sys.stdout.write(json.dumps(report) + "\n")
        else:
            direction = "from" if args.seed_from_main else "to"
            sys.stdout.write(
                f"Synced {len(report['copied_files'])} file(s) and {len(report['merged_catalogs'])} catalog(s) "
                f"{direction} {report['main_worktree']}.\n"
            )
        return 0

    env_info = bootstrap_worktree(args.project) if args.bootstrap else inspect_worktree(args.project)
    if args.json:
        sys.stdout.write(json.dumps(env_info.to_dict()) + "\n")
        return 0

    sys.stdout.write(
        f"routing_mode={env_info.routing_mode} ignore_policy={env_info.ignore_policy} "
        f"target_bundle={env_info.target_bundle_dir or 'none'} writable={env_info.bundle_writable}\n"
    )
    if env_info.linked_artifacts:
        sys.stdout.write(f"linked_artifacts={','.join(env_info.linked_artifacts)}\n")
    for warning in env_info.warnings:
        sys.stdout.write(f"warning: {warning}\n")
    return 0


def _evaluate_worktree(project_dir: Path, *, create_links: bool) -> WorktreeEnvironment:
    """Compute worktree routing and optionally create environment and bundle symlinks."""
    resolved_proj = project_dir.resolve()
    main_wt = resolve_git_main_worktree(resolved_proj)
    is_linked = main_wt is not None and main_wt != resolved_proj

    linked_artifacts: list[str] = []
    warnings: list[str] = []

    if is_linked and main_wt is not None:
        for artifact in LINKED_ENV_ARTIFACTS:
            dst = resolved_proj / artifact
            src = main_wt / artifact
            if is_link_or_junction(dst):
                linked_artifacts.append(artifact)
                continue
            if not dst.exists() and src.exists() and create_links:
                if _safe_symlink(src, dst):
                    linked_artifacts.append(artifact)
                else:
                    warnings.append(f"Could not link {artifact} from {main_wt}")

    local_agents = resolved_proj / ".agents"
    main_agents = main_wt / ".agents" if main_wt is not None else None

    setup_data, setup_owner = _load_setup_state(resolved_proj, main_wt)
    bundle_rel = str(setup_data.get("bundle_root") or ".agents/bundles").strip()
    ignore_policy = _detect_ignore_policy(setup_data, setup_owner or main_wt or resolved_proj)

    has_local_agents = local_agents.exists()
    has_main_agents = main_agents is not None and main_agents.exists()
    has_flow = has_local_agents or has_main_agents

    if not has_flow:
        return WorktreeEnvironment(
            project_dir=str(resolved_proj),
            main_worktree=str(main_wt) if main_wt is not None else None,
            is_linked_worktree=is_linked,
            has_flow=False,
            ignore_policy=ignore_policy,
            bundle_rel=bundle_rel,
            target_agents_dir=None,
            target_bundle_dir=None,
            routing_mode="none",
            bundle_writable=False,
            linked_artifacts=tuple(linked_artifacts),
            warnings=tuple(warnings),
        )

    if not is_linked or main_wt is None:
        target_bundle = resolved_proj / bundle_rel
        return WorktreeEnvironment(
            project_dir=str(resolved_proj),
            main_worktree=str(main_wt) if main_wt is not None else None,
            is_linked_worktree=False,
            has_flow=True,
            ignore_policy=ignore_policy,
            bundle_rel=bundle_rel,
            target_agents_dir=str(local_agents),
            target_bundle_dir=str(target_bundle),
            routing_mode="primary-checkout",
            bundle_writable=_is_writable_dir(target_bundle),
            linked_artifacts=tuple(linked_artifacts),
            warnings=tuple(warnings),
        )

    if ignore_policy == "shared":
        target_bundle = resolved_proj / bundle_rel
        return WorktreeEnvironment(
            project_dir=str(resolved_proj),
            main_worktree=str(main_wt),
            is_linked_worktree=True,
            has_flow=True,
            ignore_policy="shared",
            bundle_rel=bundle_rel,
            target_agents_dir=str(local_agents),
            target_bundle_dir=str(target_bundle),
            routing_mode="shared-worktree",
            bundle_writable=_is_writable_dir(target_bundle),
            linked_artifacts=tuple(linked_artifacts),
            warnings=tuple(warnings),
        )

    assert main_agents is not None
    if not local_agents.exists() and not is_link_or_junction(local_agents) and has_main_agents and create_links:
        if _safe_symlink(main_agents, local_agents):
            linked_artifacts.append(".agents")
        else:
            warnings.append(f"Could not symlink .agents to {main_agents}")
    elif is_link_or_junction(local_agents):
        linked_artifacts.append(".agents")
    elif local_agents.is_dir() and has_main_agents:
        warnings.append(
            f"Worktree contains an unlinked .agents copy while policy is local-only; "
            f"authoritative bundle is {main_wt / bundle_rel} (merge back with worktree_env.py --sync-to-main)."
        )

    target_bundle = main_wt / bundle_rel
    writable = _is_writable_dir(target_bundle)
    if not writable:
        warnings.append(
            f"Main checkout bundle {target_bundle} is read-only from this environment; "
            "run Flow state mutations in the main checkout or grant unsandboxed write access."
        )

    return WorktreeEnvironment(
        project_dir=str(resolved_proj),
        main_worktree=str(main_wt),
        is_linked_worktree=True,
        has_flow=True,
        ignore_policy="local-only",
        bundle_rel=bundle_rel,
        target_agents_dir=str(main_agents),
        target_bundle_dir=str(target_bundle),
        routing_mode="local-only-main",
        bundle_writable=writable,
        linked_artifacts=tuple(linked_artifacts),
        warnings=tuple(warnings),
    )


def _load_setup_state(project_dir: Path, main_wt: Path | None) -> tuple[dict[str, Any], Path | None]:
    """Read ``.agents/setup-state.json`` from ``project_dir`` or ``main_wt``."""
    candidates = [project_dir]
    if main_wt is not None and main_wt != project_dir:
        candidates.insert(0, main_wt)

    for root in candidates:
        state_file = root / ".agents" / "setup-state.json"
        if state_file.is_file():
            try:
                parsed = json.loads(state_file.read_text(encoding="utf-8"))
                if isinstance(parsed, dict):
                    return parsed, root
            except (OSError, json.JSONDecodeError):
                continue
    return {}, None


def _detect_ignore_policy(setup_data: dict[str, Any], repo_root: Path) -> str:
    """Resolve ``shared`` vs ``local-only`` tracking policy for ``.agents/``."""
    prefs = setup_data.get("workflow_preferences")
    if isinstance(prefs, dict):
        policy = str(prefs.get("ignore_policy") or "").strip()
        if policy in ("shared", "local-only"):
            return policy

    git_bin = shutil.which("git")
    if git_bin is not None:
        proc = subprocess.run(
            [git_bin, "-C", str(repo_root), "ls-files", "--error-unmatch", ".agents/setup-state.json"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        if proc.returncode == 0:
            return "shared"

        ign = subprocess.run(
            [git_bin, "-C", str(repo_root), "check-ignore", "-q", ".agents"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        if ign.returncode == 0:
            return "local-only"

    return "shared" if (repo_root / ".agents" / "setup-state.json").is_file() else "local-only"


def _safe_symlink(src: Path, dst: Path) -> bool:
    """Create a symlink from ``dst`` pointing to ``src``, falling back to junctions on Windows."""
    try:
        dst.symlink_to(src, target_is_directory=src.is_dir())
        return True
    except OSError:
        if os.name == "nt" and src.is_dir():
            proc = subprocess.run(
                ["cmd", "/c", "mklink", "/J", str(dst), str(src)],
                capture_output=True,
                text=True,
                check=False,
            )
            return proc.returncode == 0
        return False


def _is_writable_dir(target_dir: Path) -> bool:
    """Check whether ``target_dir`` (or its nearest existing ancestor) allows writes."""
    probe = target_dir
    while not probe.exists() and probe.parent != probe:
        probe = probe.parent
    return probe.exists() and os.access(probe, os.W_OK)


def _merge_bundle_trees(src_agents: Path, dst_agents: Path, main_wt_str: str) -> dict[str, Any]:
    """Copy non-conflicting files and merge ``index.md`` / ``log.md`` lines from ``src_agents`` into ``dst_agents``."""
    copied_files: list[str] = []
    merged_catalogs: list[str] = []
    dst_agents.mkdir(parents=True, exist_ok=True)

    for src_item in sorted(src_agents.rglob("*")):
        rel = src_item.relative_to(src_agents)
        if any(part in _SKIP_SYNC_NAMES or part.endswith((".duckdb", ".duckdb.wal")) for part in rel.parts):
            continue
        dst_item = dst_agents / rel
        if src_item.is_dir():
            dst_item.mkdir(parents=True, exist_ok=True)
            continue
        if not src_item.is_file():
            continue

        if src_item.name in ("index.md", "log.md") and dst_item.is_file():
            if _merge_line_file(src_item, dst_item, prepend=(src_item.name == "log.md")):
                merged_catalogs.append(rel.as_posix())
            continue

        dst_item.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_item, dst_item)
        copied_files.append(rel.as_posix())

    return {
        "status": "synced",
        "main_worktree": main_wt_str,
        "copied_files": copied_files,
        "merged_catalogs": merged_catalogs,
    }


def _merge_line_file(src_file: Path, dst_file: Path, *, prepend: bool) -> bool:
    """Merge non-duplicate bullet or log lines from ``src_file`` into ``dst_file``."""
    src_lines = src_file.read_text(encoding="utf-8").splitlines()
    dst_text = dst_file.read_text(encoding="utf-8")
    dst_lines = dst_text.splitlines()
    existing = {line.strip() for line in dst_lines if line.strip()}

    additions = [
        line
        for line in src_lines
        if line.strip() and not line.lstrip().startswith("#") and line.strip() not in existing
    ]
    if not additions:
        return False

    if prepend:
        insert_idx = 0
        for idx, line in enumerate(dst_lines):
            if line.lstrip().startswith("#") or not line.strip():
                insert_idx = idx + 1
            else:
                break
        merged = [*dst_lines[:insert_idx], *additions, *dst_lines[insert_idx:]]
    else:
        merged = [*dst_lines, *additions]

    dst_file.write_text("\n".join(merged).rstrip() + "\n", encoding="utf-8")
    return True


if __name__ == "__main__":
    raise SystemExit(main())

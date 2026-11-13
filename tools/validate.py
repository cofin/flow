"""Validate multi-harness manifests, hooks, subagents, skills, workflows, and OKF v0.2 bundles."""

from __future__ import annotations

import argparse
import ast
import json
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
import tomllib
from datetime import datetime
from pathlib import Path
from typing import Any

from tools.worktree_env import is_link_or_junction

__all__ = (
    "COMPACT_TASK_HEADINGS",
    "EXPECTED_AGENTS",
    "EXPECTED_SKILLS",
    "MAX_CHAPTER_TASKS",
    "MAX_SKILL_DESCRIPTION_CHARS",
    "MAX_SKILL_FILE_BYTES",
    "MAX_TASK_ESTIMATED_LOC",
    "MAX_TASK_READ_SET",
    "MAX_TRUTH_BLOCK_LINES",
    "PLANNING_QUALITY_VALUES",
    "READONLY_AGENTS",
    "REPO_ROOT",
    "REQUIRED_SPEC_HEADINGS",
    "REQUIRED_TASK_HEADINGS",
    "RETIRED_PATHS",
    "main",
    "validate_agents",
    "validate_anti_sprawl",
    "validate_hooks",
    "validate_lockfile",
    "validate_manifests",
    "validate_markdown_links",
    "validate_okf_bundle",
    "validate_repository",
    "validate_schema_cards",
    "validate_skills",
    "validate_workflows",
)

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = REPO_ROOT / "skills"
AGENTS_DIR = REPO_ROOT / "agents"
CODEX_AGENTS_DIR = REPO_ROOT / ".codex" / "agents"

MAX_SKILL_FILE_BYTES = 24000
MAX_SKILL_DESCRIPTION_CHARS = 500
MAX_TRUTH_BLOCK_LINES = 40
MAX_CHAPTER_TASKS = 4
MAX_TASK_READ_SET = 6
MAX_TASK_ESTIMATED_LOC = 250
MAX_PLAN_SCHEMA_CARD_LINES = 120
MAX_EXECUTOR_SCHEMA_CARD_LINES = 95
SKILL_DESCRIPTION_PREFIX = "Use when"
FORBIDDEN_SKILL_DESCRIPTION_TERMS = (
    "Auto-activate",
    "Produces",
    "Expert knowledge",
    "Comprehensive",
)

OKF_DOCUMENT_STATUSES: frozenset[str] = frozenset({"draft", "stable", "deprecated"})
PLANNING_QUALITY_VALUES: frozenset[str] = frozenset({"standard", "degraded"})
OPEN_TASK_STATES: frozenset[str] = frozenset({"pending", "open", "in_progress", "blocked"})
DEFERRED_STATES: frozenset[str] = frozenset({"deferred", "skipped"})
KNOWN_CLAIM_HARNESSES: frozenset[str] = frozenset({"agy", "claude", "codex", "cursor", "opencode", "vscode", "cli"})
FORBIDDEN_WORKFLOW_AGENT_TYPES: frozenset[str] = frozenset(
    {
        "code-reviewer",
        "executor",
        "plan-generator",
        "prd-orchestrator",
        "quality-reviewer",
        "researcher",
    }
)
FORBIDDEN_TAG_STATE_WORDS: frozenset[str] = frozenset(
    {
        "active",
        "archived",
        "blocked",
        "closed",
        "completed",
        "deferred",
        "deprecated",
        "draft",
        "in-progress",
        "in_progress",
        "open",
        "pending",
        "planned",
        "skipped",
        "stable",
    }
)

REQUIRED_SPEC_HEADINGS: tuple[str, ...] = (
    "## 1. Specification, Context & Provenance",
    "## 2. Requirements, Concrete Contracts & Architecture",
    "## 3. Documentation & OKF Knowledge Plan",
    "## 4. Requirement-to-Task Traceability Matrix",
    "## 5. Implementation Plan",
    "## 6. Current State & Remaining Plan Snapshot",
)

REQUIRED_TASK_HEADINGS: tuple[str, ...] = (
    "## Objective & Scope Boundary",
    "## Bounded Read Manifest",
    "## Symbol & Signature Contracts",
    "## Edge Cases & Error Semantics",
    "## Public-Seam Test Blueprint",
    "## Verification",
    "## Acceptance Criteria",
    "## Notes & Discoveries",
)

COMPACT_TASK_HEADINGS: tuple[str, ...] = (
    "## Objective & Scope Boundary",
    "## Bounded Read Manifest",
    "## Contracts & Edge Cases",
    "## Test Matrix",
    "## Verification",
    "## Acceptance Criteria",
)

SCHEMA_CARD_REQUIRED_KEYS: tuple[str, ...] = (
    "type",
    "status",
    "state",
    "planning_quality",
    "planning_degraded_reason",
    "worksheet_format",
    "read_set",
    "estimated_loc",
    "sources",
    "tags",
)

EXPECTED_SKILLS: frozenset[str] = frozenset(
    {
        "debloat",
        "flow",
        "flow-completion",
        "flow-docs",
        "flow-execution",
        "flow-learn",
        "flow-planning",
        "flow-setup",
        "multi-harness-plugins",
        "okf",
    }
)

EXPECTED_AGENTS: frozenset[str] = frozenset(
    {
        "code-reviewer",
        "executor",
        "plan-generator",
        "prd-orchestrator",
        "quality-reviewer",
        "researcher",
    }
)

READONLY_AGENTS: frozenset[str] = frozenset(
    {
        "code-reviewer",
        "quality-reviewer",
        "researcher",
    }
)

REQUIRED_AGENT_H1_HEADINGS: tuple[str, ...] = (
    "# Role & Identity",
    "# Responsibilities",
    "# Verification & Constraints",
    "# Output Contract",
)

REQUIRED_READONLY_DISALLOWED_TOOLS: frozenset[str] = frozenset(
    {
        "Edit",
        "MultiEdit",
        "NotebookEdit",
        "Write",
    }
)

ALLOWED_ANTIGRAVITY_PLUGIN_KEYS: frozenset[str] = frozenset(
    {
        "$schema",
        "agents",
        "apps",
        "contextFileName",
        "description",
        "displayName",
        "excludeTools",
        "keywords",
        "license",
        "logo",
        "mcpServers",
        "name",
        "rules",
        "skills",
        "suggestedPrompts",
        "version",
    }
)

RETIRED_PATHS: tuple[str, ...] = (
    ".codex/INSTALL.md",
    ".codex/hooks.json",
    ".cursor/hooks.json",
    ".cursor/rules/flow.mdc",
    ".github/agents",
    ".github/copilot-instructions.md",
    ".githooks/pre-commit",
    ".opencode/INSTALL.md",
    ".opencode/agents",
    "CLAUDE.md",
    "commands",
    "contracts",
    "docs",
    "hooks/agy-pre-invocation.ps1",
    "hooks/agy-pre-invocation.sh",
    "hooks/block-dangerous-git.sh",
    "hooks/cursor-session-start.sh",
    "hooks/detect-env.ps1",
    "hooks/detect-env.sh",
    "hooks/hooks-agy.json",
    "hooks/hooks-codex.json",
    "hooks/primer.txt",
    "hooks/session-start.cmd",
    "hooks/session-start.js",
    "plugins/flow",
    "rules/flow-core.md",
    "skills/apilookup",
    "skills/architecture-critic",
    "skills/challenge",
    "skills/consensus",
    "skills/deepthink",
    "skills/devils-advocate",
    "skills/docgen",
    "skills/flow-state",
    "skills/flow-sync-status",
    "skills/performance-analyst",
    "skills/perspectives",
    "skills/security-auditor",
    "skills/tracer",
    "templates/agent/flow-instructions.md",
    "templates/agent/skills",
    "templates/antigravity",
    "templates/blueprints",
    "templates/opencode",
    "templates/styleguides",
)

PUBLIC_LOCK_SOURCE_HOSTS: frozenset[str] = frozenset({"pypi.org", "files.pythonhosted.org"})
_LOCK_URL_PATTERN = re.compile(r'https?://[^"\s]+')
_LINK_PATTERN = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
_FENCED_BLOCK_PATTERN = re.compile(r"```.*?```|~~~.*?~~~|`[^`\n]+`", re.DOTALL)
_MULTILINE_FENCE_PATTERN = re.compile(r"^[ \t]*(?:```|~~~).*?^[ \t]*(?:```|~~~)[^\n]*$", re.MULTILINE | re.DOTALL)
_PYTHON_FENCE_PATTERN = re.compile(r"^[ \t]*```python[ \t]*\n(.*?)^[ \t]*```[ \t]*$", re.MULTILINE | re.DOTALL)
_FOOTNOTE_DEF_PATTERN = re.compile(r"^\[\^([A-Za-z0-9_-]+)\]:\s+.+$", re.MULTILINE)
_TRUTH_START_PATTERN = re.compile(r"<!--\s*truth:\s*start\s*-->")
_TRUTH_END_PATTERN = re.compile(r"<!--\s*truth:\s*end\s*-->")
_BODY_HR_PATTERN = re.compile(r"^[ \t]*---[ \t]*$", re.MULTILINE)
_HISTORY_HEADING_PATTERN = re.compile(
    r"^[ \t]*#+[ \t]*(?:revision history|change history|changelog|decision history)(?:[ \t:]|$)",
    re.IGNORECASE | re.MULTILINE,
)
_STRUCK_CHECKLIST_PATTERN = re.compile(r"^[ \t]*-[ \t]*\[[^\]]*\][ \t]*~~", re.MULTILINE)
_TAG_SLUG_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_CHAPTER_DIR_PATTERN = re.compile(r"^ch\d{2}-[a-z0-9-]+$")
_HEX_SHA_PATTERN = re.compile(r"^[0-9a-fA-F]{7,40}$")
_CHECKLIST_LINE_PATTERN = re.compile(r"^[ \t]*-[ \t]*\[([ xX~!>-])\][ \t]*(.+)$", re.MULTILINE)
_CHECKLIST_SHA_PATTERN = re.compile(r"^\[([0-9a-fA-F]{7,40})\]")


def validate_repository(repo_root: Path = REPO_ROOT) -> list[str]:
    """Run all structural and multi-harness validation checks against ``repo_root``."""
    errors: list[str] = []
    errors.extend(validate_manifests(repo_root))
    errors.extend(validate_hooks(repo_root))
    errors.extend(validate_agents(repo_root))
    errors.extend(validate_skills(repo_root))
    errors.extend(validate_workflows(repo_root))
    errors.extend(validate_schema_cards(repo_root))
    errors.extend(validate_markdown_links(repo_root))
    errors.extend(validate_anti_sprawl(repo_root))
    errors.extend(validate_lockfile(repo_root))
    return errors


def validate_manifests(repo_root: Path = REPO_ROOT) -> list[str]:
    """Verify manifest existence, schema compliance, and version synchronization across all harnesses."""
    errors: list[str] = []
    pyproject_path = repo_root / "pyproject.toml"
    if not pyproject_path.is_file():
        return ["Missing pyproject.toml"]

    pyproject_data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    expected_version = str(pyproject_data.get("project", {}).get("version", ""))
    if not expected_version:
        errors.append("pyproject.toml is missing [project].version")

    json_manifests = (
        "package.json",
        "plugin.json",
        ".claude-plugin/plugin.json",
        ".claude-plugin/marketplace.json",
        ".codex-plugin/plugin.json",
        ".cursor-plugin/plugin.json",
        ".agents/plugins/marketplace.json",
    )
    loaded: dict[str, dict[str, Any]] = {}
    for rel_path in json_manifests:
        full_path = repo_root / rel_path
        if not full_path.is_file():
            errors.append(f"Missing manifest file: {rel_path}")
            continue
        try:
            data = json.loads(full_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"{rel_path}: invalid JSON ({exc})")
            continue
        if not isinstance(data, dict):
            errors.append(f"{rel_path}: root JSON value must be an object")
            continue
        loaded[rel_path] = data

    for rel_path in (
        "package.json",
        "plugin.json",
        ".claude-plugin/plugin.json",
        ".codex-plugin/plugin.json",
        ".cursor-plugin/plugin.json",
    ):
        data = loaded.get(rel_path)
        if data is not None and data.get("version") != expected_version:
            errors.append(
                f"{rel_path}: version {data.get('version')!r} does not match pyproject.toml {expected_version!r}"
            )

    claude_mp = loaded.get(".claude-plugin/marketplace.json")
    if claude_mp is not None:
        plugins = claude_mp.get("plugins")
        if not isinstance(plugins, list) or not plugins:
            errors.append(".claude-plugin/marketplace.json: missing non-empty plugins list")
        else:
            entry = plugins[0]
            if entry.get("version") != expected_version:
                errors.append(
                    f".claude-plugin/marketplace.json: plugin version {entry.get('version')!r} != {expected_version!r}"
                )
            if entry.get("source") != "./":
                errors.append(".claude-plugin/marketplace.json: plugins[0].source must be './'")

    codex_mp = loaded.get(".agents/plugins/marketplace.json")
    if codex_mp is not None:
        plugins = codex_mp.get("plugins")
        if not isinstance(plugins, list) or not plugins:
            errors.append(".agents/plugins/marketplace.json: missing non-empty plugins list")
        else:
            entry = plugins[0]
            source = entry.get("source", {})
            if not isinstance(source, dict) or source.get("path") != "./":
                errors.append(".agents/plugins/marketplace.json: plugins[0].source.path must be './'")

    agy_plugin = loaded.get("plugin.json")
    if agy_plugin is not None:
        extra_keys = sorted(set(agy_plugin.keys()) - ALLOWED_ANTIGRAVITY_PLUGIN_KEYS)
        if extra_keys:
            errors.append(f"plugin.json: disallowed Antigravity manifest keys: {extra_keys}")
        if agy_plugin.get("name") != "flow":
            errors.append("plugin.json: name must be 'flow'")
        if agy_plugin.get("displayName") != "Flow":
            errors.append("plugin.json: displayName must be 'Flow'")
        agy_logo = agy_plugin.get("logo")
        if agy_logo is not None and (not isinstance(agy_logo, str) or not (repo_root / agy_logo).is_file()):
            errors.append(f"plugin.json: logo {agy_logo!r} does not exist")

    claude_plugin = loaded.get(".claude-plugin/plugin.json")
    if claude_plugin is not None and claude_plugin.get("hooks") != "./hooks/hooks-claude.json":
        errors.append(".claude-plugin/plugin.json: hooks must be './hooks/hooks-claude.json'")

    codex_plugin = loaded.get(".codex-plugin/plugin.json")
    if codex_plugin is not None and codex_plugin.get("hooks") != "./hooks/hooks-claude.json":
        errors.append(".codex-plugin/plugin.json: hooks must be './hooks/hooks-claude.json'")

    cursor_plugin = loaded.get(".cursor-plugin/plugin.json")
    if cursor_plugin is not None:
        if cursor_plugin.get("hooks") != "./hooks/hooks-cursor.json":
            errors.append(".cursor-plugin/plugin.json: hooks must be './hooks/hooks-cursor.json'")
        cursor_logo = cursor_plugin.get("logo")
        if cursor_logo is not None and (not isinstance(cursor_logo, str) or not (repo_root / cursor_logo).is_file()):
            errors.append(f".cursor-plugin/plugin.json: logo {cursor_logo!r} does not exist")

    pkg_json = loaded.get("package.json")
    if pkg_json is not None:
        if pkg_json.get("main") != ".opencode/plugins/flow.js":
            errors.append("package.json: main must be '.opencode/plugins/flow.js'")
        pkg_exports = pkg_json.get("exports")
        if not isinstance(pkg_exports, dict) or any(
            pkg_exports.get(key) != "./.opencode/plugins/flow.js" for key in (".", "./server")
        ):
            errors.append("package.json: exports '.' and './server' must be './.opencode/plugins/flow.js'")
        pkg_files = pkg_json.get("files")
        if not isinstance(pkg_files, list) or not {".opencode/plugins/", "agents/", "skills/"} <= set(pkg_files):
            errors.append("package.json: files must include '.opencode/plugins/', 'agents/', and 'skills/'")

    vscode_dir = repo_root / "vscode-extension"
    if vscode_dir.is_dir():
        vscode_pkg_path = vscode_dir / "package.json"
        if not vscode_pkg_path.is_file():
            errors.append("Missing manifest file: vscode-extension/package.json")
        else:
            try:
                vscode_pkg = json.loads(vscode_pkg_path.read_text(encoding="utf-8"))
                if vscode_pkg.get("version") != expected_version:
                    errors.append(
                        f"vscode-extension/package.json: version {vscode_pkg.get('version')!r} "
                        f"does not match pyproject.toml {expected_version!r}"
                    )
                ext_main = str(vscode_pkg.get("main", ""))
                if not ext_main or not (vscode_dir / ext_main).is_file():
                    errors.append(f"vscode-extension/package.json: main {ext_main!r} does not exist")
                ext_icon = vscode_pkg.get("icon")
                if ext_icon is not None and (not isinstance(ext_icon, str) or not (vscode_dir / ext_icon).is_file()):
                    errors.append(f"vscode-extension/package.json: icon {ext_icon!r} does not exist")
            except json.JSONDecodeError as exc:
                errors.append(f"vscode-extension/package.json: invalid JSON ({exc})")

    sidecar_dir = repo_root / "sidecars" / "studio"
    if sidecar_dir.is_dir():
        sidecar_json_path = sidecar_dir / "sidecar.json"
        if not sidecar_json_path.is_file():
            errors.append("Missing sidecars/studio/sidecar.json")
        else:
            try:
                sidecar_cfg = json.loads(sidecar_json_path.read_text(encoding="utf-8"))
                if sidecar_cfg.get("has_web_ui") is not True:
                    errors.append("sidecars/studio/sidecar.json: has_web_ui must be true")
                views = sidecar_cfg.get("ui_config", {}).get("views", [])
                if not isinstance(views, list) or not views:
                    errors.append("sidecars/studio/sidecar.json: ui_config.views must be a non-empty list")
            except json.JSONDecodeError as exc:
                errors.append(f"sidecars/studio/sidecar.json: invalid JSON ({exc})")
        if not (sidecar_dir / "main.mjs").is_file():
            errors.append("Missing sidecars/studio/main.mjs")

    workflows_dir = repo_root / "workflows"
    if workflows_dir.is_dir():
        for wf_subdir in sorted(p for p in workflows_dir.iterdir() if p.is_dir()):
            wf_manifest = wf_subdir / "workflow.json"
            rel_wf = wf_manifest.relative_to(repo_root).as_posix()
            if not wf_manifest.is_file():
                errors.append(f"Missing {rel_wf}")
                continue
            try:
                wf_data = json.loads(wf_manifest.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                errors.append(f"{rel_wf}: invalid JSON ({exc})")
                continue
            if not str(wf_data.get("name", "")).strip():
                errors.append(f"{rel_wf}: missing workflow name")
            if not str(wf_data.get("description", "")).strip():
                errors.append(f"{rel_wf}: missing workflow description")
            entry_rel = str(wf_data.get("entry", "workflow.py"))
            if not wf_data.get("library", False) and not (wf_subdir / entry_rel).is_file():
                errors.append(f"{rel_wf}: missing entry script {entry_rel!r}")

    return errors


def validate_hooks(repo_root: Path = REPO_ROOT) -> list[str]:
    """Validate SessionStart and Stop hook configs, OpenCode V2 plugin entry, and sh + PowerShell execution."""
    errors: list[str] = []
    hook_script = repo_root / "hooks" / "session-start.sh"
    if not hook_script.is_file():
        return ["Missing hooks/session-start.sh"]

    ps1_script = repo_root / "hooks" / "session-start.ps1"
    if not ps1_script.is_file():
        errors.append("Missing hooks/session-start.ps1")

    stop_sh_script = repo_root / "hooks" / "stop-check.sh"
    if not stop_sh_script.is_file():
        errors.append("Missing hooks/stop-check.sh")

    stop_ps1_script = repo_root / "hooks" / "stop-check.ps1"
    if not stop_ps1_script.is_file():
        errors.append("Missing hooks/stop-check.ps1")

    agy_hooks_path = repo_root / "hooks.json"
    if not agy_hooks_path.is_file():
        errors.append("Missing root hooks.json for Google Antigravity")
    else:
        agy_hooks = json.loads(agy_hooks_path.read_text(encoding="utf-8"))
        session_start = agy_hooks.get("flow-session-start", {}).get("SessionStart")
        if not isinstance(session_start, list) or not session_start:
            errors.append("hooks.json: missing flow-session-start.SessionStart array")
        elif "matcher" in session_start[0]:
            errors.append("hooks.json: Antigravity SessionStart must be a flat array of command handlers")
        stop_handlers = agy_hooks.get("flow-stop-check", {}).get("Stop")
        if not isinstance(stop_handlers, list) or not stop_handlers:
            errors.append("hooks.json: missing flow-stop-check.Stop array")
        elif "matcher" in stop_handlers[0]:
            errors.append("hooks.json: Antigravity Stop must be a flat array of command handlers")

        for hook_group_name, group_spec in agy_hooks.items():
            if not isinstance(group_spec, dict):
                continue
            for flat_event in ("SessionStart", "PreInvocation", "PostInvocation", "Stop"):
                ev_list = group_spec.get(flat_event)
                if isinstance(ev_list, list) and ev_list and "matcher" in ev_list[0]:
                    if flat_event not in ("SessionStart", "Stop"):
                        errors.append(
                            f"hooks.json: {hook_group_name}.{flat_event} must be a flat array of command handlers"
                        )
            for tool_event in ("PreToolUse", "PostToolUse"):
                ev_list = group_spec.get(tool_event)
                if isinstance(ev_list, list) and ev_list and "matcher" not in ev_list[0]:
                    errors.append(f"hooks.json: {hook_group_name}.{tool_event} must use nested matcher format")

    claude_hooks_path = repo_root / "hooks" / "hooks-claude.json"
    if not claude_hooks_path.is_file():
        errors.append("Missing hooks/hooks-claude.json")
    else:
        claude_hooks = json.loads(claude_hooks_path.read_text(encoding="utf-8"))
        session_start = claude_hooks.get("hooks", {}).get("SessionStart")
        if not isinstance(session_start, list) or not session_start or "matcher" not in session_start[0]:
            errors.append("hooks/hooks-claude.json: SessionStart must use nested matcher format")
        else:
            handlers = session_start[0].get("hooks", [])
            if not isinstance(handlers, list) or not handlers:
                errors.append("hooks/hooks-claude.json: SessionStart[0].hooks must be a non-empty list")
            else:
                cmd_windows = str(handlers[0].get("commandWindows", ""))
                if "session-start.ps1" not in cmd_windows:
                    errors.append("hooks/hooks-claude.json: SessionStart handler must include commandWindows")
        stop_entries = claude_hooks.get("hooks", {}).get("Stop")
        if not isinstance(stop_entries, list) or not stop_entries or "matcher" not in stop_entries[0]:
            errors.append("hooks/hooks-claude.json: Stop must use nested matcher format")
        else:
            stop_handlers = stop_entries[0].get("hooks", [])
            if not isinstance(stop_handlers, list) or not stop_handlers:
                errors.append("hooks/hooks-claude.json: Stop[0].hooks must be a non-empty list")
            else:
                stop_win = str(stop_handlers[0].get("commandWindows", ""))
                if "stop-check.ps1" not in stop_win:
                    errors.append("hooks/hooks-claude.json: Stop handler must include commandWindows")
        post_tool_entries = claude_hooks.get("hooks", {}).get("PostToolUse", [])
        if isinstance(post_tool_entries, list) and any(item.get("matcher") == "*" for item in post_tool_entries):
            errors.append("hooks/hooks-claude.json: wildcard PostToolUse matcher '*' is forbidden due to tool latency")

    cursor_hooks_path = repo_root / "hooks" / "hooks-cursor.json"
    if not cursor_hooks_path.is_file():
        errors.append("Missing hooks/hooks-cursor.json")
    else:
        cursor_hooks = json.loads(cursor_hooks_path.read_text(encoding="utf-8"))
        cursor_events = cursor_hooks.get("hooks", {})
        if cursor_hooks.get("version") != 1 or "sessionStart" not in cursor_events:
            errors.append("hooks/hooks-cursor.json: must declare version 1 and hooks.sessionStart")
        cursor_stop = cursor_events.get("stop")
        if (
            not isinstance(cursor_stop, list)
            or not cursor_stop
            or not isinstance(cursor_stop[0].get("loop_limit"), int)
        ):
            errors.append("hooks/hooks-cursor.json: must declare hooks.stop with integer loop_limit")

    opencode_plugin = repo_root / ".opencode" / "plugins" / "flow.js"
    if not opencode_plugin.is_file():
        errors.append("Missing .opencode/plugins/flow.js")
    else:
        js_text = opencode_plugin.read_text(encoding="utf-8")
        if 'id: "flow"' not in js_text or "async setup(ctx)" not in js_text:
            errors.append(".opencode/plugins/flow.js: must export OpenCode V2 { id: 'flow', async setup(ctx) }")
        if "const summary = readBundleSummary" in js_text:
            errors.append(".opencode/plugins/flow.js: must invoke readBundleSummary dynamically per turn")
        if "experimental.chat.system.transform" in js_text or "systemMessage" in js_text:
            errors.append(
                ".opencode/plugins/flow.js: must not use V1 hooks; push context with event.system.push in"
                " ctx.session.hook('context')"
            )

    errors.extend(_run_session_start_smoke_checks(hook_script, ps1_script))
    if stop_sh_script.is_file():
        errors.extend(_run_stop_hook_smoke_checks(stop_sh_script, stop_ps1_script))

    return errors


def validate_agents(repo_root: Path = REPO_ROOT) -> list[str]:
    """Validate universal Markdown subagents and Codex CLI TOML subagent parity."""
    errors: list[str] = []
    agents_dir = repo_root / "agents"
    codex_dir = repo_root / ".codex" / "agents"

    if not agents_dir.is_dir():
        return ["Missing agents/ directory"]
    if not codex_dir.is_dir():
        return ["Missing .codex/agents/ directory"]

    md_names = {p.stem for p in agents_dir.glob("*.md")}
    toml_names = {p.stem for p in codex_dir.glob("*.toml")}

    if md_names != EXPECTED_AGENTS:
        errors.append(f"agents/*.md inventory {sorted(md_names)} != expected {sorted(EXPECTED_AGENTS)}")
    if toml_names != EXPECTED_AGENTS:
        errors.append(f".codex/agents/*.toml inventory {sorted(toml_names)} != expected {sorted(EXPECTED_AGENTS)}")

    for name in sorted(EXPECTED_AGENTS & md_names):
        md_path = agents_dir / f"{name}.md"
        frontmatter, body = _split_frontmatter(md_path.read_text(encoding="utf-8"))
        if frontmatter is None:
            errors.append(f"agents/{name}.md: missing YAML frontmatter")
            continue
        if frontmatter.get("name") != name:
            errors.append(f"agents/{name}.md: frontmatter name {frontmatter.get('name')!r} != {name!r}")
        if frontmatter.get("model") != "inherit":
            errors.append(f"agents/{name}.md: model must be 'inherit'")
        if frontmatter.get("mainAgent") is not False:
            errors.append(f"agents/{name}.md: mainAgent must be false")
        if frontmatter.get("subagent") is not True:
            errors.append(f"agents/{name}.md: subagent must be true")
        if frontmatter.get("commandExecutionPolicy") != "sandbox":
            errors.append(f"agents/{name}.md: commandExecutionPolicy must be 'sandbox'")

        skills_field = frontmatter.get("skills")
        if skills_field is not None:
            if not isinstance(skills_field, list):
                errors.append(f"agents/{name}.md: skills must be a YAML list when declared")
            else:
                unknown_skills = sorted(set(skills_field) - EXPECTED_SKILLS)
                if unknown_skills:
                    errors.append(f"agents/{name}.md: unknown skills in frontmatter: {unknown_skills}")

        for heading in REQUIRED_AGENT_H1_HEADINGS:
            if not re.search(rf"^{re.escape(heading)}\s*$", body, re.MULTILINE):
                errors.append(f"agents/{name}.md: missing required H1 heading {heading!r}")

        if name in READONLY_AGENTS:
            if frontmatter.get("readonly") is not True:
                errors.append(f"agents/{name}.md: read-only agent must declare readonly: true")
            disallowed = frontmatter.get("disallowedTools")
            if not isinstance(disallowed, list):
                errors.append(f"agents/{name}.md: disallowedTools must be a YAML list")
            elif not REQUIRED_READONLY_DISALLOWED_TOOLS.issubset(set(disallowed)):
                errors.append(
                    f"agents/{name}.md: disallowedTools must include {sorted(REQUIRED_READONLY_DISALLOWED_TOOLS)}"
                )

    for name in sorted(EXPECTED_AGENTS & toml_names):
        toml_path = codex_dir / f"{name}.toml"
        try:
            toml_data = tomllib.loads(toml_path.read_text(encoding="utf-8"))
        except tomllib.TOMLDecodeError as exc:
            errors.append(f".codex/agents/{name}.toml: invalid TOML ({exc})")
            continue
        if toml_data.get("name") != name:
            errors.append(f".codex/agents/{name}.toml: name must be {name!r}")
        if not str(toml_data.get("developer_instructions", "")).strip():
            errors.append(f".codex/agents/{name}.toml: missing developer_instructions")
        expected_sandbox = "read-only" if name in READONLY_AGENTS else "workspace-write"
        if toml_data.get("sandbox_mode") != expected_sandbox:
            errors.append(f".codex/agents/{name}.toml: sandbox_mode must be {expected_sandbox!r}")

    return errors


def validate_skills(repo_root: Path = REPO_ROOT) -> list[str]:
    """Validate shipped skills inventory, frontmatter, 24 KB size cap, and structural headings."""
    errors: list[str] = []
    skills_dir = repo_root / "skills"
    if not skills_dir.is_dir():
        return ["Missing skills/ directory"]

    found_skills = {p.name for p in skills_dir.iterdir() if p.is_dir()}
    if found_skills != EXPECTED_SKILLS:
        errors.append(f"skills/ directory inventory {sorted(found_skills)} != expected {sorted(EXPECTED_SKILLS)}")

    for skill_name in sorted(EXPECTED_SKILLS & found_skills):
        skill_md = skills_dir / skill_name / "SKILL.md"
        if not skill_md.is_file():
            errors.append(f"skills/{skill_name}/SKILL.md: missing file")
            continue
        raw_bytes = skill_md.read_bytes()
        if len(raw_bytes) >= MAX_SKILL_FILE_BYTES:
            errors.append(
                f"skills/{skill_name}/SKILL.md: size {len(raw_bytes)} bytes exceeds {MAX_SKILL_FILE_BYTES} byte cap"
            )
        text = raw_bytes.decode("utf-8")
        frontmatter, body = _split_frontmatter(text)
        if frontmatter is None:
            errors.append(f"skills/{skill_name}/SKILL.md: missing YAML frontmatter")
            continue
        if frontmatter.get("name") != skill_name:
            errors.append(f"skills/{skill_name}/SKILL.md: name {frontmatter.get('name')!r} != {skill_name!r}")
        description = str(frontmatter.get("description", "")).strip()
        if not description.startswith(SKILL_DESCRIPTION_PREFIX):
            errors.append(f"skills/{skill_name}/SKILL.md: description must start with {SKILL_DESCRIPTION_PREFIX!r}")
        if len(description) > MAX_SKILL_DESCRIPTION_CHARS:
            errors.append(
                f"skills/{skill_name}/SKILL.md: description length {len(description)} > {MAX_SKILL_DESCRIPTION_CHARS}"
            )
        for forbidden_term in FORBIDDEN_SKILL_DESCRIPTION_TERMS:
            if forbidden_term.lower() in description.lower():
                errors.append(f"skills/{skill_name}/SKILL.md: description contains forbidden term {forbidden_term!r}")

        for section in ("Workflow", "Guardrails", "Validation"):
            if not re.search(rf"^##\s+.*\b{section}\b", body, re.IGNORECASE | re.MULTILINE):
                errors.append(f"skills/{skill_name}/SKILL.md: missing '## {section}' section")

        if not re.search(r"^##\s+.*\b(Example|Output)\b", body, re.IGNORECASE | re.MULTILINE):
            errors.append(f"skills/{skill_name}/SKILL.md: missing '## Example' or '## Output' section")

    return errors


def validate_workflows(repo_root: Path = REPO_ROOT) -> list[str]:
    """Validate workflow scripts and fenced Markdown workflow blocks with Python AST checks."""
    errors: list[str] = []
    workflows_dir = repo_root / "workflows"
    if workflows_dir.is_dir():
        for wf_subdir in sorted(p for p in workflows_dir.iterdir() if p.is_dir()):
            manifest_path = wf_subdir / "workflow.json"
            if not manifest_path.is_file():
                continue
            try:
                wf_data = json.loads(manifest_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            if not isinstance(wf_data, dict) or wf_data.get("library", False):
                continue
            entry_rel = str(wf_data.get("entry", "workflow.py"))
            script_path = wf_subdir / entry_rel
            if not script_path.is_file():
                continue
            rel_script = script_path.relative_to(repo_root).as_posix()
            raw_required = wf_data.get("args", {}).get("required", ())
            required_args = tuple(str(item) for item in raw_required) if isinstance(raw_required, list) else ()
            errors.extend(
                _lint_workflow_source(
                    script_path.read_text(encoding="utf-8"),
                    rel_script,
                    required_args=required_args,
                    enforce_workflow_agent_type=True,
                )
            )

    for sub in ("skills", "rules", "templates"):
        sub_dir = repo_root / sub
        if not sub_dir.is_dir():
            continue
        for md_path in sorted(sub_dir.rglob("*.md")):
            rel_md = md_path.relative_to(repo_root).as_posix()
            content = md_path.read_text(encoding="utf-8").replace("\r\n", "\n")
            for block_idx, match in enumerate(_PYTHON_FENCE_PATTERN.finditer(content), start=1):
                snippet = textwrap.dedent(match.group(1))
                if "agent(" not in snippet and "parallel(" not in snippet and "pipeline(" not in snippet:
                    continue
                errors.extend(
                    _lint_workflow_source(
                        snippet,
                        f"{rel_md}#python-block-{block_idx}",
                        required_args=(),
                        enforce_workflow_agent_type=True,
                    )
                )

    return errors


def validate_schema_cards(repo_root: Path = REPO_ROOT) -> list[str]:
    """Verify schema cards exist within line caps and match ``state.md`` task and frontmatter schemas."""
    errors: list[str] = []
    templates_dir = repo_root / "templates" / "agent"
    state_md = repo_root / "skills" / "flow" / "references" / "state.md"
    if not templates_dir.is_dir() or not state_md.is_file():
        return errors

    plan_card = templates_dir / "plan-schema-card.md"
    exec_card = templates_dir / "executor-schema-card.md"
    if not plan_card.is_file():
        errors.append("Missing templates/agent/plan-schema-card.md")
    else:
        plan_text = plan_card.read_text(encoding="utf-8").replace("\r\n", "\n")
        plan_lines = plan_text.splitlines()
        if len(plan_lines) > MAX_PLAN_SCHEMA_CARD_LINES:
            errors.append(
                f"templates/agent/plan-schema-card.md: {len(plan_lines)} lines exceeds "
                f"{MAX_PLAN_SCHEMA_CARD_LINES}-line cap"
            )
        state_text = state_md.read_text(encoding="utf-8")
        for heading in (*REQUIRED_TASK_HEADINGS, *COMPACT_TASK_HEADINGS):
            if heading not in plan_text:
                errors.append(f"templates/agent/plan-schema-card.md: missing task heading {heading!r}")
            if heading not in state_text:
                errors.append(f"skills/flow/references/state.md: missing task heading {heading!r}")
        for key in SCHEMA_CARD_REQUIRED_KEYS:
            if key not in plan_text:
                errors.append(f"templates/agent/plan-schema-card.md: missing frontmatter key {key!r}")
            if key not in state_text:
                errors.append(f"skills/flow/references/state.md: missing frontmatter key {key!r}")

    if not exec_card.is_file():
        errors.append("Missing templates/agent/executor-schema-card.md")
    else:
        exec_lines = exec_card.read_text(encoding="utf-8").replace("\r\n", "\n").splitlines()
        if len(exec_lines) > MAX_EXECUTOR_SCHEMA_CARD_LINES:
            errors.append(
                f"templates/agent/executor-schema-card.md: {len(exec_lines)} lines exceeds "
                f"{MAX_EXECUTOR_SCHEMA_CARD_LINES}-line cap"
            )

    return errors


def validate_markdown_links(repo_root: Path = REPO_ROOT) -> list[str]:
    """Verify that relative Markdown file links across shipped files resolve on disk."""
    errors: list[str] = []
    md_files: list[Path] = []
    for sub in ("skills", "agents", "rules"):
        sub_dir = repo_root / sub
        if sub_dir.is_dir():
            md_files.extend(sorted(sub_dir.rglob("*.md")))
    for root_doc in ("AGENTS.md", "README.md"):
        doc_path = repo_root / root_doc
        if doc_path.is_file():
            md_files.append(doc_path)

    for md_path in md_files:
        text = _FENCED_BLOCK_PATTERN.sub("", md_path.read_text(encoding="utf-8"))
        for match in _LINK_PATTERN.finditer(text):
            target = match.group(2).strip()
            if (
                not target
                or target.startswith(
                    ("#", "http://", "https://", "mailto:", "file://", "conversation://", "sidecar://")
                )
                or "<" in target
                or ">" in target
                or "{" in target
            ):
                continue
            path_part = target.split("#", 1)[0].strip()
            if not path_part:
                continue
            resolved = (md_path.parent / path_part).resolve()
            if not resolved.exists():
                rel_src = md_path.relative_to(repo_root).as_posix()
                errors.append(f"{rel_src}: broken relative link {target!r}")

    return errors


def validate_anti_sprawl(repo_root: Path = REPO_ROOT) -> list[str]:
    """Verify that retired duplicate harness mirrors, shims, and obsolete skills do not exist."""
    errors: list[str] = []
    for rel_path in RETIRED_PATHS:
        candidate = repo_root / rel_path
        if candidate.exists():
            errors.append(f"Retired path must not exist: {rel_path}")
    for openai_yaml in (repo_root / "skills").glob("*/agents/openai.yaml"):
        errors.append(f"Retired openai.yaml must not exist: {openai_yaml.relative_to(repo_root).as_posix()}")
    return errors


def validate_lockfile(repo_root: Path = REPO_ROOT) -> list[str]:
    """Verify that uv.lock references only public PyPI package hosts."""
    errors: list[str] = []
    lock_path = repo_root / "uv.lock"
    if not lock_path.is_file():
        return errors
    for url in _LOCK_URL_PATTERN.findall(lock_path.read_text(encoding="utf-8")):
        host = url.split("://", 1)[1].split("/", 1)[0].lower()
        if host not in PUBLIC_LOCK_SOURCE_HOSTS:
            errors.append(f"uv.lock: non-public package host {host!r} in {url!r}")
    return errors


def validate_okf_bundle(
    bundle_dir: Path,
    *,
    flow_id: str | None = None,
    require_completed_flow: str | None = None,
    project_root: Path | None = None,
) -> list[str]:
    """Validate an Open Knowledge Format (OKF v0.2) bundle directory, nested chapters, and task blueprints."""
    errors: list[str] = []
    if not bundle_dir.is_dir():
        return [f"Bundle directory does not exist: {bundle_dir}"]

    errors.extend(_validate_bundle_symlinks(bundle_dir, project_root=project_root))

    target_flow = require_completed_flow or flow_id
    root_index = bundle_dir / "index.md"
    if not root_index.is_file():
        return [f"{bundle_dir}: missing root index.md"]

    root_fm, _ = _split_frontmatter(root_index.read_text(encoding="utf-8"))
    if root_fm is None:
        errors.append(f"{root_index}: missing YAML frontmatter")
    else:
        if str(root_fm.get("okf_version", "")) != "0.2":
            errors.append(f"{root_index}: okf_version must be '0.2'")
        if not str(root_fm.get("bundle", "")).strip():
            errors.append(f"{root_index}: missing 'bundle' key in root index.md")

    scan_paths: list[Path]
    if target_flow is not None:
        flow_target_dir = bundle_dir / "specs" / target_flow
        if not flow_target_dir.is_dir():
            return [*errors, f"specs/{target_flow}: flow spec directory does not exist"]
        scan_paths = [root_index, *sorted(flow_target_dir.rglob("*.md"))]
    else:
        scan_paths = sorted(bundle_dir.rglob("*.md"))

    for md_path in scan_paths:
        rel = md_path.relative_to(bundle_dir).as_posix()
        text = md_path.read_text(encoding="utf-8")
        fm, body = _split_frontmatter(text)
        errors.extend(_validate_bundle_body_hygiene_and_links(md_path, rel, body))

        if md_path == root_index:
            if fm is not None:
                for forbidden_key in ("type", "status", "sources"):
                    if forbidden_key in fm:
                        errors.append(f"{rel}: reserved file index.md must not declare {forbidden_key!r}")
            continue

        if md_path.name in ("index.md", "log.md", "planner-notes.md"):
            if md_path.name in ("index.md", "log.md") and fm is not None:
                errors.append(f"{rel}: {md_path.name} must not contain YAML frontmatter")
            continue

        if fm is None:
            errors.append(f"{rel}: missing YAML frontmatter")
            continue

        errors.extend(_validate_concept_frontmatter_and_truth(rel, fm, body, project_root=project_root))

    effective_project = project_root or bundle_dir.parent.parent
    git_root = _resolve_git_worktree_root(effective_project)
    sha_tracking = _read_sha_tracking_mode(effective_project)
    specs_dir = bundle_dir / "specs"
    if specs_dir.is_dir():
        flow_dirs = (
            [specs_dir / target_flow]
            if target_flow is not None
            else sorted(p for p in specs_dir.iterdir() if p.is_dir())
        )
        for flow_dir in flow_dirs:
            if not flow_dir.is_dir():
                continue
            errors.extend(
                _validate_flow_spec_directory(
                    bundle_dir,
                    flow_dir,
                    git_root=git_root,
                    require_completed=(require_completed_flow == flow_dir.name),
                    sha_tracking=sha_tracking,
                )
            )

    return errors


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for repository and OKF v0.2 bundle validation."""
    parser = argparse.ArgumentParser(description="Validate Flow multi-harness manifests, skills, agents, and bundles.")
    parser.add_argument(
        "--bundle",
        type=Path,
        default=None,
        help="Optional path to an OKF v0.2 .agents/bundles directory to validate.",
    )
    parser.add_argument(
        "--flow",
        type=str,
        default=None,
        help="Optional flow_id under specs/<flow_id> to scope OKF spec validation.",
    )
    parser.add_argument(
        "--require-completed",
        type=str,
        default=None,
        help="Verify that specs/<flow_id> is fully completed, reviewed, and backed by Git commits.",
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=None,
        help="Optional project root used to resolve cited local source paths and Git history.",
    )
    args = parser.parse_args(argv)

    errors: list[str] = []
    if args.bundle is None:
        errors.extend(validate_repository(REPO_ROOT))
    else:
        errors.extend(
            validate_okf_bundle(
                args.bundle,
                flow_id=args.flow,
                require_completed_flow=args.require_completed,
                project_root=args.project_root,
            )
        )

    if errors:
        for err in errors:
            sys.stderr.write(f"ERROR: {err}\n")
        sys.stderr.write(f"Validation failed with {len(errors)} error(s).\n")
        return 1

    sys.stdout.write("Validation passed: all manifests, hooks, subagents, skills, workflows, and links are valid.\n")
    return 0


def _lint_workflow_source(
    source: str,
    label: str,
    *,
    required_args: tuple[str, ...],
    enforce_workflow_agent_type: bool,
) -> list[str]:
    """Check Python workflow source with top-level await compilation and AST structural rules."""
    errors: list[str] = []
    try:
        tree = ast.parse(source, filename=label)
    except SyntaxError as exc:
        return [f"{label}: workflow syntax error at line {exc.lineno}: {exc.msg}"]

    for top_stmt in tree.body:
        for sub in _walk_excluding_nested_functions(top_stmt):
            if isinstance(sub, ast.Return):
                errors.append(f"{label}:{sub.lineno}: top-level 'return' is a runtime error; emit output with print()")
    if errors:
        return errors

    try:
        compile(tree, label, "exec", flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT)
    except SyntaxError as exc:
        return [f"{label}: workflow syntax error at line {exc.lineno}: {exc.msg}"]

    awaited_call_ids = _collect_awaited_call_ids(tree)
    args_keys_read = _collect_args_keys(tree)

    for req_key in required_args:
        if req_key not in args_keys_read:
            errors.append(f"{label}: required workflow.json arg {req_key!r} is never read from 'args'")

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func_name = _call_func_name(node.func)
        if func_name == "agent":
            has_schema = len(node.args) >= 2 or any(kw.arg == "schema" for kw in node.keywords)
            if not has_schema:
                errors.append(f"{label}:{node.lineno}: agent() call missing required 'schema=' argument")
            if enforce_workflow_agent_type:
                type_kw = next((kw for kw in node.keywords if kw.arg == "type_name"), None)
                if (
                    type_kw is not None
                    and isinstance(type_kw.value, ast.Constant)
                    and isinstance(type_kw.value.value, str)
                ):
                    val = type_kw.value.value
                    if val in FORBIDDEN_WORKFLOW_AGENT_TYPES:
                        errors.append(
                            f"{label}:{node.lineno}: agent() must not hardcode type_name={val!r} on Antigravity "
                            "(use type_name='self' so write and shell tools are inherited)"
                        )
        elif func_name in ("parallel", "pipeline") and id(node) not in awaited_call_ids:
            errors.append(f"{label}:{node.lineno}: {func_name}() call must be awaited")

    return errors


def _walk_excluding_nested_functions(node: ast.AST) -> list[ast.AST]:
    """Walk AST children of ``node`` without descending into nested function definitions."""
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
        return []
    collected: list[ast.AST] = [node]
    for child in ast.iter_child_nodes(node):
        collected.extend(_walk_excluding_nested_functions(child))
    return collected


def _collect_awaited_call_ids(tree: ast.AST) -> set[int]:
    """Return object IDs of Call nodes that are awaited, wrapped in ``with_budget``, or returned by a helper."""
    awaited: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Await):
            if isinstance(node.value, ast.Call):
                awaited.add(id(node.value))
                if _call_func_name(node.value.func) == "with_budget" and node.value.args:
                    first_arg = node.value.args[0]
                    if isinstance(first_arg, ast.Call):
                        awaited.add(id(first_arg))
        elif isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef, ast.Lambda)):
            for child in ast.walk(node):
                if isinstance(child, ast.Return) and isinstance(child.value, ast.Call):
                    awaited.add(id(child.value))
                elif isinstance(node, ast.Lambda) and isinstance(node.body, ast.Call):
                    awaited.add(id(node.body))
    return awaited


def _collect_args_keys(tree: ast.AST) -> set[str]:
    """Extract string keys accessed on ``args[...]`` or ``args.get(...)``."""
    keys: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name) and node.value.id == "args":
            if isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, str):
                keys.add(node.slice.value)
        elif (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "args"
            and node.func.attr == "get"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            keys.add(node.args[0].value)
    return keys


def _call_func_name(func: ast.expr) -> str | None:
    """Return simple function name for ``ast.Name`` call targets."""
    if isinstance(func, ast.Name):
        return func.id
    return None


def _validate_bundle_symlinks(bundle_dir: Path, *, project_root: Path | None) -> list[str]:
    """Allow symlinks targeting the main Git checkout while rejecting escaping arbitrary symlinks."""
    errors: list[str] = []
    base_proj = (project_root or bundle_dir.parent.parent).resolve()
    allowed_roots = {base_proj}
    main_wt = _resolve_git_worktree_root(base_proj)
    if main_wt is not None:
        allowed_roots.add(main_wt.resolve())

    agents_parent = bundle_dir.parent
    for candidate in (agents_parent, bundle_dir):
        if is_link_or_junction(candidate):
            resolved = candidate.resolve()
            if not any(resolved == root or root in resolved.parents for root in allowed_roots):
                errors.append(f"{candidate}: symlink target {resolved} escapes repository and main Git worktree")
    return errors


def _resolve_git_worktree_root(start_dir: Path) -> Path | None:
    """Resolve the primary Git working tree root for ``start_dir`` if inside Git."""
    git_bin = shutil.which("git")
    if git_bin is None or not start_dir.exists():
        return None
    proc = subprocess.run(
        [git_bin, "-C", str(start_dir), "rev-parse", "--git-common-dir"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if proc.returncode != 0:
        return None
    raw = proc.stdout.strip()
    if not raw:
        return None
    common = Path(raw)
    if not common.is_absolute():
        common = (start_dir / common).resolve()
    else:
        common = common.resolve()
    if common.name == ".git":
        return common.parent
    if common.parent.name == ".git":
        return common.parent.parent
    return common.parent


def _run_session_start_smoke_checks(sh_script: Path, ps1_script: Path) -> list[str]:
    """Execute session-start.sh and session-start.ps1 across harnesses and verify stdout JSON schemas."""
    errors: list[str] = []
    expected_keys = (
        ("agy", "injectSteps"),
        ("claude", "hookSpecificOutput"),
        ("cursor", "additional_context"),
    )
    with tempfile.TemporaryDirectory() as clean_proj:
        for harness, required_key in expected_keys:
            proc = subprocess.run(
                ["sh", str(sh_script), "--harness", harness, "--project", clean_proj],
                input="{}",
                text=True,
                encoding="utf-8",
                capture_output=True,
                check=False,
            )
            if proc.returncode != 0:
                errors.append(f"hooks/session-start.sh --harness {harness} failed: {proc.stderr.strip()}")
                continue
            try:
                payload = json.loads(proc.stdout)
            except json.JSONDecodeError as exc:
                errors.append(f"hooks/session-start.sh --harness {harness} emitted invalid JSON: {exc}")
                continue
            if required_key not in payload:
                errors.append(f"hooks/session-start.sh --harness {harness} missing top-level key {required_key!r}")

        pwsh_bin = shutil.which("pwsh") or shutil.which("powershell")
        if pwsh_bin and ps1_script.is_file():
            for harness, required_key in expected_keys:
                proc = subprocess.run(
                    [
                        pwsh_bin,
                        "-NoProfile",
                        "-NonInteractive",
                        "-ExecutionPolicy",
                        "Bypass",
                        "-File",
                        str(ps1_script),
                        "--harness",
                        harness,
                        "--project",
                        clean_proj,
                    ],
                    input="{}",
                    text=True,
                    encoding="utf-8",
                    capture_output=True,
                    check=False,
                )
                if proc.returncode != 0:
                    errors.append(f"hooks/session-start.ps1 --harness {harness} failed: {proc.stderr.strip()}")
                    continue
                try:
                    payload = json.loads(proc.stdout)
                except json.JSONDecodeError as exc:
                    errors.append(f"hooks/session-start.ps1 --harness {harness} emitted invalid JSON: {exc}")
                    continue
                if required_key not in payload:
                    errors.append(f"hooks/session-start.ps1 --harness {harness} missing top-level key {required_key!r}")

    return errors


def _run_stop_hook_smoke_checks(sh_script: Path, ps1_script: Path) -> list[str]:
    """Execute stop-check.sh and stop-check.ps1 across harnesses and verify clean allow JSON."""
    errors: list[str] = []
    with tempfile.TemporaryDirectory() as clean_proj:
        for harness in ("agy", "claude", "cursor"):
            proc = subprocess.run(
                ["sh", str(sh_script), "--harness", harness, "--project", clean_proj],
                input="{}",
                text=True,
                encoding="utf-8",
                capture_output=True,
                check=False,
            )
            if proc.returncode != 0:
                errors.append(f"hooks/stop-check.sh --harness {harness} failed: {proc.stderr.strip()}")
                continue
            try:
                payload = json.loads(proc.stdout)
            except json.JSONDecodeError as exc:
                errors.append(f"hooks/stop-check.sh --harness {harness} emitted invalid JSON: {exc}")
                continue
            if payload != {}:
                errors.append(f"hooks/stop-check.sh --harness {harness} expected {{}} on clean repo, got {payload!r}")

        pwsh_bin = shutil.which("pwsh") or shutil.which("powershell")
        if pwsh_bin and ps1_script.is_file():
            for harness in ("agy", "claude", "cursor"):
                proc = subprocess.run(
                    [
                        pwsh_bin,
                        "-NoProfile",
                        "-NonInteractive",
                        "-ExecutionPolicy",
                        "Bypass",
                        "-File",
                        str(ps1_script),
                        "--harness",
                        harness,
                        "--project",
                        clean_proj,
                    ],
                    input="{}",
                    text=True,
                    encoding="utf-8",
                    capture_output=True,
                    check=False,
                )
                if proc.returncode != 0:
                    errors.append(f"hooks/stop-check.ps1 --harness {harness} failed: {proc.stderr.strip()}")
                    continue
                try:
                    payload = json.loads(proc.stdout)
                except json.JSONDecodeError as exc:
                    errors.append(f"hooks/stop-check.ps1 --harness {harness} emitted invalid JSON: {exc}")
                    continue
                if payload != {}:
                    errors.append(
                        f"hooks/stop-check.ps1 --harness {harness} expected {{}} on clean repo, got {payload!r}"
                    )

    return errors


def _validate_bundle_body_hygiene_and_links(md_path: Path, rel: str, body: str) -> list[str]:
    """Check Markdown body for forbidden horizontal rules, historical headings, struck-through items, and dead links."""
    errors: list[str] = []
    unfenced_multiline = _MULTILINE_FENCE_PATTERN.sub("", body)
    if _BODY_HR_PATTERN.search(unfenced_multiline):
        errors.append(f"{rel}: standalone '---' horizontal rule forbidden in bundle Markdown body")
    if _HISTORY_HEADING_PATTERN.search(unfenced_multiline):
        errors.append(f"{rel}: historical revision/changelog heading forbidden in present-tense bundle file")
    if _STRUCK_CHECKLIST_PATTERN.search(unfenced_multiline):
        errors.append(f"{rel}: struck-through checklist item forbidden; rewrite in place in present tense")

    stripped_links = _FENCED_BLOCK_PATTERN.sub("", body)
    for match in _LINK_PATTERN.finditer(stripped_links):
        target = match.group(2).strip()
        if (
            not target
            or target.startswith(("#", "http://", "https://", "mailto:", "file://", "conversation://", "sidecar://"))
            or "<" in target
            or ">" in target
            or "{" in target
        ):
            continue
        path_part = target.split("#", 1)[0].strip()
        if not path_part:
            continue
        resolved = (md_path.parent / path_part).resolve()
        if not resolved.exists():
            errors.append(f"{rel}: broken relative link {target!r}")
    return errors


def _validate_concept_frontmatter_and_truth(
    rel: str,
    fm: dict[str, Any],
    body: str,
    *,
    project_root: Path | None = None,
) -> list[str]:
    """Validate OKF v0.2 concept frontmatter, status/tags invariants, truth blocks, footnotes, and Spec/Task bodies."""
    errors: list[str] = []
    for req_key in ("type", "title", "description"):
        if not str(fm.get(req_key, "")).strip():
            errors.append(f"{rel}: missing required frontmatter key {req_key!r}")

    doc_type = str(fm.get("type", "")).strip()

    if "status" in fm:
        status_val = str(fm.get("status", "")).strip()
        if status_val not in OKF_DOCUMENT_STATUSES:
            errors.append(
                f"{rel}: invalid OKF status {status_val!r} (must be one of {sorted(OKF_DOCUMENT_STATUSES)}; "
                "workflow execution state belongs in 'state')"
            )

    if "planning_quality" in fm and fm["planning_quality"] is not None:
        pq_val = str(fm.get("planning_quality", "")).strip()
        if pq_val not in PLANNING_QUALITY_VALUES:
            errors.append(
                f"{rel}: invalid planning_quality {pq_val!r} (must be one of {sorted(PLANNING_QUALITY_VALUES)})"
            )
        elif pq_val == "degraded" and not str(fm.get("planning_degraded_reason") or "").strip():
            errors.append(f"{rel}: planning_quality is 'degraded' without non-empty planning_degraded_reason")

    if "tags" in fm:
        tags_val = fm.get("tags")
        if not isinstance(tags_val, list) or not (1 <= len(tags_val) <= 8):
            errors.append(f"{rel}: tags must be a list of 1..8 lowercase hyphenated strings")
        else:
            for raw_tag in tags_val:
                tag = str(raw_tag).strip()
                if not _TAG_SLUG_PATTERN.match(tag):
                    errors.append(f"{rel}: invalid tag {tag!r} (must be lowercase hyphenated slug)")
                elif tag in FORBIDDEN_TAG_STATE_WORDS:
                    errors.append(f"{rel}: tag {tag!r} encodes lifecycle state/status; use domain/work-kind tags")

    start_match = _TRUTH_START_PATTERN.search(body)
    end_match = _TRUTH_END_PATTERN.search(body)
    if doc_type == "Spec" and not start_match:
        errors.append(f"{rel}: Spec document must include a bounded '<!-- truth: start -->' block")
    if start_match and not end_match:
        errors.append(f"{rel}: '<!-- truth: start -->' missing matching '<!-- truth: end -->'")
    elif end_match and not start_match:
        errors.append(f"{rel}: '<!-- truth: end -->' missing matching '<!-- truth: start -->'")
    elif start_match and end_match:
        if end_match.start() < start_match.end():
            errors.append(f"{rel}: truth block end appears before start")
        else:
            inner_lines = [ln for ln in body[start_match.end() : end_match.start()].strip("\n").splitlines()]
            if len(inner_lines) > MAX_TRUTH_BLOCK_LINES:
                errors.append(
                    f"{rel}: truth block has {len(inner_lines)} lines (exceeds {MAX_TRUTH_BLOCK_LINES}-line limit)"
                )

    sources = fm.get("sources")
    if doc_type == "Spec" and (not isinstance(sources, list) or not sources):
        errors.append(f"{rel}: Spec document must declare non-empty OKF v0.2 'sources' provenance")
    if isinstance(sources, list) and sources:
        footnotes = set(_FOOTNOTE_DEF_PATTERN.findall(body))
        for src in sources:
            if not isinstance(src, dict):
                errors.append(f"{rel}: each item in sources must be a mapping")
                continue
            src_id = str(src.get("id", "")).strip()
            src_res = str(src.get("resource", "")).strip()
            if not src_id or not src_res:
                errors.append(f"{rel}: source entry must declare 'id' and 'resource'")
            elif src_id not in footnotes:
                errors.append(f"{rel}: source id {src_id!r} missing matching [^{src_id}]: footnote in body")
            elif project_root is not None and not src_res.startswith(("http://", "https://", "mailto:")):
                local_rel = src_res.split("::", 1)[0].split("#", 1)[0].strip()
                if local_rel and not (project_root / local_rel).exists():
                    errors.append(f"{rel}: cited source path {local_rel!r} does not exist under {project_root}")

    if doc_type == "Spec":
        unfenced = _MULTILINE_FENCE_PATTERN.sub("", body)
        for spec_heading in REQUIRED_SPEC_HEADINGS:
            if not re.search(rf"^{re.escape(spec_heading)}\s*$", unfenced, re.MULTILINE):
                errors.append(f"{rel}: missing required Spec heading {spec_heading!r}")

    if doc_type == "Task":
        errors.extend(_validate_task_blueprint_contract(rel, fm, body))

    return errors


def _validate_task_blueprint_contract(rel: str, fm: dict[str, Any], body: str) -> list[str]:
    """Validate full or compact Task worksheet headings, deferral authorization, read_set cap, and estimated_loc cap."""
    errors: list[str] = []
    unfenced = _MULTILINE_FENCE_PATTERN.sub("", body)
    ws_format = str(fm.get("worksheet_format", "full") or "full").strip().lower()
    if ws_format not in ("full", "compact"):
        errors.append(f"{rel}: invalid worksheet_format {ws_format!r} (expected 'full' or 'compact')")
        expected_headings = REQUIRED_TASK_HEADINGS
    elif ws_format == "compact":
        expected_headings = COMPACT_TASK_HEADINGS
    else:
        expected_headings = REQUIRED_TASK_HEADINGS

    for heading in expected_headings:
        if not re.search(rf"^{re.escape(heading)}\s*$", unfenced, re.MULTILINE):
            errors.append(f"{rel}: missing required Task blueprint heading {heading!r}")

    t_state = str(fm.get("state") or "pending").strip()
    if t_state in DEFERRED_STATES:
        errors.extend(_validate_user_deferral(rel, fm, t_state))

    if "read_set" in fm and fm["read_set"] is not None:
        read_set = fm["read_set"]
        if not isinstance(read_set, list):
            errors.append(f"{rel}: read_set must be a list of file paths")
        elif len(read_set) > MAX_TASK_READ_SET:
            errors.append(f"{rel}: read_set has {len(read_set)} entries (exceeds {MAX_TASK_READ_SET}-file cap)")

    if "estimated_loc" in fm and fm["estimated_loc"] is not None:
        loc_val = fm["estimated_loc"]
        if not isinstance(loc_val, int) or isinstance(loc_val, bool):
            errors.append(f"{rel}: estimated_loc must be an integer")
        elif loc_val > MAX_TASK_ESTIMATED_LOC:
            errors.append(f"{rel}: estimated_loc {loc_val} exceeds {MAX_TASK_ESTIMATED_LOC}-line cap")

    return errors


def _validate_user_deferral(rel: str, fm: dict[str, Any], state_val: str) -> list[str]:
    """Require explicit user authorization whenever a task or chapter is marked deferred or skipped."""
    errors: list[str] = []
    deferred_by = str(fm.get("deferred_by") or "").strip().lower()
    deferred_reason = str(fm.get("deferred_reason") or "").strip()
    if deferred_by != "user" or not deferred_reason:
        errors.append(
            f"{rel}: state is {state_val!r} without user authorization "
            "(requires deferred_by: 'user' and non-empty deferred_reason)"
        )
    return errors


def _validate_flow_spec_directory(
    bundle_dir: Path,
    flow_dir: Path,
    *,
    git_root: Path | None = None,
    require_completed: bool = False,
    sha_tracking: str = "strict",
) -> list[str]:
    """Validate a single-chapter or multi-chapter specs/<flow_id>/ directory for anti-skip and review-stamp parity."""
    errors: list[str] = []
    rel_flow = flow_dir.relative_to(bundle_dir).as_posix()
    root_spec = flow_dir / "spec.md"
    if not root_spec.is_file():
        return [f"{rel_flow}: missing spec.md"]

    root_fm, root_body = _split_frontmatter(root_spec.read_text(encoding="utf-8"))
    if root_fm is None:
        return errors

    chapters_dir = flow_dir / "chapters"
    has_chapters = chapters_dir.is_dir() or root_fm.get("has_chapters") is True
    root_state = str(root_fm.get("state", "")).strip()
    root_rev_sha = str(root_fm.get("last_reviewed_commit") or "").strip()
    plan_commit = str(root_fm.get("plan_commit") or "").strip()

    if require_completed and root_state != "completed":
        errors.append(f"{rel_flow}/spec.md: --require-completed failed because state is {root_state!r} != 'completed'")

    if has_chapters:
        errors.extend(
            _validate_multi_chapter_flow(
                bundle_dir,
                flow_dir,
                rel_flow,
                root_fm,
                root_body,
                root_state,
                root_rev_sha,
                git_root=git_root,
                default_plan_commit=plan_commit,
                sha_tracking=sha_tracking,
            )
        )
        return errors

    tasks_dir = flow_dir / "tasks"
    task_errors, task_total, open_task_ids = _validate_tasks_for_owner_spec(
        bundle_dir,
        f"{rel_flow}/spec.md",
        root_body,
        tasks_dir,
        git_root=git_root,
        plan_commit=plan_commit,
        sha_tracking=sha_tracking,
    )
    errors.extend(task_errors)

    if root_state == "completed" or require_completed:
        if task_total == 0:
            errors.append(f"{rel_flow}/spec.md: cannot mark completed with zero task worksheets")
        elif open_task_ids:
            errors.append(f"{rel_flow}/spec.md: state is 'completed' while tasks remain incomplete: {open_task_ids}")
        if not _HEX_SHA_PATTERN.match(root_rev_sha):
            errors.append(f"{rel_flow}/spec.md: state is 'completed' without valid hex last_reviewed_commit")
    return errors


def _validate_multi_chapter_flow(
    bundle_dir: Path,
    flow_dir: Path,
    rel_flow: str,
    root_fm: dict[str, Any],
    root_body: str,
    root_state: str,
    root_rev_sha: str,
    *,
    git_root: Path | None = None,
    default_plan_commit: str = "",
    sha_tracking: str = "strict",
) -> list[str]:
    """Validate nested chapters/<ch_id>/ layout, 1:1 roadmap parity, anti-skip invariants, and review stamps."""
    errors: list[str] = []
    chapters_dir = flow_dir / "chapters"
    if not chapters_dir.is_dir():
        return [f"{rel_flow}: has_chapters is true but chapters/ directory is missing"]

    root_tasks_dir = flow_dir / "tasks"
    if root_tasks_dir.is_dir() and any(p.name != "index.md" for p in root_tasks_dir.glob("*.md")):
        errors.append(f"{rel_flow}: multi-chapter spec must not mix root tasks/*.md with chapters/")

    ch_index = chapters_dir / "index.md"
    ch_index_text = ""
    if not ch_index.is_file():
        errors.append(f"{rel_flow}/chapters/index.md: missing chapter catalog index.md")
    else:
        ch_index_text = ch_index.read_text(encoding="utf-8")

    ch_dirs = sorted(p for p in chapters_dir.iterdir() if p.is_dir())
    disk_ch_ids = [p.name for p in ch_dirs]
    for ch_id in disk_ch_ids:
        if not _CHAPTER_DIR_PATTERN.match(ch_id):
            errors.append(f"{rel_flow}/chapters/{ch_id}: directory name must match '^ch\\d{{2}}-[a-z0-9-]+$'")

    declared_chapters = root_fm.get("chapters")
    if isinstance(declared_chapters, list):
        declared_ids = [str(item).strip() for item in declared_chapters]
        if sorted(declared_ids) != disk_ch_ids:
            errors.append(f"{rel_flow}/spec.md: frontmatter chapters {declared_ids} != disk chapters {disk_ch_ids}")

    root_unfenced = _MULTILINE_FENCE_PATTERN.sub("", root_body)
    open_chapters: list[str] = []

    for ch_dir in ch_dirs:
        ch_id = ch_dir.name
        rel_ch = f"{rel_flow}/chapters/{ch_id}"
        if ch_index_text and ch_id not in ch_index_text:
            errors.append(f"{rel_flow}/chapters/index.md: missing entry for chapter {ch_id!r}")
        if ch_id not in root_unfenced:
            errors.append(f"{rel_flow}/spec.md: full-plan body/checklist missing chapter {ch_id!r}")

        ch_spec = ch_dir / "spec.md"
        if not ch_spec.is_file():
            errors.append(f"{rel_ch}: missing spec.md")
            open_chapters.append(ch_id)
            continue

        ch_fm, ch_body = _split_frontmatter(ch_spec.read_text(encoding="utf-8"))
        if ch_fm is None:
            open_chapters.append(ch_id)
            continue

        planning_status = str(ch_fm.get("planning_status", "complete")).strip()
        if planning_status not in ("complete", "empirical_dependent"):
            errors.append(f"{rel_ch}/spec.md: invalid planning_status {planning_status!r}")
        elif planning_status == "empirical_dependent":
            trigger = str(ch_fm.get("replan_trigger") or "").strip()
            deps = ch_fm.get("depends_on_chapters")
            if not trigger:
                errors.append(f"{rel_ch}/spec.md: empirical_dependent chapter requires non-empty replan_trigger")
            if not isinstance(deps, list) or not deps:
                errors.append(f"{rel_ch}/spec.md: empirical_dependent chapter requires non-empty depends_on_chapters")

        ch_state = str(ch_fm.get("state", "")).strip()
        ch_rev = str(ch_fm.get("last_reviewed_commit") or "").strip()
        ch_plan_commit = str(ch_fm.get("plan_commit") or default_plan_commit).strip()
        task_errors, task_total, open_tasks = _validate_tasks_for_owner_spec(
            bundle_dir,
            f"{rel_ch}/spec.md",
            ch_body,
            ch_dir / "tasks",
            git_root=git_root,
            plan_commit=ch_plan_commit,
            sha_tracking=sha_tracking,
        )
        errors.extend(task_errors)

        if ch_state in DEFERRED_STATES:
            errors.extend(_validate_user_deferral(f"{rel_ch}/spec.md", ch_fm, ch_state))
        elif ch_state == "completed":
            if task_total == 0:
                errors.append(f"{rel_ch}/spec.md: cannot mark chapter 'completed' with zero task worksheets")
            elif open_tasks:
                errors.append(f"{rel_ch}/spec.md: chapter is marked 'completed' while tasks remain open: {open_tasks}")
            if not _HEX_SHA_PATTERN.match(ch_rev):
                errors.append(f"{rel_ch}/spec.md: state is 'completed' without valid hex last_reviewed_commit")
            if not re.search(rf"^[ \t]*-[ \t]*\[[xX]\].*{re.escape(ch_id)}", root_unfenced, re.MULTILINE):
                errors.append(f"{rel_flow}/spec.md: completed chapter {ch_id!r} must be marked [x] in checklist")
        else:
            open_chapters.append(ch_id)

    curr_ch = str(root_fm.get("current_chapter") or "").strip()
    if root_state == "completed":
        if not ch_dirs:
            errors.append(f"{rel_flow}/spec.md: cannot mark multi-chapter flow 'completed' with zero chapters")
        elif open_chapters:
            errors.append(
                f"{rel_flow}/spec.md: state is 'completed' while chapters remain open (cannot skip chapters): "
                f"{open_chapters}"
            )
        if not _HEX_SHA_PATTERN.match(root_rev_sha):
            errors.append(f"{rel_flow}/spec.md: state is 'completed' without valid hex last_reviewed_commit")
    elif open_chapters and curr_ch not in open_chapters:
        errors.append(
            f"{rel_flow}/spec.md: current_chapter {curr_ch!r} must reference an open chapter in {open_chapters}"
        )

    return errors


def _validate_tasks_for_owner_spec(
    bundle_dir: Path,
    owner_rel: str,
    owner_body: str,
    tasks_dir: Path,
    *,
    git_root: Path | None = None,
    plan_commit: str = "",
    sha_tracking: str = "strict",
) -> tuple[list[str], int, list[str]]:
    """Verify <= 4 tasks per chapter/spec, checklist parity, and Git file-ownership proofs."""
    errors: list[str] = []
    open_tasks: list[str] = []
    if not tasks_dir.is_dir():
        return errors, 0, open_tasks

    task_files = sorted(p for p in tasks_dir.glob("*.md") if p.name != "index.md")
    if len(task_files) > MAX_CHAPTER_TASKS:
        rel_tasks = tasks_dir.relative_to(bundle_dir).as_posix()
        errors.append(
            f"{rel_tasks}: found {len(task_files)} task worksheets (exceeds {MAX_CHAPTER_TASKS}-task chapter cap; "
            "split into additional chapters rather than compressing or overloading)"
        )

    unfenced_owner = _MULTILINE_FENCE_PATTERN.sub("", owner_body)
    checklist_rows = [
        (m.group(1).lower(), m.group(2).strip()) for m in _CHECKLIST_LINE_PATTERN.finditer(unfenced_owner)
    ]

    for tf in task_files:
        rel_tf = tf.relative_to(bundle_dir).as_posix()
        tfm, _ = _split_frontmatter(tf.read_text(encoding="utf-8"))
        if tfm is None:
            open_tasks.append(tf.name)
            continue
        t_stem = tf.name.split("-", 1)[0]
        t_id = str(tfm.get("id") or t_stem).strip()
        t_state = str(tfm.get("state") or "pending").strip()
        t_commit = str(tfm.get("commit") or "").strip()

        errors.extend(_validate_task_claim_fields(rel_tf, tfm))

        if t_state in OPEN_TASK_STATES:
            open_tasks.append(tf.name)

        expected_mark = _expected_checklist_marker(t_state)
        if t_state in ("completed", "closed"):
            if not _HEX_SHA_PATTERN.match(t_commit):
                errors.append(f"{rel_tf}: state is {t_state!r} without valid hex commit SHA")
            elif git_root is not None and sha_tracking != "off":
                errors.extend(
                    _verify_task_git_ownership(
                        rel_tf,
                        tfm,
                        t_commit,
                        git_root,
                        plan_commit,
                        sha_tracking=sha_tracking,
                    )
                )

        matched_row = _match_checklist_row(checklist_rows, tf.name, t_id, t_stem)
        if matched_row is None:
            errors.append(f"{owner_rel}: checklist missing entry for task worksheet {tf.name!r}")
            continue

        actual_mark, rest_text = matched_row
        if actual_mark != expected_mark:
            errors.append(
                f"{owner_rel}: task {tf.name!r} has checklist marker [{actual_mark}] "
                f"but worksheet state {t_state!r} requires [{expected_mark}]"
            )
        elif expected_mark == "x" and sha_tracking == "strict" and _HEX_SHA_PATTERN.match(t_commit):
            sha_match = _CHECKLIST_SHA_PATTERN.match(rest_text)
            if sha_match:
                c_sha = sha_match.group(1)
                if not (t_commit.startswith(c_sha) or c_sha.startswith(t_commit)):
                    if not (git_root is not None and _shas_represent_same_change(git_root, t_commit, c_sha)):
                        errors.append(
                            f"{owner_rel}: task {tf.name!r} commit {t_commit!r} mismatches checklist SHA {c_sha!r}"
                        )

    return errors, len(task_files), open_tasks


def _read_sha_tracking_mode(project_root: Path) -> str:
    """Resolve workflow_preferences.sha_tracking (or top-level sha_tracking) from setup-state.json."""
    setup_path = project_root / ".agents" / "setup-state.json"
    if not setup_path.is_file():
        return "strict"
    try:
        data = json.loads(setup_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "strict"
    if not isinstance(data, dict):
        return "strict"
    raw = data.get("sha_tracking")
    if raw is None and isinstance(data.get("workflow_preferences"), dict):
        raw = data["workflow_preferences"].get("sha_tracking")
    val = str(raw or "strict").strip().lower()
    return val if val in ("strict", "advisory", "off") else "strict"


def _is_gitignored(git_bin: str, git_root: Path, rel_path: str) -> bool:
    """Return True when git_root's ignore rules exclude rel_path from commit tracking."""
    proc = subprocess.run(
        [git_bin, "-C", str(git_root), "check-ignore", "-q", "--", rel_path],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    return proc.returncode == 0


def _git_commit_patch_id(git_bin: str, git_root: Path, commit_sha: str) -> str:
    """Compute stable git patch-id for commit_sha or return empty string."""
    diff_proc = subprocess.run(
        [git_bin, "-C", str(git_root), "diff-tree", "--no-ext-diff", "-p", "--root", commit_sha],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if diff_proc.returncode != 0 or not diff_proc.stdout.strip():
        return ""
    pid_proc = subprocess.run(
        [git_bin, "patch-id", "--stable"],
        input=diff_proc.stdout,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if pid_proc.returncode != 0 or not pid_proc.stdout.strip():
        return ""
    return pid_proc.stdout.strip().split()[0]


def _git_is_ancestor(git_bin: str, git_root: Path, ancestor: str, descendant: str) -> bool:
    """Return True when ancestor is reachable from descendant in git_root."""
    proc = subprocess.run(
        [git_bin, "-C", str(git_root), "merge-base", "--is-ancestor", ancestor, descendant],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    return proc.returncode == 0


def _shas_represent_same_change(git_root: Path, sha_a: str, sha_b: str) -> bool:
    """Return True when two SHAs share a stable patch-id or one was rewritten off HEAD ancestry."""
    git_bin = shutil.which("git")
    if git_bin is None:
        return False
    a_exists = (
        subprocess.run(
            [git_bin, "-C", str(git_root), "cat-file", "-e", f"{sha_a}^{{commit}}"],
            capture_output=True,
            check=False,
        ).returncode
        == 0
    )
    b_exists = (
        subprocess.run(
            [git_bin, "-C", str(git_root), "cat-file", "-e", f"{sha_b}^{{commit}}"],
            capture_output=True,
            check=False,
        ).returncode
        == 0
    )
    if a_exists and b_exists:
        pid_a = _git_commit_patch_id(git_bin, git_root, sha_a)
        pid_b = _git_commit_patch_id(git_bin, git_root, sha_b)
        return bool(pid_a and pid_a == pid_b)
    return _git_is_ancestor(git_bin, git_root, sha_a, "HEAD") != _git_is_ancestor(git_bin, git_root, sha_b, "HEAD")


def _verify_task_git_ownership(
    rel_tf: str,
    tfm: dict[str, Any],
    commit_sha: str,
    git_root: Path,
    plan_commit: str,
    *,
    sha_tracking: str = "strict",
) -> list[str]:
    """Verify a completed task's recorded Git commit touched at least one declared non-ignored path."""
    declared_paths: list[str] = []
    for key in ("files", "tests"):
        raw_list = tfm.get(key)
        if isinstance(raw_list, list):
            for entry in raw_list:
                cleaned = str(entry).split("::", 1)[0].strip().strip("/")
                if cleaned:
                    declared_paths.append(cleaned)
    if not declared_paths:
        return []

    git_bin = shutil.which("git")
    if git_bin is None:
        return []

    exists_proc = subprocess.run(
        [git_bin, "-C", str(git_root), "cat-file", "-e", f"{commit_sha}^{{commit}}"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if exists_proc.returncode != 0:
        if sha_tracking == "advisory":
            return []
        return [f"{rel_tf}: recorded commit {commit_sha!r} does not exist in Git history"]

    touched = _git_changed_files(git_bin, git_root, commit_sha, plan_commit)
    if any(decl in touched for decl in declared_paths):
        return []

    non_ignored = [decl for decl in declared_paths if not _is_gitignored(git_bin, git_root, decl)]
    if not non_ignored:
        return []
    if not any(decl in touched for decl in non_ignored):
        return [f"{rel_tf}: commit {commit_sha!r} modified none of the task's declared files/tests {non_ignored}"]
    return []


def _git_changed_files(git_bin: str, git_root: Path, commit_sha: str, plan_commit: str) -> set[str]:
    """Collect normalized relative paths touched by ``commit_sha`` (and ``plan_commit..commit_sha`` when valid)."""
    changed: set[str] = set()
    single = subprocess.run(
        [git_bin, "-C", str(git_root), "diff-tree", "--no-commit-id", "--name-only", "-r", "--root", commit_sha],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if single.returncode == 0:
        changed.update(ln.strip() for ln in single.stdout.splitlines() if ln.strip())

    if _HEX_SHA_PATTERN.match(plan_commit):
        anc = subprocess.run(
            [git_bin, "-C", str(git_root), "merge-base", "--is-ancestor", plan_commit, commit_sha],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        if anc.returncode == 0:
            span = subprocess.run(
                [git_bin, "-C", str(git_root), "diff", "--name-only", f"{plan_commit}..{commit_sha}"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
            if span.returncode == 0:
                changed.update(ln.strip() for ln in span.stdout.splitlines() if ln.strip())
    return changed


def _validate_task_claim_fields(rel_tf: str, tfm: dict[str, Any]) -> list[str]:
    """Validate task ``claimed_by`` and ``claimed_at`` frontmatter fields while preserving legacy strings."""
    errors: list[str] = []
    if "claimed_by" in tfm and tfm["claimed_by"] is not None:
        claimed_by = tfm["claimed_by"]
        if not isinstance(claimed_by, str) or not claimed_by.strip():
            errors.append(f"{rel_tf}: claimed_by must be null or a non-empty string")
        elif ":" in claimed_by:
            parts = [part.strip() for part in claimed_by.split(":")]
            if parts[0].lower() in KNOWN_CLAIM_HARNESSES and (len(parts) < 2 or not parts[1]):
                errors.append(
                    f"{rel_tf}: structured claimed_by {claimed_by!r} must match "
                    "'<harness>:<session_id>[:<role_or_worktree>]'"
                )

    if "claimed_at" in tfm and tfm["claimed_at"] is not None:
        claimed_at = tfm["claimed_at"]
        if isinstance(claimed_at, str) and claimed_at.strip():
            raw_ts = claimed_at.strip()
            if raw_ts.endswith("Z"):
                raw_ts = f"{raw_ts[:-1]}+00:00"
            try:
                datetime.fromisoformat(raw_ts)
            except ValueError:
                errors.append(f"{rel_tf}: claimed_at {claimed_at!r} must be a valid ISO-8601 UTC timestamp")
        elif not isinstance(claimed_at, datetime):
            errors.append(f"{rel_tf}: claimed_at must be null or a valid ISO-8601 UTC timestamp")
    return errors


def _expected_checklist_marker(task_state: str) -> str:
    """Return the spec.md checklist character corresponding to ``task_state``."""
    if task_state in ("completed", "closed"):
        return "x"
    if task_state in ("deferred", "skipped"):
        return "-"
    if task_state == "in_progress":
        return "~"
    if task_state == "blocked":
        return "!"
    return " "


def _match_checklist_row(
    checklist_rows: list[tuple[str, str]],
    task_filename: str,
    task_id: str,
    task_stem: str,
) -> tuple[str, str] | None:
    """Find the checklist `(marker, text)` tuple referencing ``task_filename``, ``task_id``, or ``task_stem``."""
    for mark, rest in checklist_rows:
        stripped_rest = _CHECKLIST_SHA_PATTERN.sub("", rest).lstrip()
        if (
            f"tasks/{task_filename}" in rest
            or f"({task_filename})" in rest
            or stripped_rest.startswith(f"{task_id} ")
            or stripped_rest.startswith(f"{task_id}:")
            or stripped_rest.startswith(f"{task_stem} ")
            or stripped_rest.startswith(f"{task_stem}:")
        ):
            return mark, rest
    return None


def _split_frontmatter(text: str) -> tuple[dict[str, Any] | None, str]:
    """Parse leading YAML frontmatter using pure Python stdlib and return ``(frontmatter_dict, markdown_body)``."""
    normalized = text.replace("\r\n", "\n")
    if not normalized.startswith("---\n"):
        return None, normalized
    end_idx = normalized.find("\n---\n", 4)
    if end_idx == -1:
        return None, normalized
    raw_yaml = normalized[4:end_idx]
    body = normalized[end_idx + 5 :]
    parsed = _parse_simple_yaml(raw_yaml)
    return parsed, body


def _parse_scalar(val: str) -> Any:
    """Parse a scalar YAML value into a Python bool, int, list, dict, or str."""
    stripped = val.strip()
    if not stripped:
        return ""
    if stripped in ("true", "True"):
        return True
    if stripped in ("false", "False"):
        return False
    if stripped in ("null", "None", "~"):
        return None
    if (stripped.startswith('"') and stripped.endswith('"')) or (stripped.startswith("'") and stripped.endswith("'")):
        return stripped[1:-1]
    if stripped.startswith("[") and stripped.endswith("]"):
        inner = stripped[1:-1].strip()
        if not inner:
            return []
        return [_parse_scalar(item) for item in inner.split(",")]
    if stripped.startswith("{") and stripped.endswith("}"):
        inner = stripped[1:-1].strip()
        result: dict[str, Any] = {}
        if not inner:
            return result
        for pair in inner.split(","):
            if ":" in pair:
                k, v = pair.split(":", 1)
                result[k.strip()] = _parse_scalar(v)
        return result
    if stripped.isdigit():
        return int(stripped)
    return stripped


def _parse_simple_yaml(raw_yaml: str) -> dict[str, Any]:
    """Parse YAML frontmatter mappings, lists of scalars, and lists of mappings using stdlib."""
    result: dict[str, Any] = {}
    current_key: str | None = None
    current_list: list[Any] | None = None
    current_dict_item: dict[str, Any] | None = None

    for raw_line in raw_yaml.splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        line = raw_line.strip()

        if indent == 0 and ":" in line and not line.startswith("-"):
            current_dict_item = None
            current_list = None
            key, val_part = line.split(":", 1)
            current_key = key.strip()
            val_str = val_part.strip()
            if val_str:
                result[current_key] = _parse_scalar(val_str)
            else:
                current_list = []
                result[current_key] = current_list
        elif current_key is not None and line.startswith("- "):
            if current_list is None:
                current_list = []
                result[current_key] = current_list
            item_body = line[2:].strip()
            if ":" in item_body and not (item_body.startswith('"') or item_body.startswith("'")):
                k, v = item_body.split(":", 1)
                current_dict_item = {k.strip(): _parse_scalar(v)}
                current_list.append(current_dict_item)
            else:
                current_dict_item = None
                current_list.append(_parse_scalar(item_body))
        elif indent > 0 and current_dict_item is not None and ":" in line:
            k, v = line.split(":", 1)
            current_dict_item[k.strip()] = _parse_scalar(v)
        elif indent > 0 and current_key is not None and ":" in line:
            existing = result.get(current_key)
            if not isinstance(existing, dict):
                existing = {}
                result[current_key] = existing
            k, v = line.split(":", 1)
            existing[k.strip()] = _parse_scalar(v)

    return result


if __name__ == "__main__":
    raise SystemExit(main())

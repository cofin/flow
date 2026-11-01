"""Validate multi-harness manifests, hooks, subagents, skills, and OKF v0.2 bundles."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Any

__all__ = (
    "EXPECTED_AGENTS",
    "EXPECTED_SKILLS",
    "MAX_SKILL_DESCRIPTION_CHARS",
    "MAX_SKILL_FILE_BYTES",
    "READONLY_AGENTS",
    "REPO_ROOT",
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
    "validate_skills",
)

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = REPO_ROOT / "skills"
AGENTS_DIR = REPO_ROOT / "agents"
CODEX_AGENTS_DIR = REPO_ROOT / ".codex" / "agents"

MAX_SKILL_FILE_BYTES = 24000
MAX_SKILL_DESCRIPTION_CHARS = 500
SKILL_DESCRIPTION_PREFIX = "Use when"
FORBIDDEN_SKILL_DESCRIPTION_TERMS = (
    "Auto-activate",
    "Produces",
    "Expert knowledge",
    "Comprehensive",
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
        "mcpServers",
        "name",
        "rules",
        "skills",
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
_FOOTNOTE_DEF_PATTERN = re.compile(r"^\[\^([A-Za-z0-9_-]+)\]:\s+.+$", re.MULTILINE)


def validate_repository(repo_root: Path = REPO_ROOT) -> list[str]:
    """Run all structural and multi-harness validation checks against ``repo_root``."""
    errors: list[str] = []
    errors.extend(validate_manifests(repo_root))
    errors.extend(validate_hooks(repo_root))
    errors.extend(validate_agents(repo_root))
    errors.extend(validate_skills(repo_root))
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

    claude_plugin = loaded.get(".claude-plugin/plugin.json")
    if claude_plugin is not None and claude_plugin.get("hooks") != "./hooks/hooks-claude.json":
        errors.append(".claude-plugin/plugin.json: hooks must be './hooks/hooks-claude.json'")

    codex_plugin = loaded.get(".codex-plugin/plugin.json")
    if codex_plugin is not None and codex_plugin.get("hooks") != "./hooks/hooks-claude.json":
        errors.append(".codex-plugin/plugin.json: hooks must be './hooks/hooks-claude.json'")

    cursor_plugin = loaded.get(".cursor-plugin/plugin.json")
    if cursor_plugin is not None and cursor_plugin.get("hooks") != "./hooks/hooks-cursor.json":
        errors.append(".cursor-plugin/plugin.json: hooks must be './hooks/hooks-cursor.json'")

    pkg_json = loaded.get("package.json")
    if pkg_json is not None and pkg_json.get("main") != ".opencode/plugins/flow.js":
        errors.append("package.json: main must be '.opencode/plugins/flow.js'")

    return errors


def validate_hooks(repo_root: Path = REPO_ROOT) -> list[str]:
    """Validate hook configuration files, OpenCode V2 plugin entry, and POSIX sh + PowerShell SessionStart execution."""
    errors: list[str] = []
    hook_script = repo_root / "hooks" / "session-start.sh"
    if not hook_script.is_file():
        return ["Missing hooks/session-start.sh"]

    ps1_script = repo_root / "hooks" / "session-start.ps1"
    if not ps1_script.is_file():
        errors.append("Missing hooks/session-start.ps1")

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

    cursor_hooks_path = repo_root / "hooks" / "hooks-cursor.json"
    if not cursor_hooks_path.is_file():
        errors.append("Missing hooks/hooks-cursor.json")
    else:
        cursor_hooks = json.loads(cursor_hooks_path.read_text(encoding="utf-8"))
        if cursor_hooks.get("version") != 1 or "sessionStart" not in cursor_hooks.get("hooks", {}):
            errors.append("hooks/hooks-cursor.json: must declare version 1 and hooks.sessionStart")

    opencode_plugin = repo_root / ".opencode" / "plugins" / "flow.js"
    if not opencode_plugin.is_file():
        errors.append("Missing .opencode/plugins/flow.js")
    else:
        js_text = opencode_plugin.read_text(encoding="utf-8")
        if 'id: "flow"' not in js_text or "async setup(ctx)" not in js_text:
            errors.append(".opencode/plugins/flow.js: must export OpenCode V2 { id: 'flow', async setup(ctx) }")

    for harness, required_key in (
        ("agy", "injectSteps"),
        ("claude", "hookSpecificOutput"),
        ("cursor", "additional_context"),
    ):
        proc = subprocess.run(
            ["sh", str(hook_script), "--harness", harness, "--project", str(repo_root)],
            input="{}",
            text=True,
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
        for harness, required_key in (
            ("agy", "injectSteps"),
            ("claude", "hookSpecificOutput"),
            ("cursor", "additional_context"),
        ):
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
                    str(repo_root),
                ],
                input="{}",
                text=True,
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
        if not isinstance(frontmatter.get("commandExecutionPolicy"), str):
            errors.append(f"agents/{name}.md: missing commandExecutionPolicy string")

        skills_field = frontmatter.get("skills")
        if not isinstance(skills_field, list) or not skills_field:
            errors.append(f"agents/{name}.md: skills must be a non-empty YAML list")
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


def validate_okf_bundle(bundle_dir: Path) -> list[str]:
    """Validate an Open Knowledge Format (OKF v0.2) bundle directory."""
    errors: list[str] = []
    if not bundle_dir.is_dir():
        return [f"Bundle directory does not exist: {bundle_dir}"]

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

    for md_path in sorted(bundle_dir.rglob("*.md")):
        rel = md_path.relative_to(bundle_dir).as_posix()
        text = md_path.read_text(encoding="utf-8")
        fm, body = _split_frontmatter(text)

        if md_path.name in ("index.md", "log.md"):
            if fm is not None:
                for forbidden_key in ("type", "status", "sources"):
                    if forbidden_key in fm:
                        errors.append(f"{rel}: reserved file {md_path.name} must not declare {forbidden_key!r}")
            continue

        if fm is None:
            errors.append(f"{rel}: missing YAML frontmatter")
            continue

        for req_key in ("type", "title", "description"):
            if not str(fm.get(req_key, "")).strip():
                errors.append(f"{rel}: missing required frontmatter key {req_key!r}")

        sources = fm.get("sources")
        if isinstance(sources, list) and sources:
            footnotes = set(_FOOTNOTE_DEF_PATTERN.findall(body))
            for src in sources:
                if not isinstance(src, dict):
                    errors.append(f"{rel}: each item in sources must be a mapping")
                    continue
                src_id = str(src.get("id", "")).strip()
                if not src_id or not str(src.get("resource", "")).strip():
                    errors.append(f"{rel}: source entry must declare 'id' and 'resource'")
                elif src_id not in footnotes:
                    errors.append(f"{rel}: source id {src_id!r} missing matching [^{src_id}]: footnote in body")

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
    args = parser.parse_args(argv)

    errors = validate_repository(REPO_ROOT)
    if args.bundle is not None:
        errors.extend(validate_okf_bundle(args.bundle))

    if errors:
        for err in errors:
            sys.stderr.write(f"ERROR: {err}\n")
        sys.stderr.write(f"Validation failed with {len(errors)} error(s).\n")
        return 1

    sys.stdout.write("Validation passed: all manifests, hooks, subagents, skills, and links are valid.\n")
    return 0


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

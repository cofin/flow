"""Validate shipped skills / commands / agents manifest integrity.

Consolidated validator for all harnesses (Antigravity, Claude Code, Codex, etc.).
"""

from __future__ import annotations

import datetime
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any, NamedTuple, cast

if sys.version_info >= (3, 11):
    import tomllib as _tomllib
else:  # pragma: no cover - py310 fallback path
    import tomli as _tomllib  # type: ignore[import-not-found,unused-ignore]

import yaml

_toml_loads_any: Any = _tomllib.loads


def _toml_loads(text: str) -> dict[str, Any]:
    """Parse a TOML string into a dict, tolerant of py310 ``tomli`` fallback."""
    return cast("dict[str, Any]", _toml_loads_any(text))


_TOMLDecodeError: type[Exception] = cast(
    "type[Exception]",
    _tomllib.TOMLDecodeError,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = REPO_ROOT / "skills"
COMMANDS_DIR = REPO_ROOT / "commands"
AGENTS_DIR = REPO_ROOT / "agents"
OPENCODE_AGENTS_DIR = REPO_ROOT / ".opencode" / "agents"
CLAUDE_AGENTS_DIR = REPO_ROOT / ".claude-plugin" / "agents"
CODEX_AGENTS_DIR = REPO_ROOT / ".codex" / "agents"
VSCODE_AGENTS_DIR = REPO_ROOT / ".github" / "agents"
SHIPPED_ROOT_FILES = ("AGENTS.md", "CONTRIBUTING.md", "README.md")

MAX_DESCRIPTION_CHARS = 1024
MAX_SKILL_DESCRIPTION_CHARS = 500
SKILL_DESCRIPTION_PREFIX = "Use when"
FORBIDDEN_SKILL_DESCRIPTION_TERMS = (
    "Auto-activate",
    "Produces",
    "Expert knowledge",
    "Comprehensive",
)

REQUIRED_SECTIONS = ("workflow", "guardrails", "validation", "example")

_XML_TAG_PATTERNS = {name: re.compile(rf"<{name}\b", re.IGNORECASE) for name in REQUIRED_SECTIONS}
_H2_HEADING_PATTERNS = {
    name: re.compile(
        rf"^##\s+.*\b{name}s?\b",
        re.IGNORECASE | re.MULTILINE,
    )
    for name in REQUIRED_SECTIONS
}

LINK_PATTERN = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")

_AUTHORING_TREE_SUBPATHS: tuple[str, ...] = ()
AGENTS_LEAK_PATTERN = re.compile(rf"(?<![A-Za-z0-9_])\.agents/(?:{'|'.join(re.escape(p) for p in _AUTHORING_TREE_SUBPATHS)})") if _AUTHORING_TREE_SUBPATHS else re.compile(r"$.")

FORBIDDEN_VOCAB_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"/home/cody/", re.IGNORECASE), "machine-specific filesystem path '/home/cody/...'"),
)

_FORBIDDEN_VOCAB_ALLOWLIST: frozenset[str] = frozenset(
    {
        "tools/validate.py",
        "tools/validate-skills.py",
        "tests/test_validate_skills.py",
        "tests/test_validate.py",
    }
)

VALID_AGENT_MODES = frozenset({"subagent", "primary"})
VALID_AGENT_TOOLS = frozenset({"read", "grep", "glob", "bash", "edit", "write", "todoWrite", "webFetch", "webSearch"})
VALID_AGENT_PERMISSIONS = frozenset(
    {
        "edit",
        "bash",
        "webfetch",
        "read",
        "glob",
        "grep",
        "list",
        "task",
        "websearch",
        "lsp",
        "skill",
        "external_directory",
        "todowrite",
        "question",
        "doom_loop",
    }
)
VALID_PERMISSION_DECISIONS = frozenset({"allow", "ask", "deny"})

VALID_CLAUDE_TOOLS = frozenset(
    {
        "Read",
        "Grep",
        "Glob",
        "Bash",
        "Edit",
        "Write",
        "WebFetch",
        "WebSearch",
        "TodoWrite",
        "NotebookEdit",
    }
)

_CLAUDE_HOOK_EVENT_PATTERN = re.compile(r"^[A-Z][A-Za-z0-9]*$")
ANTIGRAVITY_ROOT_TOKENS = ("ANTIGRAVITY_PLUGIN_ROOT", "AGY_PLUGIN_ROOT", "PLUGIN_ROOT")

_CODEX_NICKNAME_PATTERN = re.compile(r"^[A-Za-z0-9 _-]+$")
_AGENT_REFERENCE_PATTERN = re.compile(r"@([A-Za-z][A-Za-z0-9:_-]*)")

# Codex consolidation constants
PACKAGE_ROOT = Path("plugins/flow")
PACKAGE_DIRS = (
    ".codex-plugin",
    "skills",
    "commands",
    ".codex",
    "hooks",
)


class Violation(NamedTuple):
    path: Path
    line: int | None
    message: str


class OKFLayout(NamedTuple):
    """Resolved, repository-contained locations for one Flow installation."""

    configured_root: Path
    bundle_root: Path


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _plugin_root(manifest_path: Path) -> Path:
    return manifest_path.parent.parent.resolve()


def _resolve_plugin_path(manifest_path: Path, raw_path: str) -> tuple[Path | None, str | None]:
    plugin_root = _plugin_root(manifest_path)
    resolved = (plugin_root / raw_path).resolve()
    try:
        resolved.relative_to(plugin_root)
    except ValueError:
        return None, f"path {raw_path!r} escapes plugin root"
    return resolved, None


def _validate_manifest_path_field(path: Path, field: str, value: object) -> list[Violation]:
    if not isinstance(value, str) or not value.strip():
        return [Violation(path, 1, f"manifest field {field!r} must be a non-empty string path")]
    resolved, error = _resolve_plugin_path(path, value)
    if error is not None:
        return [Violation(path, 1, f"manifest field {field!r} {error}")]
    assert resolved is not None
    if not resolved.exists():
        return [Violation(path, 1, f"manifest path for {field!r} entry {value!r} does not exist")]
    return []


def _validate_manifest_path_list_field(path: Path, field: str, value: object) -> list[Violation]:
    violations: list[Violation] = []
    if not isinstance(value, list):
        return [Violation(path, 1, f"manifest field {field!r} must be an array of string paths")]
    for entry in value:
        if not isinstance(entry, str) or not entry.strip():
            violations.append(Violation(path, 1, f"manifest field {field!r} entries must be non-empty strings"))
            continue
        resolved, error = _resolve_plugin_path(path, entry)
        if error is not None:
            violations.append(Violation(path, 1, f"manifest path for {field!r} entry {entry!r} {error}"))
            continue
        assert resolved is not None
        if not resolved.exists():
            violations.append(Violation(path, 1, f"manifest path for {field!r} entry {entry!r} does not exist"))
    return violations


def _validate_hook_event_map(path: Path, hooks: object, *, allow_flat_events: set[str] | None = None) -> list[Violation]:
    violations: list[Violation] = []
    if not isinstance(hooks, dict):
        return [Violation(path, 1, "hook config must contain a top-level 'hooks' record")]
    if allow_flat_events is None:
        allow_flat_events = set()

    for event_name, handlers in hooks.items():
        if not isinstance(event_name, str) or not _CLAUDE_HOOK_EVENT_PATTERN.match(event_name):
            violations.append(Violation(path, 1, f"hooks event {event_name!r} must be PascalCase"))
        if not isinstance(handlers, list):
            violations.append(Violation(path, 1, f"hooks event {event_name!r} must map to a list"))
            continue

        is_flat_event = event_name in allow_flat_events

        for item in handlers:
            if not isinstance(item, dict):
                violations.append(Violation(path, 1, f"hooks event {event_name!r} entries must be objects"))
                continue
            
            if is_flat_event:
                # Flat structure: must be a hook block directly
                if item.get("type") != "command":
                    violations.append(
                        Violation(path, 1, f"hooks event {event_name!r} flat hook entries must use type 'command'")
                    )
                command = item.get("command")
                if not isinstance(command, str) or not command.strip():
                    violations.append(
                        Violation(path, 1, f"hooks event {event_name!r} flat hook entries need a non-empty command")
                    )
            else:
                # Nested structure: must be a matcher block containing hooks list
                nested_hooks = item.get("hooks")
                if not isinstance(nested_hooks, list) or not nested_hooks:
                    violations.append(
                        Violation(path, 1, f"hooks event {event_name!r} entries must contain a non-empty 'hooks' list")
                    )
                    continue
                for hook in nested_hooks:
                    if not isinstance(hook, dict):
                        violations.append(
                            Violation(path, 1, f"hooks event {event_name!r} hook entries must be objects")
                        )
                        continue
                    if hook.get("type") != "command":
                        violations.append(
                            Violation(path, 1, f"hooks event {event_name!r} hook entries must use type 'command'")
                        )
                    command = hook.get("command")
                    if not isinstance(command, str) or not command.strip():
                        violations.append(
                            Violation(path, 1, f"hooks event {event_name!r} hook entries need a non-empty command")
                        )
    return violations


def _iter_nested_strings(value: object) -> Iterator[str]:
    if isinstance(value, str):
        yield value
        return
    if isinstance(value, dict):
        for nested in value.values():
            yield from _iter_nested_strings(nested)
        return
    if isinstance(value, list):
        for nested in value:
            yield from _iter_nested_strings(nested)


def _load_hook_event_map(path: Path) -> tuple[dict[str, object] | None, list[Violation]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        return None, [Violation(path, 1, f"JSON parse error: {exc}")]

    if not isinstance(data, dict):
        return None, [Violation(path, 1, "hook config must be a JSON object")]

    hooks = data.get("hooks")
    if not isinstance(hooks, dict):
        return None, [Violation(path, 1, "hook config must contain a top-level 'hooks' record")]

    return cast("dict[str, object]", hooks), []


def validate_claude_hook_config(path: Path) -> list[Violation]:
    """Validate Claude's hook config file for harness-specific placeholder usage."""
    hook_events, violations = _load_hook_event_map(path)
    if hook_events is None:
        return violations

    violations.extend(_validate_hook_event_map(path, hook_events))
    for entry in _iter_nested_strings(hook_events):
        if "${extensionPath}" in entry:
            violations.append(
                Violation(
                    path,
                    1,
                    "Claude hook config must not use '${extensionPath}'; use '${CLAUDE_PLUGIN_ROOT}' instead",
                )
            )
            break
    return violations


ANTIGRAVITY_HOOK_EVENTS = frozenset({"PreToolUse", "PostToolUse", "PreInvocation", "PostInvocation", "Stop"})


def validate_antigravity_hook_config(path: Path) -> list[Violation]:
    """Validate Antigravity's named-hook config: {"<name>": {"<Event>": [handlers]}}."""
    violations: list[Violation] = []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        return [Violation(path, 1, f"JSON parse error: {exc}")]
    if not isinstance(data, dict) or not data:
        return [Violation(path, 1, "Antigravity hook config must be a non-empty JSON object of named hooks")]

    for hook_name, events in data.items():
        if not isinstance(events, dict):
            violations.append(Violation(path, 1, f"hook {hook_name!r} must map events to handler lists"))
            continue
        for event_name, handlers in events.items():
            if event_name not in ANTIGRAVITY_HOOK_EVENTS:
                violations.append(
                    Violation(
                        path,
                        1,
                        f"hook {hook_name!r} uses unknown Antigravity event {event_name!r} "
                        f"(supported: {', '.join(sorted(ANTIGRAVITY_HOOK_EVENTS))}; there is no SessionStart)",
                    )
                )
            if not isinstance(handlers, list) or not handlers:
                violations.append(Violation(path, 1, f"hook {hook_name!r} event {event_name!r} must be a non-empty list"))
                continue
            for handler in handlers:
                if not isinstance(handler, dict) or handler.get("type") != "command" or not handler.get("command"):
                    violations.append(
                        Violation(path, 1, f"hook {hook_name!r} event {event_name!r} handlers must be command objects")
                    )

    saw_root_token = False
    for entry in _iter_nested_strings(data):
        if "${extensionPath}" in entry or "${/}" in entry:
            violations.append(
                Violation(
                    path,
                    1,
                    "Antigravity hook config must not use legacy extension template tokens",
                )
            )
        if any(token in entry for token in ANTIGRAVITY_ROOT_TOKENS):
            saw_root_token = True
    if not saw_root_token:
        violations.append(
            Violation(
                path,
                1,
                "Antigravity hook config must resolve the plugin root with ANTIGRAVITY_PLUGIN_ROOT, AGY_PLUGIN_ROOT, or PLUGIN_ROOT",
            )
        )
    return violations


def extract_frontmatter(text: str) -> tuple[dict[str, Any], int, str]:
    if not text.startswith("---\n"):
        msg = "missing YAML frontmatter"
        raise ValueError(msg)
    try:
        end = text.index("\n---\n", 4)
    except ValueError as exc:
        msg = "unterminated YAML frontmatter"
        raise ValueError(msg) from exc
    raw = text[4:end]
    loaded = yaml.safe_load(raw)
    fm: dict[str, Any] = {} if loaded is None else cast("dict[str, Any]", loaded)
    body_start_line = text[: end + 5].count("\n") + 1
    body = text[end + 5 :]
    return fm, body_start_line, body


def _check_description(desc: object, path: Path, line: int) -> list[Violation]:
    out: list[Violation] = []
    if not isinstance(desc, str) or not desc.strip():
        out.append(Violation(path, line, "description missing or empty"))
    elif len(desc) > MAX_DESCRIPTION_CHARS:
        out.append(
            Violation(
                path,
                line,
                f"description length {len(desc)} > {MAX_DESCRIPTION_CHARS}",
            )
        )
    return out


def _check_skill_description(desc: object, path: Path, line: int) -> list[Violation]:
    out = _check_description(desc, path, line)
    if not isinstance(desc, str) or not desc.strip():
        return out
    if len(desc) > MAX_SKILL_DESCRIPTION_CHARS:
        out.append(
            Violation(
                path,
                line,
                f"skill description length {len(desc)} > {MAX_SKILL_DESCRIPTION_CHARS}",
            )
        )
    if not desc.startswith(SKILL_DESCRIPTION_PREFIX):
        out.append(Violation(path, line, "skill description must start with 'Use when'"))
    lowered = desc.lower()
    for term in FORBIDDEN_SKILL_DESCRIPTION_TERMS:
        if term.lower() in lowered:
            out.append(
                Violation(
                    path,
                    line,
                    f"skill description contains workflow/output summary term {term!r}",
                )
            )
    return out


def _validate_openai_metadata(skill_path: Path) -> list[Violation]:
    metadata_path = skill_path.parent / "agents" / "openai.yaml"
    if not metadata_path.is_file():
        return [Violation(skill_path, 1, "agents/openai.yaml missing")]
    try:
        data = yaml.safe_load(metadata_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        return [Violation(metadata_path, 1, f"YAML parse error: {exc}")]
    if not isinstance(data, dict):
        return [Violation(metadata_path, 1, "agents/openai.yaml must be a mapping")]
    interface = data.get("interface")
    if not isinstance(interface, dict):
        return [Violation(metadata_path, 1, "agents/openai.yaml must contain interface mapping")]
    violations: list[Violation] = []
    for field in ("display_name", "short_description"):
        value = interface.get(field)
        if not isinstance(value, str) or not value.strip():
            violations.append(Violation(metadata_path, 1, f"interface.{field} missing or empty"))
    return violations


def _section_present(body: str, section: str) -> bool:
    if _XML_TAG_PATTERNS[section].search(body):
        return True
    return bool(_H2_HEADING_PATTERNS[section].search(body))


def validate_skill(path: Path) -> list[Violation]:
    violations: list[Violation] = []
    text = path.read_text(encoding="utf-8")
    try:
        fm, body_start, body = extract_frontmatter(text)
    except ValueError as exc:
        return [Violation(path, 1, str(exc))]
    expected_name = path.parent.name
    fm_name = fm.get("name")
    if fm_name != expected_name:
        violations.append(Violation(path, 1, f"name {fm_name!r} != parent dir {expected_name!r}"))
    violations.extend(_check_skill_description(fm.get("description"), path, 1))
    violations.extend(_validate_openai_metadata(path))
    for section in REQUIRED_SECTIONS:
        if not _section_present(body, section):
            violations.append(
                Violation(
                    path,
                    body_start,
                    f"missing required section <{section}> (XML tag or '## {section.title()}' heading)",
                )
            )
    body_no_code = re.sub(r"```.*?```", "", body, flags=re.DOTALL)
    body_no_code = re.sub(r"`.*?`", "", body_no_code)

    for match in LINK_PATTERN.finditer(body_no_code):
        target = match.group(2).split("#")[0].strip()
        if not target:
            continue
        if target.startswith(("http://", "https://", "mailto:", "tel:")):
            continue
        resolved = (path.parent / target).resolve()
        if not resolved.exists():
            violations.append(Violation(path, body_start, f"broken link target: {target}"))
    return violations


def validate_command(path: Path) -> list[Violation]:
    violations: list[Violation] = []
    try:
        data = _toml_loads(path.read_text(encoding="utf-8"))
    except _TOMLDecodeError as exc:
        return [Violation(path, 1, f"TOML parse error: {exc}")]
    violations.extend(_check_description(data.get("description"), path, 1))
    prompt = data.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        violations.append(Violation(path, 1, "prompt missing or empty"))
    return violations


def validate_opencode_agent(path: Path) -> list[Violation]:
    violations: list[Violation] = []
    text = path.read_text(encoding="utf-8")
    try:
        fm, _body_start, _body = extract_frontmatter(text)
    except ValueError as exc:
        return [Violation(path, 1, str(exc))]
    expected_name = path.stem
    if fm.get("name") != expected_name:
        violations.append(Violation(path, 1, f"name {fm.get('name')!r} != filename stem {expected_name!r}"))
    violations.extend(_check_description(fm.get("description"), path, 1))
    mode = fm.get("mode")
    if mode not in VALID_AGENT_MODES:
        violations.append(Violation(path, 1, f"mode {mode!r} not in {sorted(VALID_AGENT_MODES)}"))
    permission = fm.get("permission")
    tools = fm.get("tools")
    if permission is not None:
        violations.extend(_check_opencode_permission(permission, path))
    elif isinstance(tools, dict):
        tools_typed = cast("dict[str, Any]", tools)
        for key, value in tools_typed.items():
            key_s = str(key)
            if key_s not in VALID_AGENT_TOOLS:
                violations.append(Violation(path, 1, f"tool key {key_s!r} not in whitelist"))
            if not isinstance(value, bool):
                type_name = type(value).__name__
                violations.append(
                    Violation(
                        path,
                        1,
                        f"tool {key_s!r} value must be bool, got {type_name}",
                    )
                )
    else:
        violations.append(Violation(path, 1, "permission object or tools mapping missing"))
    return violations


def _check_opencode_permission(permission: Any, path: Path) -> list[Violation]:
    violations: list[Violation] = []
    if not isinstance(permission, dict):
        return [Violation(path, 1, "permission must be a mapping")]
    permission_typed = cast("dict[str, Any]", permission)
    for key, value in permission_typed.items():
        key_s = str(key)
        if key_s not in VALID_AGENT_PERMISSIONS:
            violations.append(Violation(path, 1, f"permission key {key_s!r} not in whitelist"))
        if isinstance(value, dict):
            for decision in cast("dict[str, Any]", value).values():
                if decision not in VALID_PERMISSION_DECISIONS:
                    violations.append(Violation(path, 1, f"permission {key_s!r} decision {decision!r} not in {sorted(VALID_PERMISSION_DECISIONS)}"))
        elif value not in VALID_PERMISSION_DECISIONS:
            violations.append(Violation(path, 1, f"permission {key_s!r} value {value!r} not in {sorted(VALID_PERMISSION_DECISIONS)}"))
    return violations


def validate_antigravity_agent(path: Path) -> list[Violation]:
    violations: list[Violation] = []
    text = path.read_text(encoding="utf-8")
    try:
        fm, _body_start, _body = extract_frontmatter(text)
    except ValueError as exc:
        return [Violation(path, 1, str(exc))]
    expected_name = path.stem
    if fm.get("name") != expected_name:
        violations.append(Violation(path, 1, f"name {fm.get('name')!r} != filename stem {expected_name!r}"))
    violations.extend(_check_description(fm.get("description"), path, 1))
    if "mode" in fm:
        violations.append(Violation(path, 1, "mode key not allowed (Antigravity subagents reject OpenCode schema)"))
    if "permission" in fm:
        violations.append(Violation(path, 1, "permission key not allowed (Antigravity subagents reject OpenCode schema)"))
    tools = fm.get("tools")
    if tools is None:
        return violations
    if not isinstance(tools, list):
        violations.append(Violation(path, 1, "tools must be a list of strings"))
        return violations
    tools_list = cast("list[Any]", tools)  # type: ignore[redundant-cast]
    for entry in tools_list:
        if not isinstance(entry, str) or not entry.strip():
            type_name = type(entry).__name__
            violations.append(Violation(path, 1, f"tools entry must be a string, got {type_name}"))
    return violations


def validate_claude_agent(path: Path) -> list[Violation]:
    violations: list[Violation] = []
    text = path.read_text(encoding="utf-8")
    try:
        fm, _body_start, _body = extract_frontmatter(text)
    except ValueError as exc:
        return [Violation(path, 1, str(exc))]
    expected_name = path.stem
    if fm.get("name") != expected_name:
        violations.append(Violation(path, 1, f"name {fm.get('name')!r} != filename stem {expected_name!r}"))
    violations.extend(_check_description(fm.get("description"), path, 1))
    if "mode" in fm:
        violations.append(Violation(path, 1, "mode key not allowed (Claude subagents reject it)"))
    tools = fm.get("tools")
    if tools is None:
        return violations
    if not isinstance(tools, str):
        violations.append(
            Violation(path, 1, "tools must be a comma-separated string (Claude rejects YAML lists/dicts)")
        )
        return violations
    for entry in (t.strip() for t in tools.split(",")):
        if not entry:
            continue
        if entry not in VALID_CLAUDE_TOOLS:
            violations.append(Violation(path, 1, f"tool {entry!r} not in Claude tool registry"))
    return violations


def validate_vscode_agent(path: Path) -> list[Violation]:
    violations: list[Violation] = []
    if not path.name.endswith(".agent.md"):
        violations.append(Violation(path, 1, "VS Code custom agents must use the .agent.md extension"))
    text = path.read_text(encoding="utf-8")
    try:
        fm, _body_start, _body = extract_frontmatter(text)
    except ValueError as exc:
        return [Violation(path, 1, str(exc))]
    expected_name = path.name.removesuffix(".agent.md")
    if fm.get("name") != expected_name:
        violations.append(Violation(path, 1, f"name {fm.get('name')!r} != filename stem {expected_name!r}"))
    violations.extend(_check_description(fm.get("description"), path, 1))
    tools = fm.get("tools")
    if tools is not None:
        if not isinstance(tools, list):
            violations.append(Violation(path, 1, "tools must be a list when present"))
        else:
            for entry in cast("list[Any]", tools):  # type: ignore[redundant-cast]
                if not isinstance(entry, str) or not entry.strip():
                    violations.append(Violation(path, 1, "tools entries must be non-empty strings"))
    agents = fm.get("agents")
    if agents is not None:
        if agents != "*" and not isinstance(agents, list):
            violations.append(Violation(path, 1, "agents must be '*' or a list when present"))
        elif isinstance(agents, list):
            for entry in cast("list[Any]", agents):  # type: ignore[redundant-cast]
                if not isinstance(entry, str) or not entry.strip():
                    violations.append(Violation(path, 1, "agents entries must be non-empty strings"))
    return violations


def validate_command_agent_references(path: Path) -> list[Violation]:
    violations: list[Violation] = []
    try:
        data = _toml_loads(path.read_text(encoding="utf-8"))
    except _TOMLDecodeError as exc:
        return [Violation(path, 1, f"TOML parse error: {exc}")]
    prompt = data.get("prompt")
    if not isinstance(prompt, str):
        return violations
    known_agents = {agent_path.stem for agent_path in iter_antigravity_agents()}
    for match in _AGENT_REFERENCE_PATTERN.finditer(prompt):
        mention = match.group(1)
        if mention.startswith("flow:"):
            violations.append(
                Violation(path, 1, f"agent mention '@{mention}' must use the slug without the flow: namespace")
            )
            continue
        if mention in {"code-reviewer", "executor", "plan-generator", "prd-orchestrator"} and mention not in known_agents:
            violations.append(Violation(path, 1, f"agent mention '@{mention}' has no matching agents/{mention}.md"))
    return violations


def validate_manifest(path: Path) -> list[Violation]:
    violations: list[Violation] = []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        return [Violation(path, 1, f"JSON parse error: {exc}")]

    harness_dir = path.parent.name
    is_claude = harness_dir == ".claude-plugin"

    if is_claude:
        for field in ("agents", "skills", "commands"):
            val = data.get(field)
            if val is not None and not isinstance(val, list):
                violations.append(
                    Violation(
                        path,
                        1,
                        f"Claude manifest {field!r} field must be an array for maximum reliability",
                    )
                )
            if val is not None:
                violations.extend(_validate_manifest_path_list_field(path, field, val))

        hooks = data.get("hooks")
        if isinstance(hooks, str):
            violations.extend(_validate_manifest_path_field(path, "hooks", hooks))
        elif hooks is not None:
            violations.extend(_validate_hook_event_map(path, hooks))
    else:
        for field in ("skills", "commands", "hooks"):
            value = data.get(field)
            if value is not None:
                violations.extend(_validate_manifest_path_field(path, field, value))
        agents = data.get("agents")
        if agents is not None:
            if isinstance(agents, list):
                violations.extend(_validate_manifest_path_list_field(path, "agents", agents))
            else:
                violations.extend(_validate_manifest_path_field(path, "agents", agents))

    return violations


def validate_codex_agent(path: Path) -> list[Violation]:
    violations: list[Violation] = []
    try:
        data = _toml_loads(path.read_text(encoding="utf-8"))
    except _TOMLDecodeError as exc:
        return [Violation(path, 1, f"TOML parse error: {exc}")]
    expected_name = path.stem
    fm_name = data.get("name")
    if fm_name != expected_name:
        violations.append(Violation(path, 1, f"name {fm_name!r} != filename stem {expected_name!r}"))
    violations.extend(_check_description(data.get("description"), path, 1))
    instructions = data.get("developer_instructions")
    if not isinstance(instructions, str) or not instructions.strip():
        violations.append(Violation(path, 1, "developer_instructions missing or empty"))
    if "tools" in data:
        violations.append(
            Violation(
                path,
                1,
                "tools key not allowed (Codex inherits tools from session config.toml)",
            )
        )
    if "mode" in data:
        violations.append(
            Violation(
                path,
                1,
                "mode key not allowed (Codex has no mode concept; OpenCode dialect leak)",
            )
        )
    nicknames = data.get("nickname_candidates")
    if nicknames is not None:
        if not isinstance(nicknames, list) or not nicknames:
            violations.append(Violation(path, 1, "nickname_candidates must be a non-empty list"))
        else:
            nicknames_typed = cast("list[Any]", nicknames)  # type: ignore[redundant-cast]
            seen: set[str] = set()
            for entry in nicknames_typed:
                if not isinstance(entry, str):
                    type_name = type(entry).__name__
                    violations.append(
                        Violation(path, 1, f"nickname_candidates entry must be a string, got {type_name}")
                    )
                    continue
                if entry in seen:
                    violations.append(Violation(path, 1, f"nickname_candidates entry {entry!r} is duplicated"))
                seen.add(entry)
                if not _CODEX_NICKNAME_PATTERN.match(entry):
                    violations.append(
                        Violation(
                            path,
                            1,
                            f"nickname_candidates entry {entry!r} must match [A-Za-z0-9 _-]+",
                        )
                    )
    return violations


def check_agents_leak(files: Iterable[Path]) -> list[Violation]:
    violations: list[Violation] = []
    for path in files:
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            if AGENTS_LEAK_PATTERN.search(line):
                snippet = line.strip()
                if len(snippet) > 80:
                    snippet = snippet[:77] + "..."
                violations.append(
                    Violation(
                        path,
                        lineno,
                        f"shipped content references framework path: {snippet}",
                    )
                )
    return violations


def check_forbidden_vocab(files: Iterable[Path]) -> list[Violation]:
    violations: list[Violation] = []
    for path in files:
        rel = _rel(path)
        if rel in _FORBIDDEN_VOCAB_ALLOWLIST:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            for pattern, label in FORBIDDEN_VOCAB_PATTERNS:
                if pattern.search(line):
                    snippet = line.strip()
                    if len(snippet) > 80:
                        snippet = snippet[:77] + "..."
                    violations.append(
                        Violation(
                            path,
                            lineno,
                            f"forbidden vocabulary ({label}): {snippet}",
                        )
                    )
                    break
    return violations


def iter_skills() -> Iterator[Path]:
    if SKILLS_DIR.is_dir():
        yield from sorted(SKILLS_DIR.glob("*/SKILL.md"))


def iter_commands() -> Iterator[Path]:
    if COMMANDS_DIR.is_dir():
        yield from sorted(COMMANDS_DIR.rglob("*.toml"))


def iter_antigravity_agents() -> Iterator[Path]:
    if AGENTS_DIR.is_dir():
        yield from sorted(AGENTS_DIR.glob("*.md"))


def iter_opencode_agents() -> Iterator[Path]:
    if OPENCODE_AGENTS_DIR.is_dir():
        yield from sorted(OPENCODE_AGENTS_DIR.glob("*.md"))


def iter_claude_agents() -> Iterator[Path]:
    seen: set[Path] = set()
    if CLAUDE_AGENTS_DIR.is_dir():
        for path in sorted(CLAUDE_AGENTS_DIR.glob("*.md")):
            resolved = path.resolve()
            seen.add(resolved)
            yield path

    manifest_path = REPO_ROOT / ".claude-plugin" / "plugin.json"
    if not manifest_path.is_file():
        return
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return
    agents = data.get("agents") if isinstance(data, dict) else None
    if isinstance(agents, str):
        agent_paths: Iterable[str] = (agents,)
    elif isinstance(agents, list):
        agent_paths = (entry for entry in agents if isinstance(entry, str))
    else:
        return
    for raw_path in agent_paths:
        resolved, error = _resolve_plugin_path(manifest_path, raw_path)
        if error is not None or resolved is None or not resolved.is_dir():
            continue
        for path in sorted(resolved.glob("*.md")):
            real = path.resolve()
            if real in seen:
                continue
            seen.add(real)
            yield path


def iter_codex_agents() -> Iterator[Path]:
    if CODEX_AGENTS_DIR.is_dir():
        yield from sorted(CODEX_AGENTS_DIR.glob("*.toml"))


def iter_vscode_agents() -> Iterator[Path]:
    if VSCODE_AGENTS_DIR.is_dir():
        yield from sorted(VSCODE_AGENTS_DIR.glob("*.agent.md"))


def iter_manifests() -> Iterator[Path]:
    for harness in (".claude-plugin", ".codex-plugin"):
        candidate = REPO_ROOT / harness / "plugin.json"
        if candidate.is_file():
            yield candidate


def iter_claude_hook_configs() -> Iterator[Path]:
    manifest_path = REPO_ROOT / ".claude-plugin" / "plugin.json"
    if manifest_path.is_file():
        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            data = {}
        hooks = data.get("hooks") if isinstance(data, dict) else None
        if isinstance(hooks, str) and hooks.strip():
            resolved, error = _resolve_plugin_path(manifest_path, hooks)
            if error is None and resolved is not None and resolved.is_file():
                yield resolved
                return

    default_hooks = REPO_ROOT / "hooks" / "hooks.json"
    if default_hooks.is_file():
        yield default_hooks


def iter_antigravity_hook_configs() -> Iterator[Path]:
    candidate = REPO_ROOT / "hooks" / "hooks-agy.json"
    if candidate.is_file():
        yield candidate


def iter_all_shipped_files() -> Iterator[Path]:
    yield from iter_manifests()
    if SKILLS_DIR.is_dir():
        yield from sorted(SKILLS_DIR.rglob("*.md"))
    if COMMANDS_DIR.is_dir():
        yield from sorted(COMMANDS_DIR.rglob("*.toml"))
    if AGENTS_DIR.is_dir():
        yield from sorted(AGENTS_DIR.rglob("*.md"))
    if OPENCODE_AGENTS_DIR.is_dir():
        yield from sorted(OPENCODE_AGENTS_DIR.rglob("*.md"))
    if CLAUDE_AGENTS_DIR.is_dir():
        yield from sorted(CLAUDE_AGENTS_DIR.rglob("*.md"))
    if CODEX_AGENTS_DIR.is_dir():
        yield from sorted(CODEX_AGENTS_DIR.glob("*.toml"))
    if VSCODE_AGENTS_DIR.is_dir():
        yield from sorted(VSCODE_AGENTS_DIR.rglob("*.md"))
    cursor_rules_dir = REPO_ROOT / ".cursor" / "rules"
    if cursor_rules_dir.is_dir():
        yield from sorted(cursor_rules_dir.rglob("*.mdc"))
    for name in SHIPPED_ROOT_FILES:
        candidate = REPO_ROOT / name
        if candidate.is_file():
            yield candidate
    docs_dir = REPO_ROOT / "docs"
    if docs_dir.is_dir():
        yield from sorted(docs_dir.rglob("*.md"))
    for rel in (
        ".opencode/INSTALL.md",
        ".opencode/plugins/litestar-skills.js",
        ".codex/INSTALL.md",
        ".codex/config.toml",
    ):
        candidate = REPO_ROOT / rel
        if candidate.is_file():
            yield candidate


def _print_violations(violations: list[Violation]) -> None:
    for v in violations:
        loc = f":{v.line}" if v.line is not None else ""
        print(f"[FAIL] {_rel(v.path)}{loc}: {v.message}")


# --- Consolidated Validators ---

def discover_antigravity_plugin_manifests(repo_root: Path) -> Iterator[Path]:
    candidate = repo_root / "plugin.json"
    if candidate.is_file():
        yield candidate


def validate_antigravity_plugin_manifest(repo_root: Path) -> list[Violation]:
    path = repo_root / "plugin.json"
    violations: list[Violation] = []
    if not path.is_file():
        return [Violation(path, None, "missing plugin.json")]
    
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        return [Violation(path, 1, f"JSON parse error: {exc}")]

    if not isinstance(data, dict):
        return [Violation(path, 1, "manifest must be a JSON object")]

    if data.get("$schema") != "https://antigravity.google/schemas/v1/plugin.json":
        violations.append(Violation(path, 1, "schema must be https://antigravity.google/schemas/v1/plugin.json"))
    for field in ("name", "description"):
        value = data.get(field)
        if not isinstance(value, str) or not value.strip():
            violations.append(Violation(path, 1, f"{field!r} must be a non-empty string"))
    return violations


def _iter_hook_commands(hooks_manifest: object) -> Iterator[str]:
    if not isinstance(hooks_manifest, dict):
        return
    hooks = hooks_manifest.get("hooks")
    if not isinstance(hooks, dict):
        return
    session_start = hooks.get("SessionStart")
    if not isinstance(session_start, list):
        return
    for item in session_start:
        if not isinstance(item, dict):
            continue
        nested_hooks = item.get("hooks")
        if isinstance(nested_hooks, list):
            for hook in nested_hooks:
                if isinstance(hook, dict):
                    command = hook.get("command")
                    if isinstance(command, str):
                        yield command
        else:
            command = item.get("command")
            if isinstance(command, str):
                yield command


def validate_antigravity_hook_commands(repo_root: Path) -> list[Violation]:
    path = repo_root / "hooks" / "hooks-agy.json"
    violations: list[Violation] = []
    if not path.is_file():
        return [Violation(path, None, "missing hooks/hooks-agy.json")]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        return [Violation(path, 1, f"JSON parse error: {exc}")]

    if not isinstance(data, dict):
        return [Violation(path, 1, "hooks manifest must be a JSON object")]

    commands = [
        handler.get("command")
        for events in data.values() if isinstance(events, dict)
        for handlers in events.values() if isinstance(handlers, list)
        for handler in handlers if isinstance(handler, dict) and isinstance(handler.get("command"), str)
    ]
    if not commands:
        return [Violation(path, 1, "no command hooks found in Antigravity manifest")]
    for command in commands:
        if "python" in command:
            violations.append(Violation(path, 1, f"Antigravity hook commands must not require Python at runtime: {command!r}"))

    for command in commands:
        for token in ("${extensionPath}", "${/}"):
            if token in command:
                violations.append(Violation(path, 1, f"unsupported template token {token!r} in hook command"))
        if not any(token in command for token in ("ANTIGRAVITY_PLUGIN_ROOT", "AGY_PLUGIN_ROOT", "PLUGIN_ROOT")):
            violations.append(Violation(path, 1, f"hook command must resolve an Antigravity plugin root: {command!r}"))
    return violations


def validate_claude_manifests_with_cli(repo_root: Path) -> list[Violation]:
    violations: list[Violation] = []
    if os.environ.get("SKIP_CLAUDE_VALIDATE") == "1":
        return []

    claude_cmd = shutil.which("claude")
    if claude_cmd is None:
        return [Violation(repo_root / ".claude-plugin" / "plugin.json", None, 
                          "claude CLI not found on PATH. Install Claude Code or set SKIP_CLAUDE_VALIDATE=1")]

    targets = (
        repo_root / ".claude-plugin" / "plugin.json",
        repo_root / ".claude-plugin" / "marketplace.json",
    )

    for target in targets:
        if not target.is_file():
            violations.append(Violation(target, None, "missing file"))
            continue
        
        result = subprocess.run(
            [claude_cmd, "plugin", "validate", str(target)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        if result.returncode != 0:
            msg = result.stdout + result.stderr
            violations.append(Violation(target, None, f"Claude CLI validation failed:\n{msg}"))
            
    return violations


def discover_codex_marketplaces(root: Path) -> Iterator[Path]:
    candidate = root / ".agents" / "plugins" / "marketplace.json"
    if candidate.is_file():
        yield candidate


def discover_codex_plugin_manifests(root: Path) -> Iterator[Path]:
    root_manifest = root / ".codex-plugin" / "plugin.json"
    if root_manifest.is_file():
        yield root_manifest
    package_manifest = root / PACKAGE_ROOT / ".codex-plugin" / "plugin.json"
    if package_manifest.is_file():
        yield package_manifest


def validate_codex_marketplace(path: Path, repo_root: Path) -> list[Violation]:
    violations: list[Violation] = []
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        return [Violation(path, 1, f"Invalid JSON: {e}")]

    for plugin in data.get('plugins', []):
        name = plugin.get('name', 'unknown')
        source_field = plugin.get('source', {})

        path_str = ""
        is_local = False
        if isinstance(source_field, str):
            path_str, is_local = source_field, True
        elif isinstance(source_field, dict) and source_field.get('source') == 'local':
            path_str = source_field.get('path', '')
            is_local = True

        if not is_local:
            continue

        if not path_str.startswith('./'):
            violations.append(Violation(path, 1, f"[plugin {name}]: path '{path_str}' must start with './'"))
        normalized = path_str[2:] if path_str.startswith('./') else path_str
        if not normalized or normalized.strip('/') == '':
            violations.append(Violation(path, 1, f"[plugin {name}]: path '{path_str}' must not be empty or just './'"))
        if '..' in path_str:
            violations.append(Violation(path, 1, f"[plugin {name}]: path '{path_str}' must not contain '..'"))

        resolved = (repo_root / normalized).resolve()
        if not resolved.is_dir():
            violations.append(Violation(path, 1, f"[plugin {name}]: path '{path_str}' does not resolve to a directory under the repo root ({resolved})"))
        else:
            plugin_manifest = resolved / ".codex-plugin" / "plugin.json"
            if not plugin_manifest.is_file():
                violations.append(Violation(path, 1, f"[plugin {name}]: path '{path_str}' is missing .codex-plugin/plugin.json"))

    return violations


def validate_codex_plugin_manifest(path: Path) -> list[Violation]:
    violations: list[Violation] = []
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        return [Violation(path, 1, f"Invalid JSON: {e}")]

    for key in data.get('userConfig', {}).keys():
        if not re.match(r'^[a-z][a-zA-Z0-9]*$', key):
            violations.append(Violation(path, 1, f"[userConfig]: key '{key}' must be camelCase (no hyphens or underscores)"))
    return violations


def validate_codex_package_layout(repo_root: Path) -> list[Violation]:
    package = repo_root / PACKAGE_ROOT
    violations: list[Violation] = []

    if not package.exists():
        return [Violation(package, None, "package directory is missing — run 'make sync-codex-package'")]

    if package.is_symlink():
        return [Violation(package, None, "expected a real directory, got symlink")]

    expected_names = set(PACKAGE_DIRS)
    actual_names = {p.name for p in package.iterdir()}

    for name in expected_names:
        violations.extend(_check_real_directory(package / name, repo_root))

    for symlink in sorted(p.relative_to(repo_root) for p in package.rglob("*") if p.is_symlink()):
        violations.append(Violation(repo_root / symlink, None, "package payload must contain real files, got symlink"))

    for stray in sorted(actual_names - expected_names):
        violations.append(Violation(package / stray, None, f"unexpected file/directory in package: {stray}"))

    return violations


def _check_real_directory(path: Path, repo_root: Path) -> list[Violation]:
    rel_path = path.relative_to(repo_root)
    if path.is_symlink():
        return [Violation(path, None, f"expected a real directory, got symlink: {rel_path}")]
    if not path.exists():
        return [Violation(path, None, f"missing directory: {rel_path}")]
    if not path.is_dir():
        return [Violation(path, None, f"expected directory, got file: {rel_path}")]
    return []


def validate_codex_hook_commands(repo_root: Path) -> list[Violation]:
    violations: list[Violation] = []
    codex_hooks = (
        Path(".codex/hooks.json"),
        Path("hooks/hooks-codex.json"),
        Path("plugins/flow/.codex/hooks.json"),
        Path("plugins/flow/hooks/hooks.json"),
    )
    
    for rel in codex_hooks:
        path = repo_root / rel
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            violations.append(Violation(path, 1, f"invalid JSON: {e}"))
            continue
            
        hooks = data.get("hooks", {})
        session_start = hooks.get("SessionStart", [])
        if not isinstance(session_start, list):
            continue
            
        for item in session_start:
            if not isinstance(item, dict):
                continue
            nested = item.get("hooks")
            commands = []
            if isinstance(nested, list):
                # Nested structure
                for h in nested:
                    if isinstance(h, dict):
                        commands.append(h.get("command", ""))
            else:
                # Flat structure
                commands.append(item.get("command", ""))
                
            for command in commands:
                for token in ("${extensionPath}", "${/}"):
                    if token in command:
                        violations.append(Violation(path, 1, f"unsupported template token '{token}' in Codex hook command"))
                if not any(token in command for token in ("PLUGIN_ROOT", "CLAUDE_PLUGIN_ROOT")):
                    violations.append(Violation(path, 1, f"Codex hook command must anchor to $PLUGIN_ROOT or $CLAUDE_PLUGIN_ROOT: {command!r}"))
    return violations


def _contained_path(repo_root: Path, base: Path, raw: object, field: str) -> Path:
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError(f"{field} must be a non-empty relative path")
    relative = Path(raw)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"{field} escapes repository root: {raw!r}")
    current = base
    for part in relative.parts:
        current /= part
        if current.is_symlink():
            raise ValueError(f"{field} traverses a symlink component: {raw!r}")
    resolved = (base / relative).resolve()
    try:
        resolved.relative_to(repo_root.resolve())
    except ValueError as exc:
        raise ValueError(f"{field} escapes repository root: {raw!r}") from exc
    return resolved


def resolve_okf_layout(repo_root: Path = REPO_ROOT) -> OKFLayout:
    """Resolve configured and bundle roots without mutating the repository."""
    setup_path = repo_root / ".agents" / "setup-state.json"
    configured_raw: object = ".agents"
    if setup_path.is_file():
        try:
            setup = json.loads(setup_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            raise ValueError(f"invalid setup-state.json: {exc}") from exc
        if not isinstance(setup, dict):
            raise ValueError("setup-state.json must contain an object")
        configured_raw = setup.get("root_directory", ".agents")
    configured_root = _contained_path(
        repo_root, repo_root, configured_raw, "root_directory"
    )

    config_path = configured_root / "config.json"
    bundles_raw: object = "bundles"
    if config_path.is_file():
        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            raise ValueError(f"invalid config.json: {exc}") from exc
        if not isinstance(config, dict):
            raise ValueError("config.json must contain an object")
        bundles_raw = config.get("bundles_dir", "bundles")
    bundle_root = _contained_path(
        repo_root, configured_root, bundles_raw, "bundles_dir"
    )
    return OKFLayout(configured_root, bundle_root)


def iter_okf_bundles(repo_root: Path = REPO_ROOT) -> Iterator[Path]:
    try:
        layout = resolve_okf_layout(repo_root)
    except ValueError:
        return
    specs_dir = layout.bundle_root / "specs"
    if not specs_dir.is_dir():
        return
    for path in specs_dir.iterdir():
        if path.is_dir() and (path / "spec.md").is_file():
            yield path


def validate_okf_bundle_root(repo_root: Path = REPO_ROOT) -> list[Violation]:
    """Check the bundle root index declares its OKF version."""
    try:
        bundles_dir = resolve_okf_layout(repo_root).bundle_root
    except ValueError as exc:
        return [Violation(repo_root / ".agents" / "setup-state.json", 1, str(exc))]
    if not bundles_dir.is_dir():
        return []
    index_path = bundles_dir / "index.md"
    if not index_path.is_file():
        return [
            Violation(
                index_path,
                None,
                "bundle root is missing index.md (should carry okf_version)",
            )
        ]
    content = index_path.read_text(encoding="utf-8")
    if (
        not content.startswith("---\n")
        or "okf_version" not in content.split("---\n", 2)[1]
    ):
        return [
            Violation(
                index_path,
                1,
                "bundle root index.md must declare okf_version in frontmatter",
            )
        ]
    return []


def _validate_iso_timestamp(timestamp: Any) -> bool:
    # PyYAML parses unquoted ISO-8601 stamps into datetime/date objects
    if isinstance(timestamp, datetime.datetime):
        return timestamp.tzinfo is not None and timestamp.utcoffset() == datetime.timedelta(0)
    if isinstance(timestamp, datetime.date):
        return False
    pattern = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$")
    return bool(pattern.match(str(timestamp)))


def _parse_yaml_frontmatter(
    path: Path,
) -> tuple[dict[str, Any] | None, list[Violation]]:
    if not path.is_file():
        return None, [Violation(path, None, f"File does not exist: {path}")]
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as e:
        return None, [Violation(path, None, f"Failed to read file: {e}")]

    lines = content.splitlines(keepends=True)
    if not lines or lines[0].rstrip("\r\n") != "---":
        return None, [Violation(path, 1, "Missing opening frontmatter delimiter '---'")]
    closing = next(
        (index for index, line in enumerate(lines[1:], start=1) if line.rstrip("\r\n") == "---"),
        None,
    )
    if closing is None:
        return None, [Violation(path, 1, "Missing closing frontmatter delimiter '---'")]
    yaml_block = "".join(lines[1:closing])
    try:
        data = yaml.safe_load(yaml_block)
    except yaml.YAMLError as e:
        return None, [Violation(path, 2, f"Failed to parse YAML frontmatter: {e}")]
    if not isinstance(data, dict):
        return None, [
            Violation(path, 2, "YAML frontmatter must be an object/dictionary")
        ]
    return data, []


def _validate_markdown_links(
    path: Path, repo_root: Path, *, strict: bool = True
) -> list[Violation]:
    violations: list[Violation] = []
    if not path.is_file():
        return []
    content = path.read_text(encoding="utf-8")
    for line_num, line in enumerate(content.splitlines(), start=1):
        for label, url in LINK_PATTERN.findall(line):
            if url.startswith(("http://", "https://", "mailto:", "ftp:", "#")):
                continue
            url_path_only = url.split("#")[0]
            if not url_path_only:
                continue

            if url_path_only.startswith("file://"):
                clean_url = url_path_only.removeprefix("file://")
                resolved = Path(clean_url).resolve()
            else:
                resolved = (path.parent / url_path_only).resolve()

            try:
                resolved.relative_to(repo_root.resolve())
            except ValueError:
                violations.append(
                    Violation(
                        path, line_num, f"relative link '{url}' escapes repository root"
                    )
                )
                continue
            if strict and not resolved.exists():
                violations.append(
                    Violation(
                        path, line_num, f"relative link target does not exist: '{url}'"
                    )
                )
    return violations


_WORKSHEET_HEADINGS = (
    "Objective",
    "Context",
    "Steps",
    "Verification",
    "Acceptance Criteria",
)
_VAGUE_FIELD_PATTERN = re.compile(
    r"(?:\bTODO\b|\bTBD\b|works correctly|do the thing)",
    re.IGNORECASE,
)
_PLACEHOLDER_ONLY_PATTERN = re.compile(
    r"^(?:\d+[.)]|[-*])?\s*(?:"
    r"(?:improve|implement|update|fix|handle|test|verify|ensure|complete|do|make)\s+"
    r"(?:(?:the|this|that|a)\s+)?(?:code|thing|things|it|this|that|change|task|feature|work)"
    r"(?:\s+as needed)?|"
    r"(?:the\s+)?(?:change|task|work|feature)\s+is\s+(?:done|complete)|"
    r"run\s+`?[\w.-]+`?\s+and\s+(?:verify|test)\s+(?:it|this)"
    r")[.!]?$",
    re.IGNORECASE,
)


_TASK_PRIORITIES = {"P0", "P1", "P2", "P3", "P4"}
_VERIFICATION_STRATEGIES = {
    "behavior_tdd",
    "regression_tdd",
    "characterization",
    "static_validation",
    "documentation_validation",
    "integration_acceptance",
}
_SPEC_ONLY_OPERATIONS = {"activate", "reconcile", "complete", "archive"}


def _markdown_body(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].rstrip("\r\n") != "---":
        return text
    closing = next(
        (index for index, line in enumerate(lines[1:], start=1) if line.rstrip("\r\n") == "---"),
        None,
    )
    return "".join(lines[closing + 1 :]) if closing is not None else text


def _parse_h2_sections(body: str) -> dict[str, str]:
    matches = list(re.finditer(r"^##\s+(.+?)\s*$", body, re.MULTILINE))
    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        sections[match.group(1).strip()] = body[match.end() : end].strip()
    return sections


def _validate_worksheet(path: Path, body: str) -> list[Violation]:
    violations: list[Violation] = []
    sections = _parse_h2_sections(body)
    for heading in _WORKSHEET_HEADINGS:
        content = sections.get(heading)
        if not content:
            violations.append(
                Violation(path, None, f"missing or empty worksheet section '{heading}'")
            )
            continue
        if _VAGUE_FIELD_PATTERN.search(content):
            violations.append(
                Violation(
                    path,
                    None,
                    f"worksheet section '{heading}' is not executable: replace vague placeholder language",
                )
            )
        meaningful_lines = [
            line.strip() for line in content.splitlines() if line.strip()
        ]
        if meaningful_lines and all(
            _PLACEHOLDER_ONLY_PATTERN.fullmatch(line) for line in meaningful_lines
        ):
            violations.append(
                Violation(
                    path,
                    None,
                    f"worksheet section '{heading}' is not executable: placeholder-only content",
                )
            )
        words = re.findall(r"[A-Za-z0-9_./:-]+", re.sub(r"[`#*\[\]()]", " ", content))
        if len(words) < 3:
            violations.append(
                Violation(
                    path,
                    None,
                    f"worksheet section '{heading}' is not executable: provide concrete action and evidence",
                )
            )
    steps = sections.get("Steps", "")
    if steps and not re.search(r"^\s*1[.)]\s+\S", steps, re.MULTILINE):
        violations.append(
            Violation(path, None, "worksheet section 'Steps' needs numbered actions")
        )
    verification = sections.get("Verification", "")
    commands = re.findall(r"`([^`]+)`", verification)
    if verification and (
        not commands or all(len(command.split()) < 2 for command in commands)
    ):
        violations.append(
            Violation(
                path,
                None,
                "worksheet section 'Verification' needs an exact command and expected result",
            )
        )
    criteria = sections.get("Acceptance Criteria", "")
    if criteria and not re.search(r"^\s*[-*]\s+\S", criteria, re.MULTILINE):
        violations.append(
            Violation(
                path,
                None,
                "worksheet section 'Acceptance Criteria' needs checkable list items",
            )
        )
    return violations


def _validate_task_graph(
    task_records: dict[str, tuple[Path, dict[str, Any]]],
) -> list[Violation]:
    violations: list[Violation] = []
    dependencies: dict[str, list[str]] = {}
    for short_id, (path, data) in task_records.items():
        raw = data.get("depends_on", [])
        if not isinstance(raw, list):
            continue
        dependencies[short_id] = [str(item) for item in raw]
        for dependency in dependencies[short_id]:
            if dependency not in task_records:
                violations.append(
                    Violation(
                        path,
                        1,
                        f"task '{short_id}' has missing dependency '{dependency}'",
                    )
                )

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(short_id: str, trail: list[str]) -> None:
        if short_id in visiting:
            cycle = trail[trail.index(short_id) :] + [short_id]
            path = task_records[short_id][0]
            violations.append(
                Violation(path, 1, f"dependency cycle: {' -> '.join(cycle)}")
            )
            return
        if short_id in visited:
            return
        visiting.add(short_id)
        for dependency in dependencies.get(short_id, []):
            if dependency in task_records:
                visit(dependency, [*trail, dependency])
        visiting.remove(short_id)
        visited.add(short_id)

    for short_id in task_records:
        visit(short_id, [short_id])
    return violations


def _recorded_operation_request(
    repo_root: Path, operation_id: object
) -> dict[str, Any] | None:
    if not isinstance(operation_id, str) or not operation_id:
        return None
    try:
        layout = resolve_okf_layout(repo_root)
    except ValueError:
        return None
    journal = (
        layout.configured_root / "tasks" / "transactions" / operation_id / "journal.md"
    )
    data, errors = _parse_yaml_frontmatter(journal)
    request = data.get("request") if data is not None and not errors else None
    return request if isinstance(request, dict) else None


def _snapshot_value(sections: dict[str, str], label: str) -> str | None:
    snapshot = sections.get("Continuity Snapshot", "")
    match = re.search(
        rf"^\s*-\s+\*\*{re.escape(label)}:\*\*\s*(.+)$",
        snapshot,
        re.MULTILINE,
    )
    return match.group(1).strip() if match else None


def _validate_continuity_snapshot(
    spec_path: Path,
    spec_data: dict[str, Any],
    body: str,
    task_records: dict[str, tuple[Path, dict[str, Any]]],
) -> list[Violation]:
    violations: list[Violation] = []
    sections = _parse_h2_sections(body)
    required = (
        "Active flow",
        "Current task/claim",
        "Last verified checkpoint",
        "Decisions",
        "Recent discoveries",
        "Blockers/unblock conditions",
        "Next exact step",
        "Plan identity",
        "State identity",
        "Relevant rules/knowledge",
    )
    values = {label: _snapshot_value(sections, label) for label in required}
    for label, value in values.items():
        if value is None:
            violations.append(
                Violation(
                    spec_path,
                    None,
                    f"Continuity Snapshot missing field '{label}'",
                )
            )
    active = values["Active flow"] or ""
    if (
        str(spec_data.get("flow_id")) not in active
        or f"`{spec_data.get('state')}`" not in active
    ):
        violations.append(
            Violation(
                spec_path,
                None,
                "Continuity Snapshot flow/lifecycle disagrees with frontmatter",
            )
        )
    plan = values["Plan identity"] or ""
    if f"revision `{spec_data.get('plan_revision')}`" not in plan:
        violations.append(
            Violation(
                spec_path,
                None,
                "Continuity Snapshot plan_revision disagrees with frontmatter",
            )
        )
    commit = spec_data.get("plan_commit")
    rendered_commit = "null" if commit is None else str(commit)
    if f"plan_commit: {rendered_commit}" not in plan:
        violations.append(
            Violation(
                spec_path,
                None,
                "Continuity Snapshot plan_commit disagrees with frontmatter",
            )
        )
    state = values["State identity"] or ""
    if f"revision `{spec_data.get('state_revision')}`" not in state:
        violations.append(
            Violation(
                spec_path,
                None,
                "Continuity Snapshot state_revision disagrees with frontmatter",
            )
        )
    if str(spec_data.get("last_operation")) not in state:
        violations.append(
            Violation(
                spec_path,
                None,
                "Continuity Snapshot last_operation disagrees with frontmatter",
            )
        )
    rendered_targets = json.dumps(spec_data.get("operation_targets", []))
    if f"operation_targets: {rendered_targets}" not in state:
        violations.append(
            Violation(
                spec_path,
                None,
                "Continuity Snapshot operation_targets disagrees with frontmatter",
            )
        )
    current = spec_data.get("current_task")
    claim = values["Current task/claim"] or ""
    if current is not None:
        task = task_records.get(str(current))
        claimant = task[1].get("claimed_by") if task else None
        if f"`{current}`" not in claim or str(claimant) not in claim:
            violations.append(
                Violation(
                    spec_path,
                    None,
                    "Continuity Snapshot current claim disagrees with task/frontmatter",
                )
            )
    elif claim.strip("` ").lower() not in {"none", "null"}:
        violations.append(
            Violation(
                spec_path,
                None,
                "Continuity Snapshot snapshot current task/claim must be none when current_task is null",
            )
        )
    checkpoint = spec_data.get("last_verified_checkpoint")
    rendered_checkpoint = values["Last verified checkpoint"] or ""
    if checkpoint is None:
        if rendered_checkpoint.strip("`").lower() not in {"none", "null"}:
            violations.append(
                Violation(
                    spec_path,
                    None,
                    "Continuity Snapshot Last verified checkpoint disagrees with frontmatter",
                )
            )
    elif f"`{checkpoint}`" not in rendered_checkpoint:
        violations.append(
            Violation(
                spec_path,
                None,
                "Continuity Snapshot Last verified checkpoint disagrees with frontmatter",
            )
        )
    if isinstance(checkpoint, str):
        match = re.fullmatch(r"task:([^@]+)@([0-9a-f]{7,40})", checkpoint)
        if match:
            record = task_records.get(match.group(1))
            if record is None or record[1].get("commit") != match.group(2):
                violations.append(
                    Violation(
                        spec_path,
                        None,
                        "Continuity Snapshot Last verified checkpoint lacks matching task evidence",
                    )
                )
    return violations


def validate_okf_bundle(
    bundle_path: Path, repo_root: Path = REPO_ROOT
) -> list[Violation]:
    violations: list[Violation] = []
    spec_path = bundle_path / "spec.md"
    if not spec_path.is_file():
        return [
            Violation(
                bundle_path,
                None,
                f"Spec file spec.md is missing in bundle: {_rel(bundle_path)}",
            )
        ]

    spec_data, spec_errs = _parse_yaml_frontmatter(spec_path)
    violations.extend(spec_errs)

    spec_parsed_ok = False
    spec_task_short_ids = set()
    if spec_path.is_file():
        try:
            content = spec_path.read_text(encoding="utf-8")
            parts = content.split("---\n", 2)
            body = parts[2] if len(parts) >= 3 else content
            pattern = re.compile(
                r"^\s*-\s*\[([ ~x!-])\]\s*Task\s+([a-zA-Z0-9._-]+)\s*:", re.MULTILINE
            )
            spec_task_short_ids = {m.group(2) for m in pattern.finditer(body)}
            spec_parsed_ok = True
        except OSError:
            pass

    spec_state = (
        (spec_data.get("state") or spec_data.get("status") or "planned")
        if spec_data
        else "planned"
    )
    is_spec_closed = spec_state in ("completed", "archived")
    violations.extend(
        _validate_markdown_links(spec_path, repo_root, strict=is_spec_closed)
    )

    if spec_data is not None:
        required_fields = {
            "type",
            "flow_id",
            "title",
            "state",
            "created_at",
            "updated_at",
        }
        for f in required_fields:
            if f not in spec_data or spec_data[f] is None or spec_data[f] == "":
                violations.append(
                    Violation(spec_path, 1, f"spec.md missing required field: '{f}'")
                )
            elif f in ("created_at", "updated_at"):
                val = spec_data[f]
                if not _validate_iso_timestamp(val):
                    violations.append(
                        Violation(
                            spec_path,
                            1,
                            f"spec.md field '{f}' must be a valid ISO-8601 timestamp (got '{val}')",
                        )
                    )

        # OKF: unknown `type` values are tolerated; only emptiness is an error (handled above).
        if "state" in spec_data and spec_data["state"] not in (
            "planned",
            "active",
            "completed",
            None,
        ):
            violations.append(
                Violation(
                    spec_path,
                    1,
                    f"spec.md field 'state' has invalid value: '{spec_data['state']}'",
                )
            )
        if spec_data.get("status") is not None and spec_data["status"] not in (
            "draft",
            "stable",
            "deprecated",
        ):
            violations.append(
                Violation(
                    spec_path,
                    1,
                    f"spec.md field 'status' is the OKF lifecycle (draft|stable|deprecated); workflow state belongs in 'state' (got '{spec_data['status']}')",
                )
            )
        if "flow_id" in spec_data and spec_data["flow_id"] != bundle_path.name:
            violations.append(
                Violation(
                    spec_path,
                    1,
                    f"spec.md flow_id '{spec_data['flow_id']}' does not match directory name '{bundle_path.name}'",
                )
            )

    tasks_dir = bundle_path / "tasks"
    task_records: dict[str, tuple[Path, dict[str, Any]]] = {}
    if tasks_dir.is_dir():
        for task_file in sorted(tasks_dir.glob("*.md")):
            task_data, task_errs = _parse_yaml_frontmatter(task_file)
            violations.extend(task_errs)

            # Check for orphaned task file
            short_id = task_file.stem
            if spec_parsed_ok and short_id not in spec_task_short_ids:
                violations.append(
                    Violation(
                        task_file,
                        None,
                        f"orphaned task file: no corresponding 'Task {short_id}' found in spec.md implementation plan",
                    )
                )

            task_state = (
                (task_data.get("state") or task_data.get("status") or "open")
                if task_data
                else "open"
            )
            violations.extend(
                _validate_markdown_links(
                    task_file, repo_root, strict=(task_state == "closed")
                )
            )

            if task_data is not None:
                task_records[short_id] = (task_file, task_data)
                required_task_fields = {
                    "type",
                    "id",
                    "state",
                    "depends_on",
                    "files",
                    "tests",
                    "created_at",
                    "updated_at",
                }
                for f in required_task_fields:
                    if f not in task_data or task_data[f] is None:
                        violations.append(
                            Violation(
                                task_file, 1, f"task missing required field: '{f}'"
                            )
                        )
                    elif f in ("created_at", "updated_at"):
                        val = task_data[f]
                        if not _validate_iso_timestamp(val):
                            violations.append(
                                Violation(
                                    task_file,
                                    1,
                                    f"task field '{f}' must be a valid ISO-8601 timestamp (got '{val}')",
                                )
                            )

                if task_data.get("type") == "":
                    violations.append(
                        Violation(task_file, 1, "task field 'type' must be non-empty")
                    )
                priority = task_data.get("priority", "P2")
                if priority not in _TASK_PRIORITIES:
                    violations.append(
                        Violation(
                            task_file,
                            1,
                            "task priority must be P0|P1|P2|P3|P4 (default P2)",
                        )
                    )
                strategy = task_data.get("verification_strategy")
                if strategy not in _VERIFICATION_STRATEGIES:
                    violations.append(
                        Violation(
                            task_file,
                            1,
                            "task verification_strategy must use the closed contract enum",
                        )
                    )
                if "state" in task_data and task_data["state"] not in (
                    "open",
                    "in_progress",
                    "closed",
                    "blocked",
                    "skipped",
                    None,
                ):
                    violations.append(
                        Violation(
                            task_file,
                            1,
                            f"task field 'state' has invalid value: '{task_data['state']}'",
                        )
                    )
                if task_data.get("status") is not None and task_data["status"] not in (
                    "draft",
                    "stable",
                    "deprecated",
                ):
                    violations.append(
                        Violation(
                            task_file,
                            1,
                            f"task field 'status' is the OKF lifecycle (draft|stable|deprecated); workflow state belongs in 'state' (got '{task_data['status']}')",
                        )
                    )

                if "depends_on" in task_data and not isinstance(
                    task_data["depends_on"], list
                ):
                    violations.append(
                        Violation(
                            task_file, 1, "task field 'depends_on' must be a list"
                        )
                    )

                if spec_data and "flow_id" in spec_data:
                    flow_id = spec_data["flow_id"]
                    task_id = str(task_data.get("id", ""))
                    if not task_id.startswith(f"{flow_id}:"):
                        violations.append(
                            Violation(
                                task_file,
                                1,
                                f"task ID prefix '{task_id.split(':')[0] if ':' in task_id else task_id}' must match flow_id '{flow_id}'",
                            )
                        )

                for list_field in ("files", "tests"):
                    if list_field in task_data:
                        items = task_data[list_field]
                        if not isinstance(items, list):
                            violations.append(
                                Violation(
                                    task_file,
                                    1,
                                    f"task field '{list_field}' must be a list",
                                )
                            )
                        else:
                            for item in items:
                                if not isinstance(item, str):
                                    violations.append(
                                        Violation(
                                            task_file,
                                            1,
                                            f"task field '{list_field}' item must be a string path",
                                        )
                                    )
                                    continue
                                resolved = (repo_root / item).resolve()
                                try:
                                    resolved.relative_to(repo_root.resolve())
                                except ValueError:
                                    violations.append(
                                        Violation(
                                            task_file,
                                            1,
                                            f"referenced file '{item}' escapes repository root",
                                        )
                                    )
                                    continue
                                if not resolved.exists() and task_state == "closed":
                                    violations.append(
                                        Violation(
                                            task_file,
                                            1,
                                            f"referenced file does not exist: '{item}'",
                                        )
                                    )
                violations.extend(
                    _validate_worksheet(task_file, _markdown_body(task_file))
                )

    if spec_data is not None:
        for field in (
            "plan_revision",
            "plan_commit",
            "state_revision",
            "current_task",
            "last_operation",
            "operation_targets",
            "last_verified_checkpoint",
        ):
            if field not in spec_data:
                violations.append(
                    Violation(
                        spec_path, 1, f"spec.md missing continuity field: '{field}'"
                    )
                )
        plan_revision = spec_data.get("plan_revision")
        plan_commit = spec_data.get("plan_commit")
        state_revision = spec_data.get("state_revision")
        targets = spec_data.get("operation_targets")
        if not isinstance(plan_revision, int) or plan_revision < 1:
            violations.append(
                Violation(spec_path, 1, "spec.md plan_revision must be an integer >= 1")
            )
        if plan_commit is not None and not re.fullmatch(
            r"[0-9a-f]{7,40}", str(plan_commit)
        ):
            violations.append(
                Violation(
                    spec_path,
                    1,
                    "spec.md plan_commit must be null or 7-40 lowercase hex",
                )
            )
        if not isinstance(state_revision, int) or state_revision < 0:
            violations.append(
                Violation(
                    spec_path, 1, "spec.md state_revision must be a nonnegative integer"
                )
            )
        if not isinstance(targets, list) or len(targets) != len(
            set(map(str, targets or []))
        ):
            violations.append(
                Violation(
                    spec_path, 1, "spec.md operation_targets must be a unique list"
                )
            )
            targets = []

        for short_id, (task_path, task_data) in task_records.items():
            for field in (
                "plan_revision",
                "plan_commit",
                "state_revision",
                "claimed_by",
                "claimed_at",
                "last_operation",
                "operation_targets",
                "verification_strategy",
            ):
                if field not in task_data:
                    violations.append(
                        Violation(
                            task_path, 1, f"task missing continuity field: '{field}'"
                        )
                    )
            if task_data.get("plan_revision") != plan_revision:
                violations.append(
                    Violation(
                        task_path,
                        1,
                        "task plan_revision must equal spec.md plan_revision",
                    )
                )
            if task_data.get("plan_commit") != plan_commit:
                violations.append(
                    Violation(
                        task_path, 1, "task plan_commit must equal spec.md plan_commit"
                    )
                )
            task_revision = task_data.get("state_revision")
            if (
                not isinstance(task_revision, int)
                or not isinstance(state_revision, int)
                or not 0 <= task_revision <= state_revision
            ):
                violations.append(
                    Violation(
                        task_path,
                        1,
                        "task state_revision must be between zero and spec.md state_revision",
                    )
                )
            if short_id in set(map(str, targets or [])):
                for field in ("state_revision", "last_operation", "operation_targets"):
                    if task_data.get(field) != spec_data.get(field):
                        violations.append(
                            Violation(
                                task_path,
                                1,
                                f"target task {field} must equal latest spec operation identity",
                            )
                        )
            task_targets = task_data.get("operation_targets")
            if not isinstance(task_targets, list) or (
                task_targets and short_id not in set(map(str, task_targets))
            ):
                violations.append(
                    Violation(
                        task_path,
                        1,
                        "task operation_targets must be empty or include its own short id",
                    )
                )
            if task_data.get("state") == "in_progress":
                if not task_data.get("claimed_by"):
                    violations.append(
                        Violation(task_path, 1, "in_progress task needs claimed_by")
                    )
                if not _validate_iso_timestamp(task_data.get("claimed_at")):
                    violations.append(
                        Violation(
                            task_path,
                            1,
                            "task claimed_at must be a canonical UTC ISO timestamp",
                        )
                    )
                for dependency in task_data.get("depends_on", []):
                    record = task_records.get(str(dependency))
                    if record is not None and record[1].get("state") != "closed":
                        violations.append(
                            Violation(
                                task_path, 1, f"dependency '{dependency}' is not closed"
                            )
                        )
            if task_data.get("state") == "closed" and not (
                task_data.get("commit")
                and task_data.get("last_verified_at")
                and task_data.get("last_verified_commit")
                and task_data.get("verification_evidence")
            ):
                violations.append(
                    Violation(
                        task_path,
                        1,
                        "closed task requires commit and verification evidence",
                    )
                )

        target_ids = set(map(str, targets or []))
        last_operation = str(spec_data.get("last_operation") or "")
        operation_match = re.search(
            r"-(create|activate|claim|release|note|discover|block|unblock|checkpoint|close|skip|reopen|revise|reconcile|complete|archive|recover)-",
            last_operation,
        )
        if (
            operation_match
            and operation_match.group(1) in _SPEC_ONLY_OPERATIONS
            and target_ids
        ):
            violations.append(
                Violation(
                    spec_path,
                    1,
                    f"{operation_match.group(1)} is spec-only and requires empty operation_targets",
                )
            )
        if operation_match and operation_match.group(1) == "checkpoint":
            checkpoint_request = _recorded_operation_request(
                repo_root, spec_data.get("last_operation")
            )
            payload = (
                checkpoint_request.get("payload")
                if isinstance(checkpoint_request, dict)
                and isinstance(checkpoint_request.get("payload"), dict)
                else {}
            )
            scope = payload.get("scope")
            request_targets = (
                checkpoint_request.get("targets")
                if isinstance(checkpoint_request, dict)
                else None
            )
            if scope == "phase" and target_ids:
                violations.append(
                    Violation(
                        spec_path,
                        1,
                        "phase checkpoint is spec-only and requires empty operation_targets",
                    )
                )
            elif scope == "task" and target_ids != set(map(str, request_targets or [])):
                violations.append(
                    Violation(
                        spec_path,
                        1,
                        "task checkpoint targets disagree with request payload",
                    )
                )
            elif scope == "plan" and (
                target_ids != set(task_records)
                or target_ids != set(map(str, request_targets or []))
            ):
                violations.append(
                    Violation(
                        spec_path,
                        1,
                        "plan checkpoint targets disagree with complete task/request set",
                    )
                )
        missing_targets = target_ids - set(task_records)
        for short_id in sorted(missing_targets):
            violations.append(
                Violation(
                    spec_path,
                    1,
                    f"operation_targets references missing task '{short_id}'",
                )
            )
        claims = [
            short_id
            for short_id, (_, data) in task_records.items()
            if data.get("state") == "in_progress"
        ]
        if len(claims) > 1:
            violations.append(
                Violation(
                    spec_path, 1, f"competing in_progress claim: {', '.join(claims)}"
                )
            )
        current_task = spec_data.get("current_task")
        if claims and current_task != claims[0]:
            violations.append(
                Violation(
                    spec_path,
                    1,
                    "spec.md current_task must equal the sole in_progress claim",
                )
            )
        if not claims and current_task is not None:
            violations.append(
                Violation(
                    spec_path, 1, "spec.md current_task references no in_progress task"
                )
            )
        violations.extend(_validate_task_graph(task_records))
        violations.extend(
            _validate_continuity_snapshot(
                spec_path, spec_data, _markdown_body(spec_path), task_records
            )
        )
    return violations


_INSTALLED_OPERATIONAL_ROOTS = (
    "skills",
    "commands",
    "agents",
    "hooks",
    "plugins",
    ".claude-plugin",
    ".codex",
    ".opencode",
    ".github/agents",
    ".cursor/rules",
)
_RUNTIME_COMMAND = re.compile(
    r"^(?:\$\s*)?(?:python3?|uv(?:\s+run)?|bash|sh|pwsh|powershell(?:\.exe)?|flow(?:\s+|-)(?:sync|status|prd|plan|implement|archive|recover|validate|revise|task))\b",
    re.IGNORECASE,
)
_RUNTIME_PROSE_COMMAND = re.compile(
    r"\b(?:run|execute|invoke|call|spawn|launch)\s+(?:`)?(?:python3?|uv\s+run|bash|sh|pwsh|powershell(?:\.exe)?|flow\s+(?:sync|status|prd|plan|implement|archive|recover))\b",
    re.IGNORECASE,
)
_RUNTIME_CODE = re.compile(
    r"(?:node:)?child_process|\b(?:spawn|spawnSync|exec|execFile|execFileSync)\s*\(|\bsubprocess\.(?:run|Popen|call|check_call|check_output)\s*\(",
    re.IGNORECASE,
)
_HOOK_SCRIPT_SUFFIXES = {".sh", ".ps1", ".cmd", ".bat"}

def _runtime_fingerprint(
    relative: str, category: str, evidence: str, occurrence: int
) -> str:
    identity = f"{category}\0{evidence}\0{occurrence}".encode()
    digest = hashlib.sha256(identity).hexdigest()[:16]
    return f"{relative}:{category}:{digest}"


# Task 2.4 removes these exact installed runtime invocations. Fingerprints bind
# each allowance to one stable invocation and deliberately become stale when
# that invocation changes or disappears.
_RUNTIME_TRANSITION_ALLOWLIST = {
    ".opencode/plugins/flow.js:runtime_code:ddc5846ffa466e97",
    ".opencode/plugins/flow.js:runtime_code:6b35da74d620c100",
    "hooks/agy-pre-invocation.ps1:hook_script:f3cd328ea2743137",
    "hooks/agy-pre-invocation.sh:hook_script:86e155ef1940acda",
    "hooks/detect-env.ps1:hook_script:7f44ad6f7614e393",
    "hooks/detect-env.sh:hook_script:02b616946f3afc1f",
    "hooks/hooks-agy.json:hook_target:6372b9e41dd8e712",
    "hooks/hooks-claude.json:hook_target:f1f73f106d37591c",
    "hooks/hooks-codex.json:hook_target:b5bbee601285f75e",
    "hooks/hooks-cursor.json:hook_target:c8fd69038ec5f262",
    "hooks/session-start.cmd:hook_script:6ff2a1fd14e0d3ef",
    "hooks/session-start.js:runtime_code:dd0d694e3b0460b4",
    "hooks/session-start.js:runtime_code:e0291a0a474dbb68",
    "hooks/session-start.ps1:hook_script:a088526198f47ec3",
    "hooks/session-start.sh:hook_script:3409c97e20c172d7",
    "skills/flow/references/revert.md:runtime_command:b06ba3730e38798d",
    "skills/flow/references/task.md:runtime_command:7ff76bdaf45c86e9",
}


def validate_installed_runtime_dependencies(
    repo_root: Path = REPO_ROOT,
    *,
    transition_allowlist: set[str] | None = None,
) -> list[Violation]:
    """Reject executable consumer sidecars on installed operational surfaces."""
    raw_findings: list[tuple[str, str, str, Violation]] = []
    paths: set[Path] = set()
    for relative in _INSTALLED_OPERATIONAL_ROOTS:
        root = repo_root / relative
        if root.is_file():
            paths.add(root)
        elif root.is_dir():
            paths.update(
                path
                for path in root.rglob("*")
                if path.is_file()
                and "node_modules" not in path.parts
                and not (
                    relative == "plugins"
                    and len(path.relative_to(root).parts) > 1
                    and (root / path.relative_to(root).parts[0] / ".codex-plugin").is_dir()
                )
            )
    for path in sorted(paths):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        relative = path.relative_to(repo_root).as_posix()
        opaque_runtime_surface = False
        if relative.startswith("hooks/") and (
            path.suffix.lower() in _HOOK_SCRIPT_SUFFIXES
            or text.startswith(("#!/bin/sh", "#!/usr/bin/env bash", "#!/bin/bash"))
        ):
            raw_findings.append(
                (
                    relative,
                    "hook_script",
                    text.replace("\r\n", "\n"),
                    Violation(path, 1, "installed SessionStart hook requires a runtime script"),
                )
            )
            opaque_runtime_surface = True
        if path.suffix.lower() == ".json" and relative.startswith("hooks/"):
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError:
                parsed = None
            if parsed is not None and re.search(
                r"(?:\.sh|\.ps1|\.cmd|\.bat|\.js|python3?|pwsh|powershell)",
                json.dumps(parsed),
                re.IGNORECASE,
            ):
                raw_findings.append(
                    (
                        relative,
                        "hook_target",
                        json.dumps(parsed, sort_keys=True, separators=(",", ":")),
                        Violation(path, 1, "installed hook JSON targets a runtime script"),
                    )
                )
                opaque_runtime_surface = True
        if opaque_runtime_surface:
            continue
        in_fence = False
        runtime_fence = False
        for line_number, line in enumerate(text.splitlines(), start=1):
            lowered = line.lower()
            stripped = line.strip()
            if "```" in stripped:
                if in_fence:
                    in_fence = False
                    runtime_fence = False
                else:
                    in_fence = True
                    suffix = stripped.split("```", 1)[1]
                    language_match = re.match(r"([A-Za-z0-9_-]*)", suffix)
                    language = language_match.group(1).lower() if language_match else ""
                    runtime_fence = language in {"", "bash", "sh", "shell", "console", "powershell", "pwsh", "cmd", "bat"}
                continue
            if re.search(
                r"\b(?:never|must not|do not|does not|forbidden|reject)\b", lowered
            ):
                continue
            if _RUNTIME_CODE.search(line):
                raw_findings.append(
                    (
                        relative,
                        "runtime_code",
                        stripped,
                        Violation(path, line_number, "installed code invokes a forbidden runtime process"),
                    )
                )
            if (runtime_fence and _RUNTIME_COMMAND.search(stripped)) or _RUNTIME_PROSE_COMMAND.search(line):
                details = []
                if "tools/priming.py" in line:
                    details.append("tools/priming.py")
                if re.search(r"(?:tasks?|specs?)/[^\s`]*\*", line):
                    details.append("dynamic task/spec scan")
                detail = f" ({'; '.join(details)})" if details else ""
                raw_findings.append(
                    (
                        relative,
                        "runtime_command",
                        stripped,
                        Violation(path, line_number, f"installed workflow requires a forbidden consumer runtime command{detail}"),
                    )
                )
    occurrences: dict[tuple[str, str, str], int] = {}
    findings: list[tuple[str, Violation]] = []
    for relative, category, evidence, violation in raw_findings:
        occurrence_key = (relative, category, evidence)
        occurrence = occurrences.get(occurrence_key, 0)
        occurrences[occurrence_key] = occurrence + 1
        findings.append(
            (
                _runtime_fingerprint(relative, category, evidence, occurrence),
                violation,
            )
        )
    if transition_allowlist is None:
        return [violation for _, violation in findings]
    found_keys = {key for key, _ in findings}
    violations = [
        violation for key, violation in findings if key not in transition_allowlist
    ]
    for stale in sorted(transition_allowlist - found_keys):
        relative = stale.split(":", 1)[0]
        violations.append(
            Violation(
                repo_root / relative,
                1,
                f"stale runtime transition allowlist entry: {stale}",
            )
        )
    return violations


_JOURNAL_NONTERMINAL_STATES = {
    "prepared",
    "task_writes_started",
    "recovery_required",
    "contended",
    "rollback_in_progress",
}
_PATH_BASES = {"flow_root", "bundle_root", "configured_root"}
_JOURNAL_BASE_KEYS = {
    "type",
    "version",
    "operation_id",
    "state",
    "applied_writes",
    "rolled_back_writes",
    "events",
    "flow_id",
    "configured_root",
    "bundle_root",
    "flow_root",
    "request",
    "ordered_writes",
    "read_set",
    "fragments",
}
_REQUEST_KEYS = {
    "flow_id",
    "operation",
    "actor",
    "occurred_at",
    "expected_plan_revision",
    "expected_plan_commit",
    "expected_state_revision",
    "targets",
    "payload",
}
_PAYLOAD_REQUIRED: dict[str, set[str]] = {
    "activate": {"approval_evidence", "next_step"},
    "claim": {"next_step"},
    "discover": {"text", "impact", "next_step"},
    "block": {"blocked_reason", "unblock_condition", "next_step"},
    "unblock": {"resolution_evidence", "next_step"},
    "close": {"commit", "verification_evidence", "acceptance_criteria_checked"},
    "skip": {"reason", "user_approval"},
    "reopen": {"reason", "user_approval", "next_step", "replacement_checkpoint"},
    "revise": {
        "plan_diffs",
        "rationale",
        "reviewer_findings",
        "new_plan_revision",
        "state_adjustments",
    },
    "reconcile": {"mismatches", "affected_task_ids"},
    "complete": {
        "final_functional_commit",
        "verification_evidence",
        "code_review_evidence",
        "quality_review",
        "waivers",
    },
    "archive": {
        "knowledge_destinations",
        "synthesized_edits",
        "log_entry",
        "notes_incorporation",
        "archive_candidate_manifest",
        "quality_report",
        "waivers",
    },
    "recover": {"journal_operation_id", "action"},
}
_OPERATION_PREDICATES: dict[str, set[str]] = {
    "create.flow": {"no_other_unresolved_journal", "flow_absent"},
    "create.task": {
        "no_other_unresolved_journal",
        "spec_identity",
        "all_task_identities",
        "target_absent",
        "dependencies_exist_and_acyclic",
    },
    "activate": {
        "no_other_unresolved_journal",
        "spec_identity",
        "all_task_identities",
        "plan_ready_approved",
        "all_worksheets_complete",
    },
    "claim": {
        "no_other_unresolved_journal",
        "spec_identity",
        "target_identity",
        "all_dependencies_closed",
        "no_other_in_progress_claim",
    },
    "release": {"no_other_unresolved_journal", "spec_identity", "target_identity", "sole_current_claim", "actor_is_claimant_or_authorized"},
    "note.normal": {"no_other_unresolved_journal", "spec_identity", "target_identity"},
    "note.git_note_attachment": {"no_other_unresolved_journal", "spec_identity", "target_identity", "git_note_attempt_idempotent"},
    "discover": {"no_other_unresolved_journal", "spec_identity", "target_identity"},
    "block": {"no_other_unresolved_journal", "spec_identity", "target_identity", "in_progress_target_is_current"},
    "unblock": {"no_other_unresolved_journal", "spec_identity", "target_identity", "unblock_condition_satisfied"},
    "checkpoint.task": {"no_other_unresolved_journal", "spec_identity", "target_identity", "sole_current_claim", "verification_bound_to_commit"},
    "checkpoint.phase": {"no_other_unresolved_journal", "spec_identity", "all_task_identities", "affected_tasks_closed_or_skipped", "no_current_claim", "phase_verification_valid"},
    "checkpoint.plan": {"no_other_unresolved_journal", "spec_identity", "all_task_identities", "plan_bind_evidence_matches_live"},
    "close": {"no_other_unresolved_journal", "spec_identity", "target_identity", "sole_current_claim", "verification_bound_to_commit", "acceptance_criteria_satisfied"},
    "skip": {"no_other_unresolved_journal", "spec_identity", "target_identity", "fresh_user_approval", "skip_dependents_coherent"},
    "reopen": {"no_other_unresolved_journal", "spec_identity", "target_identity", "fresh_user_approval", "replacement_checkpoint_valid", "reopen_plan_dependents_consistent"},
    "revise": {"no_other_unresolved_journal", "spec_identity", "all_task_identities", "revise_diff_and_adjustments_legal"},
    "reconcile": {"no_other_unresolved_journal", "spec_identity", "all_task_identities", "reconcile_mismatches_exact"},
    "complete": {"no_other_unresolved_journal", "spec_identity", "all_task_identities", "no_current_claim", "all_tasks_terminal_no_blockers", "completion_evidence_valid"},
    "archive": {"no_other_unresolved_journal", "spec_identity", "archive_candidate_exact", "archive_evidence_valid"},
    "recover": {"selected_journal_recoverable", "journal_arbitration_single_candidate", "stage_read_set_matches"},
}
_SPEC_IDENTITY_FIELDS = {
    "state",
    "state_revision",
    "current_task",
    "plan_revision",
    "plan_commit",
    "last_operation",
    "operation_targets",
}
_TARGET_IDENTITY_FIELDS = {
    "id",
    "state",
    "state_revision",
    "plan_revision",
    "plan_commit",
    "claimed_by",
    "claimed_at",
    "blocked_reason",
    "unblock_condition",
    "commit",
}
_PREDICATE_KEYS = {
    "no_other_unresolved_journal": {"predicate", "directory", "excluding_operation_id", "observed_operation_ids"},
    "flow_absent": {"predicate", "target"},
    "all_task_identities": {"predicate", "scope", "fields"},
    "target_absent": {"predicate", "target"},
    "plan_ready_approved": {"predicate", "spec", "approval_evidence", "reviewer_state"},
    "all_worksheets_complete": {"predicate", "scope", "required_headings"},
    "dependencies_exist_and_acyclic": {"predicate", "target", "dependency_paths", "observed_states"},
    "all_dependencies_closed": {"predicate", "target", "dependency_paths", "observed_states"},
    "no_other_in_progress_claim": {"predicate", "scope", "excluding", "observed_task_ids"},
    "sole_current_claim": {"predicate", "spec", "target", "claimant"},
    "actor_is_claimant_or_authorized": {"predicate", "target", "authorization"},
    "in_progress_target_is_current": {"predicate", "spec", "target"},
    "unblock_condition_satisfied": {"predicate", "target", "resolution_evidence"},
    "verification_bound_to_commit": {"predicate", "target", "commit", "evidence"},
    "acceptance_criteria_satisfied": {"predicate", "target", "checked_ids"},
    "affected_tasks_closed_or_skipped": {"predicate", "paths", "observed_states"},
    "phase_verification_valid": {"predicate", "affected_paths", "commit", "evidence"},
    "no_current_claim": {"predicate", "spec", "scope", "observed_task_ids"},
    "plan_bind_evidence_matches_live": {"predicate", "paths", "globs", "evidence", "runtime_inspection"},
    "git_note_attempt_idempotent": {"predicate", "target", "attachment_attempt_id", "observed_payload"},
    "fresh_user_approval": {"predicate", "approval", "occurred_at"},
    "skip_dependents_coherent": {"predicate", "scope", "target", "observed_dependents"},
    "replacement_checkpoint_valid": {"predicate", "spec", "checkpoint"},
    "reopen_plan_dependents_consistent": {"predicate", "scope", "target"},
    "revise_diff_and_adjustments_legal": {"predicate", "scope", "diffs", "adjustments"},
    "reconcile_mismatches_exact": {"predicate", "spec", "scope", "mismatches"},
    "all_tasks_terminal_no_blockers": {"predicate", "scope", "observed_states"},
    "completion_evidence_valid": {"predicate", "spec", "evidence"},
    "archive_candidate_exact": {"predicate", "root", "destinations", "manifest"},
    "archive_evidence_valid": {"predicate", "candidate", "quality", "waivers"},
    "selected_journal_recoverable": {"predicate", "directory", "operation_id", "states"},
    "journal_arbitration_single_candidate": {"predicate", "directory", "observed_operation_ids"},
    "stage_read_set_matches": {"predicate", "journal", "recorded_read_set"},
}
_TRANSITIONS: dict[str, set[tuple[str, str]]] = {
    "activate": {("planned", "active")},
    "claim": {("open", "in_progress")},
    "release": {("in_progress", "open")},
    "block": {("open", "blocked"), ("in_progress", "blocked")},
    "unblock": {("blocked", "open")},
    "close": {("in_progress", "closed")},
    "skip": {("open", "skipped"), ("blocked", "skipped")},
    "reopen": {("closed", "open"), ("skipped", "open")},
    "complete": {("active", "completed")},
}


def _iter_transaction_journals(repo_root: Path) -> Iterator[Path]:
    try:
        layout = resolve_okf_layout(repo_root)
    except ValueError:
        return
    directory = layout.configured_root / "tasks" / "transactions"
    if directory.is_dir():
        yield from sorted(directory.glob("*/journal.md"))


def _journal_data(path: Path) -> tuple[dict[str, Any] | None, list[Violation]]:
    return _parse_yaml_frontmatter(path)


def _walk_path_records(
    value: object, trail: str = "journal"
) -> Iterator[tuple[str, dict[str, Any]]]:
    if isinstance(value, dict):
        if any(key in value for key in ("path", "glob")):
            yield trail, value
        if trail.endswith("archive_inventory") and "root" in value:
            yield trail, value
        for key, nested in value.items():
            yield from _walk_path_records(nested, f"{trail}.{key}")
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            yield from _walk_path_records(nested, f"{trail}[{index}]")


def _resolve_journal_path(
    roots: dict[str, Path], base: object, raw: object, *, glob: bool = False
) -> tuple[Path | None, str | None]:
    if base not in roots:
        return None, f"missing or unknown base: {base!r}"
    if not isinstance(raw, str) or not raw:
        return None, "must be a non-empty relative path"
    candidate = Path(raw)
    if candidate.is_absolute() or ".." in candidate.parts:
        return None, f"escapes its {base} namespace"
    base_path = roots[cast("str", base)]
    check_parts = candidate.parts
    current = base_path
    for part in check_parts:
        if any(character in part for character in "*?[") and glob:
            break
        current /= part
        if current.is_symlink():
            return None, "traverses a symlink component"
    resolved = (base_path / candidate).resolve(strict=False)
    try:
        resolved.relative_to(base_path.resolve())
        resolved.relative_to(roots["repo_root"].resolve())
    except ValueError:
        return None, f"escapes its {base} namespace"
    if glob:
        for match in base_path.glob(raw):
            current = base_path
            try:
                match_parts = match.relative_to(base_path).parts
            except ValueError:
                return None, "glob match escapes its namespace"
            for part in match_parts:
                current /= part
                if current.is_symlink():
                    return None, "glob matches or traverses a symlink"
            try:
                match.resolve().relative_to(base_path.resolve())
                match.resolve().relative_to(roots["repo_root"].resolve())
            except ValueError:
                return None, "glob match escapes its namespace"
    return resolved, None


def _validate_path_record(
    path: Path,
    trail: str,
    record: dict[str, Any],
    roots: dict[str, Path],
) -> list[Violation]:
    violations: list[Violation] = []
    base = record.get("base")
    if base not in _PATH_BASES:
        return [Violation(path, 1, f"{trail} has missing or unknown base: {base!r}")]
    path_keys = {key for key in ("path", "glob") if key in record}
    if trail.endswith("archive_inventory") and "root" in record:
        path_keys.add("root")
    expected_keys = {"root"} if trail.endswith("archive_inventory") else {"path", "glob"}
    if len(path_keys) != 1 or not path_keys <= expected_keys:
        return [
            Violation(
                path,
                1,
                f"{trail} must contain exactly one of path or glob"
                if not trail.endswith("archive_inventory")
                else f"{trail} must contain exactly one archive root",
            )
        ]
    key = next(iter(path_keys))
    raw = record.get(key)
    if not isinstance(raw, str) or not raw:
        return [Violation(path, 1, f"{trail}.{key} must be a non-empty relative path")]
    _, error = _resolve_journal_path(roots, base, raw, glob=key == "glob")
    if error:
        violations.append(
            Violation(path, 1, f"{trail}.{key} {error}")
        )
    if "directory" in trail and "transactions" in raw:
        if base != "configured_root":
            violations.append(
                Violation(
                    path,
                    1,
                    f"{trail} transaction directory base must be configured_root",
                )
            )
    elif trail.endswith("archive_inventory") and base != "bundle_root":
        violations.append(Violation(path, 1, f"{trail} base must be bundle_root"))
    elif (
        raw.startswith(("tasks/", "spec.md"))
        and "archive_inventory" not in trail
        and base != "flow_root"
    ):
        violations.append(
            Violation(path, 1, f"{trail} task/spec base must be flow_root")
        )
    return violations


def _entry_tuple(entry: object) -> tuple[int, str, str] | None:
    if not isinstance(entry, dict):
        return None
    index = entry.get("write_index")
    base = entry.get("base")
    path = entry.get("path")
    if (
        not isinstance(index, int)
        or not isinstance(base, str)
        or not isinstance(path, str)
    ):
        return None
    return index, base, path


def _payload_keysets(request: dict[str, Any]) -> tuple[set[str], set[str]] | None:
    operation = request.get("operation")
    payload = request.get("payload")
    if not isinstance(operation, str) or not isinstance(payload, dict):
        return None
    if operation in _PAYLOAD_REQUIRED:
        return _PAYLOAD_REQUIRED[operation], set()
    if operation == "release":
        return {"reason", "next_step"}, {"user_authorization"}
    if operation == "note":
        if payload.get("category") == "git_note_attachment":
            return {
                "category",
                "text",
                "attachment_attempt_id",
                "ref",
                "commit",
                "result",
                "diagnostic",
            }, set()
        return {"category", "text"}, set()
    if operation == "checkpoint":
        scope = payload.get("scope")
        if scope == "task":
            return {"scope", "commit", "verification_evidence", "summary"}, set()
        if scope == "phase":
            return {
                "scope",
                "phase_id",
                "affected_task_ids",
                "last_functional_commit",
                "verification_evidence",
            }, set()
        if scope == "plan":
            return {"scope", "plan_bind_evidence"}, set()
        return None
    if operation == "create":
        if payload.get("variant") == "flow":
            return {"variant", "title", "description"}, set()
        if payload.get("variant") == "task":
            return {
                "variant",
                "short_id",
                "chapter_id",
                "worksheet",
                "priority",
                "verification_strategy",
                "depends_on",
                "files",
                "tests",
            }, set()
        return None
    return None


def _validate_plan_bind_payload(
    path: Path, data: dict[str, Any], request: dict[str, Any]
) -> list[Violation]:
    payload = request.get("payload")
    if not isinstance(payload, dict) or payload.get("scope") != "plan":
        return []
    evidence = payload.get("plan_bind_evidence")
    if not isinstance(evidence, dict) or set(evidence) != {
        "evidence_id",
        "commit",
        "inventory",
        "documents",
        "verifier",
    }:
        return [Violation(path, 1, "plan_bind_evidence must use the exact keyset")]
    violations: list[Violation] = []
    inventory = evidence.get("inventory")
    documents = evidence.get("documents")
    verifier = evidence.get("verifier")
    if (
        not isinstance(evidence.get("evidence_id"), str)
        or not evidence["evidence_id"].strip()
        or not re.fullmatch(r"[0-9a-f]{7,40}", str(evidence.get("commit")))
    ):
        violations.append(Violation(path, 1, "plan_bind_evidence id/commit is invalid"))
    if not isinstance(inventory, list) or not all(
        isinstance(item, dict)
        and set(item) == {"base", "path"}
        and item.get("base") == "flow_root"
        for item in inventory
    ):
        violations.append(Violation(path, 1, "plan_bind_evidence inventory schema is invalid"))
        inventory = []
    inventory_paths = [str(item.get("path")) for item in inventory]
    expected_inventory = ["spec.md", *sorted(item for item in inventory_paths if item.startswith("tasks/"))]
    if inventory_paths != expected_inventory or len(inventory_paths) != len(set(inventory_paths)):
        violations.append(Violation(path, 1, "plan_bind_evidence inventory must be complete, unique, spec-first, tasks-sorted"))
    if not isinstance(documents, list) or len(documents) != len(inventory_paths):
        violations.append(Violation(path, 1, "plan_bind_evidence documents must match inventory"))
        documents = []
    for index, document in enumerate(documents):
        if (
            not isinstance(document, dict)
            or set(document) != {"base", "path", "plan_revision", "plan_commit", "content_utf8_lf"}
            or index >= len(inventory_paths)
            or document.get("base") != "flow_root"
            or document.get("path") != inventory_paths[index]
            or document.get("plan_revision") != request.get("expected_plan_revision")
            or document.get("plan_commit") is not None
            or not isinstance(document.get("content_utf8_lf"), str)
        ):
            violations.append(Violation(path, 1, f"plan_bind_evidence document {index} is invalid"))
    if (
        not isinstance(verifier, dict)
        or set(verifier) != {"actor", "verified_at", "result"}
        or not isinstance(verifier.get("actor"), str)
        or not verifier["actor"].strip()
        or not _validate_iso_timestamp(verifier.get("verified_at"))
        or verifier.get("result") != "verified_against_commit"
    ):
        violations.append(Violation(path, 1, "plan_bind_evidence verifier schema is invalid"))
    target_ids = [Path(item).stem for item in inventory_paths if item.startswith("tasks/")]
    if request.get("targets") != target_ids:
        violations.append(Violation(path, 1, "plan bind targets must equal the complete task inventory"))
    expected_writes = [*sorted(item for item in inventory_paths if item.startswith("tasks/")), "spec.md"]
    writes = [item.get("path") for item in data.get("ordered_writes", []) if isinstance(item, dict)]
    if writes != expected_writes or data.get("fragments") != []:
        violations.append(Violation(path, 1, "plan bind must write tasks sorted then spec with fragments empty"))
    file_fragments = data.get("file_fragments")
    by_path = {
        item.get("path"): item
        for item in file_fragments or []
        if isinstance(item, dict)
    }
    for document in documents:
        fragment = by_path.get(document.get("path"))
        if not isinstance(fragment, dict) or fragment.get("before") != {
            "exists": True,
            "content_utf8_lf": document.get("content_utf8_lf"),
        }:
            violations.append(Violation(path, 1, f"plan bind before image disagrees with evidence document {document.get('path')}"))
    return violations


def _nonempty(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _exact_record(value: object, keys: set[str]) -> bool:
    return isinstance(value, dict) and set(value) == keys


def _unique_strings(value: object, *, sorted_values: bool = False) -> bool:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        return False
    return len(value) == len(set(value)) and (not sorted_values or value == sorted(value))


def _command_evidence(value: object) -> bool:
    return (
        isinstance(value, list)
        and bool(value)
        and all(
            _exact_record(item, {"command", "result"})
            and _nonempty(item["command"])
            and _nonempty(item["result"])
            for item in value
        )
    )


def _validate_payload_values(
    path: Path, request: dict[str, Any], variant: str
) -> list[Violation]:
    payload = request.get("payload")
    targets = request.get("targets")
    if not isinstance(payload, dict):
        return [Violation(path, 1, f"journal {variant} payload must be an object")]
    violations: list[Violation] = []

    def require_strings(*keys: str) -> None:
        for key in keys:
            if not _nonempty(payload.get(key)):
                violations.append(
                    Violation(path, 1, f"journal {variant} payload {key} must be non-empty")
                )

    if variant == "create.flow":
        if payload.get("variant") != "flow":
            violations.append(Violation(path, 1, "journal create.flow payload variant is invalid"))
        require_strings("title", "description")
    elif variant == "create.task":
        require_strings("short_id", "chapter_id")
        worksheet = payload.get("worksheet")
        worksheet_keys = {"Objective", "Context", "Steps", "Verification", "Acceptance Criteria"}
        if not _exact_record(worksheet, worksheet_keys) or not all(
            _nonempty(item) or (isinstance(item, list) and bool(item))
            for item in worksheet.values()
        ):
            violations.append(Violation(path, 1, "journal create.task worksheet is incomplete"))
        if payload.get("priority") not in {"P0", "P1", "P2", "P3", "P4"}:
            violations.append(Violation(path, 1, "journal create.task priority is invalid"))
        if payload.get("verification_strategy") not in _VERIFICATION_STRATEGIES:
            violations.append(Violation(path, 1, "journal create.task verification_strategy is invalid"))
        for key in ("depends_on", "files", "tests"):
            if not _unique_strings(payload.get(key)):
                violations.append(Violation(path, 1, f"journal create.task {key} must be unique strings"))
    elif variant in {"activate", "release", "block", "unblock", "reopen"}:
        required = {
            "activate": ("approval_evidence", "next_step"),
            "release": ("reason", "next_step"),
            "block": ("blocked_reason", "unblock_condition", "next_step"),
            "unblock": ("resolution_evidence", "next_step"),
            "reopen": ("reason", "next_step"),
        }[variant]
        require_strings(*required)
    elif variant == "claim":
        require_strings("next_step")
    elif variant.startswith("note."):
        require_strings("category", "text")
        if variant == "note.normal" and payload.get("category") == "git_note_attachment":
            violations.append(Violation(path, 1, "journal note.normal category is invalid"))
        if variant == "note.git_note_attachment":
            require_strings("attachment_attempt_id", "ref", "diagnostic")
            if payload.get("category") != "git_note_attachment" or payload.get("result") not in {"attached", "failed"}:
                violations.append(Violation(path, 1, "journal git-note category/result is invalid"))
            if not re.fullmatch(r"[0-9a-f]{7,40}", str(payload.get("commit"))):
                violations.append(Violation(path, 1, "journal git-note commit is invalid"))
    elif variant == "discover":
        require_strings("text", "impact")
        if payload.get("next_step") is not None and not _nonempty(payload.get("next_step")):
            violations.append(Violation(path, 1, "journal discover payload next_step is invalid"))
    elif variant.startswith("checkpoint."):
        scope = variant.split(".", 1)[1]
        if payload.get("scope") != scope:
            violations.append(Violation(path, 1, f"journal {variant} scope is invalid"))
        if scope == "task":
            require_strings("summary")
            if not re.fullmatch(r"[0-9a-f]{7,40}", str(payload.get("commit"))):
                violations.append(Violation(path, 1, "journal checkpoint.task commit is invalid"))
            if not _command_evidence(payload.get("verification_evidence")):
                violations.append(Violation(path, 1, "journal checkpoint.task verification_evidence is invalid"))
        elif scope == "phase":
            require_strings("phase_id")
            if not _unique_strings(payload.get("affected_task_ids"), sorted_values=True) or not payload.get("affected_task_ids"):
                violations.append(Violation(path, 1, "journal checkpoint.phase affected_task_ids is invalid"))
            if not re.fullmatch(r"[0-9a-f]{7,40}", str(payload.get("last_functional_commit"))):
                violations.append(Violation(path, 1, "journal checkpoint.phase commit is invalid"))
            if not _command_evidence(payload.get("verification_evidence")):
                violations.append(Violation(path, 1, "journal checkpoint.phase verification_evidence is invalid"))
    elif variant == "close":
        if not re.fullmatch(r"[0-9a-f]{7,40}", str(payload.get("commit"))):
            violations.append(Violation(path, 1, "journal close payload commit is invalid"))
        if not _command_evidence(payload.get("verification_evidence")):
            violations.append(Violation(path, 1, "journal close payload verification_evidence is invalid"))
        if not _unique_strings(payload.get("acceptance_criteria_checked")) or not payload.get("acceptance_criteria_checked"):
            violations.append(Violation(path, 1, "journal close payload acceptance_criteria_checked is invalid"))
    elif variant == "skip":
        require_strings("reason")
    elif variant == "revise":
        require_strings("rationale")
        diffs = payload.get("plan_diffs")
        if not isinstance(diffs, list) or not diffs or not all(
            _exact_record(item, {"base", "path", "anchor", "before", "after"})
            for item in diffs
        ):
            violations.append(Violation(path, 1, "journal revise plan_diffs are invalid"))
        expected_revision = request.get("expected_plan_revision")
        if not isinstance(expected_revision, int) or payload.get("new_plan_revision") != expected_revision + 1:
            violations.append(Violation(path, 1, "journal revise new_plan_revision is invalid"))
        if not all(isinstance(payload.get(key), list) for key in ("reviewer_findings", "state_adjustments")):
            violations.append(Violation(path, 1, "journal revise review/adjustment arrays are invalid"))
    elif variant == "reconcile":
        mismatches = payload.get("mismatches")
        if not isinstance(mismatches, list) or not mismatches or not all(
            _exact_record(item, {"path", "field", "spec_value", "task_value"})
            for item in mismatches
        ):
            violations.append(Violation(path, 1, "journal reconcile mismatches are invalid"))
        if not _unique_strings(payload.get("affected_task_ids"), sorted_values=True):
            violations.append(Violation(path, 1, "journal reconcile affected_task_ids are invalid"))
    elif variant == "complete":
        if not re.fullmatch(r"[0-9a-f]{7,40}", str(payload.get("final_functional_commit"))):
            violations.append(Violation(path, 1, "journal complete final commit is invalid"))
        if not _command_evidence(payload.get("verification_evidence")):
            violations.append(Violation(path, 1, "journal complete verification_evidence is invalid"))
        review_keys = {"reviewer", "base_commit", "head_commit", "findings"}
        for key in ("code_review_evidence", "quality_review"):
            review = payload.get(key)
            if (
                not _exact_record(review, review_keys)
                or not _nonempty(review.get("reviewer"))
                or not re.fullmatch(r"[0-9a-f]{7,40}", str(review.get("base_commit")))
                or not re.fullmatch(r"[0-9a-f]{7,40}", str(review.get("head_commit")))
                or not isinstance(review.get("findings"), list)
            ):
                violations.append(Violation(path, 1, f"journal complete {key} is invalid"))
        if not isinstance(payload.get("waivers"), list) or not all(
            _exact_record(item, {"finding_id", "approval_text", "approved_at"})
            and _nonempty(item.get("finding_id"))
            and _nonempty(item.get("approval_text"))
            and _validate_iso_timestamp(item.get("approved_at"))
            for item in payload.get("waivers", [])
        ):
            violations.append(Violation(path, 1, "journal complete waivers are invalid"))
    elif variant == "archive":
        if not _unique_strings(payload.get("knowledge_destinations"), sorted_values=True):
            violations.append(Violation(path, 1, "journal archive knowledge_destinations are invalid"))
        log_entry = payload.get("log_entry")
        if (
            not _exact_record(log_entry, {"date", "flow_id", "outcome", "final_commit"})
            or log_entry.get("flow_id") != request.get("flow_id")
            or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(log_entry.get("date")))
            or not _nonempty(log_entry.get("outcome"))
            or not re.fullmatch(r"[0-9a-f]{7,40}", str(log_entry.get("final_commit")))
        ):
            violations.append(Violation(path, 1, "journal archive log_entry is invalid"))
        edits = payload.get("synthesized_edits")
        if not isinstance(edits, list) or not all(
            _exact_record(item, {"path", "before", "after"})
            and _nonempty(item.get("path"))
            and isinstance(item.get("before"), str)
            and isinstance(item.get("after"), str)
            for item in edits or []
        ):
            violations.append(Violation(path, 1, "journal archive synthesized_edits is invalid"))
        notes = payload.get("notes_incorporation")
        if not isinstance(notes, list) or not all(
            _exact_record(item, {"task_id", "note_ids", "destinations"})
            and _nonempty(item.get("task_id"))
            and _unique_strings(item.get("note_ids"))
            and _unique_strings(item.get("destinations"), sorted_values=True)
            for item in notes or []
        ):
            violations.append(Violation(path, 1, "journal archive notes_incorporation is invalid"))
        candidate = payload.get("archive_candidate_manifest")
        if not _exact_record(candidate, {"base_commit", "head_commit", "inventory", "file_fragments"}) or not all(
            re.fullmatch(r"[0-9a-f]{7,40}", str(candidate.get(key)))
            for key in ("base_commit", "head_commit")
        ) or not all(isinstance(candidate.get(key), list) for key in ("inventory", "file_fragments")):
            violations.append(Violation(path, 1, "journal archive candidate manifest is invalid"))
        quality = payload.get("quality_report")
        if not _exact_record(quality, {"reviewer", "base_commit", "head_commit", "findings"}) or not _nonempty(quality.get("reviewer")) or not all(
            re.fullmatch(r"[0-9a-f]{7,40}", str(quality.get(key)))
            for key in ("base_commit", "head_commit")
        ) or not isinstance(quality.get("findings"), list):
            violations.append(Violation(path, 1, "journal archive quality_report is invalid"))
        waivers = payload.get("waivers")
        if not isinstance(waivers, list) or not all(
            _exact_record(item, {"finding_id", "approval_text", "approved_at"})
            for item in waivers or []
        ):
            violations.append(Violation(path, 1, "journal archive waivers are invalid"))
    elif variant == "recover":
        require_strings("journal_operation_id")
        if payload.get("action") not in {"finish", "rollback"}:
            violations.append(Violation(path, 1, "journal recover action is invalid"))

    for approval_key in ("user_authorization", "user_approval"):
        if approval_key in payload:
            approval = payload[approval_key]
            if not _exact_record(approval, {"text", "at"}) or not _nonempty(approval.get("text")) or not _validate_iso_timestamp(approval.get("at")):
                violations.append(Violation(path, 1, f"journal {variant} {approval_key} is invalid"))
    if not isinstance(targets, list):
        violations.append(Violation(path, 1, f"journal {variant} targets are invalid"))
    return violations


def _validate_read_predicates(
    path: Path, data: dict[str, Any], request: dict[str, Any]
) -> list[Violation]:
    violations: list[Violation] = []
    payload = request.get("payload") if isinstance(request.get("payload"), dict) else {}

    def path_record(value: object, key: str, base: str) -> bool:
        return _exact_record(value, {"base", key}) and value.get("base") == base and _nonempty(value.get(key))

    def path_array(value: object, key: str, base: str) -> bool:
        if not isinstance(value, list) or not all(path_record(item, key, base) for item in value):
            return False
        rendered = [str(item[key]) for item in value]
        return rendered == sorted(set(rendered))

    for index, item in enumerate(data.get("read_set", [])):
        if not isinstance(item, dict):
            violations.append(Violation(path, 1, f"journal read_set[{index}] must be an object"))
            continue
        predicate = item.get("predicate")
        if predicate is None:
            expected = _SPEC_IDENTITY_FIELDS if item.get("path") == "spec.md" else _TARGET_IDENTITY_FIELDS
            if set(item) != {"base", "path", "fields"} or not isinstance(item.get("fields"), dict) or set(item["fields"]) != expected:
                name = "spec_identity" if item.get("path") == "spec.md" else "target_identity"
                violations.append(Violation(path, 1, f"journal {name} predicate body is incomplete"))
            continue
        expected_keys = _PREDICATE_KEYS.get(str(predicate))
        if expected_keys is None or set(item) != expected_keys:
            violations.append(Violation(path, 1, f"journal {predicate} predicate body has an inexact keyset"))
            continue
        if predicate == "no_other_unresolved_journal":
            if not path_record(item.get("directory"), "path", "configured_root") or item["directory"].get("path") != "tasks/transactions" or item.get("excluding_operation_id") != data.get("operation_id") or not _unique_strings(item.get("observed_operation_ids"), sorted_values=True):
                violations.append(Violation(path, 1, "journal no_other_unresolved_journal predicate values are invalid"))
        elif predicate == "flow_absent":
            if not path_record(item.get("target"), "path", "bundle_root") or item["target"].get("path") != f"specs/{request.get('flow_id')}":
                violations.append(Violation(path, 1, "journal flow_absent target is invalid"))
        elif predicate == "all_task_identities":
            fields = item.get("fields")
            if not path_record(item.get("scope"), "glob", "flow_root") or item["scope"].get("glob") != "tasks/*.md" or not isinstance(fields, list) or set(fields) != _TARGET_IDENTITY_FIELDS or len(fields) != len(_TARGET_IDENTITY_FIELDS):
                violations.append(Violation(path, 1, "journal all_task_identities fields are incomplete"))
        elif predicate == "target_absent":
            target = request.get("targets", [None])[0] if request.get("targets") else None
            if not path_record(item.get("target"), "path", "flow_root") or item["target"].get("path") != f"tasks/{target}.md":
                violations.append(Violation(path, 1, "journal target_absent target is invalid"))
        elif predicate in {"all_dependencies_closed", "dependencies_exist_and_acyclic"}:
            paths = item.get("dependency_paths")
            states = item.get("observed_states")
            ids = [Path(str(record.get("path"))).stem for record in paths or [] if isinstance(record, dict)]
            target = request.get("targets", [None])[0] if request.get("targets") else None
            if not path_record(item.get("target"), "path", "flow_root") or item["target"].get("path") != f"tasks/{target}.md" or not path_array(paths, "path", "flow_root") or ids != sorted(set(ids)) or not isinstance(states, dict) or set(states) != set(ids):
                violations.append(Violation(path, 1, f"journal {predicate} predicate paths/states are incomplete"))
            elif predicate == "all_dependencies_closed" and set(states.values()) != ({"closed"} if states else set()):
                violations.append(Violation(path, 1, "journal all_dependencies_closed predicate contains a non-closed dependency"))
        elif predicate in {"no_other_in_progress_claim", "no_current_claim"}:
            if not path_record(item.get("scope"), "glob", "flow_root") or item["scope"].get("glob") != "tasks/*.md" or not _unique_strings(item.get("observed_task_ids"), sorted_values=True):
                violations.append(Violation(path, 1, f"journal {predicate} observed task ids are invalid"))
            if predicate == "no_other_in_progress_claim" and (
                not path_record(item.get("excluding"), "path", "flow_root")
                or item["excluding"].get("path") != f"tasks/{request.get('targets', [None])[0]}.md"
            ):
                violations.append(Violation(path, 1, "journal no_other_in_progress_claim excluding target is invalid"))
            if predicate == "no_current_claim" and (item.get("observed_task_ids") != [] or not path_record(item.get("spec"), "path", "flow_root") or item["spec"].get("path") != "spec.md"):
                violations.append(Violation(path, 1, "journal no_current_claim values are invalid"))
        elif predicate == "all_worksheets_complete" and item.get("required_headings") != ["Objective", "Context", "Steps", "Verification", "Acceptance Criteria"]:
            violations.append(Violation(path, 1, "journal all_worksheets_complete headings are incomplete"))
        elif predicate == "plan_ready_approved" and (not path_record(item.get("spec"), "path", "flow_root") or item["spec"].get("path") != "spec.md" or item.get("reviewer_state") != "Ready" or item.get("approval_evidence") != payload.get("approval_evidence")):
            violations.append(Violation(path, 1, "journal plan_ready_approved values disagree with payload"))
        elif predicate == "unblock_condition_satisfied" and item.get("resolution_evidence") != payload.get("resolution_evidence"):
            violations.append(Violation(path, 1, "journal unblock predicate disagrees with payload"))
        elif predicate == "verification_bound_to_commit" and (item.get("commit") != payload.get("commit") and item.get("commit") != payload.get("last_functional_commit") or item.get("evidence") != payload.get("verification_evidence")):
            violations.append(Violation(path, 1, "journal verification predicate disagrees with payload"))
        elif predicate == "acceptance_criteria_satisfied" and item.get("checked_ids") != payload.get("acceptance_criteria_checked"):
            violations.append(Violation(path, 1, "journal acceptance predicate disagrees with payload"))
        elif predicate == "sole_current_claim" and (not path_record(item.get("spec"), "path", "flow_root") or not path_record(item.get("target"), "path", "flow_root") or item.get("claimant") != request.get("actor")):
            violations.append(Violation(path, 1, "journal sole_current_claim predicate values are invalid"))
        elif predicate == "actor_is_claimant_or_authorized":
            authorization = item.get("authorization")
            if authorization is not None and (not _exact_record(authorization, {"text", "at"}) or not _nonempty(authorization.get("text")) or not _validate_iso_timestamp(authorization.get("at"))):
                violations.append(Violation(path, 1, "journal claimant authorization predicate is invalid"))
            if authorization != payload.get("user_authorization"):
                violations.append(Violation(path, 1, "journal claimant authorization disagrees with payload"))
        elif predicate == "in_progress_target_is_current" and (not path_record(item.get("spec"), "path", "flow_root") or not path_record(item.get("target"), "path", "flow_root")):
            violations.append(Violation(path, 1, "journal in_progress_target_is_current paths are invalid"))
        elif predicate == "affected_tasks_closed_or_skipped":
            paths = item.get("paths")
            states = item.get("observed_states")
            ids = [Path(str(record.get("path"))).stem for record in paths or [] if isinstance(record, dict)]
            if not path_array(paths, "path", "flow_root") or not isinstance(states, dict) or set(states) != set(ids) or any(state not in {"closed", "skipped"} for state in states.values()):
                violations.append(Violation(path, 1, "journal affected task predicate values are invalid"))
        elif predicate == "phase_verification_valid" and (not path_array(item.get("affected_paths"), "path", "flow_root") or item.get("commit") != payload.get("last_functional_commit") or item.get("evidence") != payload.get("verification_evidence")):
            violations.append(Violation(path, 1, "journal phase verification predicate disagrees with payload"))
        elif predicate == "plan_bind_evidence_matches_live" and (item.get("paths") != [{"base": "flow_root", "path": "spec.md"}] or item.get("globs") != [{"base": "flow_root", "glob": "tasks/*.md"}] or item.get("runtime_inspection") != "forbidden" or item.get("evidence") != payload.get("plan_bind_evidence")):
            violations.append(Violation(path, 1, "journal plan-bind predicate disagrees with payload"))
        elif predicate == "git_note_attempt_idempotent" and (item.get("attachment_attempt_id") != payload.get("attachment_attempt_id") or item.get("observed_payload") is not None and not isinstance(item.get("observed_payload"), dict)):
            violations.append(Violation(path, 1, "journal git-note predicate disagrees with payload"))
        elif predicate == "fresh_user_approval" and (item.get("approval") != payload.get("user_approval") or item.get("occurred_at") != request.get("occurred_at")):
            violations.append(Violation(path, 1, "journal fresh approval predicate disagrees with request"))
        elif predicate == "replacement_checkpoint_valid" and item.get("checkpoint") != payload.get("replacement_checkpoint"):
            violations.append(Violation(path, 1, "journal replacement checkpoint predicate disagrees with payload"))
        elif predicate == "revise_diff_and_adjustments_legal" and (item.get("diffs") != payload.get("plan_diffs") or item.get("adjustments") != payload.get("state_adjustments")):
            violations.append(Violation(path, 1, "journal revise predicate disagrees with payload"))
        elif predicate == "reconcile_mismatches_exact" and item.get("mismatches") != payload.get("mismatches"):
            violations.append(Violation(path, 1, "journal reconcile predicate disagrees with payload"))
        elif predicate == "all_tasks_terminal_no_blockers":
            states = item.get("observed_states")
            if not isinstance(states, dict) or any(state not in {"closed", "skipped"} for state in states.values()):
                violations.append(Violation(path, 1, "journal terminal task predicate values are invalid"))
        elif predicate == "completion_evidence_valid" and item.get("evidence") != {key: payload.get(key) for key in ("verification_evidence", "code_review_evidence", "quality_review", "waivers")}:
            violations.append(Violation(path, 1, "journal completion predicate disagrees with payload"))
        elif predicate == "archive_candidate_exact" and item.get("manifest") != payload.get("archive_candidate_manifest"):
            violations.append(Violation(path, 1, "journal archive candidate predicate disagrees with payload"))
        elif predicate == "archive_evidence_valid" and (item.get("candidate") != payload.get("archive_candidate_manifest") or item.get("quality") != payload.get("quality_report") or item.get("waivers") != payload.get("waivers")):
            violations.append(Violation(path, 1, "journal archive evidence predicate disagrees with payload"))
        elif predicate == "selected_journal_recoverable" and (item.get("operation_id") != payload.get("journal_operation_id") or item.get("states") != ["prepared", "task_writes_started", "recovery_required", "rollback_in_progress"]):
            violations.append(Violation(path, 1, "journal selected recoverable predicate is invalid"))
        elif predicate == "journal_arbitration_single_candidate" and not _unique_strings(item.get("observed_operation_ids"), sorted_values=True):
            violations.append(Violation(path, 1, "journal arbitration predicate observations are invalid"))
        elif predicate == "stage_read_set_matches" and item.get("recorded_read_set") != data.get("read_set"):
            violations.append(Violation(path, 1, "journal stage read-set predicate is invalid"))
    return violations


def _validate_journal_semantics(
    path: Path, data: dict[str, Any], request: dict[str, Any]
) -> list[Violation]:
    violations: list[Violation] = []
    payload = request.get("payload")
    keysets = _payload_keysets(request)
    if keysets is None or not isinstance(payload, dict):
        violations.append(
            Violation(path, 1, "journal request has unknown operation/payload variant")
        )
    else:
        required, optional = keysets
        if not required <= set(payload) or set(payload) - required - optional:
            violations.append(
                Violation(
                    path, 1, "journal payload does not match the exact operation keyset"
                )
            )
    operation = request.get("operation")
    if not _nonempty(request.get("flow_id")):
        violations.append(
            Violation(path, 1, "journal request flow_id must be non-empty")
        )
    if not isinstance(request.get("actor"), str) or not request["actor"].strip():
        violations.append(Violation(path, 1, "journal request actor must be non-empty"))
    targets = request.get("targets")
    if not _unique_strings(targets, sorted_values=True):
        violations.append(
            Violation(path, 1, "journal request targets must be unique and sorted")
        )
        targets = []
    plan_commit = request.get("expected_plan_commit")
    if plan_commit is not None and not re.fullmatch(
        r"[0-9a-f]{7,40}", str(plan_commit)
    ):
        violations.append(
            Violation(path, 1, "journal request expected_plan_commit is invalid")
        )
    variant = str(operation)
    if operation == "create" and isinstance(payload, dict):
        variant = f"create.{payload.get('variant')}"
    elif operation == "checkpoint" and isinstance(payload, dict):
        variant = f"checkpoint.{payload.get('scope')}"
    elif operation == "note" and isinstance(payload, dict):
        variant = (
            "note.git_note_attachment"
            if payload.get("category") == "git_note_attachment"
            else "note.normal"
        )
    violations.extend(_validate_payload_values(path, request, variant))
    spec_only = {
        "activate",
        "checkpoint.phase",
        "reconcile",
        "complete",
        "archive",
        "recover",
        "create.flow",
    }
    if variant in spec_only and targets:
        violations.append(Violation(path, 1, f"{variant} requires empty targets"))
    single_target = {
        "claim",
        "release",
        "note.normal",
        "note.git_note_attachment",
        "discover",
        "block",
        "unblock",
        "checkpoint.task",
        "close",
        "skip",
        "reopen",
        "create.task",
    }
    if variant in single_target and len(targets) != 1:
        violations.append(Violation(path, 1, f"{variant} requires exactly one target"))
    if operation == "create":
        expected = (
            request.get("expected_plan_revision"),
            request.get("expected_plan_commit"),
            request.get("expected_state_revision"),
        )
        if variant == "create.flow" and expected != (None, None, None):
            violations.append(
                Violation(path, 1, "create.flow expected identities must be null")
            )
        if (
            variant == "create.task"
            and isinstance(payload, dict)
            and targets != [str(payload.get("short_id"))]
        ):
            violations.append(
                Violation(
                    path, 1, "create.task targets/path must equal payload short_id"
                )
            )
        if variant == "create.task" and (
            not isinstance(expected[0], int)
            or not isinstance(expected[2], int)
            or expected[0] < 1
            or expected[2] < 0
        ):
            violations.append(
                Violation(
                    path, 1, "create.task requires valid expected plan/state identity"
                )
            )
    else:
        revisions = (
            request.get("expected_plan_revision"),
            request.get("expected_state_revision"),
        )
        if any(not isinstance(value, int) or value < 0 for value in revisions):
            violations.append(
                Violation(
                    path,
                    1,
                    "existing-flow request requires nonnegative expected plan/state identity",
                )
            )

    read_set = data.get("read_set")
    observed_predicates: set[str] = set()
    if isinstance(read_set, list):
        for item in read_set:
            if not isinstance(item, dict):
                continue
            predicate = item.get("predicate")
            if isinstance(predicate, str):
                observed_predicates.add(predicate)
            elif (
                item.get("base") == "flow_root"
                and item.get("path") == "spec.md"
                and isinstance(item.get("fields"), dict)
            ):
                observed_predicates.add("spec_identity")
            elif (
                item.get("base") == "flow_root"
                and str(item.get("path", "")).startswith("tasks/")
                and isinstance(item.get("fields"), dict)
            ):
                observed_predicates.add("target_identity")
        violations.extend(_validate_read_predicates(path, data, request))
    required_predicates = _OPERATION_PREDICATES.get(variant)
    if required_predicates is not None and observed_predicates != required_predicates:
        violations.append(
            Violation(
                path,
                1,
                f"journal read_set predicates must be exact for {variant}: expected {sorted(required_predicates)}, got {sorted(observed_predicates)}",
            )
        )

    spec_read = next(
        (
            item
            for item in read_set or []
            if isinstance(item, dict)
            and item.get("base") == "flow_root"
            and item.get("path") == "spec.md"
            and isinstance(item.get("fields"), dict)
        ),
        None,
    )
    source_state = spec_read.get("fields", {}).get("state") if spec_read else None
    if spec_read is not None:
        fields = spec_read["fields"]
        expected_identity = (
            request.get("expected_plan_revision"),
            request.get("expected_plan_commit"),
            request.get("expected_state_revision"),
        )
        recorded_identity = (
            fields.get("plan_revision"),
            fields.get("plan_commit"),
            fields.get("state_revision"),
        )
        if expected_identity != recorded_identity:
            violations.append(
                Violation(
                    path,
                    1,
                    "journal request expected plan/state identity disagrees with spec read predicate",
                )
            )
    allowed_lifecycle: dict[str, set[str]] = {
        "create.task": {"planned", "active"},
        "activate": {"planned"},
        "claim": {"active"},
        "release": {"active"},
        "note.normal": {"planned", "active"},
        "note.git_note_attachment": {"planned", "active", "completed"},
        "discover": {"active"},
        "block": {"active"},
        "unblock": {"active"},
        "checkpoint.task": {"active"},
        "checkpoint.phase": {"active"},
        "checkpoint.plan": {"planned", "active"},
        "close": {"active"},
        "skip": {"active"},
        "reopen": {"active"},
        "revise": {"planned", "active"},
        "reconcile": {"active"},
        "complete": {"active"},
        "archive": {"completed"},
    }
    if variant in allowed_lifecycle and source_state not in allowed_lifecycle[variant]:
        violations.append(
            Violation(
                path,
                1,
                f"journal {variant} lifecycle source {source_state!r} is illegal",
            )
        )

    fragments = data.get("fragments")
    if not isinstance(fragments, list):
        violations.append(Violation(path, 1, "journal fragments must be a list"))
        fragments = []
    for index, fragment in enumerate(fragments):
        if not isinstance(fragment, dict) or set(fragment) != {
            "base",
            "path",
            "anchor",
            "before",
            "after",
        }:
            violations.append(
                Violation(
                    path, 1, f"journal fragment keyset is invalid at index {index}"
                )
            )
            continue
        if (
            not isinstance(fragment["before"], dict)
            or not isinstance(fragment["after"], dict)
            or set(fragment["before"]) != set(fragment["after"])
        ):
            violations.append(
                Violation(
                    path,
                    1,
                    f"journal fragment before/after keysets differ at index {index}",
                )
            )
            continue
        anchor = fragment.get("anchor")
        keys = set(fragment["before"])
        is_task_create = variant == "create.task"
        new_task_path = (
            f"tasks/{payload.get('short_id')}.md" if isinstance(payload, dict) else ""
        )
        if anchor == "frontmatter":
            if is_task_create and fragment.get("path") == new_task_path:
                violations.append(
                    Violation(
                        path,
                        1,
                        f"create.task new task must use a complete file fragment, not anchor {index}",
                    )
                )
            elif is_task_create and str(fragment.get("path", "")).startswith("tasks/"):
                if keys != {"plan_revision", "plan_commit"}:
                    violations.append(
                        Violation(
                            path,
                            1,
                            f"create.task existing task fragment {index} must contain only plan identity",
                        )
                    )
            elif (
                not {
                    "state_revision",
                    "last_operation",
                    "operation_targets",
                    "updated_at",
                }
                <= keys
            ):
                violations.append(
                    Violation(
                        path,
                        1,
                        f"journal frontmatter fragment {index} omits state identity fields",
                    )
                )
        elif (
            isinstance(anchor, str)
            and anchor.startswith("implementation-plan-task-")
            and keys != {"checklist_marker", "commit_suffix"}
        ):
            violations.append(
                Violation(
                    path,
                    1,
                    f"journal checklist fragment {index} has an inexact anchor schema",
                )
            )
        elif (
            isinstance(anchor, str)
            and anchor.startswith("implementation-plan-chapter-")
            and (not is_task_create or keys != {"checklist_items"})
        ):
            violations.append(
                Violation(
                    path,
                    1,
                    f"create.task chapter fragment {index} has an inexact insertion schema",
                )
            )
        elif anchor == "continuity-snapshot":
            if keys != {
                "current_task_claim",
                "last_verified_checkpoint",
                "next_exact_step",
                "state_identity",
            }:
                violations.append(
                    Violation(
                        path,
                        1,
                        f"journal continuity fragment {index} has an inexact anchor schema",
                    )
                )
            else:
                for image in (fragment["before"], fragment["after"]):
                    identity = image.get("state_identity")
                    if not isinstance(identity, dict) or set(identity) != {
                        "revision",
                        "last_operation",
                        "operation_targets",
                    }:
                        violations.append(
                            Violation(
                                path,
                                1,
                                f"journal continuity fragment {index} has an inexact state identity",
                            )
                        )
    ordered = data.get("ordered_writes")
    if isinstance(ordered, list) and operation not in {"archive", "create"}:
        paths = [item.get("path") for item in ordered if isinstance(item, dict)]
        task_paths = [
            item
            for item in paths
            if isinstance(item, str) and item.startswith("tasks/")
        ]
        if paths != [*sorted(task_paths), "spec.md"]:
            violations.append(
                Violation(
                    path, 1, "journal ordered_writes must use task-before-spec order"
                )
            )
        target_paths = {f"tasks/{target}.md" for target in targets}
        if target_paths != set(task_paths):
            violations.append(
                Violation(path, 1, "journal request targets/path agreement failed")
            )
    elif isinstance(ordered, list) and operation == "archive":
        paths = [item.get("path") for item in ordered if isinstance(item, dict)]
        knowledge = sorted(
            item
            for item in paths
            if isinstance(item, str) and item.startswith("knowledge/")
        )
        flow_prefix = f"specs/{data.get('flow_id')}/"
        flow_files = [
            item
            for item in paths
            if isinstance(item, str) and item.startswith(flow_prefix)
        ]
        expected_flow = sorted(
            item for item in flow_files if not item.endswith("/spec.md")
        ) + [f"{flow_prefix}spec.md"]
        if paths != [*knowledge, "log.md", *expected_flow]:
            violations.append(
                Violation(
                    path,
                    1,
                    "archive ordered_writes must be knowledge, log, task files, then spec",
                )
            )

    transitions = _TRANSITIONS.get(str(operation))
    if transitions:
        for index, fragment in enumerate(data.get("fragments", [])):
            if not isinstance(fragment, dict):
                continue
            before = fragment.get("before")
            after = fragment.get("after")
            if not isinstance(before, dict) or not isinstance(after, dict):
                continue
            if "state" in before or "state" in after:
                transition = (str(before.get("state")), str(after.get("state")))
                if transition not in transitions:
                    violations.append(
                        Violation(
                            path,
                            1,
                            f"journal.fragments[{index}] has illegal {operation} transition {transition[0]} -> {transition[1]}",
                        )
                    )
    return violations


_FORWARD_VALIDATION_CHECKS = [
    "transaction_arbitration",
    "complete_read_set",
    "ordered_mutations",
    "after_fragments",
    "operation_postconditions",
]
_ROLLBACK_VALIDATION_CHECKS = [
    "transaction_arbitration",
    "stage_read_set",
    "rolled_back_mutations",
    "before_fragments",
    "rollback_postconditions",
]


def _validate_terminal_events(path: Path, data: dict[str, Any]) -> list[Violation]:
    violations: list[Violation] = []
    events = data.get("events")
    if not isinstance(events, list):
        return [Violation(path, 1, "journal events must be a list")]
    validations: dict[str, tuple[int, str]] = {}
    invalidated: set[str] = set()
    latest_by_direction: dict[str, str] = {}
    selected_action: str | None = None
    for index, event in enumerate(events):
        if not isinstance(event, dict):
            violations.append(Violation(path, 1, f"journal event {index} must be an object"))
            continue
        kind = event.get("kind")
        if not _validate_iso_timestamp(event.get("at")):
            violations.append(Violation(path, 1, f"journal event {index} at must be canonical UTC"))
        if kind in {"validation_recorded", "rollback_validated"}:
            required = {"sequence", "kind", "at", "actor", "direction", "validation_attempt_id", "checks"}
            expected_direction = "forward" if kind == "validation_recorded" else "rollback"
            expected_checks = _FORWARD_VALIDATION_CHECKS if kind == "validation_recorded" else _ROLLBACK_VALIDATION_CHECKS
            checks = event.get("checks")
            check_ids = [item.get("check_id") for item in checks if isinstance(item, dict)] if isinstance(checks, list) else []
            checks_exact = (
                check_ids == expected_checks
                and all(
                    isinstance(item, dict)
                    and set(item) == {"check_id", "result", "observed"}
                    and item.get("result") == "passed"
                    for item in checks or []
                )
            )
            attempt_id = event.get("validation_attempt_id")
            pattern = rf"{re.escape(str(data.get('operation_id')))}:{expected_direction}:v(?:[0-9]{{2}})"
            if (
                set(event) != required
                or event.get("direction") != expected_direction
                or not isinstance(attempt_id, str)
                or not re.fullmatch(pattern, attempt_id)
                or not checks_exact
                or attempt_id in validations
                or (
                    expected_direction in latest_by_direction
                    and latest_by_direction[expected_direction] not in invalidated
                )
            ):
                violations.append(Violation(path, 1, f"journal {kind} requires exact validation checks and a fresh attempt id"))
            elif attempt_id is not None:
                validations[attempt_id] = (index, expected_direction)
                latest_by_direction[expected_direction] = attempt_id
            if (expected_direction == "forward" and selected_action == "rollback") or (
                expected_direction == "rollback" and selected_action != "rollback"
            ):
                violations.append(
                    Violation(path, 1, "journal validation direction grammar conflicts with recovery selection")
                )
        elif kind == "validation_invalidated":
            required = {"sequence", "kind", "at", "actor", "direction", "validation_attempt_id", "reason", "observed_nonterminal_operation_ids", "failed_checks"}
            attempt_id = event.get("validation_attempt_id")
            failed = event.get("failed_checks")
            failed_ids = {
                item.get("check_id")
                for item in failed or []
                if isinstance(item, dict)
            }
            reason = event.get("reason")
            reason_matches = (
                reason == "contender_appeared"
                and failed_ids == {"transaction_arbitration"}
                and bool(event.get("observed_nonterminal_operation_ids"))
            ) or (
                reason == "read_set_drift"
                and bool(failed_ids & {"complete_read_set", "stage_read_set"})
                and failed_ids <= {"complete_read_set", "stage_read_set"}
            ) or (
                reason == "mutation_drift"
                and bool(
                    failed_ids
                    & {
                        "ordered_mutations",
                        "after_fragments",
                        "operation_postconditions",
                        "rolled_back_mutations",
                        "before_fragments",
                        "rollback_postconditions",
                    }
                )
                and "transaction_arbitration" not in failed_ids
            )
            if (
                set(event) != required
                or attempt_id not in validations
                or attempt_id in invalidated
                or latest_by_direction.get(str(event.get("direction"))) != attempt_id
                or validations.get(cast("str", attempt_id), (-1, ""))[1] != event.get("direction")
                or event.get("reason") not in {"contender_appeared", "read_set_drift", "mutation_drift"}
                or not isinstance(event.get("observed_nonterminal_operation_ids"), list)
                or event.get("observed_nonterminal_operation_ids") != sorted(set(map(str, event.get("observed_nonterminal_operation_ids", []))))
                or not isinstance(failed, list)
                or not failed
                or not all(isinstance(item, dict) and set(item) == {"check_id", "expected", "observed"} for item in failed)
                or not reason_matches
            ):
                violations.append(Violation(path, 1, "journal validation_invalidated event is not exact"))
                if not reason_matches:
                    violations.append(
                        Violation(path, 1, "journal validation direction grammar requires reason-matched failed checks")
                    )
            elif isinstance(attempt_id, str):
                invalidated.add(attempt_id)
        elif isinstance(kind, str) and kind.startswith("directory_"):
            pass
        else:
            exact_keys = {
                "prepared": {"sequence", "kind", "at", "observed_nonterminal_operation_ids"},
                "write_started": {"sequence", "kind", "at", "write_index", "base", "path"},
                "write_applied": {"sequence", "kind", "at", "write_index", "base", "path"},
                "write_not_applied": {"sequence", "kind", "at", "write_index", "base", "path"},
                "recovery_selected": {"sequence", "kind", "at", "action", "actor"},
                "rollback_started": {"sequence", "kind", "at", "write_index", "base", "path"},
                "rollback_applied": {"sequence", "kind", "at", "write_index", "base", "path"},
                "contended_before_write": {"sequence", "kind", "at", "observed_nonterminal_operation_ids"},
            }.get(str(kind))
            if exact_keys is None or set(event) != exact_keys:
                violations.append(Violation(path, 1, f"journal {kind!r} event keyset is invalid"))
            if kind == "recovery_selected" and event.get("action") in {"finish", "rollback"}:
                selected_action = cast("str", event.get("action"))
    for direction in ("forward", "rollback"):
        expected_ids = {
            f"{data.get('operation_id')}:{direction}:v{suffix:02d}"
            for suffix in range(100)
        }
        if expected_ids <= set(validations) and expected_ids <= invalidated:
            violations.append(
                Violation(
                    path,
                    1,
                    f"{direction} validation attempts exhausted; hard-stop for repair or new operation",
                )
            )
    state = data.get("state")
    if state in {"committed", "rolled_back"}:
        required_kind = "validation_recorded" if state == "committed" else "rollback_validated"
        if not events or not isinstance(events[-1], dict) or events[-1].get("kind") != required_kind:
            violations.append(Violation(path, 1, f"terminal {state} requires final {required_kind}"))
        elif events[-1].get("validation_attempt_id") in invalidated:
            violations.append(Violation(path, 1, f"terminal {state} requires uninvalidated validation"))
        ordered = data.get("ordered_writes", [])
        applied = data.get("applied_writes", [])
        rolled = data.get("rolled_back_writes", [])
        if state == "committed" and len(applied) != len(ordered):
            violations.append(Violation(path, 1, "terminal committed requires complete applied prefix"))
        if state == "rolled_back" and len(rolled) != len(applied):
            violations.append(Violation(path, 1, "terminal rolled_back requires complete reverse rollback prefix"))
    return violations


def _validate_create_flow_shape(
    path: Path, data: dict[str, Any], request: dict[str, Any]
) -> list[Violation]:
    payload = request.get("payload")
    if request.get("operation") != "create" or not isinstance(payload, dict) or payload.get("variant") != "flow":
        return []
    violations: list[Violation] = []
    expected_directories = [
        {"directory_index": 0, "base": "flow_root", "path": "."},
        {"directory_index": 1, "base": "flow_root", "path": "tasks"},
    ]
    if data.get("ordered_directories") != expected_directories:
        violations.append(
            Violation(path, 1, "create.flow requires unique flow-root and tasks directories in shallow order")
        )
    fragments = data.get("file_fragments")
    expected_file = (
        isinstance(fragments, list)
        and len(fragments) == 1
        and isinstance(fragments[0], dict)
        and fragments[0].get("base") == "flow_root"
        and fragments[0].get("path") == "spec.md"
    )
    if not expected_file or data.get("ordered_writes") != [{"base": "flow_root", "path": "spec.md"}] or data.get("fragments") != []:
        violations.append(Violation(path, 1, "create.flow effects must contain only the complete spec write"))
        return violations
    content = fragments[0].get("after", {}).get("content_utf8_lf")
    if not isinstance(content, str) or not content.startswith("---\n"):
        violations.append(Violation(path, 1, "create.flow spec content is incomplete"))
        return violations
    try:
        _, raw_frontmatter, body = content.split("---\n", 2)
        frontmatter = yaml.safe_load(raw_frontmatter)
    except (ValueError, yaml.YAMLError):
        frontmatter = None
        body = ""
    required = {
        "type",
        "flow_id",
        "title",
        "state",
        "plan_revision",
        "plan_commit",
        "state_revision",
        "current_task",
        "last_operation",
        "operation_targets",
        "last_verified_checkpoint",
        "created_at",
        "updated_at",
        "description",
    }
    expected_values = {
        "type": "Spec",
        "flow_id": request.get("flow_id"),
        "title": payload.get("title"),
        "description": payload.get("description"),
        "state": "planned",
        "plan_revision": 1,
        "plan_commit": None,
        "state_revision": 0,
        "current_task": None,
        "last_operation": None,
        "operation_targets": [],
        "last_verified_checkpoint": None,
    }
    if (
        not isinstance(frontmatter, dict)
        or not required <= set(frontmatter)
        or any(frontmatter.get(key) != value for key, value in expected_values.items())
        or not _validate_iso_timestamp(frontmatter.get("created_at"))
        or not _validate_iso_timestamp(frontmatter.get("updated_at"))
    ):
        violations.append(Violation(path, 1, "create.flow spec frontmatter is incomplete or has wrong initial effects"))
    required_snapshot_labels = (
        "Lifecycle",
        "Current task/claim",
        "Last verified checkpoint",
        "Decisions",
        "Recent discoveries",
        "Blockers",
        "Next exact step",
        "Plan identity",
        "State identity",
        "Relevant paths",
    )
    if "## Implementation Plan" not in body or "## Continuity Snapshot" not in body or any(
        f"**{label}:**" not in body for label in required_snapshot_labels
    ):
        violations.append(Violation(path, 1, "create.flow spec body requires a complete Continuity Snapshot"))
    return violations


def _validate_create_task_shape(
    repo_root: Path, path: Path, data: dict[str, Any], request: dict[str, Any]
) -> list[Violation]:
    payload = request.get("payload")
    if (
        request.get("operation") != "create"
        or not isinstance(payload, dict)
        or payload.get("variant") != "task"
    ):
        return []
    violations: list[Violation] = []
    short_id = str(payload.get("short_id"))
    new_path = f"tasks/{short_id}.md"
    file_fragments = data.get("file_fragments")
    if (
        not isinstance(file_fragments, list)
        or len(file_fragments) != 1
        or not isinstance(file_fragments[0], dict)
        or (file_fragments[0].get("base"), file_fragments[0].get("path"))
        != ("flow_root", new_path)
        or file_fragments[0].get("before") != {"exists": False, "content_utf8_lf": None}
    ):
        violations.append(
            Violation(
                path,
                1,
                "create.task requires exactly one absent-before complete new-task file fragment",
            )
        )
        return violations
    flow_root = _journal_roots(repo_root, data)["flow_root"]
    existing_ids = sorted(item.stem for item in (flow_root / "tasks").glob("*.md"))
    fragments = data.get("fragments") if isinstance(data.get("fragments"), list) else []
    existing_anchor_ids = sorted(
        Path(str(item.get("path"))).stem
        for item in fragments
        if isinstance(item, dict)
        and item.get("anchor") == "frontmatter"
        and str(item.get("path", "")).startswith("tasks/")
        and item.get("path") != new_path
    )
    anchors = {
        str(item.get("anchor"))
        for item in fragments
        if isinstance(item, dict) and item.get("path") == "spec.md"
    }
    required_anchors = {
        "frontmatter",
        f"implementation-plan-chapter-{payload.get('chapter_id')}",
        "continuity-snapshot",
    }
    if existing_anchor_ids != existing_ids or anchors != required_anchors:
        violations.append(
            Violation(
                path,
                1,
                "create.task requires every existing task plan-identity anchor and exact spec anchors",
            )
        )
    expected_paths = [
        *(f"tasks/{item}.md" for item in existing_ids),
        new_path,
        "spec.md",
    ]
    ordered_paths = [
        item.get("path")
        for item in data.get("ordered_writes", [])
        if isinstance(item, dict)
    ]
    if ordered_paths != expected_paths or data.get("ordered_directories") != []:
        violations.append(
            Violation(
                path,
                1,
                "create.task ordered writes must mix tasks by id then spec with no new directories",
            )
        )
    content = file_fragments[0].get("after", {}).get("content_utf8_lf")
    try:
        _, raw_frontmatter, body = str(content).split("---\n", 2)
        frontmatter = yaml.safe_load(raw_frontmatter)
    except (ValueError, yaml.YAMLError):
        frontmatter = None
        body = ""
    required_fields = {
        "type",
        "id",
        "title",
        "state",
        "priority",
        "verification_strategy",
        "depends_on",
        "files",
        "tests",
        "plan_revision",
        "plan_commit",
        "state_revision",
        "claimed_by",
        "claimed_at",
        "blocked_reason",
        "unblock_condition",
        "next_step",
        "last_operation",
        "operation_targets",
        "last_verified_at",
        "last_verified_commit",
        "verification_evidence",
        "created_at",
        "updated_at",
        "commit",
    }
    expected_plan_revision = request.get("expected_plan_revision")
    expected_state_revision = request.get("expected_state_revision")
    expected_values = {
        "type": "Task",
        "id": f"{request.get('flow_id')}:{short_id}",
        "state": "open",
        "priority": payload.get("priority"),
        "verification_strategy": payload.get("verification_strategy"),
        "depends_on": payload.get("depends_on"),
        "files": payload.get("files"),
        "tests": payload.get("tests"),
        "plan_revision": expected_plan_revision + 1
        if isinstance(expected_plan_revision, int)
        else None,
        "plan_commit": None,
        "state_revision": expected_state_revision + 1
        if isinstance(expected_state_revision, int)
        else None,
        "last_operation": data.get("operation_id"),
        "operation_targets": [short_id],
    }
    if (
        not isinstance(frontmatter, dict)
        or not required_fields <= set(frontmatter)
        or any(frontmatter.get(key) != value for key, value in expected_values.items())
        or any(
            f"## {heading}" not in body
            for heading in (*_WORKSHEET_HEADINGS, "Notes & Discoveries")
        )
    ):
        violations.append(
            Violation(
                path,
                1,
                "create.task complete new-task content is incomplete or has wrong effects",
            )
        )
    return violations


def _validate_archive_inventory_live(
    repo_root: Path, path: Path, data: dict[str, Any]
) -> list[Violation]:
    inventory = data.get("archive_inventory")
    if data.get("request", {}).get("operation") != "archive" or not isinstance(
        inventory, dict
    ):
        return []
    root_value = inventory.get("root")
    if inventory.get("base") != "bundle_root" or not isinstance(root_value, str):
        return []
    archive_root = _journal_roots(repo_root, data)["bundle_root"] / root_value
    if not archive_root.exists():
        return []
    recorded_directories = set(map(str, inventory.get("directories", [])))
    recorded_files = set(map(str, inventory.get("files", [])))
    live_directories = {"."}
    live_files: set[str] = set()
    violations: list[Violation] = []
    for child in archive_root.rglob("*"):
        relative = child.relative_to(archive_root).as_posix()
        if child.is_symlink():
            violations.append(
                Violation(
                    path, 1, f"archive inventory live path is a symlink: {relative}"
                )
            )
        elif child.is_dir():
            live_directories.add(relative)
        elif child.is_file():
            live_files.add(relative)
            if child.suffix != ".md":
                violations.append(
                    Violation(
                        path,
                        1,
                        f"archive inventory contains non-Markdown live file: {relative}",
                    )
                )
            else:
                try:
                    child.read_text(encoding="utf-8")
                except (OSError, UnicodeDecodeError):
                    violations.append(
                        Violation(
                            path, 1, f"archive inventory file is not UTF-8: {relative}"
                        )
                    )
        else:
            violations.append(
                Violation(
                    path,
                    1,
                    f"archive inventory contains unsupported live path: {relative}",
                )
            )
    omitted = sorted(
        (live_directories - recorded_directories) | (live_files - recorded_files)
    )
    for relative in omitted:
        violations.append(
            Violation(path, 1, f"archive inventory omits live path: {relative}")
        )
    if not data.get("applied_writes") and (
        live_directories != recorded_directories or live_files != recorded_files
    ):
        violations.append(
            Violation(
                path, 1, "archive inventory does not exactly match the live-before tree"
            )
        )
    return violations


def _directory_assessment(data: dict[str, Any]) -> str:
    ordered = data.get("ordered_directories", [])
    applied = data.get("applied_directories", [])
    rolled = data.get("rolled_back_directories", [])
    if not all(isinstance(item, list) for item in (ordered, applied, rolled)):
        return "hard_conflict"
    expected = [
        (index, item.get("base"), item.get("path"))
        for index, item in enumerate(ordered)
        if isinstance(item, dict)
        and set(item) == {"directory_index", "base", "path"}
        and item.get("directory_index") == index
    ]
    if len(expected) != len(ordered):
        return "hard_conflict"
    attempts: dict[int, int] = {index: 0 for index, _, _ in expected}
    open_start: tuple[int, int, str, str] | None = None
    applied_events: list[tuple[int, int, str, str]] = []
    open_rollback: tuple[int, int, str, str] | None = None
    rolled_events: list[tuple[int, int, str, str]] = []
    for event in data.get("events", [])[1:]:
        if not isinstance(event, dict) or not str(event.get("kind", "")).startswith(
            "directory_"
        ):
            continue
        kind = event.get("kind")
        required = {
            "sequence",
            "kind",
            "at",
            "directory_index",
            "directory_attempt_index",
            "base",
            "path",
        }
        if set(event) != required:
            return "hard_conflict"
        entry = (
            event.get("directory_index"),
            event.get("directory_attempt_index"),
            event.get("base"),
            event.get("path"),
        )
        if (
            not isinstance(entry[0], int)
            or not isinstance(entry[1], int)
            or entry[0] >= len(expected)
        ):
            return "hard_conflict"
        expected_path = expected[cast("int", entry[0])]
        if (entry[0], entry[2], entry[3]) != expected_path:
            return "hard_conflict"
        if kind == "directory_started":
            if (
                open_start is not None
                or entry[1] != attempts[cast("int", entry[0])]
                or any(item[0] == entry[0] for item in applied_events)
            ):
                return "hard_conflict"
            open_start = cast("tuple[int, int, str, str]", entry)
        elif kind == "directory_not_applied":
            if entry != open_start:
                return "hard_conflict"
            attempts[cast("int", entry[0])] += 1
            open_start = None
        elif kind == "directory_applied":
            if entry != open_start:
                return "hard_conflict"
            applied_events.append(cast("tuple[int, int, str, str]", entry))
            open_start = None
        elif kind == "directory_rollback_started":
            if open_rollback is not None or entry not in applied_events:
                return "hard_conflict"
            open_rollback = cast("tuple[int, int, str, str]", entry)
        elif kind == "directory_rollback_applied":
            if entry != open_rollback:
                return "hard_conflict"
            rolled_events.append(cast("tuple[int, int, str, str]", entry))
            open_rollback = None
        else:
            return "hard_conflict"
    parsed_applied = [
        (
            item.get("directory_index"),
            item.get("directory_attempt_index"),
            item.get("base"),
            item.get("path"),
        )
        for item in applied
        if isinstance(item, dict)
        and set(item) == {"directory_index", "directory_attempt_index", "base", "path"}
    ]
    parsed_rolled = [
        (
            item.get("directory_index"),
            item.get("directory_attempt_index"),
            item.get("base"),
            item.get("path"),
        )
        for item in rolled
        if isinstance(item, dict)
        and set(item) == {"directory_index", "directory_attempt_index", "base", "path"}
    ]
    if parsed_applied != applied_events or parsed_rolled != rolled_events:
        return "hard_conflict"
    applied_indices = [item[0] for item in applied_events]
    if applied_indices != list(range(len(applied_indices))):
        return "hard_conflict"
    expected_rollback = list(reversed(applied_events))[: len(rolled_events)]
    if rolled_events != expected_rollback:
        return "hard_conflict"
    if open_rollback is not None:
        next_index = len(rolled_events)
        reverse_applied = list(reversed(applied_events))
        if (
            next_index >= len(reverse_applied)
            or open_rollback != reverse_applied[next_index]
        ):
            return "hard_conflict"
    if open_rollback or rolled_events:
        return "resumable_rollback"
    if applied_events or open_start:
        return "applied"
    return "zero"


def _journal_roots(repo_root: Path, data: dict[str, Any]) -> dict[str, Path]:
    return {
        "repo_root": repo_root.resolve(),
        "configured_root": repo_root.resolve() / str(data.get("configured_root", "")),
        "bundle_root": repo_root.resolve() / str(data.get("bundle_root", "")),
        "flow_root": repo_root.resolve() / str(data.get("flow_root", "")),
    }


def _semantic_value(value: Any) -> Any:
    if isinstance(value, datetime.datetime):
        rendered = value.astimezone(datetime.timezone.utc).isoformat()
        return rendered.replace("+00:00", "Z")
    if isinstance(value, dict):
        return {key: _semantic_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_semantic_value(item) for item in value]
    return value


def _frontmatter_fields(target: Path, fields: dict[str, Any]) -> dict[str, Any] | None:
    data, errors = _parse_yaml_frontmatter(target)
    if data is None or errors:
        return None
    return {key: _semantic_value(data.get(key)) for key in fields}


def _anchor_fields(
    target: Path, anchor: str, fields: dict[str, Any]
) -> dict[str, Any] | None:
    if anchor == "frontmatter":
        return _frontmatter_fields(target, fields)
    if not target.is_file():
        return None
    text = target.read_text(encoding="utf-8")
    if anchor.startswith("implementation-plan-task-"):
        short_id = anchor.removeprefix("implementation-plan-task-")
        match = re.search(
            rf"(?m)^- (\[[ ~x!-]\]) Task {re.escape(short_id)}: [^\n]+?(?: \[([0-9a-f]{{7,40}})\])?$",
            text,
        )
        if not match:
            return None
        return {"checklist_marker": match.group(1), "commit_suffix": match.group(2)}
    if anchor.startswith("implementation-plan-chapter-"):
        chapter_id = anchor.removeprefix("implementation-plan-chapter-")
        heading = next(
            (
                match
                for match in re.finditer(r"(?m)^(#{2,6})\s+(.+?)\s*$", text)
                if re.sub(r"[^a-z0-9]+", "-", match.group(2).lower()).strip("-")
                == chapter_id
            ),
            None,
        )
        if heading is None:
            return None
        level = len(heading.group(1))
        following = re.search(rf"(?m)^#{{2,{level}}}\s+.+$", text[heading.end() :])
        end = heading.end() + following.start() if following else len(text)
        checklist_items = re.findall(
            r"(?m)^- \[[ ~x!-]\] Task [^\n]+$", text[heading.end() : end]
        )
        return {"checklist_items": checklist_items}
    if anchor == "continuity-snapshot":
        sections = _parse_h2_sections(_markdown_body(target))
        claim_text = _snapshot_value(sections, "Current task/claim") or ""
        claim_match = re.search(r"Task `([^`]+)`, claimed by `([^`]+)`", claim_text)
        checkpoint_text = (
            _snapshot_value(sections, "Last verified checkpoint") or ""
        ).strip()
        next_step = _snapshot_value(sections, "Next exact step")
        state_text = _snapshot_value(sections, "State identity") or ""
        revision = re.search(r"revision `(\d+)`", state_text)
        operation = re.search(r"last_operation: ([^`]+)", state_text)
        targets = re.search(r"operation_targets: (\[[^`]*\])", state_text)
        try:
            parsed_targets = json.loads(targets.group(1)) if targets else None
        except json.JSONDecodeError:
            parsed_targets = None
        value = {
            "current_task_claim": (
                {"task": claim_match.group(1), "claimed_by": claim_match.group(2)}
                if claim_match
                else None
            ),
            "last_verified_checkpoint": (
                checkpoint_text.strip("`")
                if checkpoint_text.strip("`").lower() not in {"none", "null"}
                else None
            ),
            "next_exact_step": next_step,
            "state_identity": {
                "revision": int(revision.group(1)) if revision else None,
                "last_operation": operation.group(1) if operation else None,
                "operation_targets": parsed_targets,
            },
        }
        return {key: value.get(key) for key in fields}
    return None


def _live_mutation_images(
    repo_root: Path, data: dict[str, Any]
) -> tuple[
    bool, bool, dict[tuple[str, str, str], Any], dict[tuple[str, str, str], Any]
]:
    """Return stage validity, effective writes, drift values, and after images."""
    roots = _journal_roots(repo_root, data)
    applied = {
        (item.get("base"), item.get("path"))
        for item in data.get("applied_writes", [])
        if isinstance(item, dict)
    }
    rolled = {
        (item.get("base"), item.get("path"))
        for item in data.get("rolled_back_writes", [])
        if isinstance(item, dict)
    }
    open_forward = next(
        (
            (event.get("base"), event.get("path"))
            for event in reversed(data.get("events", []))
            if isinstance(event, dict)
            and event.get("kind") == "write_started"
            and not any(
                isinstance(later, dict)
                and later.get("kind") in {"write_applied", "write_not_applied"}
                and later.get("write_index") == event.get("write_index")
                for later in data.get("events", [])[event.get("sequence", 0) + 1 :]
            )
        ),
        None,
    )
    open_rollback = next(
        (
            (event.get("base"), event.get("path"))
            for event in reversed(data.get("events", []))
            if isinstance(event, dict)
            and event.get("kind") == "rollback_started"
            and not any(
                isinstance(later, dict)
                and later.get("kind") == "rollback_applied"
                and later.get("write_index") == event.get("write_index")
                for later in data.get("events", [])[event.get("sequence", 0) + 1 :]
            )
        ),
        None,
    )
    valid = True
    effective = False
    drift: dict[tuple[str, str, str], Any] = {}
    after_images: dict[tuple[str, str, str], Any] = {}
    for fragment in data.get("fragments", []):
        if not isinstance(fragment, dict):
            valid = False
            continue
        key = (
            str(fragment.get("base")),
            str(fragment.get("path")),
            str(fragment.get("anchor")),
        )
        base_path = roots.get(key[0])
        if base_path is None:
            valid = False
            continue
        live = _anchor_fields(base_path / key[1], key[2], fragment.get("before", {}))
        before = _semantic_value(fragment.get("before"))
        after = _semantic_value(fragment.get("after"))
        after_images[key] = after
        path_key = key[:2]
        expected = before if path_key in rolled or path_key not in applied else after
        if path_key in {open_forward, open_rollback} and (
            live == before or live == after
        ):
            effective |= live == after
        elif live != expected:
            valid = False
            drift[key] = live
        effective |= path_key in applied and path_key not in rolled
    for fragment in data.get("file_fragments", []):
        if not isinstance(fragment, dict):
            valid = False
            continue
        key = (str(fragment.get("base")), str(fragment.get("path")), "complete")
        base_path = roots.get(key[0])
        target = base_path / key[1] if base_path is not None else None
        live = {
            "exists": bool(target and target.is_file()),
            "content_utf8_lf": target.read_text(encoding="utf-8")
            if target and target.is_file()
            else None,
        }
        before = _semantic_value(fragment.get("before"))
        after = _semantic_value(fragment.get("after"))
        after_images[key] = after
        path_key = key[:2]
        expected = before if path_key in rolled or path_key not in applied else after
        if path_key in {open_forward, open_rollback} and (
            live == before or live == after
        ):
            effective |= live == after
        elif live != expected:
            valid = False
            drift[key] = live
        effective |= path_key in applied and path_key not in rolled

    applied_dirs = {
        (item.get("base"), item.get("path"))
        for item in data.get("applied_directories", [])
        if isinstance(item, dict)
    }
    rolled_dirs = {
        (item.get("base"), item.get("path"))
        for item in data.get("rolled_back_directories", [])
        if isinstance(item, dict)
    }
    open_directory_start: tuple[str, str] | None = None
    open_directory_rollback: tuple[str, str] | None = None
    directory_events = [
        event for event in data.get("events", []) if isinstance(event, dict)
    ]
    for event_index, event in enumerate(directory_events):
        if event.get("kind") == "directory_started" and not any(
            later.get("kind") in {"directory_applied", "directory_not_applied"}
            and later.get("directory_index") == event.get("directory_index")
            and later.get("directory_attempt_index")
            == event.get("directory_attempt_index")
            for later in directory_events[event_index + 1 :]
        ):
            open_directory_start = (str(event.get("base")), str(event.get("path")))
        if event.get("kind") == "directory_rollback_started" and not any(
            later.get("kind") == "directory_rollback_applied"
            and later.get("directory_index") == event.get("directory_index")
            and later.get("directory_attempt_index")
            == event.get("directory_attempt_index")
            for later in directory_events[event_index + 1 :]
        ):
            open_directory_rollback = (str(event.get("base")), str(event.get("path")))
    for directory in data.get("ordered_directories", []):
        if not isinstance(directory, dict):
            valid = False
            continue
        path_key = (str(directory.get("base")), str(directory.get("path")))
        base_path = roots.get(path_key[0])
        live = bool(base_path and (base_path / path_key[1]).is_dir())
        expected = path_key in applied_dirs and path_key not in rolled_dirs
        key = (*path_key, "directory")
        after_images[key] = True
        if path_key in {open_directory_start, open_directory_rollback}:
            effective |= live
        elif live != expected:
            valid = False
            drift[key] = live
        effective |= expected
    if applied_dirs:
        recorded_directories = {
            (str(item.get("base")), str(item.get("path")))
            for item in data.get("ordered_directories", [])
            if isinstance(item, dict)
        }
        recorded_files = {
            (str(item.get("base")), str(item.get("path")))
            for item in data.get("file_fragments", [])
            if isinstance(item, dict)
        }
        for base, relative in applied_dirs - rolled_dirs:
            base_path = roots.get(str(base))
            directory = base_path / str(relative) if base_path is not None else None
            if directory is None or not directory.is_dir():
                continue
            for child in directory.rglob("*"):
                child_relative = child.relative_to(base_path).as_posix()
                child_key = (str(base), child_relative)
                if (
                    child.is_symlink()
                    or (child.is_dir() and child_key not in recorded_directories)
                    or (child.is_file() and child_key not in recorded_files)
                ):
                    valid = False
                    drift[(*child_key, "unrecorded_descendant")] = child_relative
    return valid, effective, drift, after_images


def _read_set_matches_live(repo_root: Path, data: dict[str, Any]) -> bool:
    roots = _journal_roots(repo_root, data)
    changed_paths = {
        (roots[str(item.get("base"))] / str(item.get("path"))).resolve(strict=False)
        for item in data.get("applied_writes", [])
        if isinstance(item, dict) and str(item.get("base")) in roots
    }
    changed_directories = {
        (roots[str(item.get("base"))] / str(item.get("path"))).resolve(strict=False)
        for item in data.get("applied_directories", [])
        if isinstance(item, dict) and str(item.get("base")) in roots
    }
    changed_directories.update(
        (roots[str(event.get("base"))] / str(event.get("path"))).resolve(strict=False)
        for event in data.get("events", [])
        if isinstance(event, dict)
        and event.get("kind") == "directory_started"
        and str(event.get("base")) in roots
    )

    def record_path(record: object) -> Path | None:
        if not isinstance(record, dict) or str(record.get("base")) not in roots:
            return None
        return (roots[str(record["base"])] / str(record.get("path", ""))).resolve(
            strict=False
        )

    def task_frontmatters(scope: object) -> list[dict[str, Any]] | None:
        if (
            not isinstance(scope, dict)
            or str(scope.get("base")) not in roots
            or not isinstance(scope.get("glob"), str)
        ):
            return None
        records: list[dict[str, Any]] = []
        for target in sorted(roots[str(scope["base"])].glob(scope["glob"])):
            parsed, errors = _parse_yaml_frontmatter(target)
            if parsed is None or errors:
                return None
            records.append(parsed)
        return records

    for item in data.get("read_set", []):
        if not isinstance(item, dict):
            return False
        item_base = roots.get(str(item.get("base")))
        item_path = (
            (item_base / str(item.get("path"))).resolve(strict=False)
            if item_base is not None and "path" in item
            else None
        )
        if (
            item.get("predicate") is None
            and "fields" in item
            and item_path not in changed_paths
        ):
            base_path = roots.get(str(item.get("base")))
            fields = item.get("fields")
            if (
                base_path is None
                or not isinstance(fields, dict)
                or _frontmatter_fields(base_path / str(item.get("path")), fields)
                != _semantic_value(fields)
            ):
                return False
        if item.get("predicate") in {
            "all_dependencies_closed",
            "dependencies_exist_and_acyclic",
        }:
            observed = item.get("observed_states")
            if not isinstance(observed, dict):
                return False
            for dependency in item.get("dependency_paths", []):
                if not isinstance(dependency, dict):
                    return False
                base_path = roots.get(str(dependency.get("base")))
                parsed = (
                    _frontmatter_fields(
                        base_path / str(dependency.get("path")), {"state": None}
                    )
                    if base_path
                    else None
                )
                short_id = Path(str(dependency.get("path"))).stem
                if parsed is None or parsed.get("state") != observed.get(short_id):
                    return False
        predicate = item.get("predicate")
        if predicate == "no_other_in_progress_claim":
            records = task_frontmatters(item.get("scope"))
            excluding = Path(str(item.get("excluding", {}).get("path", ""))).stem
            observed = sorted(
                str(record.get("id", "")).split(":")[-1]
                for record in records or []
                if record.get("state") == "in_progress"
                and str(record.get("id", "")).split(":")[-1] != excluding
            )
            if records is None or observed != item.get("observed_task_ids"):
                return False
        elif predicate == "sole_current_claim":
            spec_path = record_path(item.get("spec"))
            target_path = record_path(item.get("target"))
            spec = (
                _frontmatter_fields(spec_path, {"current_task": None})
                if spec_path
                else None
            )
            target = (
                _frontmatter_fields(
                    target_path, {"id": None, "state": None, "claimed_by": None}
                )
                if target_path
                else None
            )
            short_id = str(target.get("id", "")).split(":")[-1] if target else None
            if (
                not spec
                or not target
                or target.get("state") != "in_progress"
                or target.get("claimed_by") != item.get("claimant")
                or spec.get("current_task") != short_id
            ):
                return False
        elif predicate == "in_progress_target_is_current":
            spec_path = record_path(item.get("spec"))
            target_path = record_path(item.get("target"))
            spec = (
                _frontmatter_fields(spec_path, {"current_task": None})
                if spec_path
                else None
            )
            target = (
                _frontmatter_fields(target_path, {"id": None, "state": None})
                if target_path
                else None
            )
            short_id = str(target.get("id", "")).split(":")[-1] if target else None
            if (
                target
                and target.get("state") == "in_progress"
                and (not spec or spec.get("current_task") != short_id)
            ):
                return False
        elif predicate == "no_current_claim":
            spec_path = record_path(item.get("spec"))
            spec = (
                _frontmatter_fields(spec_path, {"current_task": None})
                if spec_path
                else None
            )
            records = task_frontmatters(item.get("scope"))
            if (
                not spec
                or spec.get("current_task") is not None
                or records is None
                or any(record.get("state") == "in_progress" for record in records)
            ):
                return False
        elif predicate == "all_tasks_terminal_no_blockers":
            records = task_frontmatters(item.get("scope"))
            observed = {
                str(record.get("id", "")).split(":")[-1]: record.get("state")
                for record in records or []
            }
            if (
                records is None
                or any(
                    state not in {"closed", "skipped"} for state in observed.values()
                )
                or observed != item.get("observed_states")
            ):
                return False
        elif predicate in {"flow_absent", "target_absent"}:
            target = record_path(item.get("target"))
            if target is None or (
                target.exists()
                and target not in changed_paths
                and target not in changed_directories
            ):
                return False
    return True


def _local_journal_assessment(data: dict[str, Any]) -> str:
    events = data.get("events")
    ordered = data.get("ordered_writes")
    applied_raw = data.get("applied_writes")
    rolled_raw = data.get("rolled_back_writes")
    directory_status = _directory_assessment(data)
    if directory_status == "hard_conflict":
        return "hard_conflict"
    if not all(
        isinstance(item, list) for item in (events, ordered, applied_raw, rolled_raw)
    ):
        return "hard_conflict"
    if not events or events[0].get("kind") != "prepared":
        return "hard_conflict"
    if [event.get("sequence") for event in events] != list(range(len(events))):
        return "hard_conflict"

    expected_entries = [
        (index, item.get("base"), item.get("path"))
        for index, item in enumerate(ordered)
        if isinstance(item, dict)
    ]
    if len(expected_entries) != len(ordered):
        return "hard_conflict"
    applied = [_entry_tuple(item) for item in applied_raw]
    rolled = [_entry_tuple(item) for item in rolled_raw]
    if any(item is None for item in applied + rolled):
        return "hard_conflict"
    applied_entries = cast("list[tuple[int, str, str]]", applied)
    rolled_entries = cast("list[tuple[int, str, str]]", rolled)
    if (
        len(set(applied_entries)) != len(applied_entries)
        or applied_entries != expected_entries[: len(applied_entries)]
    ):
        return "hard_conflict"
    if (
        len(set(rolled_entries)) != len(rolled_entries)
        or rolled_entries != list(reversed(applied_entries))[: len(rolled_entries)]
    ):
        return "hard_conflict"

    open_forward: tuple[int, str, str] | None = None
    aborted: set[int] = set()
    confirmed_applied: list[tuple[int, str, str]] = []
    open_rollback: tuple[int, str, str] | None = None
    confirmed_rolled: list[tuple[int, str, str]] = []
    selected: str | None = None
    contended = False
    for event in events[1:]:
        kind = event.get("kind")
        entry = _entry_tuple(event)
        if kind == "write_started":
            if selected == "rollback" or open_forward is not None or entry is None:
                return "hard_conflict"
            if entry not in expected_entries:
                return "hard_conflict"
            index = entry[0]
            if entry in confirmed_applied or (
                index in aborted and selected != "finish"
            ):
                return "hard_conflict"
            open_forward = entry
        elif kind == "write_not_applied":
            if entry is None or entry != open_forward:
                return "hard_conflict"
            aborted.add(entry[0])
            open_forward = None
        elif kind == "write_applied":
            if entry is None or entry != open_forward:
                return "hard_conflict"
            confirmed_applied.append(entry)
            open_forward = None
        elif kind == "recovery_selected":
            action = event.get("action")
            if action not in {"finish", "rollback"} or open_forward is not None:
                return "hard_conflict"
            if selected is not None and selected != action:
                return "hard_conflict"
            if selected is not None:
                return "hard_conflict"
            selected = cast("str", action)
        elif kind == "rollback_started":
            if (
                selected != "rollback"
                or open_forward is not None
                or open_rollback is not None
                or entry is None
            ):
                return "hard_conflict"
            expected_reverse = list(reversed(confirmed_applied))
            if (
                len(confirmed_rolled) >= len(expected_reverse)
                or entry != expected_reverse[len(confirmed_rolled)]
            ):
                return "hard_conflict"
            open_rollback = entry
        elif kind == "rollback_applied":
            if entry is None or entry != open_rollback:
                return "hard_conflict"
            confirmed_rolled.append(entry)
            open_rollback = None
        elif kind == "contended_before_write":
            if confirmed_applied or open_forward is not None or selected is not None:
                return "hard_conflict"
            contended = True
        elif kind in {
            "validation_recorded",
            "rollback_validated",
            "validation_invalidated",
        }:
            continue
        elif isinstance(kind, str) and kind.startswith("directory_"):
            continue
        else:
            return "hard_conflict"

    if confirmed_applied != applied_entries or confirmed_rolled != rolled_entries:
        return "hard_conflict"
    if selected == "rollback" or directory_status == "resumable_rollback":
        return "resumable_rollback"
    if selected == "finish":
        return "finishable"
    if open_rollback is not None:
        return "resumable_rollback"
    if confirmed_applied or open_forward is not None or directory_status == "applied":
        return "applied"
    if contended:
        return "proven_zero"
    return "zero"


def validate_markdown_transactions(repo_root: Path = REPO_ROOT) -> list[Violation]:
    """Validate journal roots, namespaced paths, and append-only provenance."""
    violations: list[Violation] = []
    try:
        layout = resolve_okf_layout(repo_root)
    except ValueError as exc:
        return [Violation(repo_root / ".agents" / "setup-state.json", 1, str(exc))]
    configured_rel = str(layout.configured_root.relative_to(repo_root.resolve()))
    bundle_rel = str(layout.bundle_root.relative_to(repo_root.resolve()))
    journal_records: list[tuple[Path, dict[str, Any]]] = []
    for path in _iter_transaction_journals(repo_root):
        data, errors = _journal_data(path)
        violations.extend(errors)
        if data is None:
            continue
        journal_records.append((path, data))
        if data.get("type") != "FlowTransaction" or data.get("version") != 1:
            violations.append(
                Violation(path, 1, "journal type/version must be FlowTransaction/1")
            )
        request_value = data.get("request")
        operation = (
            request_value.get("operation") if isinstance(request_value, dict) else None
        )
        allowed_keys = set(_JOURNAL_BASE_KEYS)
        required_keys = set(_JOURNAL_BASE_KEYS)
        if operation == "archive":
            extras = {"target_state_revision", "archive_inventory", "file_fragments"}
            allowed_keys.update(extras)
            required_keys.update(extras)
        elif operation == "create":
            extras = {
                "ordered_directories",
                "applied_directories",
                "rolled_back_directories",
                "file_fragments",
            }
            allowed_keys.update(extras)
            required_keys.update(extras)
        elif (
            operation == "checkpoint"
            and isinstance(request_value, dict)
            and isinstance(request_value.get("payload"), dict)
            and request_value["payload"].get("scope") == "plan"
        ):
            allowed_keys.add("file_fragments")
            required_keys.add("file_fragments")
        missing_keys = required_keys - set(data)
        unknown_keys = set(data) - allowed_keys
        if missing_keys:
            violations.append(
                Violation(
                    path,
                    1,
                    f"journal missing exact top-level keys: {sorted(missing_keys)}",
                )
            )
        if unknown_keys:
            violations.append(
                Violation(
                    path,
                    1,
                    f"journal has unknown top-level keys: {sorted(unknown_keys)}",
                )
            )
        if data.get("state") not in _JOURNAL_NONTERMINAL_STATES | {
            "committed",
            "rolled_back",
            "superseded",
        }:
            violations.append(
                Violation(path, 1, f"journal has invalid state: {data.get('state')!r}")
            )
        if path.parent.name != data.get("operation_id"):
            violations.append(
                Violation(
                    path, 1, "journal operation_id must match transaction directory"
                )
            )
        if data.get("configured_root") != configured_rel:
            violations.append(
                Violation(
                    path, 1, "journal configured_root disagrees with resolved layout"
                )
            )
        if data.get("bundle_root") != bundle_rel:
            violations.append(
                Violation(path, 1, "journal bundle_root disagrees with resolved layout")
            )
        expected_flow = f"{bundle_rel}/specs/{data.get('flow_id')}"
        if data.get("flow_root") != expected_flow:
            violations.append(
                Violation(path, 1, "journal flow_root disagrees with flow/layout")
            )
        roots = {
            "repo_root": repo_root.resolve(),
            "configured_root": layout.configured_root,
            "bundle_root": layout.bundle_root,
            "flow_root": repo_root.resolve() / expected_flow,
        }
        request = data.get("request")
        if not isinstance(request, dict) or request.get("flow_id") != data.get(
            "flow_id"
        ):
            violations.append(
                Violation(
                    path, 1, "journal request must be a typed matching flow request"
                )
            )
        elif set(request) != _REQUEST_KEYS:
            violations.append(
                Violation(
                    path, 1, "journal request must use the exact typed request keyset"
                )
            )
        elif not _validate_iso_timestamp(request.get("occurred_at")):
            violations.append(
                Violation(path, 1, "journal request occurred_at must be ISO-8601")
            )
        if isinstance(request, dict):
            violations.extend(_validate_journal_semantics(path, data, request))
            violations.extend(_validate_plan_bind_payload(path, data, request))
            violations.extend(_validate_create_flow_shape(path, data, request))
            violations.extend(
                _validate_create_task_shape(repo_root, path, data, request)
            )
        violations.extend(_validate_terminal_events(path, data))
        if data.get("state") in {"committed", "rolled_back"}:
            try:
                live_valid, _, _, _ = _live_mutation_images(repo_root, data)
            except (OSError, UnicodeDecodeError, ValueError):
                live_valid = False
            if not live_valid:
                violations.append(
                    Violation(
                        path,
                        1,
                        f"terminal live image does not match recorded {'after' if data.get('state') == 'committed' else 'before'} fragments",
                    )
                )
            if not _read_set_matches_live(repo_root, data):
                violations.append(
                    Violation(
                        path,
                        1,
                        "terminal semantic read_set no longer matches dependency/claim predicates",
                    )
                )
        if operation == "archive":
            inventory = data.get("archive_inventory")
            if not isinstance(inventory, dict):
                violations.append(
                    Violation(path, 1, "archive journal requires archive_inventory")
                )
            else:
                files = inventory.get("files")
                directories = inventory.get("directories")
                if not isinstance(files, list) or files != sorted(set(map(str, files))):
                    violations.append(
                        Violation(
                            path,
                            1,
                            "archive inventory files must be unique and sorted",
                        )
                    )
                if not isinstance(directories, list) or len(directories) != len(
                    set(map(str, directories))
                ):
                    violations.append(
                        Violation(
                            path, 1, "archive inventory directories must be unique"
                        )
                    )
                if isinstance(files, list) and isinstance(inventory.get("root"), str):
                    expected_archived = {
                        ("bundle_root", f"{inventory['root'].rstrip('/')}/{item}")
                        for item in files
                    }
                    recorded_files = {
                        (item.get("base"), item.get("path"))
                        for item in data.get("file_fragments", [])
                        if isinstance(item, dict)
                    }
                    if not expected_archived <= recorded_files:
                        violations.append(
                            Violation(
                                path,
                                1,
                                "archive inventory files require matching complete file_fragments",
                            )
                        )
            violations.extend(_validate_archive_inventory_live(repo_root, path, data))
        file_fragments = data.get("file_fragments", [])
        if not isinstance(file_fragments, list):
            violations.append(
                Violation(path, 1, "journal file_fragments must be a list")
            )
        else:
            for index, fragment in enumerate(file_fragments):
                exact = isinstance(fragment, dict) and set(fragment) == {
                    "base",
                    "path",
                    "before",
                    "after",
                }
                before = fragment.get("before") if isinstance(fragment, dict) else None
                after = fragment.get("after") if isinstance(fragment, dict) else None
                if not exact or not all(
                    isinstance(image, dict)
                    and set(image) == {"exists", "content_utf8_lf"}
                    for image in (before, after)
                ):
                    violations.append(
                        Violation(
                            path,
                            1,
                            f"file_fragments[{index}] has invalid exact complete-file schema",
                        )
                    )
                    continue
                for image_name, image in (("before", before), ("after", after)):
                    exists = image.get("exists")
                    content = image.get("content_utf8_lf")
                    if (
                        not isinstance(exists, bool)
                        or (exists and not isinstance(content, str))
                        or (not exists and content is not None)
                        or (isinstance(content, str) and "\r" in content)
                    ):
                        violations.append(
                            Violation(
                                path,
                                1,
                                f"file_fragments[{index}].{image_name} is not an exact UTF-8/LF image",
                            )
                        )
                if operation == "create" and (
                    before != {"exists": False, "content_utf8_lf": None}
                    or after.get("exists") is not True
                ):
                    violations.append(
                        Violation(
                            path,
                            1,
                            f"create file_fragments[{index}] must be absent before and complete after",
                        )
                    )
        if operation == "create":
            if not file_fragments:
                violations.append(
                    Violation(
                        path, 1, "create journal requires non-empty file_fragments"
                    )
                )
            elif (
                isinstance(data.get("ordered_writes"), list)
                and isinstance(request, dict)
                and request.get("payload", {}).get("variant") == "flow"
            ):
                fragment_paths = [
                    (item.get("base"), item.get("path"))
                    for item in file_fragments
                    if isinstance(item, dict)
                ]
                ordered_paths = [
                    (item.get("base"), item.get("path"))
                    for item in data["ordered_writes"]
                    if isinstance(item, dict)
                ]
                if fragment_paths != ordered_paths:
                    violations.append(
                        Violation(
                            path,
                            1,
                            "create.flow ordered_writes and file_fragments must agree exactly",
                        )
                    )
        if operation in {"archive"} or (
            operation == "checkpoint"
            and isinstance(request, dict)
            and isinstance(request.get("payload"), dict)
            and request["payload"].get("scope") == "plan"
        ):
            fragment_paths = [
                (item.get("base"), item.get("path"))
                for item in file_fragments
                if isinstance(item, dict)
            ]
            ordered_paths = [
                (item.get("base"), item.get("path"))
                for item in data.get("ordered_writes", [])
                if isinstance(item, dict)
            ]
            if fragment_paths != ordered_paths:
                violations.append(
                    Violation(
                        path,
                        1,
                        "complete file_fragments must agree with ordered_writes",
                    )
                )
        for trail, record in _walk_path_records(data):
            violations.extend(_validate_path_record(path, trail, record, roots))
        if _local_journal_assessment(data) == "hard_conflict":
            violations.append(
                Violation(path, 1, "journal event/write provenance is a hard conflict")
            )
    unresolved = {
        str(data.get("operation_id"))
        for _, data in journal_records
        if data.get("state") in _JOURNAL_NONTERMINAL_STATES
    }
    for path, data in journal_records:
        if data.get("state") not in _JOURNAL_NONTERMINAL_STATES:
            continue
        operation_id = str(data.get("operation_id"))
        events = data.get("events")
        prepared = (
            events[0]
            if isinstance(events, list) and events and isinstance(events[0], dict)
            else {}
        )
        observed = prepared.get("observed_nonterminal_operation_ids")
        transaction = next(
            (
                item
                for item in data.get("read_set", [])
                if isinstance(item, dict)
                and item.get("predicate") == "no_other_unresolved_journal"
            ),
            {},
        )
        valid_observed = (
            isinstance(observed, list)
            and observed == sorted(set(map(str, observed)))
            and operation_id not in observed
            and set(observed) <= unresolved
            and transaction.get("observed_operation_ids") == observed
        )
        if not valid_observed:
            violations.append(
                Violation(
                    path,
                    1,
                    "prepared observation must be a complete internally consistent sorted set of observed nonterminal journal ids",
                )
            )
    if len(unresolved) == 1:
        for path, data in journal_records:
            if data.get(
                "state"
            ) in _JOURNAL_NONTERMINAL_STATES and not _read_set_matches_live(
                repo_root, data
            ):
                violations.append(
                    Violation(
                        path,
                        1,
                        "journal read predicate values do not match the stage-aware live tree",
                    )
                )
    for path, data in journal_records:
        if data.get("state") not in {"committed", "rolled_back"}:
            continue
        events = data.get("events", [])
        validated_at = (
            events[-1].get("at") if events and isinstance(events[-1], dict) else None
        )
        contenders = sorted(
            str(other.get("operation_id"))
            for _, other in journal_records
            if other.get("state") in _JOURNAL_NONTERMINAL_STATES
            and isinstance(validated_at, str)
            and str(other.get("request", {}).get("occurred_at", "")) <= validated_at
        )
        if contenders:
            violations.append(
                Violation(
                    path,
                    1,
                    f"terminal transaction arbitration was invalidated by contenders: {contenders}",
                )
            )
    return violations


def assess_markdown_transactions(repo_root: Path = REPO_ROOT) -> dict[str, str]:
    """Jointly classify unresolved Markdown journals without choosing by scan order."""
    records: list[
        tuple[
            Path,
            dict[str, Any],
            str,
            dict[tuple[str, str, str], Any],
            dict[tuple[str, str, str], Any],
        ]
    ] = []
    invalid_paths = {
        violation.path for violation in validate_markdown_transactions(repo_root)
    }
    for path in _iter_transaction_journals(repo_root):
        data, errors = _journal_data(path)
        if data is None or errors:
            continue
        state = data.get("state")
        if state not in _JOURNAL_NONTERMINAL_STATES:
            continue
        local = "hard_conflict" if path in invalid_paths else _local_journal_assessment(data)
        drift: dict[tuple[str, str, str], Any] = {}
        after_images: dict[tuple[str, str, str], Any] = {}
        deleted_archive = (
            data.get("request", {}).get("operation") == "archive"
            and not (repo_root / str(data.get("flow_root"))).exists()
        )
        if local != "hard_conflict":
            live_valid, _, drift, after_images = _live_mutation_images(repo_root, data)
            read_valid = _read_set_matches_live(repo_root, data)
            if not live_valid or not read_valid:
                if local in {"zero", "proven_zero"} and drift:
                    local = "zero_drift"
                else:
                    local = "hard_conflict"
        if deleted_archive and local in {"applied", "finishable"}:
            local = "deleted_archive"
        records.append((path, data, local, drift, after_images))
    if not records:
        return {}
    if any(local == "hard_conflict" for _, _, local, _, _ in records):
        return {
            str(data.get("operation_id")): "hard_conflict" for _, data, _, _, _ in records
        }
    nonzero = [item for item in records if item[2] not in {"zero", "proven_zero", "zero_drift"}]
    if len(nonzero) > 1:
        return {
            str(data.get("operation_id")): "hard_conflict" for _, data, _, _, _ in records
        }
    results: dict[str, str] = {}
    if not nonzero:
        if any(local == "zero_drift" for _, _, local, _, _ in records):
            return {
                str(data.get("operation_id")): "hard_conflict"
                for _, data, _, _, _ in records
            }
        outcome = "superseded_proven_zero" if len(records) > 1 else "finishable"
        return {str(data.get("operation_id")): outcome for _, data, _, _, _ in records}
    candidate = nonzero[0]
    candidate_after = candidate[4]
    for _, data, local, drift, _ in records:
        operation_id = str(data.get("operation_id"))
        if data is candidate[1]:
            results[operation_id] = {
                "applied": "sole_recovery_candidate",
                "finishable": "finishable",
                "resumable_rollback": "resumable_rollback",
                "deleted_archive": "recoverable_deleted_archive",
            }[local]
        elif local == "zero_drift" and not all(
            key in candidate_after and candidate_after[key] == live
            for key, live in drift.items()
        ):
            return {
                str(item[1].get("operation_id")): "hard_conflict" for item in records
            }
        else:
            results[operation_id] = "superseded_proven_zero"
    return results


def main() -> int:
    all_violations: list[Violation] = []
    skills = list(iter_skills())
    commands = list(iter_commands())
    antigravity_agents = list(iter_antigravity_agents())
    opencode_agents = list(iter_opencode_agents())
    claude_agents = list(iter_claude_agents())
    codex_agents = list(iter_codex_agents())
    vscode_agents = list(iter_vscode_agents())
    manifests = list(iter_manifests())
    claude_hook_configs = list(iter_claude_hook_configs())
    antigravity_hook_configs = list(iter_antigravity_hook_configs())
    
    for manifest_path in manifests:
        all_violations.extend(validate_manifest(manifest_path))
    for skill_path in skills:
        all_violations.extend(validate_skill(skill_path))
    for cmd_path in commands:
        all_violations.extend(validate_command(cmd_path))
        all_violations.extend(validate_command_agent_references(cmd_path))
    for agent_path in antigravity_agents:
        all_violations.extend(validate_antigravity_agent(agent_path))
    for agent_path in opencode_agents:
        all_violations.extend(validate_opencode_agent(agent_path))
    for agent_path in claude_agents:
        all_violations.extend(validate_claude_agent(agent_path))
    for agent_path in codex_agents:
        all_violations.extend(validate_codex_agent(agent_path))
    for agent_path in vscode_agents:
        all_violations.extend(validate_vscode_agent(agent_path))
    for hook_config_path in claude_hook_configs:
        all_violations.extend(validate_claude_hook_config(hook_config_path))
    for hook_config_path in antigravity_hook_configs:
        all_violations.extend(validate_antigravity_hook_config(hook_config_path))
        
    shipped = list(iter_all_shipped_files())
    all_violations.extend(check_agents_leak(shipped))
    all_violations.extend(check_forbidden_vocab(shipped))
    
    # Antigravity specific manifests
    all_violations.extend(validate_antigravity_plugin_manifest(REPO_ROOT))
    all_violations.extend(validate_antigravity_hook_commands(REPO_ROOT))
    
    # Claude CLI validation
    all_violations.extend(validate_claude_manifests_with_cli(REPO_ROOT))
    
    # Codex validation
    for path in discover_codex_marketplaces(REPO_ROOT):
        all_violations.extend(validate_codex_marketplace(path, REPO_ROOT))
    for path in discover_codex_plugin_manifests(REPO_ROOT):
        all_violations.extend(validate_codex_plugin_manifest(path))
    all_violations.extend(validate_codex_package_layout(REPO_ROOT))
    all_violations.extend(validate_codex_hook_commands(REPO_ROOT))
    
    # Repository-local .agents/ is ignored working state, not a shipped fixture.
    # Validate committed OKF scenarios so maintainer checks stay deterministic.
    okf_fixtures = REPO_ROOT / "tests" / "fixtures" / "okf"
    if okf_fixtures.is_dir():
        for fixture_root in sorted(path for path in okf_fixtures.iterdir() if path.is_dir()):
            all_violations.extend(validate_okf_bundle_root(fixture_root))
            for bundle_path in iter_okf_bundles(fixture_root):
                all_violations.extend(validate_okf_bundle(bundle_path, fixture_root))
            all_violations.extend(validate_markdown_transactions(fixture_root))
    all_violations.extend(
        validate_installed_runtime_dependencies(
            REPO_ROOT, transition_allowlist=_RUNTIME_TRANSITION_ALLOWLIST
        )
    )
        
    if all_violations:
        _print_violations(all_violations)
        print(f"\n{len(all_violations)} violation(s)", file=sys.stderr)
        return 1
        
    agent_total = len(antigravity_agents) + len(opencode_agents) + len(claude_agents) + len(codex_agents) + len(vscode_agents)
    print(f"[ OK ] validated {len(skills)} skills, {len(commands)} commands, {agent_total} agents, and all harness manifests — no violations")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

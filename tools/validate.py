"""Validate shipped skills / commands / agents manifest integrity.

Consolidated validator for all harnesses (Antigravity, Claude Code, Codex, etc.).
"""

from __future__ import annotations

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


def validate_antigravity_hook_config(path: Path) -> list[Violation]:
    """Validate Antigravity's root hook config file."""
    hook_events, violations = _load_hook_event_map(path)
    if hook_events is None:
        return violations

    violations.extend(_validate_hook_event_map(
        path,
        hook_events,
        allow_flat_events={"SessionStart", "PreInvocation", "PostInvocation", "Stop"}
    ))
    saw_root_token = False
    for entry in _iter_nested_strings(hook_events):
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
    if not isinstance(data.get("hooks"), dict):
        return [Violation(path, 1, "top-level 'hooks' record missing")]

    commands = list(_iter_hook_commands(data))
    if not commands:
        return [Violation(path, 1, "no SessionStart command hooks found")]

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


def iter_okf_bundles(repo_root: Path = REPO_ROOT) -> Iterator[Path]:
    specs_dir = repo_root / ".agents" / "bundles" / "specs"
    if not specs_dir.is_dir():
        return
    for path in specs_dir.iterdir():
        if path.is_dir() and (path / "spec.md").is_file():
            yield path


def _validate_iso_timestamp(timestamp: str) -> bool:
    pattern = re.compile(
        r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?$"
    )
    return bool(pattern.match(timestamp))


def _parse_yaml_frontmatter(path: Path) -> tuple[dict[str, Any] | None, list[Violation]]:
    if not path.is_file():
        return None, [Violation(path, None, f"File does not exist: {path}")]
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as e:
        return None, [Violation(path, None, f"Failed to read file: {e}")]

    if not content.startswith("---\n"):
        return None, [Violation(path, 1, "Missing opening frontmatter delimiter '---'")]
    parts = content.split("---\n", 2)
    if len(parts) < 3:
        return None, [Violation(path, 1, "Missing closing frontmatter delimiter '---'")]
    yaml_block = parts[1]
    try:
        data = yaml.safe_load(yaml_block)
    except yaml.YAMLError as e:
        return None, [Violation(path, 2, f"Failed to parse YAML frontmatter: {e}")]
    if not isinstance(data, dict):
        return None, [Violation(path, 2, "YAML frontmatter must be an object/dictionary")]
    return data, []


def _validate_markdown_links(path: Path, repo_root: Path, *, strict: bool = True) -> list[Violation]:
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
                violations.append(Violation(path, line_num, f"relative link '{url}' escapes repository root"))
                continue
            if strict and not resolved.exists():
                violations.append(Violation(path, line_num, f"relative link target does not exist: '{url}'"))
    return violations


def validate_okf_bundle(bundle_path: Path, repo_root: Path = REPO_ROOT) -> list[Violation]:
    violations: list[Violation] = []
    spec_path = bundle_path / "spec.md"
    if not spec_path.is_file():
        return [Violation(bundle_path, None, f"Spec file spec.md is missing in bundle: {_rel(bundle_path)}")]

    spec_data, spec_errs = _parse_yaml_frontmatter(spec_path)
    violations.extend(spec_errs)
    
    spec_parsed_ok = False
    spec_task_short_ids = set()
    if spec_path.is_file():
        try:
            content = spec_path.read_text(encoding="utf-8")
            parts = content.split("---\n", 2)
            body = parts[2] if len(parts) >= 3 else content
            pattern = re.compile(r"^\s*-\s*\[([ ~x!-])\]\s*Task\s+([a-zA-Z0-9._-]+)\s*:", re.MULTILINE)
            spec_task_short_ids = {m.group(2) for m in pattern.finditer(body)}
            spec_parsed_ok = True
        except OSError:
            pass

    spec_status = spec_data.get("status", "planned") if spec_data else "planned"
    is_spec_closed = spec_status in ("completed", "archived")
    violations.extend(_validate_markdown_links(spec_path, repo_root, strict=is_spec_closed))
    
    if spec_data is not None:
        required_fields = {"flow_id", "type", "status", "created_at", "updated_at", "description"}
        for f in required_fields:
            if f not in spec_data or spec_data[f] is None:
                violations.append(Violation(spec_path, 1, f"spec.md missing required field: '{f}'"))
            elif f in ("created_at", "updated_at"):
                val = str(spec_data[f])
                if not _validate_iso_timestamp(val):
                    violations.append(Violation(spec_path, 1, f"spec.md field '{f}' must be a valid ISO-8601 timestamp (got '{val}')"))

        if "type" in spec_data and spec_data["type"] not in ("prd", "saga", "flow", "feature", "bug", "refactor", "task"):
            violations.append(Violation(spec_path, 1, f"spec.md field 'type' has invalid value: '{spec_data['type']}'"))
        if "status" in spec_data and spec_data["status"] not in ("planned", "active", "completed", "archived"):
            violations.append(Violation(spec_path, 1, f"spec.md field 'status' has invalid value: '{spec_data['status']}'"))
        if "flow_id" in spec_data and spec_data["flow_id"] != bundle_path.name:
            violations.append(Violation(spec_path, 1, f"spec.md flow_id '{spec_data['flow_id']}' does not match directory name '{bundle_path.name}'"))

    tasks_dir = bundle_path / "tasks"
    if tasks_dir.is_dir():
        for task_file in tasks_dir.glob("*.md"):
            task_data, task_errs = _parse_yaml_frontmatter(task_file)
            violations.extend(task_errs)
            
            # Check for orphaned task file
            short_id = task_file.stem
            if spec_parsed_ok and short_id not in spec_task_short_ids:
                violations.append(Violation(task_file, None, f"orphaned task file: no corresponding 'Task {short_id}' found in spec.md implementation plan"))
            
            task_status = task_data.get("status", "open") if task_data else "open"
            violations.extend(_validate_markdown_links(task_file, repo_root, strict=(task_status == "closed")))
            
            if task_data is not None:
                required_task_fields = {"id", "status", "depends_on", "files", "tests", "created_at", "updated_at"}
                for f in required_task_fields:
                    if f not in task_data or task_data[f] is None:
                        violations.append(Violation(task_file, 1, f"task missing required field: '{f}'"))
                    elif f in ("created_at", "updated_at"):
                        val = str(task_data[f])
                        if not _validate_iso_timestamp(val):
                            violations.append(Violation(task_file, 1, f"task field '{f}' must be a valid ISO-8601 timestamp (got '{val}')"))

                if "status" in task_data and task_data["status"] not in ("open", "in_progress", "closed", "blocked", "skipped"):
                    violations.append(Violation(task_file, 1, f"task field 'status' has invalid value: '{task_data['status']}'"))

                if "depends_on" in task_data and not isinstance(task_data["depends_on"], list):
                    violations.append(Violation(task_file, 1, "task field 'depends_on' must be a list"))

                if spec_data and "flow_id" in spec_data:
                    flow_id = spec_data["flow_id"]
                    task_id = str(task_data.get("id", ""))
                    if not task_id.startswith(f"{flow_id}:"):
                        violations.append(Violation(task_file, 1, f"task ID prefix '{task_id.split(':')[0] if ':' in task_id else task_id}' must match flow_id '{flow_id}'"))

                for list_field in ("files", "tests"):
                    if list_field in task_data:
                        items = task_data[list_field]
                        if not isinstance(items, list):
                            violations.append(Violation(task_file, 1, f"task field '{list_field}' must be a list"))
                        else:
                            for item in items:
                                if not isinstance(item, str):
                                    violations.append(Violation(task_file, 1, f"task field '{list_field}' item must be a string path"))
                                    continue
                                resolved = (repo_root / item).resolve()
                                try:
                                    resolved.relative_to(repo_root.resolve())
                                except ValueError:
                                    violations.append(Violation(task_file, 1, f"referenced file '{item}' escapes repository root"))
                                    continue
                                if not resolved.exists() and task_status == "closed":
                                    violations.append(Violation(task_file, 1, f"referenced file does not exist: '{item}'"))
    return violations


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
    
    # OKF Bundle validation
    for bundle_path in iter_okf_bundles(REPO_ROOT):
        all_violations.extend(validate_okf_bundle(bundle_path, REPO_ROOT))
        
    if all_violations:
        _print_violations(all_violations)
        print(f"\n{len(all_violations)} violation(s)", file=sys.stderr)
        return 1
        
    agent_total = len(antigravity_agents) + len(opencode_agents) + len(claude_agents) + len(codex_agents) + len(vscode_agents)
    print(f"[ OK ] validated {len(skills)} skills, {len(commands)} commands, {agent_total} agents, and all harness manifests — no violations")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Validate shipped skills / commands / agents manifest integrity.

Walks every shipped SKILL.md, command TOML, and agent Markdown file and
enforces:

* YAML frontmatter present, with ``name`` (matching parent dir / filename) and
  ``description`` (<= 1024 characters).
* SKILL.md body contains the four required sections (``workflow``,
  ``guardrails``, ``validation``, ``example``) — present either as
  ``<workflow>`` / ``<guardrails>`` / ``<validation>`` / ``<example>`` XML tags
  *or* as H2 Markdown headings (``## Workflow`` etc., case-insensitive).
* Every ``[text](./path)`` or ``[text](relative/path.md)`` link in a SKILL.md
  resolves relative to the file.
* ``commands/**/*.toml`` parses as TOML and has top-level ``description`` (str,
  <= 1024 chars) and ``prompt`` (non-empty str).
* ``agents/*.md`` frontmatter has ``name`` matching filename, ``description``
  (<= 1024 chars), ``mode`` in {subagent, primary}, and ``tools`` mapping with
  whitelisted keys and bool values.
* Shipped content (skills, commands, agents, and the root ``AGENTS.md`` /
  ``CONTRIBUTING.md`` / ``README.md`` / ``GEMINI.md``) contains no references
  to the framework authoring tree — except the user-install convention path
  (``skills/`` sub-path of the authoring directory), which is whitelisted.

Exit 0 on clean; exit 1 with a per-file violation list otherwise.
"""

import json
import re
import sys
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any, NamedTuple, cast

if sys.version_info >= (3, 11):
    import tomllib as _tomllib
else:  # pragma: no cover - py310 fallback path
    import tomli as _tomllib  # type: ignore[import-not-found,unused-ignore]

import yaml

# The tomllib / tomli shim yields a dict whose keys are strings; the stdlib
# function returns ``dict[str, Any]`` but the py310 fallback lives in a third-
# party package without stubs, so we wrap the callables in ``Any``-typed
# aliases to keep pyright/mypy strict mode happy across both code paths.
_toml_loads_any: Any = _tomllib.loads  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]


def _toml_loads(text: str) -> dict[str, Any]:
    """Parse a TOML string into a dict, tolerant of py310 ``tomli`` fallback."""
    return cast("dict[str, Any]", _toml_loads_any(text))


_TOMLDecodeError: type[Exception] = cast(
    "type[Exception]",
    _tomllib.TOMLDecodeError,  # pyright: ignore[reportUnknownMemberType]
)

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = REPO_ROOT / "skills"
COMMANDS_DIR = REPO_ROOT / "commands"
# `agents/` at repo root is Gemini CLI's extension subagents directory.
# `.opencode/agents/` is OpenCode's project-scoped subagents directory.
# `.claude-plugin/agents/` is Claude Code's plugin subagents directory.
# All three hosts use incompatible frontmatter schemas, so each location is
# validated by its own rules (see `validate_gemini_agent` /
# `validate_opencode_agent` / `validate_claude_agent`).
AGENTS_DIR = REPO_ROOT / "agents"
OPENCODE_AGENTS_DIR = REPO_ROOT / ".opencode" / "agents"
CLAUDE_AGENTS_DIR = REPO_ROOT / ".claude-plugin" / "agents"
CODEX_AGENTS_DIR = REPO_ROOT / ".codex" / "agents"
SHIPPED_ROOT_FILES = ("AGENTS.md", "CONTRIBUTING.md", "README.md", "GEMINI.md")

MAX_DESCRIPTION_CHARS = 1024

REQUIRED_SECTIONS = ("workflow", "guardrails", "validation", "example")

# Match `<tag>` for each required section.
_XML_TAG_PATTERNS = {name: re.compile(rf"<{name}\b", re.IGNORECASE) for name in REQUIRED_SECTIONS}
# Match `## Heading` lines for each required section. Accepts any H2 that
# *mentions* the section name as a word ("## Example", "## End-to-End Example",
# "## Validation Checkpoint", "## Canonical Example", etc.) — singular or
# plural. This is intentionally lenient so existing skill docs with slightly
# different heading conventions are still considered structurally compliant.
_H2_HEADING_PATTERNS = {
    name: re.compile(
        rf"^##\s+.*\b{name}s?\b",
        re.IGNORECASE | re.MULTILINE,
    )
    for name in REQUIRED_SECTIONS
}

LINK_PATTERN = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")

# Match references to the framework authoring tree. A "leak" is a shipped-
# content file citing a path that only exists in the authoring workspace
# (``.agents/patterns.md``, ``.agents/knowledge/...``, ``.agents/specs/...``,
# ``.agents/archive/...``, ``.agents/plans/...``, ``.agents/research/...``,
# ``.agents/flows.md``, ``.agents/product.md``, ``.agents/product-guidelines.md``,
# ``.agents/workflow.md``, ``.agents/tech-stack.md``, ``.agents/index.md``,
# ``.agents/beads.json``, ``.agents/setup-state.json``, ``.agents/code-styleguides/``,
# ``.agents/backlog/``). These never exist on a user install.
#
# Benign mentions (prose about the Flow authoring convention, the user-install
# ``.agents/skills/`` or ``.agents/plugins/`` convention paths, or a bare
# ``.agents/`` directory reference) are allowed. The lookbehind rejects alnum/
# underscore prefixes so filesystem paths like ``foo_.agents/`` are not
# flagged.
_AUTHORING_TREE_SUBPATHS: tuple[str, ...] = ()
AGENTS_LEAK_PATTERN = re.compile(rf"(?<![A-Za-z0-9_])\.agents/(?:{'|'.join(re.escape(p) for p in _AUTHORING_TREE_SUBPATHS)})") if _AUTHORING_TREE_SUBPATHS else re.compile(r"$.")

# Forbidden vocabulary in shipped content. These tokens leak machine-
# specific filesystem paths. Each tuple is ``(regex, human-readable label)``.
# Keep the list narrow and high-confidence. Add allowlist exceptions in 
# ``_FORBIDDEN_VOCAB_ALLOWLIST`` below if a legitimate use is found.
FORBIDDEN_VOCAB_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    # --- Machine-specific paths --------------------------------------------
    (re.compile(r"/home/cody/", re.IGNORECASE), "machine-specific filesystem path '/home/cody/...'"),
)

# Files exempt from FORBIDDEN_VOCAB_PATTERNS. Tests legitimately reference the
# literal patterns to verify the validator catches them; the validator itself
# documents the patterns in code. Use repo-relative POSIX paths.
_FORBIDDEN_VOCAB_ALLOWLIST: frozenset[str] = frozenset(
    {
        "tools/validate-skills.py",  # the validator defines the patterns
        "tests/test_validate_skills.py",  # tests assert against the patterns
    }
)

VALID_AGENT_MODES = frozenset({"subagent", "primary"})
VALID_AGENT_TOOLS = frozenset({"read", "grep", "glob", "bash", "edit", "write", "todoWrite", "webFetch", "webSearch"})

# Claude Code subagent tool registry (canonical Claude tool names exposed to
# subagents — see https://code.claude.com/docs/en/sub-agents).
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

# Gemini CLI subagent tool registry (see docs/core/subagents.md in google-gemini/gemini-cli).
# Wildcards `*`, `mcp_*`, and `mcp_<server>_*` are also accepted at runtime.
VALID_GEMINI_TOOLS = frozenset(
    {
        "read_file",
        "grep_search",
        "glob",
        "run_shell_command",
        "list_directory",
        "web_fetch",
        "google_web_search",
        "write_file",
        "edit",
        "save_memory",
    }
)
_GEMINI_WILDCARD_PATTERN = re.compile(r"^(?:\*|mcp_[A-Za-z0-9_-]*\*?)$")
_CLAUDE_HOOK_EVENT_PATTERN = re.compile(r"^[A-Z][A-Za-z0-9]*$")
_CROSS_HOST_HOOK_FALLBACK = "${CLAUDE_PLUGIN_ROOT:-${extensionPath}}"

# Codex nickname_candidates entries: ASCII letters, digits, spaces, hyphens,
# underscores only. Per https://developers.openai.com/codex/subagents.
_CODEX_NICKNAME_PATTERN = re.compile(r"^[A-Za-z0-9 _-]+$")


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


def _validate_hook_event_map(path: Path, hooks: object) -> list[Violation]:
    violations: list[Violation] = []
    if not isinstance(hooks, dict):
        return [Violation(path, 1, "hook config must contain a top-level 'hooks' record")]
    for event_name, matchers in hooks.items():
        if not isinstance(event_name, str) or not _CLAUDE_HOOK_EVENT_PATTERN.match(event_name):
            violations.append(Violation(path, 1, f"Claude hooks event {event_name!r} must be PascalCase"))
        if not isinstance(matchers, list):
            violations.append(Violation(path, 1, f"Claude hooks event {event_name!r} must map to a list"))
            continue
        for matcher in matchers:
            if not isinstance(matcher, dict):
                violations.append(Violation(path, 1, f"Claude hooks event {event_name!r} entries must be objects"))
                continue
            nested_hooks = matcher.get("hooks")
            if not isinstance(nested_hooks, list) or not nested_hooks:
                violations.append(
                    Violation(path, 1, f"Claude hooks event {event_name!r} entries must contain a non-empty 'hooks' list")
                )
                continue
            for hook in nested_hooks:
                if not isinstance(hook, dict):
                    violations.append(
                        Violation(path, 1, f"Claude hooks event {event_name!r} hook entries must be objects")
                    )
                    continue
                if hook.get("type") != "command":
                    violations.append(
                        Violation(path, 1, f"Claude hooks event {event_name!r} hook entries must use type 'command'")
                    )
                command = hook.get("command")
                if not isinstance(command, str) or not command.strip():
                    violations.append(
                        Violation(path, 1, f"Claude hooks event {event_name!r} hook entries need a non-empty command")
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
    """Validate Claude's hook config file for host-specific placeholder usage."""
    hook_events, violations = _load_hook_event_map(path)
    if hook_events is None:
        return violations

    violations.extend(_validate_hook_event_map(path, hook_events))
    for entry in _iter_nested_strings(hook_events):
        if "${extensionPath}" in entry and _CROSS_HOST_HOOK_FALLBACK not in entry:
            violations.append(
                Violation(
                    path,
                    1,
                    "Claude hook config must not use '${extensionPath}'; use '${CLAUDE_PLUGIN_ROOT}' instead",
                )
            )
            break
    return violations


def validate_gemini_hook_config(path: Path) -> list[Violation]:
    """Validate Gemini's hook config file for host-specific placeholder usage."""
    hook_events, violations = _load_hook_event_map(path)
    if hook_events is None:
        return violations

    violations.extend(_validate_hook_event_map(path, hook_events))
    for entry in _iter_nested_strings(hook_events):
        if "${CLAUDE_PLUGIN_ROOT}" in entry and _CROSS_HOST_HOOK_FALLBACK not in entry:
            violations.append(
                Violation(
                    path,
                    1,
                    "Gemini hook config must not use '${CLAUDE_PLUGIN_ROOT}'; use '${extensionPath}' instead",
                )
            )
            break
    return violations


def extract_frontmatter(text: str) -> tuple[dict[str, Any], int, str]:
    """Return ``(frontmatter_dict, body_start_line, body_text)``.

    Raises :class:`ValueError` on missing or unterminated frontmatter.
    """
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
    violations.extend(_check_description(fm.get("description"), path, 1))
    for section in REQUIRED_SECTIONS:
        if not _section_present(body, section):
            violations.append(
                Violation(
                    path,
                    body_start,
                    f"missing required section <{section}> (XML tag or '## {section.title()}' heading)",
                )
            )
    # Strip code blocks before checking links to avoid false positives from
    # square brackets in code (e.g. Mojo / Rust / TypeScript generics).
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
    """Validate an OpenCode subagent file under ``.opencode/agents/``.

    OpenCode schema: ``mode`` in {primary, subagent}, ``tools`` as a dict
    mapping whitelisted tool keys to bool values.
    """
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
    tools = fm.get("tools")
    if not isinstance(tools, dict):
        violations.append(Violation(path, 1, "tools missing or not a mapping"))
    else:
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
    return violations


def validate_gemini_agent(path: Path) -> list[Violation]:
    """Validate a Gemini CLI subagent file under ``agents/``.

    Gemini schema: no ``mode`` key (rejected by Gemini's loader), ``tools`` as
    a list of tool-name strings. Each string must be a known Gemini tool or a
    wildcard pattern (``*``, ``mcp_*``, ``mcp_<server>_*``).
    """
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
        violations.append(Violation(path, 1, "mode key not allowed (Gemini subagents reject it)"))
    tools = fm.get("tools")
    if tools is None:
        return violations
    if not isinstance(tools, list):
        violations.append(Violation(path, 1, "tools must be a list of strings"))
        return violations
    # pyright strict requires an explicit cast here even though mypy's
    # narrowing already gives us list[Any]; silence the redundant-cast warning.
    tools_list = cast("list[Any]", tools)  # type: ignore[redundant-cast]
    for entry in tools_list:
        if not isinstance(entry, str):
            type_name = type(entry).__name__
            violations.append(Violation(path, 1, f"tools entry must be a string, got {type_name}"))
            continue
        if entry in VALID_GEMINI_TOOLS:
            continue
        if _GEMINI_WILDCARD_PATTERN.match(entry):
            continue
        violations.append(Violation(path, 1, f"tool {entry!r} not in Gemini tool registry"))
    return violations


def validate_claude_agent(path: Path) -> list[Violation]:
    """Validate a Claude Code subagent file under ``.claude-plugin/agents/``.

    Claude schema: ``tools`` as a comma-separated string of canonical Claude
    tool names (e.g. ``Read, Grep, Glob, Bash``). YAML lists and dict mappings
    are rejected by Claude's plugin manifest validator. ``mode`` is not part
    of Claude's subagent schema.
    """
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


def validate_manifest(path: Path) -> list[Violation]:
    """Validate a host-specific plugin.json manifest.

    Enforces host-specific schema requirements (e.g. Claude Code requiring arrays
    for file lists).
    """
    violations: list[Violation] = []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        return [Violation(path, 1, f"JSON parse error: {exc}")]

    # Identify host by parent directory name
    host_dir = path.parent.name
    is_claude = host_dir == ".claude-plugin"

    # Claude Code specific rules
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
    """Validate a Codex CLI subagent file under ``.codex/agents/``.

    Codex schema (per https://developers.openai.com/codex/subagents) is pure
    TOML: the prompt body lives in ``developer_instructions`` (string), and
    tools are inherited from the session's ``config.toml`` — Codex does NOT
    accept a per-agent ``tools`` allowlist. ``mode`` is an OpenCode dialect
    and is also rejected.
    """
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
    """Flag forbidden internal vocabulary or machine-specific paths in shipped
    content.

    Walks every file, line by line, and flags any match of
    :data:`FORBIDDEN_VOCAB_PATTERNS`. Files in
    :data:`_FORBIDDEN_VOCAB_ALLOWLIST` are skipped (the validator + its tests
    legitimately reference the literal patterns).
    """
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
                    break  # one violation per line is enough
    return violations


def iter_skills() -> Iterator[Path]:
    if SKILLS_DIR.is_dir():
        yield from sorted(SKILLS_DIR.glob("*/SKILL.md"))


def iter_commands() -> Iterator[Path]:
    if COMMANDS_DIR.is_dir():
        yield from sorted(COMMANDS_DIR.rglob("*.toml"))


def iter_gemini_agents() -> Iterator[Path]:
    if AGENTS_DIR.is_dir():
        yield from sorted(AGENTS_DIR.glob("*.md"))


def iter_opencode_agents() -> Iterator[Path]:
    if OPENCODE_AGENTS_DIR.is_dir():
        yield from sorted(OPENCODE_AGENTS_DIR.glob("*.md"))


def iter_claude_agents() -> Iterator[Path]:
    if CLAUDE_AGENTS_DIR.is_dir():
        yield from sorted(CLAUDE_AGENTS_DIR.glob("*.md"))


def iter_codex_agents() -> Iterator[Path]:
    if CODEX_AGENTS_DIR.is_dir():
        yield from sorted(CODEX_AGENTS_DIR.glob("*.toml"))


def iter_manifests() -> Iterator[Path]:
    for host in (".claude-plugin", ".codex-plugin", ".cursor-plugin"):
        candidate = REPO_ROOT / host / "plugin.json"
        if candidate.is_file():
            yield candidate


def iter_claude_hook_configs() -> Iterator[Path]:
    """Resolve Claude's hook manifest path. If .claude-plugin/plugin.json
    declares a `hooks` field, that is authoritative; otherwise Claude
    auto-discovers hooks/hooks.json. Per-host manifests are needed because
    Gemini also default-discovers hooks/hooks.json with incompatible
    template syntax."""
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


def iter_gemini_hook_configs() -> Iterator[Path]:
    candidate = REPO_ROOT / "hooks" / "hooks.json"
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
        yield from sorted(CODEX_AGENTS_DIR.rglob("*.toml"))
    for name in SHIPPED_ROOT_FILES:
        candidate = REPO_ROOT / name
        if candidate.is_file():
            yield candidate
    # Public docs/ tree — user-facing release notes, roadmap, launch playbook.
    docs_dir = REPO_ROOT / "docs"
    if docs_dir.is_dir():
        yield from sorted(docs_dir.rglob("*.md"))
    # Host-specific install / config files that ship with the plugin.
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


def main() -> int:
    all_violations: list[Violation] = []
    skills = list(iter_skills())
    commands = list(iter_commands())
    gemini_agents = list(iter_gemini_agents())
    opencode_agents = list(iter_opencode_agents())
    claude_agents = list(iter_claude_agents())
    codex_agents = list(iter_codex_agents())
    manifests = list(iter_manifests())
    claude_hook_configs = list(iter_claude_hook_configs())
    gemini_hook_configs = list(iter_gemini_hook_configs())
    for manifest_path in manifests:
        all_violations.extend(validate_manifest(manifest_path))
    for skill_path in skills:
        all_violations.extend(validate_skill(skill_path))
    for cmd_path in commands:
        all_violations.extend(validate_command(cmd_path))
    for agent_path in gemini_agents:
        all_violations.extend(validate_gemini_agent(agent_path))
    for agent_path in opencode_agents:
        all_violations.extend(validate_opencode_agent(agent_path))
    for agent_path in claude_agents:
        all_violations.extend(validate_claude_agent(agent_path))
    for agent_path in codex_agents:
        all_violations.extend(validate_codex_agent(agent_path))
    for hook_config_path in claude_hook_configs:
        all_violations.extend(validate_claude_hook_config(hook_config_path))
    for hook_config_path in gemini_hook_configs:
        all_violations.extend(validate_gemini_hook_config(hook_config_path))
    shipped = list(iter_all_shipped_files())
    all_violations.extend(check_agents_leak(shipped))
    all_violations.extend(check_forbidden_vocab(shipped))
    if all_violations:
        _print_violations(all_violations)
        print(f"\n{len(all_violations)} violation(s)", file=sys.stderr)
        return 1
    agent_total = len(gemini_agents) + len(opencode_agents) + len(claude_agents) + len(codex_agents)
    print(f"[ OK ] validated {len(skills)} skills, {len(commands)} commands, {agent_total} agents — no violations")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

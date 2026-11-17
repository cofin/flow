"""Prose linter enforcing Flow's plain vocabulary and writing rules."""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

__all__ = ["ProseLinter", "validate_prose"]

_FRONTMATTER_RE = re.compile(r"\A---\n.*?\n---\n?", re.DOTALL)
_CODE_OR_COMMENT_RE = re.compile(r"`[^`\n]+`|(<!--.*?-->)", re.DOTALL)
_FENCE_RE = re.compile(r"^\s*(`{3,}|~{3,})(.*)$")
_INLINE_CODE_RE = re.compile(r"`[^`\n]+`")
_MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]+\)")
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.?!;])\s+")
_WORD_RE = re.compile(r"[A-Za-z0-9_'’]+(?:-[A-Za-z0-9_'’]+)*")
_BLOCK_SCALAR_RE = re.compile(r"^[|>][+-]?\d*$")


class ProseLinter:
    """Check shipped Flow prose against the plain vocabulary and writing rules."""

    MAX_SENTENCE_WORDS: int = 35
    MAX_HEADING_WORDS: int = 8

    RETIRED_TERMS: tuple[tuple[str, re.Pattern[str], str], ...] = (
        ("wave", re.compile(r"\bwaves?\b", re.IGNORECASE), 'Say "step".'),
        (
            "slice",
            re.compile(r"\b(?:micro-|vertical[- ]|horizontal[- ])?slic(?:e|es|ed|ing)\b", re.IGNORECASE),
            'Say "task".',
        ),
        ("context pack", re.compile(r"\bcontext[- ]packs?\b", re.IGNORECASE), 'Say "brief".'),
        ("slot", re.compile(r"\bslots?\b", re.IGNORECASE), 'Say "worker".'),
        ("batch size", re.compile(r"\bbatch[- ]size\b", re.IGNORECASE), 'Say "workers" or "tasks per worker".'),
        ("disjoint", re.compile(r"\bdisjoint(?:ness)?\b", re.IGNORECASE), 'Say "separate files".'),
        ("reconcile", re.compile(r"\breconcil(?:e|es|ed|ing|iation)\b", re.IGNORECASE), 'Say "sync".'),
        ("gate", re.compile(r"\bgates?\b", re.IGNORECASE), 'Say "check".'),
        (
            "cold-read",
            re.compile(r"\bcold-read(?:er|ing|s)?\b", re.IGNORECASE),
            'Say "independent" or "first-time reader".',
        ),
        ("zero-context", re.compile(r"\bzero-context\b", re.IGNORECASE), 'Say "independent".'),
        (
            "zero-LLM",
            re.compile(r"\bzero-(?:llm|token|regex|pypi|history|decision)\b", re.IGNORECASE),
            "Name what runs or say the point.",
        ),
        ("deterministic", re.compile(r"\bdeterministic(?:ally)?\b", re.IGNORECASE), "Name what runs."),
        ("frontier", re.compile(r"\bfrontier\b", re.IGNORECASE), 'Say "strongest model" or "open decisions".'),
        ("tier", re.compile(r"\btiers?\b", re.IGNORECASE), 'Say "model role" or name the size.'),
        (
            "compaction",
            re.compile(r"\b(?:context )?compactions?\b", re.IGNORECASE),
            'Say "small enough to finish in one run".',
        ),
        ("cold start", re.compile(r"\bcold[- ]starts?\b", re.IGNORECASE), "Say what happens directly."),
        ("bin-packed", re.compile(r"\bbin-pack(?:ed|ing|s)?\b", re.IGNORECASE), 'Say "grouped".'),
        ("work-conserving", re.compile(r"\bwork-conserving\b", re.IGNORECASE), 'Say "keeps every worker busy".'),
        ("semaphore", re.compile(r"\bsemaphore(?:-bounded)?\b", re.IGNORECASE), "Say how many run at once."),
        ("true-up", re.compile(r"\btrue-?ups?\b", re.IGNORECASE), 'Say "sync" or "align".'),
        (
            "reorient",
            re.compile(r"\breorient(?:ing|ed|ation)?\b", re.IGNORECASE),
            'Say "catch up" or "status summary".',
        ),
        (
            "resynthesize",
            re.compile(r"\bresynthesi(?:ze|zes|zed|zing|s)\b", re.IGNORECASE),
            'Say "update knowledge" or "refresh".',
        ),
        ("contraction", re.compile(r"\bcontraction\b", re.IGNORECASE), 'Say "archive order" or "capture learnings".'),
        (
            "adjudicate",
            re.compile(r"\badjudicat(?:e|es|ed|ing|ion|or|ors)\b", re.IGNORECASE),
            'Say "decide on each finding".',
        ),
        ("adjudication ledger", re.compile(r"\bledger\b", re.IGNORECASE), 'Say "review summary".'),
        ("blueprint", re.compile(r"\bblueprints?\b", re.IGNORECASE), 'Say "task worksheet".'),
        ("bounded read manifest", re.compile(r"\bbounded read manifest\b", re.IGNORECASE), 'Say "read list".'),
        ("read fence", re.compile(r"\bread fence\b", re.IGNORECASE), 'Say "read list".'),
        (
            "public-seam",
            re.compile(r"\b(?:public|deep-module|multi)-seams?\b", re.IGNORECASE),
            'Say "public interface" or "module interface".',
        ),
        ("iron law", re.compile(r"\biron law\b", re.IGNORECASE), 'Say "run the check before claiming it passed".'),
        ("north star", re.compile(r"\bnorth star\b", re.IGNORECASE), 'Say "goal".'),
        (
            "altitude control",
            re.compile(r"\baltitude control\b", re.IGNORECASE),
            'Say "architecture in spec.md, file details in worksheets".',
        ),
        ("red-capable", re.compile(r"\bred-capable\b", re.IGNORECASE), 'Say "fast failing test".'),
        ("worked test matrix", re.compile(r"\bworked test matrix\b", re.IGNORECASE), 'Say "test cases".'),
        ("circuit breaker", re.compile(r"\bcircuit breakers?\b", re.IGNORECASE), 'Say "stop-loop limit".'),
        (
            "hypothesis-driven bug diagnosis",
            re.compile(r"\bhypothesis-driven\b", re.IGNORECASE),
            'Say "bug diagnosis".',
        ),
        (
            "System Under Test",
            re.compile(r"\b(?:(?i:system under test)|SUT)\b"),
            'Say "real code" or "module under test".',
        ),
        ("mock-echo", re.compile(r"\bmock-echo\b", re.IGNORECASE), 'Say "mock-only test".'),
        ("tautological", re.compile(r"\btautological\b", re.IGNORECASE), 'Say "mock-only test".'),
        (
            "implementation-coupled",
            re.compile(r"\bimplementation-coupled\b", re.IGNORECASE),
            'Say "private-detail test".',
        ),
        ("anti-skip", re.compile(r"\banti-skip\b", re.IGNORECASE), 'Say "completion check".'),
        ("anti-truncation", re.compile(r"\banti-truncation\b", re.IGNORECASE), 'Say "plan the whole scope".'),
        ("anti-sprawl", re.compile(r"\banti-sprawl\b", re.IGNORECASE), 'Say "layout check".'),
        ("chronological sediment", re.compile(r"\bsediment\b", re.IGNORECASE), 'Say "current state only".'),
        ("co-designer", re.compile(r"\bco-design(?:er|ers|ing)?\b", re.IGNORECASE), 'Say "planner".'),
        ("stateful planner", re.compile(r"\bstateful plann(?:er|ing)\b", re.IGNORECASE), 'Say "planner".'),
        ("orthogonal", re.compile(r"\borthogonal\b", re.IGNORECASE), 'Say "independent" or "from a different vendor".'),
        ("sharded", re.compile(r"\bshard(?:ed|ing)?\b", re.IGNORECASE), 'Say "parallel".'),
        ("reconnaissance", re.compile(r"\breconnaissance\b", re.IGNORECASE), 'Say "research".'),
        ("scout", re.compile(r"\bscout(?:s|ing)?\b", re.IGNORECASE), 'Say "researcher" or "research".'),
        (
            "upward delegation",
            re.compile(r"\bupward delegation\b", re.IGNORECASE),
            'Say "planning and review use the strongest model".',
        ),
        ("fail-closed", re.compile(r"\bfail[- ]closed\b", re.IGNORECASE), 'Say "stop without editing".'),
        ("manifest-driven", re.compile(r"\bmanifest-driven\b", re.IGNORECASE), 'Say "file checklist".'),
        ("deliverable-sized", re.compile(r"\bdeliverable-sized\b", re.IGNORECASE), 'Say "sized to the feature".'),
        ("write-time", re.compile(r"\bwrite-time\b", re.IGNORECASE), 'Say "right after writing".'),
        ("commit-first", re.compile(r"\bcommit-first\b", re.IGNORECASE), 'Say "commit code first".'),
        ("local-substitutable", re.compile(r"\blocal-substitutable\b", re.IGNORECASE), 'Say "local test double".'),
        ("SubsystemDigest", re.compile(r"\bSubsystemDigest\b"), 'Say "subsystem summary".'),
        ("Token Stratum", re.compile(r"\bToken Stratum\b", re.IGNORECASE), 'Say "Model Routing".'),
        ("System-One", re.compile(r"\bSystem-One\b", re.IGNORECASE), 'Say "model picker".'),
        (
            "structured-choice-v1",
            re.compile(
                r"\b(?:structured-choice|quality-review|worksheet-execution|structured-result)-v1\b", re.IGNORECASE
            ),
            "Remove the coined versioned label.",
        ),
        ("flow-memory-keeper", re.compile(r"\bflow-memory-keeper\b", re.IGNORECASE), "Remove stale references."),
    )

    PUFFERY: frozenset[str] = frozenset(
        {
            "comprehensive",
            "crucial",
            "delve",
            "foster",
            "leverage",
            "pivotal",
            "robust",
            "seamless",
            "showcase",
            "tapestry",
            "underscore",
            "unlock",
        }
    )

    COUNT_LABEL_RE: re.Pattern[str] = re.compile(
        r"\b\d+-(?:Layer|Stage|Point|Pillar|Tier|Step|Way|Term|Part|Factor)\b",
        re.IGNORECASE,
    )

    EXEMPT_VOCAB_FILES: frozenset[str] = frozenset({"skills/flow/references/vocabulary.md"})

    def __init__(self) -> None:
        """Precompile puffery pattern."""
        joined = "|".join(sorted(self.PUFFERY))
        self._puffery_re = re.compile(rf"\b(?:{joined})\b", re.IGNORECASE)

    def lint_file(self, path: Path, repo_root: Path) -> list[str]:
        """Lint a single Markdown file against retired terms, puffery, and length limits."""
        rel = path.relative_to(repo_root).as_posix()
        text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
        return self.lint_text(text, rel)

    def lint_text(self, text: str, rel: str, *, check_length: bool = True) -> list[str]:
        """Lint Markdown or plain description text and return formatted findings."""
        normalized = text.replace("\r\n", "\n").replace("\r", "\n")
        errors: list[str] = []
        skip_vocab = rel in self.EXEMPT_VOCAB_FILES
        body = _FRONTMATTER_RE.sub("", normalized, count=1)
        fm_lines = len(normalized[: len(normalized) - len(body)].splitlines())

        frontmatter_desc = self._extract_frontmatter_description(normalized)
        if frontmatter_desc:
            errors.extend(self._check_inline_terms(frontmatter_desc, rel, 1, skip_vocab=skip_vocab))

        non_fence_chunks: list[tuple[int, list[str]]] = []
        current_start: int | None = None
        current_lines: list[str] = []
        in_fence = False
        fence_char = ""
        fence_len = 0

        for idx, raw_line in enumerate(body.splitlines(), start=fm_lines + 1):
            fence_match = _FENCE_RE.match(raw_line)
            if fence_match:
                marker, info = fence_match.group(1), fence_match.group(2)
                if not in_fence and not (marker[0] == "`" and "`" in info):
                    if current_start is not None and current_lines:
                        non_fence_chunks.append((current_start, current_lines))
                        current_start = None
                        current_lines = []
                    in_fence = True
                    fence_char = marker[0]
                    fence_len = len(marker)
                    continue
                if in_fence and marker[0] == fence_char and len(marker) >= fence_len and not info.strip():
                    in_fence = False
                    fence_char = ""
                    fence_len = 0
                    continue
            if in_fence:
                continue
            if current_start is None:
                current_start = idx
            current_lines.append(raw_line)

        if current_start is not None and current_lines:
            non_fence_chunks.append((current_start, current_lines))

        for start_line, chunk_lines in non_fence_chunks:
            cleaned_chunk = self._strip_html_comments("\n".join(chunk_lines))
            for offset, cleaned in enumerate(cleaned_chunk.split("\n")):
                line_no = start_line + offset
                stripped = cleaned.strip()
                if not stripped:
                    continue

                heading_match = _HEADING_RE.match(cleaned)
                if heading_match:
                    heading_text = heading_match.group(2)
                    errors.extend(self._check_inline_terms(heading_text, rel, line_no, skip_vocab=skip_vocab))
                    if check_length:
                        heading_words = self._count_words(heading_text)
                        if heading_words > self.MAX_HEADING_WORDS:
                            errors.append(
                                f"PROSE_LONG_HEADING: {rel}:{line_no}: heading has {heading_words} words "
                                f"(max {self.MAX_HEADING_WORDS}): {heading_text!r}"
                            )
                    continue

                errors.extend(self._check_inline_terms(cleaned, rel, line_no, skip_vocab=skip_vocab))

                if check_length and not stripped.startswith("|") and not stripped.startswith("<"):
                    errors.extend(self._check_sentence_lengths(cleaned, rel, line_no))

        return errors

    def lint_repository(self, repo_root: Path) -> list[str]:
        """Lint all shipped Flow Markdown files and manifest/workflow descriptions."""
        errors: list[str] = []
        md_files: list[Path] = []
        for sub in ("skills", "agents", "rules", ".agents/rules", "templates"):
            sub_dir = repo_root / sub
            if sub_dir.is_dir():
                md_files.extend(sorted(sub_dir.rglob("*.md")))
        for doc_rel in ("README.md", "CONTRIBUTING.md", "vscode-extension/README.md"):
            doc_path = repo_root / doc_rel
            if doc_path.is_file():
                md_files.append(doc_path)

        for md_path in md_files:
            errors.extend(self.lint_file(md_path, repo_root))

        for json_rel in (
            "plugin.json",
            ".claude-plugin/plugin.json",
            ".codex-plugin/plugin.json",
            ".cursor-plugin/plugin.json",
            "package.json",
            "mods/claude-flow/.claude-plugin/plugin.json",
        ):
            jpath = repo_root / json_rel
            if jpath.is_file():
                errors.extend(self._lint_json_descriptions(jpath, repo_root))

        workflows_dir = repo_root / "workflows"
        if workflows_dir.is_dir():
            for wf_json in sorted(workflows_dir.glob("*/workflow.json")):
                errors.extend(self._lint_json_descriptions(wf_json, repo_root))

        codex_agents = repo_root / ".codex" / "agents"
        if codex_agents.is_dir():
            for toml_path in sorted(codex_agents.glob("*.toml")):
                errors.extend(self._lint_codex_agent_toml(toml_path, repo_root))

        return errors

    def _strip_html_comments(self, chunk: str) -> str:
        """Remove single-line and multi-line HTML comments outside inline code while preserving line count."""
        return _CODE_OR_COMMENT_RE.sub(
            lambda m: "\n" * m.group(1).count("\n") if m.group(1) else m.group(0),
            chunk,
        )

    def _extract_frontmatter_description(self, text: str) -> str:
        """Extract single-line or multi-line ``description`` value from YAML frontmatter."""
        match = _FRONTMATTER_RE.match(text)
        if not match:
            return ""
        fm_lines = match.group(0).splitlines()
        for idx, line in enumerate(fm_lines):
            if not line.startswith("description:"):
                continue
            val = line.split(":", 1)[1].strip()
            parts: list[str] = []
            is_block = not val or bool(_BLOCK_SCALAR_RE.match(val))
            if not is_block:
                parts.append(val)
            for cont in fm_lines[idx + 1 :]:
                if cont.strip() == "---":
                    break
                if cont.startswith((" ", "\t")):
                    stripped_cont = cont.strip()
                    if stripped_cont:
                        parts.append(stripped_cont)
                elif not cont.strip() and is_block:
                    continue
                else:
                    break
            joined = " ".join(parts).strip()
            if len(joined) >= 2 and joined[0] == joined[-1] and joined[0] in ('"', "'"):
                joined = joined[1:-1]
            return joined
        return ""

    def _strip_code_and_links(self, text: str) -> str:
        """Remove inline code spans and keep visible markdown link labels."""
        without_code = _INLINE_CODE_RE.sub(" ", text)
        return _MARKDOWN_LINK_RE.sub(r"\1", without_code)

    def _count_words(self, text: str) -> int:
        """Count words while treating each inline code span as one word."""
        with_code_tokens = _INLINE_CODE_RE.sub(" code ", text)
        without_links = _MARKDOWN_LINK_RE.sub(r"\1", with_code_tokens)
        return len(_WORD_RE.findall(without_links))

    def _check_inline_terms(self, text: str, rel: str, line_no: int, *, skip_vocab: bool) -> list[str]:
        """Check one line for retired terms, puffery, and count-prefixed labels."""
        if skip_vocab:
            return []
        plain = self._strip_code_and_links(text)
        errors: list[str] = []
        for _key, pattern, advice in self.RETIRED_TERMS:
            match = pattern.search(plain)
            if match:
                errors.append(f"PROSE_RETIRED_TERM: {rel}:{line_no}: retired term {match.group(0)!r}. {advice}")
        puff = self._puffery_re.search(plain)
        if puff:
            errors.append(f"PROSE_PUFFERY: {rel}:{line_no}: puffery word {puff.group(0)!r}; state the concrete fact.")
        count_match = self.COUNT_LABEL_RE.search(plain)
        if count_match:
            errors.append(f"PROSE_COUNT_LABEL: {rel}:{line_no}: drop count-prefixed label {count_match.group(0)!r}.")
        return errors

    def _check_sentence_lengths(self, line: str, rel: str, line_no: int) -> list[str]:
        """Flag sentences on a prose line exceeding ``MAX_SENTENCE_WORDS``."""
        cleaned = re.sub(r"^\s*(?:[-*+]|\d+\.)\s+", "", line)
        cleaned = _MARKDOWN_LINK_RE.sub(r"\1", cleaned)
        with_code_tokens = _INLINE_CODE_RE.sub(" code ", cleaned)
        errors: list[str] = []
        for sentence in _SENTENCE_SPLIT_RE.split(with_code_tokens.strip()):
            words = _WORD_RE.findall(sentence)
            if len(words) > self.MAX_SENTENCE_WORDS:
                errors.append(
                    f"PROSE_LONG_SENTENCE: {rel}:{line_no}: sentence has {len(words)} words "
                    f"(max {self.MAX_SENTENCE_WORDS})."
                )
        return errors

    def _collect_json_texts(self, node: object) -> list[str]:
        """Collect ``description`` and ``suggestedPrompts`` strings recursively from parsed JSON."""
        texts: list[str] = []
        if isinstance(node, dict):
            desc = node.get("description")
            if isinstance(desc, str) and desc.strip():
                texts.append(desc)
            prompts = node.get("suggestedPrompts")
            if isinstance(prompts, list):
                for prompt in prompts:
                    if isinstance(prompt, str) and prompt.strip():
                        texts.append(prompt)
            for val in node.values():
                if isinstance(val, (dict, list)):
                    texts.extend(self._collect_json_texts(val))
        elif isinstance(node, list):
            for item in node:
                if isinstance(item, (dict, list)):
                    texts.extend(self._collect_json_texts(item))
        return texts

    def _lint_json_descriptions(self, path: Path, repo_root: Path) -> list[str]:
        """Lint ``description`` and ``suggestedPrompts`` fields inside a JSON manifest or workflow."""
        rel = path.relative_to(repo_root).as_posix()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []
        errors: list[str] = []
        for text_val in self._collect_json_texts(data):
            errors.extend(self.lint_text(text_val, rel, check_length=False))
        return errors

    def _lint_codex_agent_toml(self, path: Path, repo_root: Path) -> list[str]:
        """Lint ``description`` and ``developer_instructions`` fields in a Codex agent TOML file."""
        rel = path.relative_to(repo_root).as_posix()
        try:
            data = tomllib.loads(path.read_text(encoding="utf-8"))
        except tomllib.TOMLDecodeError:
            return []
        errors: list[str] = []
        for key in ("description", "developer_instructions"):
            val = data.get(key)
            if isinstance(val, str) and val.strip():
                errors.extend(self.lint_text(val, rel, check_length=False))
        return errors


def validate_prose(repo_root: Path) -> list[str]:
    """Run ``ProseLinter`` across all shipped Flow prose files."""
    return ProseLinter().lint_repository(repo_root)

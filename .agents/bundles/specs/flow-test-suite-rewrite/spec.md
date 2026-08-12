---
type: flow
id: flow-test-suite-rewrite
title: Flow Test Suite Rewrite
status: active
timestamp: 2026-08-11 15:35:25+00:00
flow_id: flow-test-suite-rewrite
description: Flow Test Suite Rewrite
created_at: '2026-08-11T22:50:00Z'
updated_at: '2026-08-11T22:50:00Z'
---

# Flow: Flow Test Suite Rewrite

## Goal
Extend the repository's validation test suite to support validating schemas for OKF specifications (`.agents/bundles/specs/`) and knowledge base articles (`.agents/bundles/knowledge/`).

## Architecture
We will update the Python validation tool ([`tools/validate.py`](../../../../tools/validate.py)) and write associated unit tests in [`tests/test_validate_skills.py`](../../../../tests/test_validate_skills.py).

---

## Implementation Plan

### Task 1: Refine spec.md itself
- **Target Files**:
  - [`spec.md`](./spec.md)
- **Implementation Details**:
  - Ensure the specification is refined and written under the Beads-free layout with relative links and TDD-structured tasks.
- **Verification**:
  - Verify that the spec file exists and is formatted correctly.

### Task 2: Implement OKF workspace directory path resolution in validation utility
- **Target Files**:
  - [`tools/validate.py`](../../../../tools/validate.py#L38-L47)
- **Write Tests**:
  - In [`tests/test_validate_skills.py`](../../../../tests/test_validate_skills.py), add `test_get_flow_root` using `monkeypatch` to simulate existence/non-existence of `setup-state.json` inside the `.agents` folder, verifying correct directory resolution.
  - Code Sample:
    ```python
    def test_get_flow_root(tmp_path: Path, monkeypatch) -> None:
        # Mock REPO_ROOT to point to tmp_path
        monkeypatch.setattr(validate_skills, "REPO_ROOT", tmp_path)
        
        # Scenario 1: setup-state.json does not exist
        assert validate_skills.get_flow_root() == tmp_path / ".agents"
        
        # Scenario 2: setup-state.json exists in .agents directory with root_directory field
        setup_file = tmp_path / ".agents" / "setup-state.json"
        _write_json(setup_file, {"root_directory": "custom_agents"})
        assert validate_skills.get_flow_root() == tmp_path / "custom_agents"
    ```
- **Implement Feature**:
  - Implement `get_flow_root() -> Path` in [`tools/validate.py`](../../../../tools/validate.py).
  - Code Snippet:
    ```python
    def get_flow_root() -> Path:
        """Resolve the root directory of flow specifications and knowledge documents."""
        state_file = REPO_ROOT / ".agents" / "setup-state.json"
        if state_file.is_file():
            try:
                state = json.loads(state_file.read_text(encoding="utf-8"))
                if isinstance(state, dict):
                    root_dir = state.get("root_directory")
                    if isinstance(root_dir, str) and root_dir.strip():
                        path = Path(root_dir)
                        if not path.is_absolute():
                            path = REPO_ROOT / path
                        return path.resolve()
            except (json.JSONDecodeError, OSError):
                pass
        return REPO_ROOT / ".agents"
    ```
- **Verification**:
  - Run the test suite:
    ```bash
    python -m pytest tests/test_validate_skills.py -k test_get_flow_root
    ```
  - Criteria: Test passes successfully.

### Task 3: Implement validation functions for OKF specs and knowledge documents
- **Target Files**:
  - [`tools/validate.py`](../../../../tools/validate.py#L910-L911)
- **Write Tests**:
  - In [`tests/test_validate_skills.py`](../../../../tests/test_validate_skills.py), add unit tests for scan and validation functions:
    - `test_iter_okf_specs(tmp_path)`: Verify it matches `bundles/specs/*/spec.md`.
    - `test_iter_okf_knowledge(tmp_path)`: Verify it matches `bundles/knowledge/**/*.md`, excluding `index.md` and `log.md`.
    - `test_validate_okf_spec(tmp_path)`: Test success cases, missing frontmatter, wrong `type`, mismatched `id`, missing `title`, invalid `status`, missing implementation plan, and broken relative links.
    - `test_validate_okf_knowledge(tmp_path)`: Test success cases, missing frontmatter, missing `type`, and broken links.
- **Implement Feature**:
  - In [`tools/validate.py`](../../../../tools/validate.py):
    - Extract link validation into a helper function `_validate_markdown_links(path: Path, body: str, body_start: int) -> list[Violation]`.
    - Implement `iter_okf_specs(flow_root: Path) -> Iterator[Path]`.
    - Implement `iter_okf_knowledge(flow_root: Path) -> Iterator[Path]`.
    - Implement `validate_okf_spec(path: Path) -> list[Violation]`.
    - Implement `validate_okf_knowledge(path: Path) -> list[Violation]`.
  - Code Snippet:
    ```python
    def _validate_markdown_links(path: Path, body: str, body_start: int) -> list[Violation]:
        """Helper to find and validate relative markdown links."""
        violations: list[Violation] = []
        body_no_code = re.sub(r"```.*?```", "", body, flags=re.DOTALL)
        body_no_code = re.sub(r"`.*?`", "", body_no_code)

        for match in LINK_PATTERN.finditer(body_no_code):
            target = match.group(2).split("#")[0].strip()
            if not target:
                continue
            if target.startswith(("http://", "https://", "mailto:", "tel:")):
                continue
            # Resolve relative target against the directory of the markdown file
            resolved = (path.parent / target).resolve()
            if not resolved.exists():
                violations.append(Violation(path, body_start, f"broken link target: {target}"))
        return violations

    def iter_okf_specs(flow_root: Path) -> Iterator[Path]:
        """Scan flow_root / "bundles" / "specs" / * / spec.md"""
        specs_dir = flow_root / "bundles" / "specs"
        if specs_dir.is_dir():
            for sub in sorted(specs_dir.iterdir()):
                if sub.is_dir():
                    spec_file = sub / "spec.md"
                    if spec_file.is_file():
                        yield spec_file

    def iter_okf_knowledge(flow_root: Path) -> Iterator[Path]:
        """Scan flow_root / "bundles" / "knowledge" / ** / *.md (excluding index.md, log.md)"""
        knowledge_dir = flow_root / "bundles" / "knowledge"
        if knowledge_dir.is_dir():
            for path in sorted(knowledge_dir.rglob("*.md")):
                if path.name not in ("index.md", "log.md"):
                    yield path

    IMPLEMENTATION_PLAN_PATTERN = re.compile(r"^##\s+Implementation\s+Plan\b", re.IGNORECASE | re.MULTILINE)
    VALID_FLOW_STATUSES = frozenset({"pending", "in_progress", "completed", "blocked", "skipped"})

    def validate_okf_spec(path: Path) -> list[Violation]:
        """Validate OKF spec.md frontmatter and body."""
        violations: list[Violation] = []
        text = path.read_text(encoding="utf-8")
        try:
            fm, body_start, body = extract_frontmatter(text)
        except ValueError as exc:
            return [Violation(path, 1, str(exc))]

        if fm.get("type") != "flow":
            violations.append(Violation(path, 1, "frontmatter 'type' must be 'flow'"))

        expected_id = path.parent.name
        fm_id = fm.get("id")
        if fm_id != expected_id:
            violations.append(Violation(path, 1, f"frontmatter 'id' {fm_id!r} must match directory name {expected_id!r}"))

        title = fm.get("title") or fm.get("name")
        if not isinstance(title, str) or not title.strip():
            violations.append(Violation(path, 1, "frontmatter must contain a non-empty string 'title' or 'name'"))

        status = fm.get("status")
        if status not in VALID_FLOW_STATUSES:
            violations.append(Violation(path, 1, f"frontmatter 'status' {status!r} must be one of {sorted(VALID_FLOW_STATUSES)}"))

        if not IMPLEMENTATION_PLAN_PATTERN.search(body):
            violations.append(Violation(path, body_start, "missing required '## Implementation Plan' section"))

        violations.extend(_validate_markdown_links(path, body, body_start))
        return violations

    def validate_okf_knowledge(path: Path) -> list[Violation]:
        """Validate OKF knowledge base article."""
        violations: list[Violation] = []
        text = path.read_text(encoding="utf-8")
        try:
            fm, body_start, body = extract_frontmatter(text)
        except ValueError as exc:
            return [Violation(path, 1, str(exc))]

        if "type" not in fm or not isinstance(fm.get("type"), str) or not fm.get("type").strip():
            violations.append(Violation(path, 1, "frontmatter must contain a non-empty string 'type'"))

        violations.extend(_validate_markdown_links(path, body, body_start))
        return violations
    ```
- **Verification**:
  - Run the test suite:
    ```bash
    python -m pytest tests/test_validate_skills.py -k "okf"
    ```
  - Criteria: All new tests pass successfully.

### Task 4: Integrate new validation functions into the main command workflow
- **Target Files**:
  - [`tools/validate.py`](../../../../tools/validate.py#L1165-L1227)
- **Write Tests**:
  - In [`tests/test_validate_skills.py`](../../../../tests/test_validate_skills.py), write `test_main_integration_with_invalid_okf` to verify that `main()` exits with a non-zero code when there are OKF validation failures.
- **Implement Feature**:
  - In [`tools/validate.py`](../../../../tools/validate.py):
    - Update `main()` to fetch flow root, call `iter_okf_specs` and `iter_okf_knowledge` and validate each file, appending violations to `all_violations`.
    - Update `iter_all_shipped_files()` to yield paths from `iter_okf_specs(flow_root)` and `iter_okf_knowledge(flow_root)`.
- **Verification**:
  - Run the full validator command on the current codebase:
    ```bash
    python tools/validate.py
    ```
  - Run all validation tests:
    ```bash
    python -m pytest tests/test_validate_skills.py
    ```
  - Criteria: Both commands execute and pass without errors.

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
GUIDE_PATH = REPO_ROOT / "docs" / "git-notes.md"
STATE_PATH = REPO_ROOT / "skills" / "flow" / "references" / "state.md"
IMPLEMENT_PATH = REPO_ROOT / "skills" / "flow" / "references" / "implement.md"
FINISH_PATH = REPO_ROOT / "skills" / "flow" / "references" / "finish.md"
ARCHIVE_PATH = REPO_ROOT / "skills" / "flow" / "references" / "archive.md"
WORKFLOW_PATHS = (
    REPO_ROOT / "skills" / "flow-execution" / "SKILL.md",
    REPO_ROOT / "skills" / "flow-completion" / "SKILL.md",
    IMPLEMENT_PATH,
    FINISH_PATH,
    ARCHIVE_PATH,
    STATE_PATH,
)


def _git(
    repo: Path, *args: str, input_text: str | None = None, check: bool = True
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        check=check,
        capture_output=True,
        text=True,
        input=input_text,
    )


def _init_repo(path: Path) -> str:
    _git(path, "init", "-q")
    _git(path, "config", "user.name", "Flow Tests")
    _git(path, "config", "user.email", "flow-tests@example.invalid")
    tracked = path / "tracked.txt"
    tracked.write_text("functional change\n", encoding="utf-8")
    _git(path, "add", "tracked.txt")
    _git(path, "commit", "-q", "-m", "feat: functional change")
    return _git(path, "rev-parse", "HEAD").stdout.strip()


def _marked_yaml(path: Path, name: str) -> dict[str, Any]:
    content = path.read_text(encoding="utf-8")
    pattern = re.compile(
        rf"<!-- {re.escape(name)}: start -->\s*```yaml\s*(.*?)\s*```\s*"
        rf"<!-- {re.escape(name)}: end -->",
        re.DOTALL,
    )
    match = pattern.search(content)
    assert match is not None, f"missing {name} block in {path}"
    parsed = yaml.safe_load(match.group(1))
    assert isinstance(parsed, dict)
    return parsed


def _note_record(
    kind: str,
    subject_id: str,
    commit: str,
    *,
    rationale: str = "Fresh verification passed.",
) -> str:
    return yaml.safe_dump(
        {
            "version": 1,
            "kind": kind,
            "flow_id": "example-flow",
            "subject_id": subject_id,
            "operation_id": f"operation-{kind}",
            "attachment_attempt_id": (
                f"example-flow:{subject_id}:{commit}:refs/notes/flow"
            ),
            "plan_identity": {"revision": 3, "commit": None},
            "commit": commit,
            "changed_files": ["tracked.txt"],
            "verification": [
                {"command": "test command", "result": "passed", "exit_status": 0}
            ],
            "rationale": rationale,
        },
        explicit_start=True,
        sort_keys=False,
    )


def test_note_record_schema_is_versioned_and_closed() -> None:
    contract = _marked_yaml(GUIDE_PATH, "flow-git-notes-contract")

    assert contract["contract"] == "flow-git-note-v1"
    assert contract["authority"] == "tracked_markdown"
    assert contract["ref"] == "refs/notes/flow"
    assert contract["record"]["required"] == [
        "version",
        "kind",
        "flow_id",
        "subject_id",
        "operation_id",
        "attachment_attempt_id",
        "plan_identity",
        "commit",
        "changed_files",
        "verification",
        "rationale",
    ]
    assert contract["record"]["optional"] == ["manual_confirmation"]
    assert contract["record"]["unknown_fields"] == "refuse"
    assert contract["record"]["kind"] == {
        "task": "subject_id_is_task_id",
        "phase": "subject_id_is_phase_id",
    }
    assert contract["record"]["verification_item"] == {
        "required": ["command", "result", "exit_status"],
        "optional": [],
        "unknown_fields": "refuse",
    }


def test_git_notes_append_preserves_multiple_records(tmp_path: Path) -> None:
    commit = _init_repo(tmp_path)
    first = _note_record("task", "3.1", commit)
    second = _note_record("phase", "3", commit)

    _git(
        tmp_path,
        "notes",
        "--ref=refs/notes/flow",
        "append",
        "--file=-",
        commit,
        input_text=first,
    )
    _git(
        tmp_path,
        "notes",
        "--ref=refs/notes/flow",
        "append",
        "--file=-",
        commit,
        input_text=second,
    )

    note = _git(tmp_path, "notes", "--ref=refs/notes/flow", "show", commit).stdout
    assert first.strip() in note
    assert second.strip() in note
    assert note.index(first.strip()) < note.index(second.strip())
    records = list(yaml.safe_load_all(note))
    assert [record["kind"] for record in records] == ["task", "phase"]


def test_exact_attachment_retry_does_not_append_and_conflict_is_detected(
    tmp_path: Path,
) -> None:
    commit = _init_repo(tmp_path)
    record = _note_record("task", "3.1", commit)
    _git(
        tmp_path,
        "notes",
        "--ref=refs/notes/flow",
        "append",
        "--file=-",
        commit,
        input_text=record,
    )
    ref_before = _git(tmp_path, "rev-parse", "refs/notes/flow").stdout.strip()

    existing = list(
        yaml.safe_load_all(
            _git(
                tmp_path,
                "notes",
                "--ref=refs/notes/flow",
                "show",
                commit,
            ).stdout
        )
    )
    payload = yaml.safe_load(record)
    same_attempt = [
        item
        for item in existing
        if item["attachment_attempt_id"] == payload["attachment_attempt_id"]
    ]
    assert same_attempt == [payload]

    conflicting = yaml.safe_load(
        _note_record(
            "task",
            "3.1",
            commit,
            rationale="Different evidence for the same stable attempt.",
        )
    )
    assert conflicting["attachment_attempt_id"] == payload["attachment_attempt_id"]
    assert conflicting != same_attempt[0]
    assert _git(tmp_path, "rev-parse", "refs/notes/flow").stdout.strip() == ref_before

    contract = _marked_yaml(GUIDE_PATH, "flow-git-notes-contract")
    assert contract["attachment"]["git_note_preflight"] == {
        "same_attempt_same_record": "do_not_append_then_record_attached_result",
        "same_attempt_different_record": "conflict_without_writes",
        "attempt_absent": "append_once",
    }


def test_absent_notes_ref_does_not_affect_functional_commit_recovery(
    tmp_path: Path,
) -> None:
    commit = _init_repo(tmp_path)

    missing = _git(
        tmp_path,
        "notes",
        "--ref=refs/notes/flow",
        "show",
        commit,
        check=False,
    )

    assert missing.returncode != 0
    assert (
        _git(tmp_path, "show", "--format=%H", "--no-patch", commit).stdout.strip()
        == commit
    )
    contract = _marked_yaml(GUIDE_PATH, "flow-git-notes-contract")
    assert contract["portability"]["absent_ref"] == "continue_from_tracked_markdown"


def test_invalid_note_target_fails_without_creating_the_ref(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    result = _git(
        tmp_path,
        "cat-file",
        "-e",
        f"{'0' * 40}^{{commit}}",
        check=False,
    )

    assert result.returncode != 0
    assert (
        _git(
            tmp_path, "show-ref", "--verify", "refs/notes/flow", check=False
        ).returncode
        != 0
    )
    contract = _marked_yaml(GUIDE_PATH, "flow-git-notes-contract")
    assert contract["attachment"]["preflight"] == ("git cat-file -e <commit>^{commit}")



def test_attachment_order_replay_and_failure_contract_are_exact() -> None:
    contract = _marked_yaml(GUIDE_PATH, "flow-git-notes-contract")

    assert contract["attachment"]["command"] == (
        "git notes --ref=refs/notes/flow append --file=- <commit>"
    )
    assert contract["attachment"]["after_successful_operation"] == {
        "task": "close",
        "phase": "checkpoint",
    }
    assert contract["attachment"]["result_note_target"] == {
        "task": "subject_task_id",
        "phase": "first_affected_task_id_in_checkpoint_order",
    }
    assert contract["attachment"]["result_operation"] == "note.git_note_attachment"
    assert contract["attachment"]["attempt_id"] == (
        "<flow-id>:<task-or-phase-id>:<commit>:refs/notes/flow"
    )
    assert contract["attachment"]["replay"] == {
        "same_key_same_payload": "return_recorded_result_without_note_or_revision",
        "same_key_different_payload": "conflict_without_writes",
    }
    assert contract["attachment"]["failure"] == (
        "record_failed_result_without_reopening_task_or_checkpoint"
    )


def test_phase_notes_target_last_functional_commit_without_empty_commit(
    tmp_path: Path,
) -> None:
    first_commit = _init_repo(tmp_path)
    tracked = tmp_path / "tracked.txt"
    tracked.write_text(
        "functional change\nsecond functional change\n", encoding="utf-8"
    )
    _git(tmp_path, "add", "tracked.txt")
    _git(tmp_path, "commit", "-q", "-m", "feat: second functional change")
    last_functional_commit = _git(tmp_path, "rev-parse", "HEAD").stdout.strip()
    assert last_functional_commit != first_commit

    _git(
        tmp_path,
        "notes",
        "--ref=refs/notes/flow",
        "append",
        "--file=-",
        last_functional_commit,
        input_text=_note_record("phase", "3", last_functional_commit),
    )

    targets = _git(tmp_path, "notes", "--ref=refs/notes/flow", "list").stdout.split()
    assert last_functional_commit in targets
    assert first_commit not in targets
    contract = _marked_yaml(GUIDE_PATH, "flow-git-notes-contract")
    assert contract["phase"]["target"] == "last_functional_commit"
    assert contract["phase"]["checkpoint_commit"] == "forbidden"


def test_state_and_lifecycle_docs_require_markdown_first_evidence() -> None:
    state = STATE_PATH.read_text(encoding="utf-8")
    implement = IMPLEMENT_PATH.read_text(encoding="utf-8")
    finish = FINISH_PATH.read_text(encoding="utf-8")
    archive = ARCHIVE_PATH.read_text(encoding="utf-8")

    for content in (state, implement):
        assert "close request" in content
        assert "verification_evidence" in content
        assert "only after" in content.lower()
        assert "git note" in content.lower()
    for content in (state, implement, finish):
        assert "checkpoint" in content
        assert "last functional commit" in content.lower()
        assert "empty checkpoint commit" in content.lower()
    assert "Git notes" in archive
    assert "supplementary" in archive
    assert "recovery" in archive


def test_installed_workflows_never_push_flow_notes_automatically() -> None:
    automatic_push = re.compile(r"git\s+push[^\n]*refs/notes/flow")
    violations = [
        str(path.relative_to(REPO_ROOT))
        for path in WORKFLOW_PATHS
        if automatic_push.search(path.read_text(encoding="utf-8"))
    ]
    assert not violations

    guide = GUIDE_PATH.read_text(encoding="utf-8")
    assert "fresh, explicit permission" in guide
    assert "git push <remote> refs/notes/flow:refs/notes/flow" in guide


def test_git_tags_are_forbidden_as_evidence_or_fallback() -> None:
    contract = _marked_yaml(GUIDE_PATH, "flow-git-notes-contract")
    assert contract["git_tags"] == {
        "mutation": "forbidden",
        "fallback_for_notes": "forbidden",
        "state_or_evidence_transport": "forbidden",
    }

    for path in WORKFLOW_PATHS:
        content = re.sub(r"\s+", " ", path.read_text(encoding="utf-8"))
        assert "Never create or mutate Git tags" in content

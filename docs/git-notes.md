# Flow Git Notes

Flow may attach detailed task or phase verification evidence to the functional
commit it describes. These Git notes are supplementary audit records only:
tracked Markdown remains the authority for lifecycle state, verification,
continuity, and recovery. A missing notes ref never blocks normal work.

## Record contract

Each appended document is one UTF-8 YAML record beginning with `---`. The
explicit document marker keeps multiple appended records a valid YAML stream.
The schema is closed so a reader can reject ambiguous evidence instead of
guessing.

<!-- flow-git-notes-contract: start -->
```yaml
contract: flow-git-note-v1
authority: tracked_markdown
ref: refs/notes/flow
record:
  encoding: utf8_yaml_document_with_explicit_start
  required: [version, kind, flow_id, subject_id, operation_id, attachment_attempt_id, plan_identity, commit, changed_files, verification, rationale]
  optional: [manual_confirmation]
  unknown_fields: refuse
  version: 1
  kind:
    task: subject_id_is_task_id
    phase: subject_id_is_phase_id
  plan_identity:
    required: [revision, commit]
    optional: []
    unknown_fields: refuse
  changed_files: unique_sorted_repository_relative_paths
  verification_item:
    required: [command, result, exit_status]
    optional: []
    unknown_fields: refuse
  manual_confirmation:
    required: [text, confirmed_by, confirmed_at]
    optional: []
    unknown_fields: refuse
attachment:
  preflight: git cat-file -e <commit>^{commit}
  command: git notes --ref=refs/notes/flow append --file=- <commit>
  overwrite_commands: forbidden
  after_successful_operation:
    task: close
    phase: checkpoint
  result_note_target:
    task: subject_task_id
    phase: first_affected_task_id_in_checkpoint_order
  result_operation: note.git_note_attachment
  attempt_id: <flow-id>:<task-or-phase-id>:<commit>:refs/notes/flow
  git_note_preflight:
    same_attempt_same_record: do_not_append_then_record_attached_result
    same_attempt_different_record: conflict_without_writes
    attempt_absent: append_once
  replay:
    same_key_same_payload: return_recorded_result_without_note_or_revision
    same_key_different_payload: conflict_without_writes
  failure: record_failed_result_without_reopening_task_or_checkpoint
phase:
  target: last_functional_commit
  checkpoint_commit: forbidden
portability:
  absent_ref: continue_from_tracked_markdown
  fetch_is_optional: true
  push_is_manual_permission_only: true
git_tags:
  mutation: forbidden
  fallback_for_notes: forbidden
  state_or_evidence_transport: forbidden
```
<!-- flow-git-notes-contract: end -->

`kind: task` uses the Flow task short id as `subject_id`; `kind: phase` uses the
phase id. `operation_id` is the successful `close` or phase `checkpoint`
operation. `attachment_attempt_id` uses the stable id below. `plan_identity` is
the exact `revision` and nullable `commit` from that operation. `commit` must
equal the existing functional commit named by the Markdown evidence. Every
`verification` item records the exact command, result, and integer exit status.
`rationale` explains why the evidence is relevant. `manual_confirmation` is
included only when a manual check was actually made.

## Attachment sequence

1. Put compact verification evidence in the task `close` request or phase
   `checkpoint` request. The state sidecar writes it together with operation
   metadata in its one Markdown transaction.
2. Reread the committed sidecar result. Stop if it did not succeed.
3. Validate the target with `git cat-file -e <commit>^{commit}`. For phase
   evidence, use the checkpoint payload's last functional commit; never create
   an empty checkpoint commit.
4. Read and parse any existing note as the explicit-start YAML stream. If the
   same `attachment_attempt_id` has the exact same record, do not append it;
   proceed to record the attached result. If that id has a different record,
   stop with a conflict and write nothing. Only an absent id may continue.
5. Serialize the detailed record and append it with:

   ```bash
   git notes --ref=refs/notes/flow append --file=- <commit>
   ```

   `append` preserves existing records on the commit. Do not use `add -f`,
   `remove`, `prune`, or `update-ref` in the attachment workflow.
6. Whether attachment succeeds or fails, request the canonical idempotent
   `note(category=git_note_attachment)` operation with the stable attempt id,
   ref, commit, `attached|failed` result, and exact diagnostic. Attachment
   failure does not reopen the task or invalidate the phase checkpoint. A task
   result targets that task. A phase result targets the first id in the
   checkpoint's already sorted `affected_task_ids`.

The first attachment-result request for an attempt id appends one Markdown
entry and increments state once. An exact same-key/same-payload replay returns
the recorded result without appending a Git note, creating a journal, or
incrementing the tracked revision. The same key with a different payload is a
conflict and writes nothing.

## Reading and transport

List or read local evidence explicitly:

```bash
git notes --ref=refs/notes/flow list
git notes --ref=refs/notes/flow show <commit>
```

Notes refs are not transferred by normal branch fetches. A reader may fetch the
optional ref explicitly when the remote is trusted:

```bash
git fetch <remote> refs/notes/flow:refs/notes/flow
```

If the ref is absent, continue from tracked Markdown. Do not reconstruct state
from a note and do not treat missing detailed evidence as a recovery failure.

Pushing notes is outside every normal Flow workflow. Only after the user gives
fresh, explicit permission for that exact remote and repository may a person
manually run:

```bash
git push <remote> refs/notes/flow:refs/notes/flow
```

Flow never runs or recommends an automatic notes push.

## No Git tags

Flow never creates, moves, overwrites, or deletes Git tags. A tag is never a
fallback when `refs/notes/flow` is absent, cannot be fetched, or cannot be
written. Continue from tracked Markdown and record the optional attachment
failure through the state sidecar instead.

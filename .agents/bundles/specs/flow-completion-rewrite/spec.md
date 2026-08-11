---
type: flow
id: flow-completion-rewrite
title: Flow Completion & Knowledge Base Synthesis
description: Rewrite flow completion and archiving commands to synthesize task notes
  into the knowledge base and remove active specs.
status: completed
parent_prd: remove-beads
created_at: '2026-07-09T00:27:32+00:00'
updated_at: '2026-08-11T23:14:32.495787Z'
flow_id: flow-completion-rewrite
---

# Flow: flow-completion-rewrite

## Goal
Rewrite flow completion and archiving commands to synthesize task notes into the knowledge base and remove active specs.

## Specification

This flow rewrites `/flow:finish` and `/flow:archive` to synthesize task notes and designs into formal knowledge base articles and clean up the active workspace under the Beads-free OKF layout.

### Requirements

1. **Finish Command (`/flow:finish`)**:
   - Scans all task files `.agents/bundles/specs/{flow_id}/tasks/*.md` to verify that their `status` is either `closed` or `skipped`.
   - Halts and warns the user if any task is still open.
   - Marks `.agents/bundles/specs/{flow_id}/spec.md` frontmatter status as `completed` and updates `updated_at`.
   - Replaces all legacy Beads dependencies (`bd close`, `bd show`, etc.) with file-based metadata checking.

2. **Archiving (`/flow:archive`)**:
   - Scans task files under `.agents/bundles/specs/{flow_id}/tasks/*.md`.
   - Synthesizes findings, code paths, and architectural decisions into structured articles under the global Knowledge Base directory (`.agents/bundles/knowledge/`).
   - Group learnings by topic and map them to subfolders: `workflow/`, `product/`, `code-styleguides/`, `patterns/`.
   - Recursively deletes the active flow spec directory `.agents/bundles/specs/{flow_id}/` from the filesystem (no `archive/` folder creation).
   - Stages and commits the synthesized knowledge base updates, while removing the active spec from git.

3. **Revert command (`/flow:revert`)**:
   - Restores a deleted flow by executing `git checkout HEAD -- .agents/bundles/specs/{flow_id}`.
   - Sets the restored spec's status to `in_progress` in frontmatter.
   - Reverts a task or phase by identifying the Git commits recorded in task frontmatter files and running `git revert --no-commit` on them in reverse order, setting task status back to `open` and commit to `null`.
   - Removes all Beads operations and uses local file checkouts instead.

---

## Implementation Plan

### Phase 1: Python Completion Tooling (`tools/flow_completion.py`)

- [x] Task 1.1: Write unit tests for the completion helper script [09fb75a]
  - **Target Files**:
    - [tests/test_flow_completion.py](../../../../tests/test_flow_completion.py)
  - **Implementation Details**:
    - Write test cases using `pytest` and standard library `unittest.mock`.
    - Stub a temporary spec layout using the pytest `tmp_path` fixture.
    - Define `test_consolidate(tmp_path)`:
      - Create a test flow directory `specs/test-flow/tasks/` under `tmp_path`.
      - Write a markdown task file `001-test.md` containing frontmatter (`status: closed`, `commit: abc1234`, `files: [src/test.py]`) and a `## Notes & Discoveries` header with some content.
      - Write a second markdown task file `002-test.md` containing frontmatter (`status: closed`, `commit: def5678`, `files: [src/test2.py]`) and a `## Learnings` header with some content.
      - Run the consolidation function from `flow_completion.py` pointing to `tmp_path`.
      - Verify that `specs/test-flow/extracted_learnings.md` is created and contains the consolidated text of both tasks.
    - Define `test_delete_safety(tmp_path)`:
      - Create a test flow directory with one open task (`status: open`).
      - Verify that running delete raises `ValueError`.
      - Verify that running delete with `force=True` succeeds and deletes the spec directory.
    - Define `test_revert_delete(tmp_path)`:
      - Mock `subprocess.run` to assert it calls `git checkout HEAD -- .agents/bundles/specs/test-flow`.
  - **Verification**:
    - Run the tests:
      ```bash
      pytest tests/test_flow_completion.py
      ```

- [x] Task 1.2: Implement the completion helper script [09fb75a]
  - **Target Files**:
    - [tools/flow_completion.py](../../../../tools/flow_completion.py)
  - **Implementation Details**:
    - Create the CLI using `argparse` supporting commands: `consolidate`, `delete`, and `revert-delete`.
    - Add positional arguments: `flow_id` and optional `--force` flag for the delete command.
    - Implement `consolidate(flow_id: str)`:
      - Set the base specs directory to `.agents/bundles/specs`.
      - Read all task files matching `.agents/bundles/specs/{flow_id}/tasks/*.md` sorted by filename.
      - Extract the YAML frontmatter (lines between the first `---` and second `---`) and load using `yaml.safe_load`.
      - Search the task content for headings `## Notes & Discoveries` or `## Learnings` (case-insensitive) using regex `r"(?i)^##\s+(?:Notes\s+&\s+Discoveries|Learnings)\b"`.
      - Extract all text following the matched header until the next H2 heading (`## `) or end of file.
      - Format consolidated learnings into `.agents/bundles/specs/{flow_id}/extracted_learnings.md` listing the task ID, title, status, commit, files list, and the extracted notes.
    - Implement `delete(flow_id: str, force: bool = False)`:
      - If `force` is False, inspect all task files under `.agents/bundles/specs/{flow_id}/tasks/*.md`.
      - Check that each task's frontmatter contains `status: closed` or `status: skipped`.
      - If any task is in another state, print a validation error and exit with code 1.
      - Delete the entire directory `.agents/bundles/specs/{flow_id}/` using `shutil.rmtree`.
    - Implement `revert_delete(flow_id: str)`:
      - Run `git checkout HEAD -- .agents/bundles/specs/{flow_id}` using `subprocess.run(check=True)`.
      - Catch `subprocess.CalledProcessError` and print a descriptive error: "Flow spec folder was not committed/tracked in Git. Cannot auto-restore." and exit with code 1.
  - **Verification**:
    - Run the test suite:
      ```bash
      pytest tests/test_flow_completion.py
      ```
    - Verify CLI help options:
      ```bash
      python3 tools/flow_completion.py -h
      ```

---

### Phase 2: Command & Reference Refactoring

- [x] Task 2.1: Refactor the `/flow:finish` command and reference documentation [477fac8]
  - **Target Files**:
    - [commands/flow-finish.md](../../../../commands/flow-finish.md)
    - [commands/flow/finish.toml](../../../../commands/flow/finish.toml)
    - [skills/flow/references/finish.md](../../../../skills/flow/references/finish.md)
  - **Implementation Details**:
    - In `commands/flow-finish.md`:
      - Remove the Beads mode gate note at lines 9-11.
      - Under `3.0 Verification & Sync`, replace the Beads Finalization section. Define the new task verification workflow: read all files under `.agents/bundles/specs/{flow_id}/tasks/*.md` to ensure they are marked as closed/skipped.
      - Under `7.0 Cleanup`, remove `bd close`. Replace with: "Mark spec complete by editing the frontmatter of `.agents/bundles/specs/{flow_id}/spec.md` to `status: completed` and updating `updated_at`, then suggest running `/flow:archive {flow_id}`."
    - In `commands/flow/finish.toml`:
      - Rewrite the `prompt` string to instruct the executor on the new Beads-free file-based validation flow (validating status of files in `.agents/bundles/specs/{flow_id}/tasks/*.md`, editing the frontmatter of `spec.md`, and suggesting `/flow:archive {flow_id}`).
    - In `skills/flow/references/finish.md`:
      - Rewrite Phase 1: remove Beads show and list commands. Instruct to check all task files in `.agents/bundles/specs/{flow_id}/tasks/*.md`.
      - Rewrite Phase 3 (Code Review): instruct to find the Git range without Beads:
        ```bash
        git log --oneline $(git merge-base main HEAD)..HEAD
        ```
      - Remove Phase 6 (Beads Cleanup).
  - **Verification**:
    - Run validation checking commands and references:
      ```bash
      python3 tools/validate.py
      ```

- [x] Task 2.2: Refactor the `/flow:archive` command and reference documentation [477fac8]
  - **Target Files**:
    - [commands/flow-archive.md](../../../../commands/flow-archive.md)
    - [commands/flow/archive.toml](../../../../commands/flow/archive.toml)
    - [skills/flow/references/archive.md](../../../../skills/flow/references/archive.md)
  - **Implementation Details**:
    - In `commands/flow-archive.md`:
      - Under Phase 1: remove `bd show`. Verify flow is completed by checking `status: completed` in `.agents/bundles/specs/{flow_id}/spec.md`.
      - Under Phase 3: rewrite the knowledge synthesis to describe running `python3 tools/flow_completion.py consolidate {flow_id}` and merging learnings from `extracted_learnings.md` into appropriate folders in `.agents/bundles/knowledge/` (`workflow/`, `product/`, `code-styleguides/`, `patterns/`).
      - Under Phase 4: remove the instructions for moving to `archive/` folders. Instruct to delete the specs directory by running `python3 tools/flow_completion.py delete {flow_id}`.
      - Under Phase 5: remove registry updates to `flows.md` (registry is dynamic).
      - Under Phase 6: remove all Beads epic closing commands.
      - Under Phase 7: update Git commands to commit knowledge base additions and remove spec directory from tracking:
        ```bash
        git add .agents/bundles/knowledge/
        git rm -r .agents/specs/{flow_id}
        git commit -m "chore(archive): synthesize learnings from {flow_id} and archive spec"
        ```
    - In `commands/flow/archive.toml`:
      - Rewrite `prompt` to match the updated archive sequence (Consolidate -> Synthesize Knowledge -> Delete active spec folder -> Git commit changes).
    - In `skills/flow/references/archive.md`:
      - Rewrite sections to align with the new archive-deletion workflow, avoiding all Beads references.
  - **Verification**:
    - Run validation:
      ```bash
      python3 tools/validate.py
      ```

- [x] Task 2.3: Refactor the `/flow:revert` command and reference documentation [477fac8]
  - **Target Files**:
    - [commands/flow-revert.md](../../../../commands/flow-revert.md)
    - [commands/flow/revert.toml](../../../../commands/flow/revert.toml)
    - [skills/flow/references/revert.md](../../../../skills/flow/references/revert.md)
  - **Implementation Details**:
    - In `commands/flow-revert.md`:
      - Replace references to Beads commands under Phase 5.
      - Reverting a deleted flow: run `python3 tools/flow_completion.py revert-delete {flow_id}`, update frontmatter status to `in_progress`.
      - Reverting a task: read task file `.agents/bundles/specs/{flow_id}/tasks/{task_id}.md` to get commit SHA from YAML frontmatter. Run `git revert --no-commit {commit_sha}`. Update frontmatter status to `open` and commit to `null`.
      - Reverting a phase: parse `.agents/bundles/specs/{flow_id}/spec.md` to find phase tasks. Read their frontmatters to get commits. Run `git revert --no-commit` on all commits in reverse order. Update all tasks to status `open` and commit `null`.
    - In `commands/flow/revert.toml`:
      - Rewrite the `prompt` string to guide the revert executor on the file-based target resolution, restoring deleted folders using `revert-delete`, and reverting task commits, completely removing Beads.
    - In `skills/flow/references/revert.md`:
      - Update references and example commands to match the file-based and Git revert implementation.
  - **Verification**:
    - Run validation:
      ```bash
      python3 tools/validate.py
      ```

- [x] Task 2.4: Update the `flow-completion` lifecycle skill [477fac8]
  - **Target Files**:
    - [skills/flow-completion/SKILL.md](../../../../skills/flow-completion/SKILL.md)
  - **Implementation Details**:
    - Under `Workflow`, replace verification instructions with scanning `.agents/bundles/specs/{flow_id}/tasks/*.md` files and updating `spec.md` frontmatter.
    - Under `Guardrails`, remove references to Beads and update to mention active spec folder deletion on archive.
    - Under `References Index`, adjust references links to target the new refactored reference markdown files.
  - **Verification**:
    - Run validation check:
      ```bash
      python3 tools/validate.py
      ```

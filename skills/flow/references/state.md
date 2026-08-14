# Flow Markdown State Contract

This document is the normative contract for Flow plan identity, lifecycle state, continuity, state operations, and recoverable Markdown transactions. Lifecycle procedures link here instead of restating or weakening these rules. Task files are authoritative for task state; `spec.md` carries global identity and derived checklist/snapshot state.

Consumer agents perform every state operation and recovery with ordinary file read/write/edit tools. Python in `tools/` is repository-development support for validation, generation, and tests only; no consumer operation, recovery path, hook, skill, or agent prompt may require Python, `uv`, shell, PowerShell, a Flow executable, a task database, daemon, or hidden service.

## Root resolution

`<configured-root>` is the normalized repository-relative `root_directory` read from `.agents/setup-state.json`, or `.agents/` when that file is absent. `<bundle-root>` is `bundles_dir` from `<configured-root>/config.json`, resolved relative to `<configured-root>`, or `<configured-root>/bundles` by default. `<flow-root>` is `<bundle-root>/specs/<flow_id>`.

All three roots must remain inside the repository, contain no `..`, and traverse no symlink. Absolute, escaping, or invalid roots refuse before any state read or write. A journal records all three resolved repository-relative roots before a spec can disappear. Transaction journals live only at `<configured-root>/tasks/transactions/<operation-id>/journal.md`; there is no fixed `.agents/tasks/` exception.

## Contract enums and defaults

```yaml
spec_states: [planned, active, completed]
task_states: [open, in_progress, closed, blocked, skipped]
priorities: [P0, P1, P2, P3, P4]
default_priority: P2
recoverable_journal_states: [prepared, task_writes_started, recovery_required, rollback_in_progress]
nonterminal_journal_states: [prepared, task_writes_started, recovery_required, contended, rollback_in_progress]
terminal_journal_states: [committed, rolled_back, superseded]
```

## Normative documents

### Spec frontmatter

```yaml
---
type: Spec
flow_id: user-auth
title: User Authentication
state: planned
plan_revision: 1
plan_commit: null
state_revision: 0
current_task: null
last_operation: null
operation_targets: []
last_verified_checkpoint: null
created_at: 2026-08-11T12:00:00Z
updated_at: 2026-08-11T12:00:00Z
description: Add repository-native authentication.
---
```

Spec `state` is exactly `planned|active|completed`. Archive removes the spec directory after a committed archive transaction; no resident spec has `state: archived`. `plan_commit`, `current_task`, `last_operation`, and `last_verified_checkpoint` default to `null`; `operation_targets` defaults to `[]`; `state_revision` starts at `0`.

### Task frontmatter

```yaml
---
type: Task
id: user-auth:1.1
title: Add login endpoint
state: open
priority: P2
verification_strategy: behavior_tdd
depends_on: []
files: [src/auth.py]
tests: [tests/test_auth.py]
plan_revision: 1
plan_commit: null
state_revision: 0
claimed_by: null
claimed_at: null
blocked_reason: null
unblock_condition: null
next_step: null
last_operation: null
operation_targets: []
last_verified_at: null
last_verified_commit: null
verification_evidence: null
created_at: 2026-08-11T12:00:00Z
updated_at: 2026-08-11T12:00:00Z
commit: null
---
```

Task `state` is exactly `open|in_progress|closed|blocked|skipped`. Priority is the closed enum `P0|P1|P2|P3|P4`, defaults to `P2`, and is ordered in that sequence. Any other value refuses validation. Ready tasks are open tasks whose dependencies are all closed, ordered `(priority, created_at, task_id)`. Nullable claim, block, next-step, operation, verification, and commit fields default to `null`; `operation_targets` defaults to `[]`; `state_revision` starts at `0`.

`verification_strategy` is exactly one of `behavior_tdd|regression_tdd|characterization|static_validation|documentation_validation|integration_acceptance`. Observable behavior/regression work begins with a focused failing test; behavior-preserving cleanup establishes characterization first; generated/configuration/static documentation work uses native validation without manufacturing a low-signal red test; integration acceptance runs its declared end-to-end evidence.

### Required bodies

Every task is a complete worksheet with these headings: `## Objective`, `## Context`, `## Steps`, `## Verification`, and `## Acceptance Criteria`. A stub is not Ready. Every task also has append-only `## Notes & Discoveries`; entries are timestamped and existing entries are never rewritten.

Every executable spec has an `## Implementation Plan` checklist and `## Continuity Snapshot`. The snapshot records active flow/lifecycle, current task and claimant, last verified checkpoint, decisions, the five newest discoveries, blockers and unblock conditions, next exact step, plan identity, state identity, and relevant rule/knowledge paths. Verification records live under `## Verification Evidence` in the affected task or spec and name scope, commit, exact command/result evidence, summary, operation id, actor, and time.

Checklist markers are derived from task files: `open -> [ ]`, `in_progress -> [~]`, `closed -> [x]` plus commit, `blocked -> [!]`, and `skipped -> [-]`. A task-file/spec mismatch is reconciled to task-file truth only through `reconcile`; agents never flip a checklist marker as an independent mutation.

## Identity and revision invariants

`plan_revision` starts at `1`, is copied into the spec and every task, and increments once whenever an approved `revise` changes plan-bearing content: spec scope/decisions or a task's title, priority, dependencies, files, tests, verification strategy, Objective, Context, Steps, Verification, or Acceptance Criteria. The revision transaction updates all task copies before the spec. `plan_commit` is `null` until that approved revision is committed, then is the same 7-40 lowercase hexadecimal commit in the spec and every task. State-only operations never change plan identity.

Each successful mutation increments the spec `state_revision` exactly once. A task-targeting mutation writes that identical revision, `last_operation`, `operation_targets`, and `updated_at` to every target task and then the spec. Untouched tasks keep their prior revision. Every task always satisfies `0 <= task.state_revision <= spec.state_revision`. A spec-only mutation changes only spec state identity and uses `operation_targets: []`; affected task ids belong in typed evidence, not targets. Recovery finishes or reverses the original revision and never creates another tracked revision. New-flow `create` initializes revision `0`; read-only `status` creates no operation id or revision.

## Exact operation contract

The operation set is `create`, `activate`, `claim`, `release`, `note`, `discover`, `block`, `unblock`, `checkpoint`, `close`, `skip`, `reopen`, `revise`, `reconcile`, `complete`, `archive`, `recover`, and `status`. Every mutating request for an existing flow supplies `flow_id`, operation, actor, canonical UTC `occurred_at`, expected plan revision/commit, expected spec state revision, explicit task targets, and the exact operation payload. The `flow-reconciler` applies the request literally or refuses it; lifecycle reasoning belongs to the planner/executor.

Flow lifecycle guards apply before row-specific rules. Task `create` and `revise` require `planned|active`; `activate` requires `planned`; `claim`, `release`, normal `note`, `discover`, `block`, `unblock`, task/phase `checkpoint`, `close`, `skip`, `reopen`, and `reconcile` require `active`; plan-bind `checkpoint` permits `planned|active`; `complete` requires `active`; and `archive` requires `completed`. In `completed`, only `status`, `recover`, `archive`, and `note(category=git_note_attachment)` are legal. Removed/archived flows are addressable only by recovery through an unresolved archive journal.

“Append note” means append a timestamped bullet containing operation id, category, and text under `## Notes & Discoveries`. “Clear claim/block/verification” sets every corresponding nullable field to `null`; it never omits fields.

| Operation | Allowed source -> result | Required payload and preconditions | Exact effects |
| --- | --- | --- | --- |
| `create` | absent flow -> `planned`; absent task -> `open` | Flow: id/title/description. Task: unique short id, complete worksheet, priority, strategy, dependencies/files/tests; dependencies exist and DAG stays acyclic. Expected plan/state identity is null. | Flow creates spec/snapshot/tasks at revision 0. Task creates the file at a new global state revision, adds `[ ]` in the declared chapter, preserves `current_task`; plan-bearing creation also increments plan revision, clears plan commit, and updates every task before spec. |
| `activate` | spec `planned` -> `active` | Ready validator/code-reviewer evidence, complete worksheets, no unresolved journal, `approval_evidence`, `next_step`; targets empty. | Increment spec revision, set active/empty targets, update snapshot lifecycle/next step. Do not claim or touch task identity. |
| `claim` | `open` -> `in_progress` | All dependencies closed; no other task/spec claim; target plan identity equals spec. | Set claim fields, clear block fields, set spec current task, `[~]`, snapshot claim and exact worksheet step; preserve checkpoint. |
| `release` | `in_progress` -> `open` | Sole current task, `reason`, `next_step`; actor is claimant or request records explicit user authorization. | Clear claim/spec current task, set next step, append release note, `[ ]`, snapshot no claim/next step; preserve checkpoint/evidence. |
| `note` | any non-archived task -> same | Non-empty `category`/`text`. Git-note category additionally requires stable attachment attempt id, ref, commit, result `attached|failed`, diagnostic. | Append normally; update recent discoveries only for current task. Git-note identical replay returns existing result without journal/revision; same key with different payload conflicts. Never alter claim/block/checkpoint/plan identity. |
| `discover` | any non-archived task -> same | `text`, `impact`, and `next_step` or `none`; contradictions request later block/revise. | Append discovery and optional task next step. Update current snapshot fields only for current task; non-current discovery changes only bounded discovery summary. Never change worksheet/lifecycle. |
| `block` | `open|in_progress` -> `blocked` | `blocked_reason`, `unblock_condition`, `next_step`; in-progress task is sole current task. | Set block fields and `[!]`; if current, clear claim/current task and update blocker/unblock/next step; otherwise preserve another claim/next step and add aggregate blocker. Preserve checkpoint. |
| `unblock` | `blocked` -> `open` | `resolution_evidence`, `next_step`; evidence satisfies recorded condition. | Append resolution, clear block fields, set next step and `[ ]`, remove aggregate blocker. Preserve other claim/snapshot step; use target step only if no claim. Never auto-claim. |
| `checkpoint` | task `in_progress` -> same; phase spec `active` -> same; plan-bind spec `planned|active` with null plan commit -> same | Task: sole claim, scope, commit, non-empty passed commands/results, summary. Phase: phase id, sorted affected ids, last functional commit, passed phase verification; tasks closed/skipped and no claim. Plan: strict `plan_bind_evidence` attests the commit and complete current spec/task contents; sidecar validates that evidence against live Markdown/plan identity using file reads only, with no Git/runtime inspection. | Task writes target verification and identical spec/snapshot checkpoint. Phase is spec-only with evidence/affected ids. Plan-bind targets every task sorted then spec, copying the attested commit and operation identity without lifecycle changes. Increment one state revision. |
| `close` | `in_progress` -> `closed` | Sole current claim; commit and fresh passed evidence bound to commit; acceptance criteria checked. | Set commit/evidence; clear claim/block/next step; `[x]` plus commit; clear current task; identical checkpoint and next ready action. Git-note attachment is later. |
| `skip` | `open|blocked` -> `skipped` | `reason` and fresh explicit user approval text/time; dependent open tasks remain coherent or separate revise accompanies it. | Clear claim/block/next step, `[-]`, append note, remove current task if applicable; preserve checkpoint. |
| `reopen` | `closed|skipped` -> `open` | `reason`, fresh approval, `next_step`, replacement checkpoint null or existing verified task checkpoint; plan/dependents consistent. | Append prior commit/evidence summary, clear commit/evidence/claim/block, set next step and `[ ]`, set spec/snapshot checkpoint exactly to payload. Plan identity changes only by separate revise. |
| `revise` | spec `planned|active` -> same | Exact plan diffs, rationale, reviewer findings, new plan revision old+1; optional state adjustments each satisfy their own row. | Apply plan diffs; update every task then spec to new plan revision/null commit; increment state revision once; reconcile checklist/snapshot; append decision note. No implicit close/skip. |
| `reconcile` | task/spec states unchanged | Expected mismatches and sorted affected task ids; task files authoritative; no unresolved journal or identity mismatch. | Spec-only/empty targets: update derived checklist/snapshot/status and record affected ids. Do not touch task metadata or plan revision. |
| `complete` | spec `active` -> `completed` | All tasks closed/skipped; no claim/block/journal; full verification and code review passed; mandatory quality review bound to exact final base/head has no unwaived Critical/Important finding; final commit and exact evidence/waivers. | Spec-only/empty targets: increment revision, completed, clear current task, preserve checkpoint, next archive synthesis. Never delete or attach/push notes. |
| `archive` | spec `completed` -> directory absent | Exact knowledge destinations/current-state edits, log entry `{date, flow_id, outcome, final_commit}`, notes incorporation, archive manifest, quality report on exact candidate with no unwaived Critical/Important finding; no unresolved journal. | Journal target revision old+1 with empty targets; write reviewed knowledge then log; delete recorded spec files then empty dirs; terminal only after absence/postconditions. Remediation invalidates candidate and requires fresh reviews. Never push or require Git history. |
| `recover` | journal `prepared|task_writes_started|recovery_required|rollback_in_progress` -> `committed|rolled_back` | Journal id, explicit `finish|rollback`, complete stage-aware live read set, dependencies/claims still valid; existing selected action matches. `contended` is not directly recoverable: arbitration proves it zero-write and supersedes it, or reports conflict. | Resume original revision and direction. Finish remaining after-fragments or reverse only applied writes. Do not increment revision, replace last operation, change direction, or create another mutation. Drift refuses without tracked writes. |
| `status` | read-only -> read-only | Optional flow/task filter only. | Read specs/tasks/journals; report current/ready/blocked/conflicts in `(priority, created_at, task_id)` order; write nothing and create no id/journal. |

## Operation identifiers

The id is `<YYYYMMDDTHHMMSSZ>-<actor-slug>-<operation>-<target-slug>-<00..99>`. Slugs use Unicode NFKD, discard combining marks/non-ASCII, lowercase, replace each non-`[a-z0-9]` run with `-`, trim `-`, and truncate actor/operation/id components to 32 characters. Empty actor becomes `agent`; empty normalized id becomes `item`. Targets sort by task id: zero uses `spec`; one its normalized id; multiple join the first three with `+` and append `+n<count>` when more than three, truncating the combined target slug to 64 characters. Absent-flow create uses requested flow id; status has no id.

Read the configured transaction directory and select the first free two-digit suffix. Exhausting all 100 suffixes for the exact timestamp/actor/operation/target refuses before writing; retry at a later real UTC second. Never wrap, overwrite, delete, or invent a future timestamp.

## Journal contract

The journal is untracked Markdown. The following claim journal is the exact minimum field/shape contract. Values are illustrative; consumers replace them with the complete live values prepared for the requested operation. Unknown top-level keys, missing keys, unqualified paths, incomplete predicates, and incomplete fragments refuse validation.

### Claim journal minimum shape

```yaml
type: FlowTransaction
version: 1
operation_id: 20260813T203342Z-flow-executor-claim-1-1-00
state: prepared
applied_writes: []
rolled_back_writes: []
events:
  - sequence: 0
    kind: prepared
    at: 2026-08-13T20:33:42Z
    observed_nonterminal_operation_ids: []
flow_id: conductor-flow-continuity
configured_root: .agents
bundle_root: .agents/bundles
flow_root: .agents/bundles/specs/conductor-flow-continuity
request:
  flow_id: conductor-flow-continuity
  operation: claim
  actor: flow-executor
  occurred_at: 2026-08-13T20:33:42Z
  expected_plan_revision: 1
  expected_plan_commit: null
  expected_state_revision: 1
  targets: ["1.1"]
  payload: {next_step: "execute Task 1.1 exactly from its worksheet"}
ordered_writes:
  - {base: flow_root, path: tasks/1.1.md}
  - {base: flow_root, path: spec.md}
read_set:
  - predicate: no_other_unresolved_journal
    directory: {base: configured_root, path: tasks/transactions}
    excluding_operation_id: 20260813T203342Z-flow-executor-claim-1-1-00
    observed_operation_ids: []
  - base: flow_root
    path: spec.md
    fields: {state: active, state_revision: 1, current_task: null, plan_revision: 1, plan_commit: null, last_operation: 20260813T203300Z-flow-executor-activate-spec-00, operation_targets: []}
  - base: flow_root
    path: tasks/1.1.md
    fields: {state: open, state_revision: 0, plan_revision: 1, plan_commit: null, claimed_by: null, claimed_at: null}
  - predicate: all_dependencies_closed
    target: {base: flow_root, path: tasks/1.1.md}
    dependency_paths: []
    observed_states: {}
  - predicate: no_other_in_progress_claim
    scope: {base: flow_root, glob: tasks/*.md}
    excluding: {base: flow_root, path: tasks/1.1.md}
    observed_task_ids: []
fragments:
  - base: flow_root
    path: tasks/1.1.md
    anchor: frontmatter
    before: {state: open, state_revision: 0, claimed_by: null, claimed_at: null, blocked_reason: null, unblock_condition: null, next_step: null, last_operation: null, operation_targets: [], updated_at: 2026-08-13T20:30:00Z}
    after: {state: in_progress, state_revision: 2, claimed_by: flow-executor, claimed_at: 2026-08-13T20:33:42Z, blocked_reason: null, unblock_condition: null, next_step: "execute Task 1.1 exactly from its worksheet", last_operation: 20260813T203342Z-flow-executor-claim-1-1-00, operation_targets: ["1.1"], updated_at: 2026-08-13T20:33:42Z}
  - base: flow_root
    path: spec.md
    anchor: frontmatter
    before: {state_revision: 1, current_task: null, last_operation: 20260813T203300Z-flow-executor-activate-spec-00, operation_targets: [], updated_at: 2026-08-13T20:33:00Z}
    after: {state_revision: 2, current_task: "1.1", last_operation: 20260813T203342Z-flow-executor-claim-1-1-00, operation_targets: ["1.1"], updated_at: 2026-08-13T20:33:42Z}
  - base: flow_root
    path: spec.md
    anchor: implementation-plan-task-1.1
    before: {checklist_marker: "[ ]", commit_suffix: null}
    after: {checklist_marker: "[~]", commit_suffix: null}
  - base: flow_root
    path: spec.md
    anchor: continuity-snapshot
    before: {current_task_claim: null, last_verified_checkpoint: null, next_exact_step: "claim Task 1.1", state_identity: {revision: 1, last_operation: 20260813T203300Z-flow-executor-activate-spec-00, operation_targets: []}}
    after: {current_task_claim: {task: "1.1", claimed_by: flow-executor}, last_verified_checkpoint: null, next_exact_step: "execute Task 1.1 exactly from its worksheet", state_identity: {revision: 2, last_operation: 20260813T203342Z-flow-executor-claim-1-1-00, operation_targets: ["1.1"]}}
```

The exact ordinary existing-document journal key set is `type`, `version`, `operation_id`, `state`, `applied_writes`, `rolled_back_writes`, `events`, `flow_id`, `configured_root`, `bundle_root`, `flow_root`, `request`, `ordered_writes`, `read_set`, and `fragments`. `request` is the sole request authority; its duplicated top-level aliases are forbidden. Plan-bind checkpoint additionally requires `file_fragments` and requires `fragments: []`. Create additionally requires `ordered_directories`, `applied_directories`, `rolled_back_directories`, and `file_fragments`. Archive additionally requires `target_state_revision`, `archive_inventory`, and `file_fragments`. No other top-level keys are permitted. An operation may require more read-set predicates/fragments than the example, but may not omit any semantic value it reads, checks, or changes.

The exact mutating request key set is `flow_id`, `operation`, `actor`, `occurred_at`, `expected_plan_revision`, `expected_plan_commit`, `expected_state_revision`, `targets`, and `payload`. Unknown/missing keys refuse. `occurred_at` is canonical UTC; targets are explicit, unique, and sorted; expected identity values match the live read set (`null` plan/state identity only for absent-flow create); and payload matches exactly one operation variant below. A journal's `flow_id` must equal `request.flow_id`.

### Operation payload schemas

Every schema below has `additional_keys: forbidden`. `required` and `optional` are the complete payload keysets. Constraints are conjunctive. Nested records also reject unknown keys and use the exact nested keysets named in constraints.

```yaml
create:
  flow:
    required: [variant, title, description]
    optional: []
    constraints: ["variant=flow", "targets=[]", "expected_plan_revision=null", "expected_plan_commit=null", "expected_state_revision=null", "title/description non-empty"]
  task:
    required: [variant, short_id, chapter_id, worksheet, priority, verification_strategy, depends_on, files, tests]
    optional: []
    constraints: ["variant=task", "targets=[short_id]", "short_id unique", "worksheet exact keys Objective|Context|Steps|Verification|Acceptance Criteria", "priority and verification_strategy use contract enums", "depends_on/files/tests unique arrays", "dependencies exist", "DAG acyclic"]
activate:
  required: [approval_evidence, next_step]
  optional: []
  constraints: ["targets=[]", "both non-empty"]
claim:
  required: [next_step]
  optional: []
  constraints: ["exactly one target", "next_step is exact first worksheet step and non-empty"]
release:
  required: [reason, next_step]
  optional: [user_authorization]
  constraints: ["exactly one target", "reason/next_step non-empty", "user_authorization exact keys text|at and required when actor differs from claimant"]
note:
  normal:
    required: [category, text]
    optional: []
    constraints: ["exactly one target", "category non-empty and not git_note_attachment", "text non-empty"]
  git_note_attachment:
    required: [category, text, attachment_attempt_id, ref, commit, result, diagnostic]
    optional: []
    constraints: ["category=git_note_attachment", "exactly one target", "text/attachment_attempt_id/ref/diagnostic non-empty", "commit is 7-40 lowercase hex", "result=attached|failed"]
discover:
  required: [text, impact, next_step]
  optional: []
  constraints: ["exactly one target", "text/impact non-empty", "next_step is non-empty string or null", "contradicting impact requests later block/revise"]
block:
  required: [blocked_reason, unblock_condition, next_step]
  optional: []
  constraints: ["exactly one target", "all values non-empty"]
unblock:
  required: [resolution_evidence, next_step]
  optional: []
  constraints: ["exactly one target", "both non-empty"]
checkpoint:
  task:
    required: [scope, commit, verification_evidence, summary]
    optional: []
    constraints: ["scope=task", "exactly one target", "commit is 7-40 lowercase hex", "verification_evidence is non-empty array of exact command|result records", "summary non-empty"]
  phase:
    required: [scope, phase_id, affected_task_ids, last_functional_commit, verification_evidence]
    optional: []
    constraints: ["scope=phase", "targets=[]", "phase_id non-empty", "affected_task_ids unique sorted non-empty", "last_functional_commit is 7-40 lowercase hex", "verification_evidence is non-empty array of exact command|result records"]
  plan:
    required: [scope, plan_bind_evidence]
    optional: []
    constraints: ["scope=plan", "targets are every task id sorted", "plan_bind_evidence matches the strict schema and live Markdown"]
close:
  required: [commit, verification_evidence, acceptance_criteria_checked]
  optional: []
  constraints: ["exactly one target", "commit is 7-40 lowercase hex", "verification_evidence is non-empty array of exact command|result records bound to commit", "acceptance_criteria_checked is exact non-empty array of criterion ids"]
skip:
  required: [reason, user_approval]
  optional: []
  constraints: ["exactly one target", "reason non-empty", "user_approval exact keys text|at with both non-empty"]
reopen:
  required: [reason, user_approval, next_step, replacement_checkpoint]
  optional: []
  constraints: ["exactly one target", "reason/next_step non-empty", "user_approval exact keys text|at", "replacement_checkpoint is null or existing verified task checkpoint"]
revise:
  required: [plan_diffs, rationale, reviewer_findings, new_plan_revision, state_adjustments]
  optional: []
  constraints: ["targets are every task whose plan identity/content changes, sorted", "plan_diffs is non-empty array of exact base|path|anchor|before|after records", "rationale non-empty", "reviewer_findings array", "new_plan_revision=expected_plan_revision+1", "state_adjustments array and every entry is an exact legal operation request except revise"]
reconcile:
  required: [mismatches, affected_task_ids]
  optional: []
  constraints: ["targets=[]", "mismatches non-empty array of exact path|field|spec_value|task_value records", "affected_task_ids unique sorted"]
complete:
  required: [final_functional_commit, verification_evidence, code_review_evidence, quality_review, waivers]
  optional: []
  constraints: ["targets=[]", "final_functional_commit is 7-40 lowercase hex", "verification_evidence non-empty command|result records", "code_review_evidence exact reviewer|base_commit|head_commit|findings record", "quality_review exact reviewer|base_commit|head_commit|findings record and range equals final candidate", "waivers exact finding_id|approval_text|approved_at records and only finding-specific fresh user waivers"]
archive:
  required: [knowledge_destinations, synthesized_edits, log_entry, notes_incorporation, archive_candidate_manifest, quality_report, waivers]
  optional: []
  constraints: ["targets=[]", "knowledge_destinations unique sorted bundle-root paths", "synthesized_edits exact path|before|after complete-content records", "log_entry exact keys date|flow_id|outcome|final_commit", "notes_incorporation exact task_id|note_ids|destinations records", "archive_candidate_manifest exact base_commit|head_commit|inventory|file_fragments record", "quality_report exact reviewer|base_commit|head_commit|findings record on candidate range", "waivers exact finding_id|approval_text|approved_at records"]
recover:
  required: [journal_operation_id, action]
  optional: []
  constraints: ["targets=[]", "journal_operation_id equals selected journal", "action=finish|rollback", "action equals prior recovery_selected when present"]
```

### Plan-bind evidence schema

The committing executor/reviewer supplies this attestation; the sidecar does not run Git, shell, Python, or another runtime and does not inspect a commit tree.

```yaml
required: [evidence_id, commit, inventory, documents, verifier]
optional: []
inventory:
  item_schema: {required: [base, path], optional: [], constraints: ["base=flow_root", "path is spec.md or tasks/<short-id>.md"]}
  constraints: ["complete unique sorted flow-relative inventory", "spec.md first then tasks sorted by short id", "equals live spec.md plus tasks/*.md"]
documents:
  item_schema: {required: [base, path, plan_revision, plan_commit, content_utf8_lf], optional: [], constraints: ["base=flow_root", "path occurs once in inventory", "plan_revision equals expected plan revision", "plan_commit=null", "content_utf8_lf equals complete live file"]}
  constraints: ["one document per inventory path in identical order", "no omitted or extra path"]
verifier:
  required: [actor, verified_at, result]
  optional: []
  constraints: ["actor non-empty", "verified_at canonical UTC", "result=verified_against_commit", "verifier attests commit contains exact documents"]
constraints: ["unknown keys forbidden recursively", "evidence_id non-empty and stable", "commit is 7-40 lowercase hex", "sidecar compares inventory/documents/identity to live Markdown using file reads only"]
initial_bind:
  request_identity: "complete exact journal request, including stable evidence_id"
  live_precondition: "every live path/content/plan identity equals documents and expected request identity"
  journal_file_fragment_schema:
    required: [base, path, before, after]
    optional: []
    before_after_required: [exists, content_utf8_lf]
    constraints: ["base=flow_root", "path equals its inventory entry", "before.exists=true", "after.exists=true", "before/after content_utf8_lf are complete exact files", "unknown keys forbidden recursively"]
  journal_file_fragments: "one per inventory path in identical order; before content equals evidence document; fragments=[]; ordered_writes equals tasks sorted then spec"
  after_images:
    every_target_frontmatter_keys: [plan_commit, state_revision, last_operation, operation_targets, updated_at]
    spec_body_anchors: [verification_evidence]
    constraints: ["all shared identity values agree", "verification evidence contains exact plan_bind_evidence and operation identity", "complete file contents are authoritative"]
  terminal_result_projection:
    required: [operation_id, state, flow_id, targets, plan_revision, plan_commit, state_revision]
    sources: [journal.operation_id, journal.state, journal.flow_id, journal.request.targets, journal.file_fragments.after]
    constraints: ["state=committed", "shared after-image identities agree", "unknown keys forbidden"]
replay:
  replay_key: evidence_id
  lookup: "exactly one terminal committed plan-bind journal with this flow/evidence_id"
  exact_request_match: "current complete request equals original journal request recursively with identical keysets and values"
  exact_after_image_match: "inventory and every live target equal journal file_fragments after exists/content image"
  success: return_original_terminal_result_without_journal_or_revision
  same_key_different_request_or_payload: conflict_without_writes
  missing_or_noncommitted_original_journal: refuse_without_writes
  live_after_image_or_inventory_drift: refuse_without_writes
  pre_bind_documents_on_replay: never_revalidated
  different_evidence_after_plan_commit_bound: refuse_without_writes
  failed_or_missing_verifier_result: refuse_without_writes
```

On first bind, validate the complete inventory and every full-content document against live Markdown, require the shared revision/null plan commit, and prepare one complete existing-file fragment per inventory path. Each fragment's exact full before image equals its evidence document; its exact full after image includes the shared bound `plan_commit`, new state identity, and `## Verification Evidence` append. Write tasks in sorted id order then spec, and use `plan_bind_evidence.commit` as the new shared `plan_commit`. The sidecar validates only the attestation and live files; responsibility for verifying the commit belongs to the named verifier.

`evidence_id` is the stable replay key. Replay is considered before ordinary pre-bind identity checks: find the unique terminal committed plan-bind journal with that flow/key, require the current complete request to equal its stored request recursively with identical keysets and values, then reread the current inventory and compare every file to the journal's exact full after image. Only that condition returns the exact terminal-result projection derived from the original journal and its after fragments, without a journal, write, or revision. Replay never compares live files to the evidence's pre-bind `documents`. The same key with a different request/payload conflicts; missing/noncommitted provenance, inventory/content drift from the recorded after image, a different key after bind, or failed verifier result refuses without writes.

### Status request schema

```yaml
required: [operation, flow_id, task_ids]
optional: []
constraints: ["operation=status", "flow_id is null or one flow id", "task_ids is a unique sorted array; empty means no task filter", "actor/time/expected identity/targets/payload forbidden", "no operation id or journal"]
```

### Operation read/precondition matrix

The matrix is exact. Each listed name expands to a complete namespaced read-set entry; no unlisted claim/dependency guard may be added because doing so would reject a legal operation. Every read value that contributes to a listed predicate is recorded, even when the illustrative claim journal shows an empty dependency set.

```yaml
predicate_shapes:
  transaction_directory_clear: {predicate: no_other_unresolved_journal, directory: {base: configured_root, path: tasks/transactions}, keys: [excluding_operation_id, observed_operation_ids]}
  flow_absent: {predicate: flow_absent, target: {base: bundle_root, path: specs/<flow_id>}}
  spec_identity: {base: flow_root, path: spec.md, fields: [state, state_revision, current_task, plan_revision, plan_commit, last_operation, operation_targets]}
  all_task_identities: {predicate: all_task_identities, scope: {base: flow_root, glob: tasks/*.md}, fields: [id, state, state_revision, plan_revision, plan_commit, claimed_by, claimed_at, blocked_reason, unblock_condition, commit]}
  target_absent: {predicate: target_absent, target: {base: flow_root, path: tasks/<short_id>.md}}
  target_identity: {base: flow_root, path: tasks/<short_id>.md, fields: [id, state, state_revision, plan_revision, plan_commit, claimed_by, claimed_at, blocked_reason, unblock_condition, commit]}
  plan_ready_approved: {predicate: plan_ready_approved, spec: {base: flow_root, path: spec.md}, approval_evidence: "exact payload value", reviewer_state: Ready}
  all_worksheets_complete: {predicate: all_worksheets_complete, scope: {base: flow_root, glob: tasks/*.md}, required_headings: [Objective, Context, Steps, Verification, Acceptance Criteria]}
  dependencies_exist_and_acyclic: {predicate: dependencies_exist_and_acyclic, target: {base: flow_root, path: tasks/<short_id>.md}, dependency_paths: "complete namespaced sorted array", observed_states: "exact id->state map"}
  all_dependencies_closed: {predicate: all_dependencies_closed, target: {base: flow_root, path: tasks/<short_id>.md}, dependency_paths: "complete namespaced sorted array", observed_states: "exact id->closed map"}
  no_other_in_progress_claim: {predicate: no_other_in_progress_claim, scope: {base: flow_root, glob: tasks/*.md}, excluding: {base: flow_root, path: tasks/<short_id>.md}, observed_task_ids: "complete sorted array"}
  sole_current_claim: {predicate: sole_current_claim, spec: {base: flow_root, path: spec.md}, target: {base: flow_root, path: tasks/<short_id>.md}, claimant: "exact actor"}
  actor_is_claimant_or_authorized: {predicate: actor_is_claimant_or_authorized, target: {base: flow_root, path: tasks/<short_id>.md}, authorization: "null or exact text|at record"}
  in_progress_target_is_current: {predicate: in_progress_target_is_current, spec: {base: flow_root, path: spec.md}, target: {base: flow_root, path: tasks/<short_id>.md}}
  unblock_condition_satisfied: {predicate: unblock_condition_satisfied, target: {base: flow_root, path: tasks/<short_id>.md}, resolution_evidence: "exact payload value"}
  verification_bound_to_commit: {predicate: verification_bound_to_commit, target: {base: flow_root, path: tasks/<short_id>.md}, commit: "exact payload commit", evidence: "exact payload evidence"}
  acceptance_criteria_satisfied: {predicate: acceptance_criteria_satisfied, target: {base: flow_root, path: tasks/<short_id>.md}, checked_ids: "exact payload acceptance_criteria_checked"}
  affected_tasks_closed_or_skipped: {predicate: affected_tasks_closed_or_skipped, paths: "complete namespaced sorted affected task paths", observed_states: "exact id->state map"}
  phase_verification_valid: {predicate: phase_verification_valid, affected_paths: "complete namespaced sorted affected task paths", commit: "payload last_functional_commit", evidence: "exact payload verification_evidence"}
  no_current_claim: {predicate: no_current_claim, spec: {base: flow_root, path: spec.md}, scope: {base: flow_root, glob: tasks/*.md}, observed_task_ids: []}
  plan_bind_evidence_matches_live: {predicate: plan_bind_evidence_matches_live, paths: [{base: flow_root, path: spec.md}], globs: [{base: flow_root, glob: tasks/*.md}], evidence: "exact payload plan_bind_evidence", runtime_inspection: forbidden}
  git_note_attempt_idempotent: {predicate: git_note_attempt_idempotent, target: {base: flow_root, path: tasks/<short_id>.md}, attachment_attempt_id: "payload id", observed_payload: "null or exact prior payload"}
  fresh_user_approval: {predicate: fresh_user_approval, approval: "exact payload text|at record", occurred_at: "request occurred_at"}
  skip_dependents_coherent: {predicate: skip_dependents_coherent, scope: {base: flow_root, glob: tasks/*.md}, target: {base: flow_root, path: tasks/<short_id>.md}, observed_dependents: "complete sorted ids/states"}
  replacement_checkpoint_valid: {predicate: replacement_checkpoint_valid, spec: {base: flow_root, path: spec.md}, checkpoint: "payload null or exact existing checkpoint"}
  reopen_plan_dependents_consistent: {predicate: reopen_plan_dependents_consistent, scope: {base: flow_root, glob: tasks/*.md}, target: {base: flow_root, path: tasks/<short_id>.md}}
  revise_diff_and_adjustments_legal: {predicate: revise_diff_and_adjustments_legal, scope: {paths: [{base: flow_root, path: spec.md}], globs: [{base: flow_root, glob: tasks/*.md}]}, diffs: "exact payload diffs", adjustments: "exact payload adjustments"}
  reconcile_mismatches_exact: {predicate: reconcile_mismatches_exact, spec: {base: flow_root, path: spec.md}, scope: {base: flow_root, glob: tasks/*.md}, mismatches: "exact payload list"}
  all_tasks_terminal_no_blockers: {predicate: all_tasks_terminal_no_blockers, scope: {base: flow_root, glob: tasks/*.md}, observed_states: "complete id->closed|skipped map"}
  completion_evidence_valid: {predicate: completion_evidence_valid, spec: {base: flow_root, path: spec.md}, evidence: "exact verification/code/quality/waiver payload"}
  archive_candidate_exact: {predicate: archive_candidate_exact, root: {base: flow_root, glob: "**/*"}, destinations: {paths: [{base: bundle_root, path: log.md}], globs: [{base: bundle_root, glob: knowledge/*.md}]}, manifest: "exact payload manifest"}
  archive_evidence_valid: {predicate: archive_evidence_valid, candidate: "exact payload archive_candidate_manifest", quality: "exact payload quality_report", waivers: "exact payload waivers"}
  selected_journal_recoverable: {predicate: selected_journal_recoverable, directory: {base: configured_root, path: tasks/transactions}, operation_id: "payload journal_operation_id", states: [prepared, task_writes_started, recovery_required, rollback_in_progress]}
  journal_arbitration_single_candidate: {predicate: journal_arbitration_single_candidate, directory: {base: configured_root, path: tasks/transactions}, observed_operation_ids: "complete sorted nonterminal ids"}
  stage_read_set_matches: {predicate: stage_read_set_matches, journal: {base: configured_root, path: tasks/transactions/<operation-id>/journal.md}, recorded_read_set: "complete journal read_set"}
operations:
  create.flow: [transaction_directory_clear, flow_absent]
  create.task: [transaction_directory_clear, spec_identity, all_task_identities, target_absent, dependencies_exist_and_acyclic]
  activate: [transaction_directory_clear, spec_identity, all_task_identities, plan_ready_approved, all_worksheets_complete]
  claim: [transaction_directory_clear, spec_identity, target_identity, all_dependencies_closed, no_other_in_progress_claim]
  release: [transaction_directory_clear, spec_identity, target_identity, sole_current_claim, actor_is_claimant_or_authorized]
  note.normal: [transaction_directory_clear, spec_identity, target_identity]
  note.git_note_attachment: [transaction_directory_clear, spec_identity, target_identity, git_note_attempt_idempotent]
  discover: [transaction_directory_clear, spec_identity, target_identity]
  block: [transaction_directory_clear, spec_identity, target_identity, in_progress_target_is_current]
  unblock: [transaction_directory_clear, spec_identity, target_identity, unblock_condition_satisfied]
  checkpoint.task: [transaction_directory_clear, spec_identity, target_identity, sole_current_claim, verification_bound_to_commit]
  checkpoint.phase: [transaction_directory_clear, spec_identity, all_task_identities, affected_tasks_closed_or_skipped, no_current_claim, phase_verification_valid]
  checkpoint.plan: [transaction_directory_clear, spec_identity, all_task_identities, plan_bind_evidence_matches_live]
  close: [transaction_directory_clear, spec_identity, target_identity, sole_current_claim, verification_bound_to_commit, acceptance_criteria_satisfied]
  skip: [transaction_directory_clear, spec_identity, target_identity, fresh_user_approval, skip_dependents_coherent]
  reopen: [transaction_directory_clear, spec_identity, target_identity, fresh_user_approval, replacement_checkpoint_valid, reopen_plan_dependents_consistent]
  revise: [transaction_directory_clear, spec_identity, all_task_identities, revise_diff_and_adjustments_legal]
  reconcile: [transaction_directory_clear, spec_identity, all_task_identities, reconcile_mismatches_exact]
  complete: [transaction_directory_clear, spec_identity, all_task_identities, no_current_claim, all_tasks_terminal_no_blockers, completion_evidence_valid]
  archive: [transaction_directory_clear, spec_identity, archive_candidate_exact, archive_evidence_valid]
  recover: [selected_journal_recoverable, journal_arbitration_single_candidate, stage_read_set_matches]
```

In particular, `note.normal`, `discover`, and an `open` non-current `block` have no dependency-closed, no-other-claim, or sole-current-claim predicate. `in_progress_target_is_current` is conditional: it accepts an open non-current block without reading another claimant as a blocker, but requires an in-progress target to equal the spec's sole current task. Release, task checkpoint, and close require the stronger sole-current-claim predicate. Recover deliberately does not require `transaction_directory_clear`; it reads and arbitrates the unresolved journals.

### Create complete-file fragments

Create journals use complete files for every absent-before document; anchors are legal only for documents that already exist. Their exact additional top-level fields have these shapes:

```yaml
flow_create:
  ordered_directories:
    - {directory_index: 0, base: flow_root, path: "."}
    - {directory_index: 1, base: flow_root, path: tasks}
  applied_directories: []
  rolled_back_directories: []
  file_fragments:
    - base: flow_root
      path: spec.md
      before: {exists: false, content_utf8_lf: null}
      after: {exists: true, content_utf8_lf: "<complete UTF-8/LF spec with snapshot>"}
  fragments: []
  ordered_writes:
    - {base: flow_root, path: spec.md}
task_create:
  ordered_directories: []
  applied_directories: []
  rolled_back_directories: []
  file_fragments:
    - base: flow_root
      path: tasks/2.1.md
      before: {exists: false, content_utf8_lf: null}
      after: {exists: true, content_utf8_lf: "<complete UTF-8/LF task worksheet>"}
  fragments:
    - {base: flow_root, path: tasks/1.1.md, anchor: frontmatter, before: {plan_revision: 3, plan_commit: null}, after: {plan_revision: 4, plan_commit: null}}
    - {base: flow_root, path: spec.md, anchor: frontmatter, before: {plan_revision: 3, plan_commit: null, state_revision: 8, last_operation: 20260813T203300Z-flow-executor-close-1-1-00, operation_targets: ["1.1"], updated_at: 2026-08-13T20:33:00Z}, after: {plan_revision: 4, plan_commit: null, state_revision: 9, last_operation: 20260813T203342Z-flow-planner-create-2-1-00, operation_targets: ["2.1"], updated_at: 2026-08-13T20:33:42Z}}
    - {base: flow_root, path: spec.md, anchor: implementation-plan-chapter-phase-2, before: {checklist_items: []}, after: {checklist_items: ["- [ ] Task 2.1: New task"]}}
    - {base: flow_root, path: spec.md, anchor: continuity-snapshot, before: {current_task_claim: null, next_exact_step: "claim next ready task", state_identity: {revision: 8, last_operation: 20260813T203300Z-flow-executor-close-1-1-00, operation_targets: ["1.1"]}}, after: {current_task_claim: null, next_exact_step: "claim Task 2.1 when ready", state_identity: {revision: 9, last_operation: 20260813T203342Z-flow-planner-create-2-1-00, operation_targets: ["2.1"]}}}
  ordered_writes:
    - {base: flow_root, path: tasks/1.1.md}
    - {base: flow_root, path: tasks/2.1.md}
    - {base: flow_root, path: spec.md}
recovery_rules:
  forward: [apply_ordered_directories_shallowest_first_with_provenance, apply_ordered_writes, confirm_exact_after_before_write_applied]
  rollback: [restore_applied_writes_in_exact_reverse, delete_created_file_when_before_exists_false, restore_anchor_before_values, rollback_applied_directories_deepest_first_with_provenance]
  terminal_before: [all_create_file_fragments_absent, all_anchor_fragments_at_before, all_applied_directories_rolled_back]
  conflict: [created_file_content_not_exact_after, missing_applied_file_without_unmatched_rollback_started, nonempty_directory_at_rollback, unrecorded_path_change]
directory_event_schemas:
  entry_required: [directory_index, directory_attempt_index, base, path]
  directory_started: [sequence, kind, at, directory_index, directory_attempt_index, base, path]
  directory_applied: [sequence, kind, at, directory_index, directory_attempt_index, base, path]
  directory_not_applied: [sequence, kind, at, directory_index, directory_attempt_index, base, path]
  directory_rollback_started: [sequence, kind, at, directory_index, directory_attempt_index, base, path]
  directory_rollback_applied: [sequence, kind, at, directory_index, directory_attempt_index, base, path]
  optional: []
  constraints: ["kind equals mapping key", "base=flow_root", "path/directory_index equal ordered_directories entry", "directory_attempt_index is a nonnegative integer", "sequence is next gap-free event number", "unknown keys forbidden"]
directory_attempt_grammar:
  closed_not_applied_prefix: "zero or more pairs directory_started(n) -> directory_not_applied(n)"
  terminal_suffix: "none, directory_started(n), or directory_started(n) -> directory_applied(n)"
  started_attempt_indices: "gap-free 0..n in event order; no maximum"
  completion_attempt_index: "equals its immediately preceding unmatched directory_started attempt index"
  max_unmatched_started: 1
  max_applied_attempts: 1
  applied_attempt_must_be_final: true
  start_after_applied: conflict
  directory_not_applied_requires: [final_unmatched_directory_started, live_directory_absent]
  directory_not_applied_contributes_applied_entry: false
  unmatched_directory_started_at_live_before: {classification: unresolved_attempt, zero_applied: false, proven_zero_write: false, supersession: forbidden, required_action: append_directory_not_applied}
  closed_not_applied_prefix_at_live_before: {classification: zero_applied, zero_applied: true, proven_zero_eligible: true, supersession: allowed, finish: start_next_gap_free_attempt}
  two_crashes_apply_then_rollback: [directory_started(0), directory_not_applied(0), directory_started(1), directory_not_applied(1), directory_started(2), directory_applied(2), directory_rollback_started(2), directory_rollback_applied(2)]
  rollback_reference: "directory_rollback_started/applied reference the sole applied directory_attempt_index"
directory_fault_cases:
  before_directory_started: {live: absent, classification: zero_applied, finish: start_directory, rollback: terminal_without_directory_write, supersession: allowed}
  after_directory_started_before_mkdir: {live: absent, classification: unmatched_directory_not_applied, finish: append_directory_not_applied_then_restart, rollback: append_directory_not_applied_then_validate, supersession: forbidden_until_start_closed}
  after_directory_not_applied: {live: absent, classification: zero_applied_closed_start, finish: restart_directory, rollback: continue_validation, supersession: allowed}
  after_mkdir_before_directory_applied: {live: empty_directory, classification: partially_applied_directory, finish: append_applied_entry_and_directory_applied, rollback: append_applied_entry_then_remove_with_rollback_events, supersession: forbidden}
  after_directory_applied: {live: directory_with_only_recorded_descendants, classification: partially_applied_directory, finish: continue_next_mutation, rollback: reverse_later_mutations_then_remove_directory, supersession: forbidden}
  after_directory_rollback_started_before_rmdir: {live: empty_directory, classification: rollback_in_progress, finish: forbidden, rollback: retry_rmdir, supersession: forbidden}
  after_rmdir_before_directory_rollback_applied: {live: absent, classification: rollback_in_progress, finish: forbidden, rollback: append_rolled_back_entry_and_directory_rollback_applied, supersession: forbidden}
  after_directory_rollback_applied: {live: absent, classification: rollback_in_progress, finish: forbidden, rollback: continue_next_reverse_or_validate, supersession: forbidden}
```

`ordered_directories` is the exact unique shallowest-first list of directories absent before the operation and required by file fragments. Each entry is `{directory_index, base, path}` with gap-free directory indices. `applied_directories` and `rolled_back_directories` are append-only `{directory_index, directory_attempt_index, base, path}` entries that bind provenance to the successful attempt. Task create normally uses empty lists because `<flow-root>/tasks` exists. A task-create journal contains one plan-identity anchor fragment for every pre-existing task, the new task's complete file fragment, and spec identity/checklist/Continuity Snapshot fragments. Apply task-create writes across the complete task set in sorted task-id order, mixing complete-file and anchor fragments at the corresponding path, then spec last. Confirm complete UTF-8/LF bytes and exists-state after every file write before recording `write_applied`.

Before mkdir append `directory_started` with the next gap-free `directory_attempt_index`; after reread confirms the exact directory exists and contains only descendants explained by later recorded mutations, append the same indexed entry to `applied_directories` and `directory_applied`. A final unmatched start is closed at that same index by `directory_applied` when live exists or `directory_not_applied` when absent. Finish may always append the next gap-free attempt after a not-applied closure; there is no retry cap. Thus each directory has zero or more closed not-applied pairs, followed by at most one applied pair or one final unmatched start. Rollback processes files/anchors first, then the duplicate-free deepest-first reverse prefix of applied directories: append `directory_rollback_started` referring to the sole applied attempt, require empty, remove, reread absent, append the same indexed entry to `rolled_back_directories`, then `directory_rollback_applied`. Only the final directory start/rollback-start may be unmatched after a crash and is resolved from exact live state.

Finish recovery resumes the ordered directory prefix before file/anchor writes. Rollback processes only applied writes/directories. A live created file must equal exact after-content; a live directory must be explained by its applied prefix and recorded descendants. A missing applied file/directory conflicts unless explained by the final unmatched rollback start. Zero-write/proven-zero classification requires every ordered directory absent and empty directory provenance; a live created directory is effective applied state and forbids zero-write supersession. No unrecorded path is deleted. Terminal rollback requires every create file absent, every anchor at before, and every applied directory present exactly once in `rolled_back_directories` and live absent.

`anchor: frontmatter` requires `before` and `after` maps with the identical exact key set. A body anchor identifies one stable semantic region: `implementation-plan-task-<short-id>` means heading `## Implementation Plan` plus exactly one checklist item `Task <short-id>:`; `implementation-plan-chapter-<chapter-id>` means exactly one declared chapter heading and its checklist region (used to insert a new task); `continuity-snapshot` means exactly one `## Continuity Snapshot`. Other body fragments likewise name a heading plus stable task/list id in their anchor contract. Zero or multiple matches hard-conflict.

### Event and write-entry shapes

```yaml
applied_writes:
  - {write_index: 0, base: flow_root, path: tasks/1.1.md}
rolled_back_writes:
  - {write_index: 0, base: flow_root, path: tasks/1.1.md}
events:
  - {sequence: 0, kind: prepared, at: 2026-08-13T20:33:42Z, observed_nonterminal_operation_ids: []}
  - {sequence: 1, kind: write_started, at: 2026-08-13T20:33:43Z, write_index: 0, base: flow_root, path: tasks/1.1.md}
  - {sequence: 2, kind: write_applied, at: 2026-08-13T20:33:44Z, write_index: 0, base: flow_root, path: tasks/1.1.md}
  - {sequence: 3, kind: write_not_applied, at: 2026-08-13T20:33:45Z, write_index: 1, base: flow_root, path: spec.md}
  - {sequence: 4, kind: recovery_selected, at: 2026-08-13T20:33:46Z, action: rollback, actor: flow-executor}
  - {sequence: 5, kind: rollback_started, at: 2026-08-13T20:33:47Z, write_index: 0, base: flow_root, path: tasks/1.1.md}
  - {sequence: 6, kind: rollback_applied, at: 2026-08-13T20:33:48Z, write_index: 0, base: flow_root, path: tasks/1.1.md}
  - {sequence: 7, kind: validation_recorded, at: 2026-08-13T20:33:49Z, actor: flow-executor, direction: forward, validation_attempt_id: "20260813T203342Z-flow-executor-claim-1-1-00:forward:v00", checks: [{check_id: transaction_arbitration, result: passed, observed: []}, {check_id: complete_read_set, result: passed, observed: "exact recorded values"}, {check_id: ordered_mutations, result: passed, observed: "complete applied prefixes"}, {check_id: after_fragments, result: passed, observed: "exact after values"}, {check_id: operation_postconditions, result: passed, observed: "exact claim postconditions"}]}
  - {sequence: 8, kind: rollback_validated, at: 2026-08-13T20:33:50Z, actor: flow-executor, direction: rollback, validation_attempt_id: "20260813T203342Z-flow-executor-claim-1-1-00:rollback:v00", checks: [{check_id: transaction_arbitration, result: passed, observed: []}, {check_id: stage_read_set, result: passed, observed: "exact rollback-stage values"}, {check_id: rolled_back_mutations, result: passed, observed: "complete reverse prefixes"}, {check_id: before_fragments, result: passed, observed: "exact before values"}, {check_id: rollback_postconditions, result: passed, observed: "exact pre-operation state"}]}
contention_events:
  - {sequence: 0, kind: prepared, at: 2026-08-13T20:33:42Z, observed_nonterminal_operation_ids: []}
  - {sequence: 1, kind: contended_before_write, at: 2026-08-13T20:33:43Z, observed_nonterminal_operation_ids: [20260813T203342Z-other-agent-claim-1-1-00]}
```

The event list above is a shape catalogue, not one legal history: `write_not_applied` closes only the final unmatched start, and rollback events occur only after the immutable rollback selection. Pre-write contention has `prepared`, then zero or more fully closed not-applied attempt pairs, then `{sequence, kind: contended_before_write, at, observed_nonterminal_operation_ids}`. It has no applied entry/event and no unmatched start.

### Terminal validation event schemas

```yaml
check_record:
  required: [check_id, result, observed]
  optional: []
  constraints: ["check_id is one required id for the direction", "result=passed", "observed is the exact reread value/result, not a summary"]
validation_recorded:
  required: [sequence, kind, at, actor, direction, validation_attempt_id, checks]
  optional: []
  required_check_ids: [transaction_arbitration, complete_read_set, ordered_mutations, after_fragments, operation_postconditions]
  constraints: ["kind=validation_recorded", "direction=forward", "checks have unique ids in required order", "last event before committed"]
rollback_validated:
  required: [sequence, kind, at, actor, direction, validation_attempt_id, checks]
  optional: []
  required_check_ids: [transaction_arbitration, stage_read_set, rolled_back_mutations, before_fragments, rollback_postconditions]
  constraints: ["kind=rollback_validated", "direction=rollback", "checks have unique ids in required order", "last event before rolled_back"]
validation_invalidated:
  required: [sequence, kind, at, actor, direction, validation_attempt_id, reason, observed_nonterminal_operation_ids, failed_checks]
  optional: []
  constraints: ["kind=validation_invalidated", "direction equals referenced validation", "validation_attempt_id references latest uninvalidated validation", "reason=contender_appeared|read_set_drift|mutation_drift", "observed_nonterminal_operation_ids unique sorted", "failed_checks exact check_id|expected|observed records", "at most one invalidation per attempt"]
terminal_rules:
  committed_requires: validation_recorded
  rolled_back_requires: rollback_validated
  attempt_id: "<operation-id>:<forward|rollback>:v<00..99>; choose first free suffix, never reuse"
  attempt_exhaustion: "when all v00..v99 for the direction exist, hard-stop/refuse without a new event or tracked write; require user repair or a new operation; never wrap or reuse"
  append_only: true
  duplicate_event: forbidden
  latest_validation_must_be: [uninvalidated, final_event, exact_live_checks_passed]
  resume_after_event: "reread arbitration and exact recorded checks; if identical/pass and no contender, apply only terminal journal state; otherwise append one validation_invalidated"
  resume_after_invalidation: "do not duplicate invalidation; enter recovery/arbitration, then append a fresh validation attempt only after stable"
  terminal_without_event: conflict
  event_after_terminal: forbidden
validation_fault_cases:
  after_validation_before_terminal_clean: {live: exact_validated_state, action: apply_terminal_state_only, append_event: none}
  after_validation_before_terminal_contender: {live: contender_present, action: append_validation_invalidated_then_arbitrate, terminal: forbidden}
  after_validation_before_terminal_drift: {live: reread_mismatch, action: append_validation_invalidated_then_recover, terminal: forbidden}
  after_invalidation_before_recovery_state: {live: invalidation_is_final_event, action: retain_invalidation_and_enter_recovery, duplicate_invalidation: forbidden}
  after_recovery_before_revalidation: {live: stable_nonterminal_state, action: append_fresh_validation_attempt, terminal: forbidden}
  after_fresh_validation_before_terminal: {live: exact_revalidated_state, action: apply_terminal_state_only, append_event: none}
  after_terminal: {live: terminal_state, action: none, append_event: forbidden}
```

Terminal validation is not a prose note. After all forward mutations and final arbitration, append one `validation_recorded` event with a fresh attempt id and the exact keyset/check records above, reread the journal, then set `state: committed`. Rollback uses `rollback_validated` analogously before `rolled_back`. Terminal state requires the latest validation attempt to be uninvalidated, its exact checks to pass live, and that validation to be the final event.

If a contender or drift appears after validation and before terminal, append exactly one `validation_invalidated` referencing that attempt and the live reason/ids/failed checks; terminal is then forbidden. A crash before invalidation is resolved from the live arbitration/read set: clean state applies only terminal, while contender/drift appends invalidation. A crash after invalidation never duplicates it: resume enters arbitration/recovery, then uses a fresh attempt id only after stable. Exact replay of validation/invalidation returns the existing event; same attempt id with different payload conflicts. If all 100 suffixes for that direction exist, hard-stop without an event or tracked write and require user repair or a new operation; never wrap or reuse an id. Missing/changed checks, reused ids, multiple invalidations, terminal with invalidated/nonfinal validation, or events after terminal conflict.

Every path-bearing value in fragments, ordered writes, read set, target/dependency/excluding records, directory records, inventories, and glob scopes has `base: flow_root|bundle_root|configured_root` plus exactly one relative `path` or `glob`. State/task reads use `flow_root`; knowledge/log/archive use `bundle_root`; transaction-directory reads use `configured_root`. Missing/unknown bases, absolute/`..`, symlink traversal, escape, and matches outside the base/repository refuse. Unqualified paths/globs are invalid. Paths are unique within their namespace; an ordered file may repeat only for explicit unique fragment order.

Before recovery writes, validate exact keys/version/roots, targets/path agreement, unique fragments, task-before-spec ordering, every semantic before/after fragment, and operation legality. Frontmatter anchors name exact key sets. Body anchors name a heading plus stable task/list id and match exactly once. The complete live semantic read set is evaluated at the current forward/rollback stage before every edit; reread the target afterward.

### Forward provenance and concurrency

Journal states are nonterminal `prepared|task_writes_started|recovery_required|contended|rollback_in_progress` and terminal `committed|rolled_back|superseded`. Events begin at sequence zero with `prepared` and the final complete sorted nonterminal-id observation. Every file write/event path is `{write_index, base, path}` using its zero-based ordered-write index; create directory events use `{directory_index, base, path}` from `ordered_directories`. Immediately after journal creation, before/after each tracked directory or file write, before validation, and before the terminal state edit, reread the transaction directory and full semantic read set.

Before a forward edit append `write_started`; after exact reread confirmation append its `applied_writes` entry and `write_applied`. Never remove, rewrite, reorder, duplicate, or gap events/write entries. A crash after edit but before confirmation is explained only by the final unmatched start and the exact live after-fragment.

If another nonterminal journal appears before any tracked write, first close a final live-before directory/file start with its namespaced not-applied event, then append `contended_before_write` with complete sorted ids/time, set contended, retain empty applied lists, and stop. `contended_before_write` is legal immediately after prepared or after a gap-free sequence of closed-not-applied attempt pairs; never after an unmatched start or applied event. If a contender appears after any after-fragment/directory was applied, set recovery-required and stop before the next mutation/validation/terminal mark.

Direct-read arbitration classifies all journals jointly:

- `proven_zero_write`: `prepared`, optionally closed-not-applied attempt pairs, then `contended_before_write`; no unmatched/applied/rollback event or entry; every directory/file/anchor at before; shared drift exactly the sole applied candidate's after.
- `zero_applied`: every directory absent, complete-file/anchor fragment at before, and all applied/rolled-back lists empty. A final unmatched file `write_started` may be classified before and closed under the file grammar, but an unmatched `directory_started(n)` is never zero-applied or supersedable: recovery must first append `directory_not_applied(n)`. Any fully closed gap-free prefix of `directory_started(n) -> directory_not_applied(n)` pairs contributes no applied entry, is zero/proven-zero eligible, and permits finish to append the next indexed attempt without an arbitrary retry limit.
- `partially_or_fully_applied`: one or more effective live directory/file/anchor after-values and gap-free directory-then-file forward prefixes explain them; only the final start across both mutation sequences may lack confirmation.
- `rollback_in_progress`: one immutable rollback selection, prior unmatched starts closed, duplicate-free reverse prefixes in rolled-back file and directory lists, restored entries at before, remaining applied entries at after, and at most one final unmatched file or directory rollback start live at before or after.
- Anything with unexplained paths/directories, event gaps/reordering, duplicate/unclosed starts, changed action, applied/rolled-back entry/live mismatch, or unexplained shared drift is `conflict`.

If all candidates are zero/proven-zero, supersede lexicographically and retry later. If exactly one has an applied directory/file/anchor or rollback prefix and every other is explained zero/proven-zero, supersede zero-write journals and require explicit recovery for the sole candidate. More than one applied candidate or any conflict hard-stops with exact journal/path/fragment/directory conflicts and makes no tracked write. Scan order never chooses authority.

### Recovery provenance

Resolve a final unmatched forward start before selecting direction. If live is exact after, append its missing applied entry and `write_applied`; if exact before, append `write_not_applied` for that namespaced index. For a directory start, append the completion at the identical directory-attempt index: live created appends the applied entry/event, while live absent appends `directory_not_applied`. Any other value conflicts. A not-applied closure contributes no applied entry; finish may append the next monotonically increasing attempt, while rollback ignores every closed not-applied attempt.

Append exactly one immutable `recovery_selected` with action `finish|rollback`, actor, and time. Resumption must retain that action. Finish continues forward, using a fresh attempt for a closed-not-applied index. Rollback ignores not-applied attempts, sets rollback-in-progress, and restores only applied writes in exact reverse order: append namespaced `rollback_started`, restore, reread, append the entry to `rolled_back_writes`, then `rollback_applied`. Rolled-back entries form a duplicate-free reverse prefix. Only the final rollback start may be unconfirmed: live after retries; live before receives its missing confirmation. After all restores, append `rollback_validated`, reread/arbitrate, then terminal rolled-back. Every crash boundary resumes the same grammar/direction.

### Archive fragments

Archive inventory uses `base: bundle_root`, a root beneath it, complete sorted directory inventory, and the complete sorted recursive set of unique regular UTF-8 Markdown files. It rejects symlinks, devices, absolute/`..`, and unrecorded files. Every inventory file has one complete file fragment with full UTF-8/LF preimage and absent after-state. Every knowledge/log create/edit has complete before/after content.

#### Archive inventory minimum shape

```yaml
target_state_revision: 18
archive_inventory:
  base: bundle_root
  root: specs/conductor-flow-continuity
  directories: [".", tasks]
  files: [spec.md, tasks/1.1.md]
file_fragments:
  - path: knowledge/workflow.md
    base: bundle_root
    before: {exists: true, content_utf8_lf: "<complete preimage>"}
    after: {exists: true, content_utf8_lf: "<complete reviewed synthesis>"}
  - path: log.md
    base: bundle_root
    before: {exists: true, content_utf8_lf: "<complete preimage>"}
    after: {exists: true, content_utf8_lf: "<complete preimage plus one reviewed entry>"}
  - path: specs/conductor-flow-continuity/tasks/1.1.md
    base: bundle_root
    before: {exists: true, content_utf8_lf: "<complete task content>"}
    after: {exists: false, content_utf8_lf: null}
  - path: specs/conductor-flow-continuity/spec.md
    base: bundle_root
    before: {exists: true, content_utf8_lf: "<complete spec content>"}
    after: {exists: false, content_utf8_lf: null}
```

Ordered writes are sorted knowledge files, `log.md`, sorted task/other flow files, and `spec.md`; remove empty directories deepest first. Rollback recreates directories shallowest first, restores flow files in reverse deletion order, restores log/knowledge in reverse write order, and deletes newly created knowledge only when its before-state was absent. The journal stays outside the deleted flow. Finish/rollback requires the recorded inventory and stage-aware live fragments; Git history is never a recovery prerequisite.

## Direct-read continuity contract

After compaction, handoff, or session loss, reconstruct authority with file tools in this exact order. Do not trust a hook, plugin, interpreter, synthesized packet, or prior conversation.

1. Resolve/validate configured root, then read `<configured-root>/tasks/transactions/*/journal.md` before requiring any spec. A nonterminal journal blocks normal work; jointly arbitrate multiples. A sole/applied archive candidate selects its recorded flow even with no spec. Terminal journals are history only.
2. If no journal selected the flow, resolve bundle/index/spec paths through the index contract. Read every planned/active/completed spec frontmatter and Continuity Snapshot. Respect explicit user target; otherwise require exactly one active flow, or if none active exactly one completed flow awaiting archive; otherwise stop with candidates.
3. For an existing spec, read all task frontmatter and verify equal plan revision/commit, revision bounds, current-task agreement, unique claim, dependencies, and checklist. For a deleted archive target, validate complete inventory/file-fragment live before/after states.
4. For active work choose explicit requested task, else sole valid in-progress claim, else first ready `(priority, created_at, task_id)`. Read its complete worksheet and direct dependencies. For planned/completed flows, report activate/archive rather than selecting task work.
5. Read the five newest task discoveries and only knowledge/rule paths named by the snapshot, worksheet, journal, and root index. Paths point to authority; injected prose is not authority.
6. Before mutation restate flow/lifecycle, plan/state identity, task/claim, verified checkpoint, decisions, discoveries, blockers/unblock conditions, next exact step, unresolved journal state, and relevant paths. Then submit an explicit state request carrying the expected identities just read.

Installed hooks/plugins may only emit static routing such as “read the Flow index.” They never scan tasks, synthesize continuity, invoke `tools/priming.py`, compute authority, or mutate state. `tools/priming.py` is maintainer/test-only.

## File-tool transaction protocol

1. **Prepare:** resolve/validate roots; read the transaction directory, spec, complete target/dependency/claim task set, checklist, snapshot, and every path/field required by the operation; compute exact proposed fragments; choose a collision-free id.
2. **Preflight:** require exact plan/state identity, source/result transition, dependencies, claim uniqueness, payload, paths, and no nonterminal journal. Record the complete transaction-directory predicate. A mismatch refuses without writes.
3. **Journal:** create the untracked prepared journal with roots, strict request, complete read predicates, ordered namespaced paths, exact before/after fragments, empty file/directory applied and rolled-back lists, and sequence-zero prepared event containing the final pre-create nonterminal-id observation. Immediately arbitrate journals.
4. **Write:** for create, apply `ordered_directories` first with directory start/applied provenance. Before each tracked directory/file edit reread/arbitrate the transaction directory and full read set, then append its namespaced start event. Write target tasks in sorted id order and spec last; archive follows its recorded order. Reread target, append the namespaced applied entry/event only after exact confirmation, then reread/arbitrate again.
5. **Validate:** reread directory/spec/targets/dependencies/claims and require operation, checklist, snapshot, read predicates, mutation prefixes, and exact after-values. After final arbitration append the one strict `validation_recorded` event, reread it, then mark committed. Ambiguity/drift becomes contended or recovery-required; never infer or overwrite.
6. **Recover:** read the journal and complete stage-aware live set; close a final unmatched directory/file start with applied or not-applied exactly as above; require every value and operation-specific predicate to match the recorded prefixes; record/retain one direction; finish directories then files forward, or resume reverse file then directory rollback. After rollback append the one strict `rollback_validated` event, reread it, then mark rolled back. A crash after either validation event reruns its exact checks and applies only the terminal state; resumed recovery never duplicates validation or creates a new tracked revision.

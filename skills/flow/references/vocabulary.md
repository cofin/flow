# Flow Vocabulary and Plain Writing

Use these words in replies, specs, skills, command output, Studio labels, and code names.
Flow's repository validator fails when a retired word returns to shipped prose.

## Terms We Keep

- **Core nouns**: flow, PRD, spec, chapter, task, worksheet, step, worker, brief.
- **Core actions**: validate the spec, write or revise the spec, implement the flow or chapter, review the flow, finish, archive, revert, sync, refresh, learn.
- **Existing terms**: stealth mode (`local-only` via `.git/info/exclude`), brownfield, deep module, preflight, closeout, truth block (`<!-- truth: start -->`), OKF (`Attested Computation`).

On-disk keys and headings shared with other tools stay as they are: frontmatter keys, `empirical_dependent`, `## Bounded Read Manifest`, `## Public-Seam Test Blueprint`, and the six `spec.md` headings.
Quote them in backticks when prose refers to them.

## Retired Scheduling Words

| Retired | Say | Meaning |
| --- | --- | --- |
| `wave` | step | Position in the execution order. Tasks in one step do not wait on each other. |
| `slice`, `micro-slice`, `vertical slice`, `horizontal slicing`, `pack` | task | One unit of work (or a small group of tasks for one worker). Each task includes its own tests. |
| `context pack` | brief | Task text plus the file excerpts a worker needs to start. |
| `slot`, `batch size` | worker, workers | One agent running tasks. `workers: 4` means up to four at once. |
| `disjoint`, `overlap` | separate files, shared files | Whether two tasks edit the same file. |
| `reconcile` | sync | Bring spec and task files in line with disk and Git. |
| `gate` | check | Chapter check is lint plus the chapter's tests. Full check is the whole suite. |
| `cold-read`, `zero-context` | independent | A reviewer or worker that sees only the files it was given. |
| `zero-LLM`, `zero-token`, `zero-regex`, `zero-pypi`, `deterministic` | name what runs | Example: "The CLI updates the files." |
| `frontier`, `tier` | strongest model, model role | Roles are `strong`, `standard`, `fast`, `light`. |
| `compaction`, `cold start` | say the point | Example: "Small enough for one worker to finish in one run." |
| `bin-packed`, `work-conserving`, `semaphore` | say what happens | Example: "Small tasks are grouped." "Every worker stays busy." |

## Retired Older Flow Jargon

| Retired | Say |
| --- | --- |
| `true-up`, `reorient`, `reorientation` | sync, catch up, status summary |
| `resynthesize`, `resynthesis` | update knowledge, refresh |
| `contraction` | archive order, capture learnings |
| `cold-reader` | first-time reader |
| `adjudicate`, `adjudication`, `adjudication ledger` | decide on each finding, review summary |
| `blueprint` | task worksheet |
| `bounded read manifest`, `read fence` | read list |
| `public-seam`, `multi-seam`, `deep-module seam` | public interface, module interface |
| `zero-decision` | ready to implement without guessing |
| `iron law` | run the check before claiming it passed |
| `north star` | goal |
| `altitude control` | architecture in `spec.md`, file details in worksheets |
| `red-capable` | fast failing test |
| `worked test matrix` | test cases |
| `circuit breaker` | stop-loop limit |
| `hypothesis-driven bug diagnosis` | bug diagnosis |
| `System Under Test`, `SUT` | real code, module under test |
| `mock-echo`, `tautological`, `implementation-coupled` | mock-only test, private-detail test |
| `anti-skip` | completion check |
| `anti-truncation` | plan the whole scope |
| `anti-sprawl` | layout check |
| `chronological sediment`, `zero-history` | current state only |
| `co-designer`, `stateful planner` | planner |
| `design-tree frontier`, `orthogonal` | open decisions, independent |
| `sharded`, `reconnaissance`, `scout` | parallel read-only research, researcher |
| `upward delegation`, `frontier floor` | planning and review use the strongest model |
| `fail-closed` | stop without editing |
| `manifest-driven` | file checklist |
| `deliverable-sized` | sized to the feature |
| `write-time`, `commit-first` | right after writing, commit code first |
| `local-substitutable` | local test double |
| `SubsystemDigest` | subsystem summary |
| `Token Stratum`, `System-One` | model routing, model picker |
| `structured-choice-v1`, `quality-review-v1`, `worksheet-execution-v1`, `structured-result-v1` | remove |
| `flow-memory-keeper` | remove stale references |

## Writing Rules

- Put what changes for the reader first.
- Write one idea per sentence, at most 35 words.
- Keep headings to at most 8 words and one topic.
- State a number once, in a table or one bullet.
- Name a class, function, or flag only when the reader needs to type it or find it.
- Do not stack qualifiers such as "cleanly", "strictly", or "bounded".

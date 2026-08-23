# Flow Research

Conduct bounded technical research from primary sources. Research agents are
read-only and return closed cited results; the parent owns every tracked write.

## Proportional Dispatch

Dispatch only when a predicate below is satisfied. Count independent unknowns
before dispatch and use one researcher per independent unknown or source
domain; overlapping questions stay in one brief.

<!-- research-fanout-contract: proportional-v1 -->
```yaml
researcher:
  when: at least_two_independent_unknowns | current_external_evidence_required
  count: one_per_independent_unknown_or_source_domain
interface_design:
  when: competing_public_shapes
architecture_review:
  when: new_seam | state_contract | public_contract | hard_to_reverse_choice
devils_advocacy:
  when: destructive | security_sensitive | high_uncertainty
otherwise: zero_extra_dispatches
```

Researcher briefs name one question, scoped primary sources, required current
sources, and a target for the parent to write. Current external API behavior
must come from current source material, not recalled syntax. Keep one task per execution subagent; research fan-out does not split implementation ownership.

## Result Adoption

The researcher returns the `structured-result-v1` schema in
`agents/researcher.md`; it never writes a note. The parent must validate that:

- every required key exists and there are no unknown keys;
- every finding id is unique and supported by at least one exact citation;
- every cited finding exists and every primary-source citation is retained;
- confidence and limitations are explicit; and
- contradictions are resolved with evidence or marked unresolved.

Malformed or uncited results and results with unresolved contradictions are
not adopted or silently summarized. The parent resolves the gap, dispatches a
justified follow-up, or records a blocker. Only after validation does the parent
write the target research document or worksheet note, preserving citations,
limitations, and contradictions verbatim enough to audit their meaning.

## Frontmatter Schema

```yaml
---
type: Research
research_id: "topic-slug"
title: Research Title
scope: architecture | domain | integration
tags: [tag1, tag2]
status: stable
state: open                     # open | promoted
promoted_to: null               # flow_id once adopted by a spec
created_at: 2026-08-23T12:00:00Z
updated_at: 2026-08-23T12:00:00Z
---
```

## Promotion Contract

Un-promoted research lives in `.agents/bundles/research/<topic>/`. When a flow adopts the research, the parent moves the folder to `.agents/bundles/specs/<flow_id>/research/` and sets `state: promoted` and `promoted_to: <flow_id>`.

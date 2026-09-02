# ARGUS–ARGOS Architecture v0

## Status

Candidate architecture for URANO. This document preserves `ARGUS` and `ARGOS` as project labels and does **not** invent or freeze acronym expansions.

## Placement

URANO is the host/runtime environment. ARGUS–ARGOS is the epistemic-operational subsystem responsible for turning heterogeneous information into qualified observations and governed decisions.

```text
SOURCES
  ↓
Bridge / ingest adapters
  ↓
ARGUS
  ↓
EvidenceObservation
  ↓
ARGOS
  ↓
Adjudication (PASS | HOLD | BLOCK)
  ↓
Evidence Gate / Ω-Gate / Ledger / Replay
  ↓
URANO runtime
```

## ARGUS

ARGUS performs perception and qualification. It records:

- source reference;
- representation type;
- deterministic content hash;
- authority by predicate domain;
- metadata;
- unresolved conflicts;
- observation notes.

ARGUS does not decide publication, execution or persistence.

## ARGOS

ARGOS adjudicates an `EvidenceObservation` under an explicit policy. It does not reinterpret the original source.

Current outcomes:

- `PASS`: policy requirements are satisfied;
- `HOLD`: evidence is incomplete, below threshold, ambiguous or conflicted;
- `BLOCK`: malformed input or a policy-defined hard conflict.

## Predicate authority

Authority is a policy vector, not a probability of truth:

`content | version | authorship | publication | timestamp | execution | integrity | custody`

A source can be strong for one predicate and weak or irrelevant for another.

## Boundaries

- `ARGUS != Bridge`: Bridge acquires/transports evidence; ARGUS qualifies observations.
- `ARGOS != Ω-Gate`: ARGOS adjudicates evidence context; downstream gates enforce execution/publication policy.
- `ARGUS–ARGOS != URANO`: URANO hosts and integrates these organs.
- `EvidenceRoot != RepresentationCount`: derivative representations must not inflate evidence count.
- `ClaimedID != ResolvedID`: identifiers asserted inside an artifact require independent resolution.

## Integration strategy

This v0 is deliberately independent of PR #4 (`evidence_gate`) so the subsystem can be reviewed without stacking unmerged branches. After PR #4 lands, a follow-up integration may translate `Adjudication` into the gate contract without duplicating gate semantics.

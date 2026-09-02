# ARGUS–ARGOS Architecture v0

## Status

Corrected candidate architecture for URANO, grounded in the corpus distinction:

- `ARGUS` = vertical fake-news / factual-integrity tool;
- `ARGOS` = broader operational system for evidence governance.

The project labels are preserved and no acronym expansion is invented or frozen in this PR.

## Placement

URANO is the host/runtime environment. ARGOS is a governance system hosted by URANO. ARGUS is a specialized tool that produces factual-integrity findings which ARGOS may govern alongside outputs from other laboratories.

```text
URANO
├── ARGOS  (evidence governance system)
│   ├── policy / admissibility
│   ├── Ω-Gate / downstream gates
│   ├── ledger / receipts / replay
│   ├── review / contest / revocation
│   ├── external witness integration
│   └── receives governed records from multiple producers
│
├── ARGUS  (fake-news / factual-integrity tool)
├── MANDELA (separate analytical producer; not implemented here)
└── CARTOMANCIA (separate analytical producer; not implemented here)
```

A representative ARGUS flow is:

```text
SOURCE / CLAIM / MEDIA
  ↓
Bridge / ingest / ARGUS Connect adapters
  ↓
ARGUS investigation
  ↓
ArgusFinding
  ↓
GovernanceEnvelope(producer="ARGUS")
  ↓
ARGOS governance kernel
  ↓
PASS | HOLD | BLOCK
  ↓
policy / gate / ledger / receipt / replay
  ↓
URANO runtime
```

ARGOS is not structurally dependent on ARGUS. A producer such as MANDELA or CARTOMANCIA can create its own `GovernanceEnvelope` and be governed by the same ARGOS policy layer.

## ARGUS — exact function

ARGUS is the vertical tool for fake news, misinformation and factual integrity. Its scope includes organizing evidence about:

- false, misleading or unverifiable claims;
- contradictions between sources;
- loss of context / decontextualization;
- suspected media manipulation or deepfake evidence;
- suspected documentary fabrication;
- suspected artificial coordination / disinformation campaigns;
- provenance and factual-support signals used in human or automated investigation.

ARGUS does **not** infer truth from raw content by default. In v0, stronger findings require explicit evidence signals or conflicts. Suspicion labels remain suspicions and are not silently promoted to final factual conclusions.

Current conservative finding states:

- `SUPPORTED`
- `UNVERIFIED`
- `INSUFFICIENT_EVIDENCE`
- `CONTRADICTORY`
- `OUT_OF_CONTEXT`
- `MANIPULATION_SUSPECTED`
- `FABRICATION_SUSPECTED`
- `COORDINATION_SUSPECTED`

ARGUS does not own system-wide publication, persistence, ledger, receipts or replay.

## ARGOS — exact function

ARGOS is the broader operational evidence-governance system. Its canonical scope is larger than the `Argos` class implemented in this PR.

ARGOS governs:

- evidence admissibility;
- policy application;
- authority thresholds by predicate;
- unresolved conflicts;
- execution/publication gating through downstream contracts;
- receipts;
- ledger;
- replay;
- human review;
- contestation and revocation;
- external witness / independent validation integration;
- governed integration of outputs from multiple tools and laboratories.

The v0 `Argos` class implements only the policy-adjudication kernel needed to establish this boundary. It accepts a generic `GovernanceEnvelope` rather than an ARGUS-specific observation.

Current kernel outcomes:

- `PASS`: explicit policy requirements are satisfied;
- `HOLD`: evidence is incomplete, below threshold, from a disallowed producer, ambiguous or conflicted;
- `BLOCK`: malformed governance input or a policy-defined hard conflict.

## Related components

The corpus distinguishes these names from the canonical ARGUS/ARGOS roles:

- `ARGUS Connect`: user-facing intake / explorer / review interface; not the ARGUS analytical core and not ARGOS itself.
- `ARGOS Agent`: backend/executor for jobs, models, hashing, APIs and automations; not the full ARGOS governance system.

Neither component is implemented by this PR.

## Predicate authority

Authority is a policy vector, not a probability of truth:

`content | version | authorship | publication | timestamp | execution | integrity | custody`

A source can be strong for one predicate and weak or irrelevant for another.

## Boundaries

- `ARGUS != ARGOS`: fake-news/factual-integrity analysis is not the governance system.
- `ARGUS != Bridge`: Bridge acquires/transports/resolves source evidence; ARGUS investigates factual-integrity questions.
- `ARGUS Connect != ARGUS`: interface is not analytical core.
- `ARGOS Agent != ARGOS`: executor is not the governance system.
- `ARGOS != Ω-Gate`: ARGOS is broader; Ω-Gate is one governed passage/enforcement mechanism.
- `ARGOS != URANO`: URANO hosts and integrates ARGOS and other organs.
- `EvidenceRoot != RepresentationCount`: derivative representations must not inflate evidence count.
- `ClaimedID != ResolvedID`: identifiers asserted inside an artifact require independent resolution.

## Integration strategy

This PR remains independent of PR #4 (`evidence_gate`) to avoid stacked-branch coupling. After PR #4 lands, a follow-up should map `GovernanceDecision` into the gate contract rather than duplicating gate semantics.

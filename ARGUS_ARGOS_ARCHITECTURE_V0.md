# ARGUS–ARGOS Architecture v0

## Status

Corrected candidate architecture for URANO, grounded in the corpus distinction:

- `ARGUS` = vertical fake-news / misinformation / factual-integrity tool;
- `ARGOS` = broader operational system for evidence governance;
- `URANO` = host/runtime/laboratory that integrates these organs.

The project labels are preserved. This PR does not invent or freeze acronym expansions.

## Placement

```text
URANO
├── ARGOS  (evidence-governance system)
│   ├── policy / admissibility
│   ├── Ω-Gate / downstream gates
│   ├── ledger / receipts / replay
│   ├── review / contest / revocation
│   ├── external witness integration
│   └── governed records from multiple producers
│
├── ARGUS  (fake-news / factual-integrity tool)
├── MANDELA (separate analytical producer; not implemented here)
└── CARTOMANCIA (separate analytical producer; not implemented here)
```

ARGOS is not structurally dependent on ARGUS. Any authorized producer can emit a `GovernanceEnvelope` with an explicit epistemic state and predicate-specific authority.

## End-to-end flow implemented in this PR

```text
SOURCE / CLAIM / MEDIA
  ↓
Bridge / local corpus / ARGUS Connect / explicit adapter
  ↓
SourceIntake
  ├── representation class
  ├── SHA-256
  ├── expected-hash check
  ├── provenance flags
  ├── generated/derivative classification
  └── predicate authority
  ↓
ClaimExtractor
  ↓
EvidenceComparator
  ↓
EvidenceRootIndex
  ├── exact-byte/root deduplication
  ├── derivative representations do not inflate support
  ├── generated material is not independent support
  └── max authority per predicate, never additive voting
  ↓
ARGUS
  ↓
ArgusFinding
  ↓
GovernanceEnvelope
  ↓
ARGOS
  ↓
PASS | HOLD | BLOCK
  ↓
URANO runtime
  ├── redacted event history
  ├── decision summary
  ├── MemoryGate hash-chain
  └── EvidencePack seal
```

## ARGUS — exact function

ARGUS is the vertical tool for fake news, misinformation and factual integrity. It organizes inspectable evidence about:

- false, misleading or unverifiable claims;
- contradictions between independent source roots;
- loss of context / decontextualization;
- integrity mismatches;
- suspected media manipulation or deepfake evidence supplied by explicit detectors;
- suspected documentary fabrication;
- suspected artificial coordination / disinformation campaigns;
- provenance and factual-support signals used in human or automated investigation.

ARGUS does **not** infer truth from raw content by default. Strong or suspicious findings require evidence signals or conflicts. Suspicion labels remain suspicions; they are not silently promoted to final factual conclusions.

Current finding states:

- `SUPPORTED`
- `UNVERIFIED`
- `INSUFFICIENT_EVIDENCE`
- `CONTRADICTORY`
- `OUT_OF_CONTEXT`
- `INTEGRITY_CONFLICT`
- `MANIPULATION_SUSPECTED`
- `FABRICATION_SUSPECTED`
- `COORDINATION_SUSPECTED`

ARGUS does not own system-wide publication, persistence, ledger, receipts or replay.

## ARGOS — exact function

ARGOS is the broader operational evidence-governance system. Its canonical scope is larger than the `Argos` class implemented here.

ARGOS governs:

- evidence admissibility;
- explicit epistemic state;
- policy application;
- authority thresholds by predicate;
- allowed producers;
- unresolved conflicts;
- downstream execution/publication gates;
- receipts;
- ledger;
- replay;
- human review;
- contestation and revocation;
- external witness / independent validation;
- integration of outputs from multiple tools and laboratories.

The v0 `Argos` class is the policy-adjudication kernel. It accepts a generic `GovernanceEnvelope` rather than an ARGUS-specific object.

Fail-closed rules include:

- missing epistemic state → `HOLD`;
- unknown epistemic state → `HOLD` unless explicitly mapped by policy;
- `UNVERIFIED`, `INSUFFICIENT_EVIDENCE`, `CONTRADICTORY`, `OUT_OF_CONTEXT` and suspicious/integrity states → `HOLD` by default;
- high numeric authority cannot override an unresolved epistemic state;
- unresolved conflict → `HOLD`, or `BLOCK` under strict policy;
- malformed governance envelope → `BLOCK`.

Current kernel outcomes:

- `PASS`: explicit policy requirements are satisfied;
- `HOLD`: evidence/context/authority/state remains unresolved;
- `BLOCK`: malformed input or a policy-defined hard prohibition.

## Source representations and authority

The URANO intake mirrors the evidence classes already used by the GPT-Project-Bridge, without importing that repository at runtime. Supported policy classes include:

`LIVE_HTML | API_METADATA | SAVED_HTML | LATEX_SOURCE | ARXIV_EPRINT_SOURCE | SAVED_PDF | SAVED_IMAGE | SCREENSHOT | DOCUMENT_PAGE_RENDER | GENERATED_IMAGE | DOI_METADATA | ORCID_SNAPSHOT | REPOSITORY_FILE | GIT_COMMIT | HF_SNAPSHOT | CORPUS_COPY | MODEL_REPORT | OBSERVED_TEXT`

Authority is a policy vector, not a probability of truth:

`content | version | authorship | publication | timestamp | execution | integrity | custody`

Examples:

- TeX may be strong for content/version but not publication;
- DOI metadata may be strong for publication but weak for paper-content claims;
- screenshots prove rendered state, not backend state;
- generated images and document-page renders are non-independent;
- matching expected SHA-256 supports byte integrity only;
- high entropy is recorded as a descriptive statistic and is not interpreted as proof of steganography/manipulation.

## Evidence-root semantics

`EvidenceRoot != RepresentationCount`.

The same evidentiary origin may exist as HTML, PDF, PNG, screenshot or local copy. Those representations must not become artificial independent votes.

The v0 root index therefore:

1. groups exact duplicate bytes by SHA-256 by default;
2. accepts an explicit `evidence_root_id`/derivation root from a trusted adapter;
3. counts generated and derivative representations as non-independent;
4. aggregates authority by maximum per predicate domain, never by summing corroborators;
5. keeps perceptually similar but byte-different files separate unless a derivation relation is explicitly demonstrated.

A claim source cannot support itself merely because its own text contains the claim. `claim_source=true` suppresses that self-corroboration path.

## Conservative comparator

The built-in comparator is intentionally narrow and replayable. It supports:

- explicit adapter relation: `SUPPORTS | CONTRADICTS | CONTEXTUALIZES | INTEGRITY_WARNING`;
- exact textual support from an independent source;
- expected SHA-256 mismatch → integrity conflict;
- explicit context-loss status;
- structured HTML metadata contradiction such as archived prose saying a DOI is pending while `citation_doi` already exists;
- explicit integrity status from a media/document detector.

It does not use a language model as an opaque truth oracle. Rich semantic search, web resolution, deepfake models or institutional databases should enter through adapters and leave inspectable signals/evidence roots.

## CorpusHarness

`CorpusHarness` lets the same pipeline run locally over real corpus material without copying that corpus into GitHub.

It can:

- infer conservative representation types from file suffixes;
- accept explicit representation/root/hash/context/relation metadata in a JSON manifest;
- analyze a single claim or extract claims from text/HTML/TeX/corpus files;
- use PDF/images as evidence while refusing to interpret binary bytes as claim text without an extracted-text representation;
- generate `matverse.argus-corpus-audit.v1` JSON reports;
- redact raw claim text by default.

Example command:

```bash
python -m src.urano_kernel.argus_argos.corpus_harness audit.json --output report.json
```

## URANO runtime integration

URANO registers two governed events:

- `argus_case`: one explicit claim plus evidence;
- `argus_document`: a textual document plus optional evidence.

Both event types use `retain_payload=False`. The runtime history stores only a SHA-256 commitment to the incoming payload. MemoryGate and EvidencePack receive only redacted decision summaries containing hashes, states, authority and evidence-root identifiers.

Raw claim/evidence content is therefore not duplicated into URANO operational memory by default.

Malformed ARGUS runtime payloads fail closed as `BLOCK` summaries.

## GPT-Project-Bridge retriever integration

`BridgeEvidenceRetriever` implements the ARGUS `EvidenceRetriever` protocol over a versioned wire contract:

- query: `matverse.argus-evidence-query.v1`;
- response: `matverse.bridge-evidence-batch.v1`.

The retriever can use HTTP or an injected transport for offline/replay tests. It maps Bridge evidence into local `SourceDocument` objects while preserving:

- representation class;
- source-content hash as provenance;
- explicit evidence-root id;
- generated/derivative status;
- bounded metadata;
- optional explicit claim relation/context/integrity signals;
- optional observed text with its own SHA-256 commitment.

The adapter deliberately does **not** trust a remote scalar/authority value as local truth. `SourceIntake` recalculates authority from the representation class under URANO policy.

Metadata-only evidence never pretends that original source bytes crossed the interface. If observed text is omitted, the original source hash remains provenance only; it is not compared against a synthetic payload.

An explicit Bridge relation such as `SUPPORTS` controls the semantic relation, but not ARGOS admissibility. Example:

```text
Bridge relation = SUPPORTS
API_METADATA content authority = 25
ARGOS content threshold = 50
→ ARGUS SUPPORTED
→ ARGOS HOLD (AUTHORITY_BELOW_THRESHOLD:content)
```

Bridge transport/protocol failure is not interpreted as a false claim. In the URANO runtime it produces `HOLD / BRIDGE_RETRIEVAL_UNAVAILABLE`.

The corresponding Bridge exporter is `app/source_exchange.py` in `Gpt-project-bridge`, which emits the same response schema and never exports raw source text implicitly.

A deployed discovery/catalog/search endpoint is still a replaceable adapter boundary: the client contract and evidence exchange are implemented, while the choice of web search, local catalog, institutional database or other discovery service remains external to the epistemic kernel.

## Related components

- `ARGUS Connect`: user-facing intake / explorer / review interface; not the ARGUS analytical core and not ARGOS itself.
- `ARGOS Agent`: backend/executor for jobs, models, hashing, APIs and automations; not the full ARGOS governance system.
- `GPT-Project-Bridge`: source acquisition/resolution/interoperability layer. It supplies governed representations and resolved metadata to ARGUS through the versioned evidence exchange contract.
- `Evidence Gate` / `Ω-Gate`: downstream enforcement mechanisms; ARGOS is broader than either individual gate.

## Boundaries

- `ARGUS != ARGOS`.
- `ARGUS != Bridge`.
- `ARGUS Connect != ARGUS`.
- `ARGOS Agent != ARGOS`.
- `ARGOS != Ω-Gate`.
- `ARGOS != URANO`.
- `ClaimedID != ResolvedID`.
- `EvidenceRoot != RepresentationCount`.
- `HighAuthority != VerifiedEpistemicState`.
- `GeneratedRepresentation != IndependentEvidence`.
- `BridgeSupports != ArgosPass`.

## Validation status

The implementation is covered by CI for:

- role separation;
- epistemic fail-closed behavior;
- source intake;
- predicate authority;
- evidence-root deduplication;
- generated/derivative evidence handling;
- integrity hash checks;
- context and metadata conflicts;
- claim self-support prevention;
- end-to-end ARGUS → ARGOS pipeline;
- URANO runtime integration and payload redaction;
- local CorpusHarness behavior;
- Bridge wire-contract mapping and protocol failure;
- full repository regression suite.

These tests validate software behavior, not the truth of arbitrary external claims. External verification quality still depends on the evidence and adapters supplied to the pipeline.

## Integration strategy

This PR remains independent of PR #4 (`evidence_gate`) to avoid stacked-branch coupling. After PR #4 lands, a follow-up should map `GovernanceDecision` into that gate contract rather than duplicating gate semantics.

The Bridge evidence client/export contract is implemented. Live discovery remains modular so the core is usable offline and fail-closed when no independent evidence is available.

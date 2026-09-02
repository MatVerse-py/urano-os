"""End-to-end ARGUS -> ARGOS pipeline.

The pipeline is deterministic and adapter-driven. It never asks a language
model to decide truth inside the kernel. External search/model/media analyzers
may contribute evidence through `SourceDocument` metadata, but the core keeps
claim extraction, provenance, root deduplication, finding selection and ARGOS
adjudication replayable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from typing import Protocol, Sequence
import re

from .argus import Argus
from .argos import Argos, ArgosPolicy
from .evidence_graph import EvidenceComparator, EvidenceRelation, EvidenceRootIndex
from .models import ArgusFinding, ArgusFindingType, GovernanceDecision, PredicateAuthority
from .source_intake import ParsedSource, SourceDocument, SourceIntake


class EvidenceRetriever(Protocol):
    def retrieve(self, *, claim_ref: str, claim_text: str) -> Sequence[SourceDocument]: ...


class NullRetriever:
    def retrieve(self, *, claim_ref: str, claim_text: str) -> Sequence[SourceDocument]:
        return ()


@dataclass(frozen=True)
class PipelinePolicy:
    min_claim_chars: int = 16
    max_claim_chars: int = 1000
    max_claims: int = 100
    min_independent_support_roots: int = 1
    argos_policy: ArgosPolicy = field(
        default_factory=lambda: ArgosPolicy(required_authority={"content": 50})
    )


@dataclass(frozen=True)
class ClaimCandidate:
    claim_ref: str
    text: str
    source_ref: str
    ordinal: int


@dataclass(frozen=True)
class PipelineResult:
    claim: ClaimCandidate
    finding: ArgusFinding
    governance: GovernanceDecision
    evidence_root_count: int
    independent_root_count: int
    support_root_count: int
    contradiction_root_count: int
    evidence_root_ids: tuple[str, ...]


class ClaimExtractor:
    """Conservative declarative-claim extractor."""

    _SPLIT_RE = re.compile(r"(?<=[.!;])\s+|\n+")

    def extract(self, *, text: str, source_ref: str, policy: PipelinePolicy) -> tuple[ClaimCandidate, ...]:
        candidates: list[ClaimCandidate] = []
        for raw in self._SPLIT_RE.split(text):
            value = " ".join(raw.split()).strip(" -\t")
            if not value or len(value) < policy.min_claim_chars or len(value) > policy.max_claim_chars:
                continue
            if value.endswith("?"):
                continue
            if value.startswith(("```", "#", "//")):
                continue
            if value.count("{") + value.count("}") > 4:
                continue
            ordinal = len(candidates) + 1
            digest = sha256(f"{source_ref}\0{ordinal}\0{value}".encode("utf-8")).hexdigest()[:24]
            candidates.append(
                ClaimCandidate(
                    claim_ref=f"claim://{digest}",
                    text=value,
                    source_ref=source_ref,
                    ordinal=ordinal,
                )
            )
            if len(candidates) >= policy.max_claims:
                break
        return tuple(candidates)


class InMemoryRetriever:
    """Deterministic test/offline retriever keyed by claim ref or wildcard '*'."""

    def __init__(self, mapping: dict[str, Sequence[SourceDocument]]) -> None:
        self.mapping = dict(mapping)

    def retrieve(self, *, claim_ref: str, claim_text: str) -> Sequence[SourceDocument]:
        return tuple(self.mapping.get(claim_ref, ())) + tuple(self.mapping.get("*", ()))


class ArgusPipeline:
    def __init__(
        self,
        *,
        argus: Argus | None = None,
        argos: Argos | None = None,
        intake: SourceIntake | None = None,
        comparator: EvidenceComparator | None = None,
        extractor: ClaimExtractor | None = None,
        retriever: EvidenceRetriever | None = None,
        policy: PipelinePolicy | None = None,
    ) -> None:
        self.argus = argus or Argus()
        self.argos = argos or Argos()
        self.intake = intake or SourceIntake()
        self.comparator = comparator or EvidenceComparator()
        self.extractor = extractor or ClaimExtractor()
        self.retriever = retriever or NullRetriever()
        self.policy = policy or PipelinePolicy()

    @staticmethod
    def _claim_source(document: SourceDocument) -> SourceDocument:
        metadata = dict(document.metadata)
        metadata["claim_source"] = True
        return SourceDocument(
            locator=document.locator,
            representation=document.representation,
            content=document.content,
            metadata=metadata,
            expected_sha256=document.expected_sha256,
            evidence_root_id=document.evidence_root_id,
        )

    @staticmethod
    def _scope_shared_evidence(document: SourceDocument, claim: ClaimCandidate) -> SourceDocument:
        """Drop unbound claim-scoped controls from evidence reused across claims."""
        metadata = dict(document.metadata)
        controls_present = any(key in metadata for key in ("claim_relation", "context_status"))
        if not controls_present:
            return document

        bound_ref = str(metadata.get("relation_claim_ref") or "").strip()
        bound_hash = str(metadata.get("relation_claim_sha256") or "").strip().lower()
        claim_hash = sha256(" ".join(claim.text.split()).encode("utf-8")).hexdigest()
        bound = bool((bound_ref and bound_ref == claim.claim_ref) or (bound_hash and bound_hash == claim_hash))
        if bound:
            return document

        metadata.pop("claim_relation", None)
        metadata.pop("context_status", None)
        metadata["unbound_claim_control_dropped"] = True
        return SourceDocument(
            locator=document.locator,
            representation=document.representation,
            content=document.content,
            metadata=metadata,
            expected_sha256=document.expected_sha256,
            evidence_root_id=document.evidence_root_id,
        )

    @staticmethod
    def _select_finding_type(index: EvidenceRootIndex, *, min_support: int) -> ArgusFindingType:
        roots = index.summaries()
        if any(EvidenceRelation.INTEGRITY_WARNING in root.relations for root in roots):
            return ArgusFindingType.INTEGRITY_CONFLICT
        if any(EvidenceRelation.CONTEXTUALIZES in root.relations for root in roots):
            return ArgusFindingType.OUT_OF_CONTEXT
        contradictions = index.independent_roots(EvidenceRelation.CONTRADICTS)
        if contradictions or index.conflicts():
            return ArgusFindingType.CONTRADICTORY
        supports = index.independent_roots(EvidenceRelation.SUPPORTS)
        if len(supports) >= min_support:
            return ArgusFindingType.SUPPORTED
        if roots:
            return ArgusFindingType.INSUFFICIENT_EVIDENCE
        return ArgusFindingType.UNVERIFIED

    @staticmethod
    def _authority_relation_for(finding_type: ArgusFindingType) -> EvidenceRelation | None:
        return {
            ArgusFindingType.SUPPORTED: EvidenceRelation.SUPPORTS,
            ArgusFindingType.CONTRADICTORY: EvidenceRelation.CONTRADICTS,
            ArgusFindingType.OUT_OF_CONTEXT: EvidenceRelation.CONTEXTUALIZES,
            ArgusFindingType.INTEGRITY_CONFLICT: EvidenceRelation.INTEGRITY_WARNING,
        }.get(finding_type)

    def analyze_claim(
        self,
        *,
        claim: ClaimCandidate,
        evidence: Sequence[SourceDocument] = (),
        include_claim_source: SourceDocument | None = None,
    ) -> PipelineResult:
        documents: list[SourceDocument] = []
        if include_claim_source is not None:
            documents.append(self._claim_source(include_claim_source))
        documents.extend(evidence)
        documents.extend(self.retriever.retrieve(claim_ref=claim.claim_ref, claim_text=claim.text))

        parsed_sources: list[ParsedSource] = [self.intake.parse(document) for document in documents]
        index = EvidenceRootIndex(
            self.comparator.compare(claim_ref=claim.claim_ref, claim_text=claim.text, source=source)
            for source in parsed_sources
        )

        finding_type = self._select_finding_type(
            index,
            min_support=self.policy.min_independent_support_roots,
        )
        authority = index.aggregate_authority(self._authority_relation_for(finding_type))
        signals = list(index.signals())
        conflicts = list(index.conflicts())

        roots = index.summaries()
        support_roots = index.independent_roots(EvidenceRelation.SUPPORTS)
        contradiction_roots = index.independent_roots(EvidenceRelation.CONTRADICTS)
        independent_roots = index.independent_roots()

        signals.extend(
            (
                f"EVIDENCE_ROOTS:{len(roots)}",
                f"INDEPENDENT_ROOTS:{len(independent_roots)}",
                f"SUPPORT_ROOTS:{len(support_roots)}",
                f"CONTRADICTION_ROOTS:{len(contradiction_roots)}",
            )
        )

        if finding_type is ArgusFindingType.UNVERIFIED:
            authority = PredicateAuthority()

        finding = self.argus.inspect(
            claim_ref=claim.claim_ref,
            source_ref=claim.source_ref,
            representation="ARGUS_CASE",
            content=claim.text,
            finding_type=finding_type,
            authority=authority,
            signals=tuple(sorted(set(signals))),
            conflicts=tuple(sorted(set(conflicts))),
            metadata={
                "evidence_root_count": len(roots),
                "independent_root_count": len(independent_roots),
                "support_root_count": len(support_roots),
                "contradiction_root_count": len(contradiction_roots),
                "evidence_root_ids": tuple(root.root_id for root in roots),
            },
        )
        governance = self.argos.adjudicate(finding.governance_envelope(), self.policy.argos_policy)

        return PipelineResult(
            claim=claim,
            finding=finding,
            governance=governance,
            evidence_root_count=len(roots),
            independent_root_count=len(independent_roots),
            support_root_count=len(support_roots),
            contradiction_root_count=len(contradiction_roots),
            evidence_root_ids=tuple(root.root_id for root in roots),
        )

    def analyze_document(
        self,
        document: SourceDocument,
        *,
        evidence: Sequence[SourceDocument] = (),
    ) -> tuple[PipelineResult, ...]:
        primary = self.intake.parse(document)
        claims = self.extractor.extract(text=primary.text, source_ref=document.locator, policy=self.policy)
        return tuple(
            self.analyze_claim(
                claim=claim,
                evidence=tuple(self._scope_shared_evidence(item, claim) for item in evidence),
                include_claim_source=document,
            )
            for claim in claims
        )

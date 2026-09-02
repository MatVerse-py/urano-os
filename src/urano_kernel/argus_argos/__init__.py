"""ARGUS fake-news tool and ARGOS governance contracts for URANO.

The names ARGUS and ARGOS are preserved as project labels. This package does
not invent or freeze acronym expansions.
"""

from .models import (
    ArgusFinding,
    ArgusFindingType,
    GovernanceDecision,
    GovernanceEnvelope,
    GovernanceState,
    PredicateAuthority,
)
from .argus import Argus
from .argos import Argos, ArgosPolicy
from .source_intake import ParsedSource, SourceDocument, SourceIntake
from .evidence_graph import (
    EvidenceComparator,
    EvidenceLink,
    EvidenceRelation,
    EvidenceRootIndex,
    EvidenceRootSummary,
)
from .pipeline import (
    ArgusPipeline,
    ClaimCandidate,
    ClaimExtractor,
    EvidenceRetriever,
    InMemoryRetriever,
    NullRetriever,
    PipelinePolicy,
    PipelineResult,
)
from .corpus_harness import CorpusHarness, infer_representation, load_source, redacted_result

__all__ = [
    "ArgusFinding",
    "ArgusFindingType",
    "GovernanceDecision",
    "GovernanceEnvelope",
    "GovernanceState",
    "PredicateAuthority",
    "Argus",
    "Argos",
    "ArgosPolicy",
    "ParsedSource",
    "SourceDocument",
    "SourceIntake",
    "EvidenceComparator",
    "EvidenceLink",
    "EvidenceRelation",
    "EvidenceRootIndex",
    "EvidenceRootSummary",
    "ArgusPipeline",
    "ClaimCandidate",
    "ClaimExtractor",
    "EvidenceRetriever",
    "InMemoryRetriever",
    "NullRetriever",
    "PipelinePolicy",
    "PipelineResult",
    "CorpusHarness",
    "infer_representation",
    "load_source",
    "redacted_result",
]

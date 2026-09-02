"""Contracts for the ARGUS fake-news tool and ARGOS governance system.

ARGUS and ARGOS are preserved as project labels. No acronym expansion is
invented here.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Mapping, Tuple


@dataclass(frozen=True)
class PredicateAuthority:
    """Authority by predicate domain.

    Values are policy weights in [0, 100]. They are not probabilities and do
    not represent scientific truth.
    """

    content: int = 0
    version: int = 0
    authorship: int = 0
    publication: int = 0
    timestamp: int = 0
    execution: int = 0
    integrity: int = 0
    custody: int = 0

    def as_dict(self) -> Dict[str, int]:
        values = {
            "content": self.content,
            "version": self.version,
            "authorship": self.authorship,
            "publication": self.publication,
            "timestamp": self.timestamp,
            "execution": self.execution,
            "integrity": self.integrity,
            "custody": self.custody,
        }
        if any(value < 0 or value > 100 for value in values.values()):
            raise ValueError("authority values must be between 0 and 100")
        return values


class ArgusFindingType(str, Enum):
    """Conservative factual-integrity outcomes produced by ARGUS.

    These labels describe the state of the investigation. Suspicion labels are
    not equivalent to a final assertion that content is false.
    """

    SUPPORTED = "SUPPORTED"
    UNVERIFIED = "UNVERIFIED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    CONTRADICTORY = "CONTRADICTORY"
    OUT_OF_CONTEXT = "OUT_OF_CONTEXT"
    INTEGRITY_CONFLICT = "INTEGRITY_CONFLICT"
    MANIPULATION_SUSPECTED = "MANIPULATION_SUSPECTED"
    FABRICATION_SUSPECTED = "FABRICATION_SUSPECTED"
    COORDINATION_SUSPECTED = "COORDINATION_SUSPECTED"


@dataclass(frozen=True)
class GovernanceEnvelope:
    """Generic evidence input governed by ARGOS.

    ARGOS accepts envelopes from ARGUS or any other laboratory/tool. This
    prevents the governance system from being structurally coupled to the
    fake-news tool. `epistemic_state` is explicit so governance cannot be
    bypassed by assigning high numeric authority to an unresolved finding.
    """

    record_id: str
    producer: str
    subject_ref: str
    authority: PredicateAuthority
    epistemic_state: str = ""
    conflicts: Tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ArgusFinding:
    """Finding from the ARGUS fake-news / factual-integrity tool."""

    finding_id: str
    claim_ref: str
    source_ref: str
    representation: str
    content_hash: str
    finding_type: ArgusFindingType
    authority: PredicateAuthority
    signals: Tuple[str, ...] = ()
    conflicts: Tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)
    notes: Tuple[str, ...] = ()

    def governance_envelope(self) -> GovernanceEnvelope:
        return GovernanceEnvelope(
            record_id=self.finding_id,
            producer="ARGUS",
            subject_ref=self.claim_ref,
            authority=self.authority,
            epistemic_state=self.finding_type.value,
            conflicts=self.conflicts,
            metadata={
                **dict(self.metadata),
                "finding_type": self.finding_type.value,
                "source_ref": self.source_ref,
                "representation": self.representation,
                "content_hash": self.content_hash,
                "signals": self.signals,
            },
        )


class GovernanceState(str, Enum):
    PASS = "PASS"
    HOLD = "HOLD"
    BLOCK = "BLOCK"


@dataclass(frozen=True)
class GovernanceDecision:
    """Policy decision produced by the ARGOS governance kernel."""

    record_id: str
    state: GovernanceState
    reasons: Tuple[str, ...]
    policy_id: str

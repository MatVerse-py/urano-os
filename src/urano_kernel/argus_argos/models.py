"""Shared contracts for ARGUS perception and ARGOS adjudication."""

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


@dataclass(frozen=True)
class EvidenceObservation:
    """Qualified observation produced by ARGUS.

    An observation records what was seen and the authority attached to that
    representation. It is not itself an execution or publication decision.
    """

    observation_id: str
    source_ref: str
    representation: str
    content_hash: str
    authority: PredicateAuthority
    metadata: Mapping[str, Any] = field(default_factory=dict)
    conflicts: Tuple[str, ...] = ()
    notes: Tuple[str, ...] = ()


class AdjudicationState(str, Enum):
    PASS = "PASS"
    HOLD = "HOLD"
    BLOCK = "BLOCK"


@dataclass(frozen=True)
class Adjudication:
    """Governed decision produced by ARGOS."""

    observation_id: str
    state: AdjudicationState
    reasons: Tuple[str, ...]
    policy_id: str

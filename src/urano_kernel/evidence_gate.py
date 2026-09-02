"""Evidence Gate – fronteira de evidência com portões fail-closed.

Toda alegação que entra no kernel carrega uma classe de proveniência
declarada. Os portões apenas admitem ou bloqueiam: não há ponderação,
e a falha em qualquer portão bloqueia a alegação (fail-closed).
"""
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Optional


class EvidenceClass(str, Enum):
    OBSERVED_TEXT = "OBSERVED_TEXT"
    FILE_READ = "FILE_READ"
    COMPUTED = "COMPUTED"
    EXTERNAL_VERIFIED = "EXTERNAL_VERIFIED"
    INFERRED = "INFERRED"
    UNVERIFIED = "UNVERIFIED"


# Classes cuja proveniência pode ser checada mecanicamente.
VERIFIABLE = {
    EvidenceClass.OBSERVED_TEXT,
    EvidenceClass.FILE_READ,
    EvidenceClass.EXTERNAL_VERIFIED,
    EvidenceClass.COMPUTED,
}

# Subconjunto de VERIFIABLE que pode ancorar a existência de uma alegação
# (COMPUTED sozinho não basta: um cálculo sobre nada ainda é nada).
ANCHORING = {
    EvidenceClass.OBSERVED_TEXT,
    EvidenceClass.FILE_READ,
    EvidenceClass.EXTERNAL_VERIFIED,
}


@dataclass(frozen=True)
class Claim:
    """Uma alegação com proveniência declarada."""
    content: Any
    evidence_class: EvidenceClass
    source: str = ""


@dataclass(frozen=True)
class GateVerdict:
    passed: bool
    failed_gate: Optional[str]
    source: str


GatePredicate = Callable[[list], bool]


def _can_exist(claims: list) -> bool:
    """Ao menos uma alegação precisa estar ancorada em evidência direta."""
    return any(c.evidence_class in ANCHORING for c in claims)


def _can_publish(claims: list) -> bool:
    """Nenhuma alegação UNVERIFIED pode sair do portão como se fosse fato."""
    return all(c.evidence_class is not EvidenceClass.UNVERIFIED for c in claims)


# Sequência estrita: a ordem importa (CanExist antes de CanPublish).
GATES: tuple = (
    ("CanExist", _can_exist),
    ("CanPublish", _can_publish),
)


def judge(claims: list, source: str = "") -> GateVerdict:
    """Aplica os portões em sequência estrita. Primeira falha bloqueia."""
    if not claims:
        return GateVerdict(False, "CanExist", source)
    for name, predicate in GATES:
        if not predicate(claims):
            return GateVerdict(False, name, source)
    return GateVerdict(True, None, source)


def density(claims: list) -> float:
    """ρ: fração de alegações com classe de proveniência verificável."""
    if not claims:
        return 0.0
    return sum(1 for c in claims if c.evidence_class in VERIFIABLE) / len(claims)

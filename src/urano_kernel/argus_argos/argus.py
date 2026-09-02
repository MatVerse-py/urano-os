"""ARGUS: fake-news, misinformation and factual-integrity investigation tool."""

import hashlib
import json
from typing import Any, Mapping, Sequence

from .models import ArgusFinding, ArgusFindingType, PredicateAuthority


def _canonical_bytes(value: Any) -> bytes:
    if isinstance(value, bytes):
        return value
    if isinstance(value, str):
        return value.encode("utf-8")
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


class Argus:
    """Build conservative findings about factual integrity and misinformation.

    ARGUS is the vertical fake-news / factual-integrity tool. It may organize
    detector outputs, contradictions, context loss, manipulation signals and
    provenance evidence. It does not govern persistence, publication, ledger,
    replay or system policy; those responsibilities belong to ARGOS.

    This core does not pretend to infer truth from raw content. Findings stronger
    than UNVERIFIED/INSUFFICIENT_EVIDENCE require at least one supporting
    signal or conflict, preventing unsupported labels from being emitted.
    """

    _EVIDENCE_REQUIRED = {
        ArgusFindingType.SUPPORTED,
        ArgusFindingType.CONTRADICTORY,
        ArgusFindingType.OUT_OF_CONTEXT,
        ArgusFindingType.INTEGRITY_CONFLICT,
        ArgusFindingType.MANIPULATION_SUSPECTED,
        ArgusFindingType.FABRICATION_SUSPECTED,
        ArgusFindingType.COORDINATION_SUSPECTED,
    }

    def inspect(
        self,
        *,
        claim_ref: str,
        source_ref: str,
        representation: str,
        content: Any,
        finding_type: ArgusFindingType,
        authority: PredicateAuthority,
        signals: Sequence[str] = (),
        conflicts: Sequence[str] = (),
        metadata: Mapping[str, Any] | None = None,
        notes: Sequence[str] = (),
    ) -> ArgusFinding:
        if not claim_ref.strip():
            raise ValueError("claim_ref is required")
        if not source_ref.strip():
            raise ValueError("source_ref is required")
        if not representation.strip():
            raise ValueError("representation is required")

        authority.as_dict()
        signals = tuple(signal for signal in signals if str(signal).strip())
        conflicts = tuple(conflict for conflict in conflicts if str(conflict).strip())

        if finding_type in self._EVIDENCE_REQUIRED and not (signals or conflicts):
            raise ValueError("supported or suspicious findings require evidence signals or conflicts")

        content_hash = hashlib.sha256(_canonical_bytes(content)).hexdigest()
        seed = {
            "claim_ref": claim_ref,
            "source_ref": source_ref,
            "representation": representation,
            "content_hash": content_hash,
            "finding_type": finding_type.value,
            "signals": sorted(signals),
            "conflicts": sorted(conflicts),
        }
        finding_id = hashlib.sha256(_canonical_bytes(seed)).hexdigest()

        return ArgusFinding(
            finding_id=finding_id,
            claim_ref=claim_ref,
            source_ref=source_ref,
            representation=representation,
            content_hash=content_hash,
            finding_type=finding_type,
            authority=authority,
            signals=signals,
            conflicts=conflicts,
            metadata=dict(metadata or {}),
            notes=tuple(notes),
        )

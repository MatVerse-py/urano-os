"""ARGUS: perception and qualification of heterogeneous information."""

import hashlib
import json
from typing import Any, Mapping, Sequence

from .models import EvidenceObservation, PredicateAuthority


def _canonical_bytes(value: Any) -> bytes:
    if isinstance(value, bytes):
        return value
    if isinstance(value, str):
        return value.encode("utf-8")
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


class Argus:
    """Turn a source representation into a qualified evidence observation.

    ARGUS records provenance-facing facts. It does not decide whether an
    observation may be executed, persisted or published.
    """

    def observe(
        self,
        *,
        source_ref: str,
        representation: str,
        content: Any,
        authority: PredicateAuthority,
        metadata: Mapping[str, Any] | None = None,
        conflicts: Sequence[str] = (),
        notes: Sequence[str] = (),
    ) -> EvidenceObservation:
        if not source_ref.strip():
            raise ValueError("source_ref is required")
        if not representation.strip():
            raise ValueError("representation is required")

        content_hash = hashlib.sha256(_canonical_bytes(content)).hexdigest()
        authority.as_dict()  # validate policy-weight domain values

        seed = {
            "source_ref": source_ref,
            "representation": representation,
            "content_hash": content_hash,
        }
        observation_id = hashlib.sha256(_canonical_bytes(seed)).hexdigest()

        return EvidenceObservation(
            observation_id=observation_id,
            source_ref=source_ref,
            representation=representation,
            content_hash=content_hash,
            authority=authority,
            metadata=dict(metadata or {}),
            conflicts=tuple(conflicts),
            notes=tuple(notes),
        )

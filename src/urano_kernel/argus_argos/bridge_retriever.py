"""GPT-Project-Bridge -> ARGUS evidence retriever adapter.

The adapter consumes a small, versioned wire contract. It intentionally does
not trust remote scalar/authority scores as local truth. URANO re-evaluates
representation authority locally through SourceIntake while preserving Bridge
hashes, evidence-root identities, epistemic state and explicit relations as
provenance metadata.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from typing import Any, Callable, Mapping, Sequence
from urllib import request
import json

from .source_intake import SourceDocument


QUERY_SCHEMA = "matverse.argus-evidence-query.v1"
BATCH_SCHEMA = "matverse.bridge-evidence-batch.v1"


class BridgeProtocolError(RuntimeError):
    """Raised when the Bridge response cannot be safely interpreted."""


Transport = Callable[[str, bytes, Mapping[str, str], float], bytes]


def _default_transport(url: str, payload: bytes, headers: Mapping[str, str], timeout: float) -> bytes:
    req = request.Request(url, data=payload, headers=dict(headers), method="POST")
    with request.urlopen(req, timeout=timeout) as response:  # nosec - explicit configured endpoint
        return response.read()


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode("utf-8")


def _clean_mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


@dataclass(frozen=True)
class BridgeEvidenceRetriever:
    """Retrieve evidence from a Bridge-compatible evidence endpoint.

    The endpoint receives a redacted claim query and returns a versioned batch.
    `observed_text` is optional. Metadata-only items remain useful for structured
    conflicts (DOI/version/status) but cannot become textual corroboration unless
    the Bridge supplies an explicit, auditable `claim_relation`.
    """

    endpoint: str
    timeout: float = 15.0
    max_sources: int = 32
    headers: Mapping[str, str] = field(default_factory=dict)
    transport: Transport = _default_transport

    def _query(self, *, claim_ref: str, claim_text: str) -> Mapping[str, Any]:
        if not self.endpoint.strip():
            raise BridgeProtocolError("Bridge endpoint is required")
        query = {
            "schema": QUERY_SCHEMA,
            "claim_ref": claim_ref,
            "claim_text": claim_text,
            "max_sources": self.max_sources,
        }
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            **dict(self.headers),
        }
        try:
            raw = self.transport(self.endpoint, _canonical_bytes(query), headers, self.timeout)
            payload = json.loads(raw.decode("utf-8"))
        except Exception as exc:
            raise BridgeProtocolError(f"Bridge transport failed: {type(exc).__name__}: {exc}") from exc
        if not isinstance(payload, Mapping):
            raise BridgeProtocolError("Bridge response must be a JSON object")
        if payload.get("schema") != BATCH_SCHEMA:
            raise BridgeProtocolError(f"unsupported Bridge schema: {payload.get('schema')!r}")
        if not isinstance(payload.get("items"), list):
            raise BridgeProtocolError("Bridge batch must contain items[]")
        return payload

    @staticmethod
    def _item_to_source(item: Mapping[str, Any], *, batch: Mapping[str, Any]) -> SourceDocument:
        locator = str(item.get("locator") or "").strip()
        representation = str(item.get("representation") or "").strip().upper()
        if not locator or not representation:
            raise BridgeProtocolError("Bridge item requires locator and representation")

        metadata = _clean_mapping(item.get("metadata"))
        metadata.update(
            {
                "bridge_contract": BATCH_SCHEMA,
                "bridge_evidence_hash": batch.get("evidence_hash"),
                "bridge_evidence_state": batch.get("state"),
                "bridge_evidence_tier": batch.get("evidence_tier"),
                "bridge_source_content_hash": item.get("source_content_hash"),
                "bridge_independent": item.get("independent"),
            }
        )

        for key in ("claim_relation", "context_status", "integrity_status"):
            value = item.get(key)
            if value is not None and str(value).strip():
                metadata[key] = str(value)

        generated = item.get("model_generated") is True or item.get("generated") is True
        if generated:
            metadata["model_generated"] = True
        if item.get("derived_representation") is True or item.get("independent") is False:
            metadata["derived_representation"] = True

        observed_text = item.get("observed_text")
        observed_text_sha256 = str(item.get("observed_text_sha256") or "").strip().lower()
        if observed_text is not None:
            content = str(observed_text)
            expected_sha256 = observed_text_sha256 or None
            if expected_sha256 is None:
                metadata["bridge_text_unanchored"] = True
        else:
            # Metadata-only evidence is represented by its canonical metadata,
            # never by pretending that source bytes were transferred.
            content = json.dumps(metadata, sort_keys=True, ensure_ascii=False, default=str)
            expected_sha256 = None
            metadata["bridge_metadata_only"] = True

        root_id = str(
            item.get("evidence_root_id")
            or item.get("source_content_hash")
            or batch.get("evidence_hash")
            or ""
        ).strip()
        if not root_id:
            root_id = sha256(_canonical_bytes({"locator": locator, "representation": representation})).hexdigest()

        return SourceDocument(
            locator=locator,
            representation=representation,
            content=content,
            metadata=metadata,
            expected_sha256=expected_sha256,
            evidence_root_id=root_id,
        )

    def retrieve(self, *, claim_ref: str, claim_text: str) -> Sequence[SourceDocument]:
        payload = self._query(claim_ref=claim_ref, claim_text=claim_text)
        items = payload["items"][: max(0, self.max_sources)]
        sources: list[SourceDocument] = []
        for raw_item in items:
            if not isinstance(raw_item, Mapping):
                raise BridgeProtocolError("Bridge items must be JSON objects")
            sources.append(self._item_to_source(raw_item, batch=payload))
        return tuple(sources)

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
from urllib import parse, request
import json
import re

from .source_intake import SourceDocument


QUERY_SCHEMA = "matverse.argus-evidence-query.v1"
BATCH_SCHEMA = "matverse.bridge-evidence-batch.v1"
_QUERY_TOKEN_RE = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ0-9_.:/-]{3,}")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)
_UUID_RE = re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\b", re.IGNORECASE)
_SECRET_RE = re.compile(r"\b(?:sk-|ghp_|github_pat_|hf_)[A-Za-z0-9_-]{8,}\b", re.IGNORECASE)
_LONG_NUMBER_RE = re.compile(r"\b\d{9,}\b")
_LONG_HEX_RE = re.compile(r"\b[0-9a-f]{20,}\b", re.IGNORECASE)
_ABSOLUTE_MAX_RESPONSE_BYTES = 4 * 1024 * 1024
_DEFAULT_MAX_RESPONSE_BYTES = 2 * 1024 * 1024
_DEFAULT_MAX_OBSERVED_TEXT_CHARS = 256_000
_SAFE_BRIDGE_METADATA_KEYS = {
    "citation_doi",
    "citation_title",
    "citation_author",
    "citation_publication_date",
    "citation_pdf_url",
    "canonical_url",
    "title",
    "author",
    "version",
    "description",
    "og:description",
    "closure_complete",
    "official_version",
    "model_generated",
    "generated",
    "derived_representation",
    "evidence_root_id",
    "derived_from_root",
    "integrity_status",
    "content_type",
    "captured_at",
    "published_at",
    "provider",
    "record_id",
    "repo",
    "commit_sha",
    "timestamp",
}


class BridgeProtocolError(RuntimeError):
    """Raised when the Bridge response cannot be safely interpreted."""


Transport = Callable[[str, bytes, Mapping[str, str], float], bytes]


def _default_transport(url: str, payload: bytes, headers: Mapping[str, str], timeout: float) -> bytes:
    req = request.Request(url, data=payload, headers=dict(headers), method="POST")
    with request.urlopen(req, timeout=timeout) as response:  # nosec - explicit configured endpoint
        raw = response.read(_ABSOLUTE_MAX_RESPONSE_BYTES + 1)
    if len(raw) > _ABSOLUTE_MAX_RESPONSE_BYTES:
        raise BridgeProtocolError("Bridge response exceeds absolute size limit")
    return raw


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode("utf-8")


def _bounded_metadata_value(value: Any) -> Any | None:
    if isinstance(value, str):
        return value[:4096]
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    if isinstance(value, (list, tuple)) and len(value) <= 32:
        out: list[Any] = []
        for item in value:
            if isinstance(item, str):
                out.append(item[:1024])
            elif isinstance(item, (int, float, bool)) or item is None:
                out.append(item)
            else:
                return None
        return out
    return None


def _clean_mapping(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    out: dict[str, Any] = {}
    for raw_key, raw_value in value.items():
        key = str(raw_key)
        if key not in _SAFE_BRIDGE_METADATA_KEYS:
            continue
        bounded = _bounded_metadata_value(raw_value)
        if bounded is not None or raw_value is None:
            out[key] = bounded
    return out


def _normalized_claim(value: str) -> str:
    return " ".join(value.split())


def _redact_sensitive_spans(value: str) -> str:
    redacted = value
    for pattern in (_EMAIL_RE, _URL_RE, _UUID_RE, _SECRET_RE, _LONG_NUMBER_RE, _LONG_HEX_RE):
        redacted = pattern.sub(" ", redacted)
    return redacted


def _query_terms(value: str, *, limit: int = 64) -> tuple[str, ...]:
    value = _redact_sensitive_spans(value)
    seen: set[str] = set()
    terms: list[str] = []
    for match in _QUERY_TOKEN_RE.finditer(value):
        term = match.group(0).casefold()
        if term in seen or len(term) > 96:
            continue
        seen.add(term)
        terms.append(term)
        if len(terms) >= limit:
            break
    return tuple(terms)


def _scope_matches(item: Mapping[str, Any], *, claim_ref: str, claim_sha256: str) -> bool:
    bound_ref = str(item.get("relation_claim_ref") or "").strip()
    bound_hash = str(item.get("relation_claim_sha256") or "").strip().lower()
    return bool((bound_ref and bound_ref == claim_ref) or (bound_hash and bound_hash == claim_sha256))


@dataclass(frozen=True)
class BridgeEvidenceRetriever:
    """Retrieve evidence from a Bridge-compatible evidence endpoint.

    `TERMS` (default) sends a claim hash plus sanitized deterministic search
    terms. `HASH_ONLY` sends no lexical content and therefore only discovers
    evidence already bound/indexed by digest. `FULL_TEXT` requires explicit
    operator opt-in.
    """

    endpoint: str
    timeout: float = 15.0
    max_sources: int = 32
    query_disclosure: str = "TERMS"
    max_response_bytes: int = _DEFAULT_MAX_RESPONSE_BYTES
    max_observed_text_chars: int = _DEFAULT_MAX_OBSERVED_TEXT_CHARS
    headers: Mapping[str, str] = field(default_factory=dict)
    transport: Transport = _default_transport

    def __post_init__(self) -> None:
        endpoint = self.endpoint.strip()
        parsed = parse.urlsplit(endpoint)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise BridgeProtocolError("Bridge endpoint must be an explicit http(s) URL")
        if self.timeout <= 0 or self.timeout > 120:
            raise BridgeProtocolError("Bridge timeout must be within (0, 120] seconds")
        if self.max_sources < 0 or self.max_sources > 256:
            raise BridgeProtocolError("max_sources must be between 0 and 256")
        if self.max_response_bytes < 1024 or self.max_response_bytes > _ABSOLUTE_MAX_RESPONSE_BYTES:
            raise BridgeProtocolError("max_response_bytes is outside the supported bound")
        if self.max_observed_text_chars < 0 or self.max_observed_text_chars > 1_000_000:
            raise BridgeProtocolError("max_observed_text_chars is outside the supported bound")
        if self.query_disclosure.strip().upper() not in {"TERMS", "HASH_ONLY", "FULL_TEXT"}:
            raise BridgeProtocolError(f"unsupported query disclosure mode: {self.query_disclosure!r}")

    def _query(self, *, claim_ref: str, claim_text: str) -> Mapping[str, Any]:
        normalized = _normalized_claim(claim_text)
        disclosure = self.query_disclosure.strip().upper()

        query: dict[str, Any] = {
            "schema": QUERY_SCHEMA,
            "claim_ref": claim_ref,
            "claim_sha256": sha256(normalized.encode("utf-8")).hexdigest(),
            "query_terms": [] if disclosure == "HASH_ONLY" else list(_query_terms(normalized)),
            "max_sources": self.max_sources,
        }
        if disclosure == "FULL_TEXT":
            query["claim_text"] = normalized

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            **dict(self.headers),
        }
        try:
            raw = self.transport(self.endpoint, _canonical_bytes(query), headers, self.timeout)
            if len(raw) > self.max_response_bytes:
                raise BridgeProtocolError("Bridge response exceeds configured size limit")
            payload = json.loads(raw.decode("utf-8"))
        except BridgeProtocolError:
            raise
        except Exception as exc:
            raise BridgeProtocolError(f"Bridge transport failed: {type(exc).__name__}: {exc}") from exc
        if not isinstance(payload, Mapping):
            raise BridgeProtocolError("Bridge response must be a JSON object")
        if payload.get("schema") != BATCH_SCHEMA:
            raise BridgeProtocolError(f"unsupported Bridge schema: {payload.get('schema')!r}")
        if not isinstance(payload.get("items"), list):
            raise BridgeProtocolError("Bridge batch must contain items[]")
        return payload

    def _item_to_source(
        self,
        item: Mapping[str, Any],
        *,
        batch: Mapping[str, Any],
        claim_ref: str,
        claim_sha256: str,
    ) -> SourceDocument:
        locator = str(item.get("locator") or "").strip()
        representation = str(item.get("representation") or "").strip().upper()
        if not locator or not representation:
            raise BridgeProtocolError("Bridge item requires locator and representation")

        source_content_hash = str(item.get("source_content_hash") or "").strip().lower()
        if source_content_hash and not _SHA256_RE.fullmatch(source_content_hash):
            raise BridgeProtocolError("Bridge source_content_hash must be SHA-256 hex")

        metadata = _clean_mapping(item.get("metadata"))
        metadata.update(
            {
                "bridge_contract": BATCH_SCHEMA,
                "bridge_evidence_hash": batch.get("evidence_hash"),
                "bridge_evidence_state": batch.get("state"),
                "bridge_evidence_tier": batch.get("evidence_tier"),
                "bridge_source_content_hash": source_content_hash or None,
                "bridge_independent": item.get("independent"),
            }
        )

        scoped = _scope_matches(item, claim_ref=claim_ref, claim_sha256=claim_sha256)
        for key in ("claim_relation", "context_status"):
            value = item.get(key)
            if value is not None and str(value).strip():
                if scoped:
                    metadata[key] = str(value)[:256]
                else:
                    metadata["bridge_unbound_claim_control_dropped"] = True

        integrity_status = item.get("integrity_status")
        if integrity_status is not None and str(integrity_status).strip():
            metadata["integrity_status"] = str(integrity_status)[:256]

        generated = item.get("model_generated") is True or item.get("generated") is True
        if generated:
            metadata["model_generated"] = True
        if item.get("derived_representation") is True or item.get("independent") is False:
            metadata["derived_representation"] = True

        observed_text = item.get("observed_text")
        observed_text_sha256 = str(item.get("observed_text_sha256") or "").strip().lower()
        if observed_text is not None:
            content = str(observed_text)
            if len(content) > self.max_observed_text_chars:
                raise BridgeProtocolError("Bridge observed_text exceeds configured size limit")
            if observed_text_sha256 and not _SHA256_RE.fullmatch(observed_text_sha256):
                raise BridgeProtocolError("observed_text_sha256 must be SHA-256 hex")
            expected_sha256 = observed_text_sha256 or None
            if expected_sha256 is None:
                metadata["bridge_text_unanchored"] = True
        else:
            content = json.dumps(metadata, sort_keys=True, ensure_ascii=False, default=str)
            expected_sha256 = None
            metadata["bridge_metadata_only"] = True

        root_id = str(
            item.get("evidence_root_id")
            or source_content_hash
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
        normalized = _normalized_claim(claim_text)
        claim_sha256 = sha256(normalized.encode("utf-8")).hexdigest()
        payload = self._query(claim_ref=claim_ref, claim_text=claim_text)
        items = payload["items"][: self.max_sources]
        sources: list[SourceDocument] = []
        for raw_item in items:
            if not isinstance(raw_item, Mapping):
                raise BridgeProtocolError("Bridge items must be JSON objects")
            sources.append(
                self._item_to_source(
                    raw_item,
                    batch=payload,
                    claim_ref=claim_ref,
                    claim_sha256=claim_sha256,
                )
            )
        return tuple(sources)

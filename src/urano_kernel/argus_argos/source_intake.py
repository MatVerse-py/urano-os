"""Governed source intake for ARGUS.

This module mirrors the representation semantics already used by the
GPT-Project-Bridge without making the URANO kernel depend on that repository.
The scalar representation ranking is never treated as a probability of truth;
ARGUS uses predicate-specific authority and explicit provenance flags.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from html.parser import HTMLParser
from math import log2
from typing import Any, Mapping
import json

from .models import PredicateAuthority


REPRESENTATION_AUTHORITY: dict[str, dict[str, int]] = {
    "LATEX_SOURCE": {"content": 100, "version": 100, "authorship": 30, "publication": 0, "timestamp": 0, "execution": 0},
    "ARXIV_EPRINT_SOURCE": {"content": 100, "version": 100, "authorship": 60, "publication": 70, "timestamp": 90, "execution": 0},
    "SAVED_PDF": {"content": 80, "version": 60, "authorship": 30, "publication": 0, "timestamp": 0, "execution": 0},
    "DOI_METADATA": {"content": 20, "version": 70, "authorship": 60, "publication": 100, "timestamp": 90, "execution": 0},
    "GIT_COMMIT": {"content": 90, "version": 100, "authorship": 60, "publication": 0, "timestamp": 85, "execution": 0},
    "API_METADATA": {"content": 25, "version": 75, "authorship": 65, "publication": 90, "timestamp": 80, "execution": 0},
    "LIVE_HTML": {"content": 80, "version": 55, "authorship": 40, "publication": 70, "timestamp": 50, "execution": 0},
    "SAVED_HTML": {"content": 75, "version": 55, "authorship": 40, "publication": 55, "timestamp": 45, "execution": 0},
    "ORCID_SNAPSHOT": {"content": 10, "version": 20, "authorship": 90, "publication": 40, "timestamp": 80, "execution": 0},
    "REPOSITORY_FILE": {"content": 80, "version": 80, "authorship": 35, "publication": 0, "timestamp": 30, "execution": 0},
    "HF_SNAPSHOT": {"content": 70, "version": 70, "authorship": 35, "publication": 45, "timestamp": 60, "execution": 0},
    "CORPUS_COPY": {"content": 50, "version": 30, "authorship": 20, "publication": 0, "timestamp": 10, "execution": 0},
    "SAVED_IMAGE": {"content": 35, "version": 10, "authorship": 5, "publication": 0, "timestamp": 5, "execution": 0},
    "SCREENSHOT": {"content": 30, "version": 5, "authorship": 5, "publication": 0, "timestamp": 5, "execution": 0},
    "DOCUMENT_PAGE_RENDER": {"content": 0, "version": 0, "authorship": 0, "publication": 0, "timestamp": 0, "execution": 0},
    "GENERATED_IMAGE": {"content": 0, "version": 0, "authorship": 0, "publication": 0, "timestamp": 0, "execution": 0},
    "MODEL_REPORT": {"content": 5, "version": 0, "authorship": 0, "publication": 0, "timestamp": 0, "execution": 0},
    "OBSERVED_TEXT": {"content": 35, "version": 10, "authorship": 0, "publication": 0, "timestamp": 0, "execution": 0},
}

NON_INDEPENDENT_REPRESENTATIONS = {"GENERATED_IMAGE", "DOCUMENT_PAGE_RENDER", "MODEL_REPORT"}


@dataclass(frozen=True)
class SourceDocument:
    """One source representation presented to ARGUS.

    `expected_sha256` proves only byte equality when supplied by a trusted
    upstream anchor. `evidence_root_id` may bind derivative representations to
    a common evidence root; otherwise the content hash is the root key.
    """

    locator: str
    representation: str
    content: str | bytes
    metadata: Mapping[str, Any] = field(default_factory=dict)
    expected_sha256: str | None = None
    evidence_root_id: str | None = None


@dataclass(frozen=True)
class ParsedSource:
    locator: str
    representation: str
    content_hash: str
    root_id: str
    text: str
    metadata: Mapping[str, Any]
    authority: PredicateAuthority
    independent: bool
    tampered: bool
    signals: tuple[str, ...] = ()


class _MetaParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.metadata: dict[str, str] = {}
        self.text_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "meta":
            return
        data = {str(k).lower(): (v or "") for k, v in attrs}
        key = data.get("name") or data.get("property")
        value = data.get("content")
        if key and value:
            self.metadata.setdefault(key, value)

    def handle_data(self, data: str) -> None:
        value = " ".join(data.split())
        if value:
            self.text_parts.append(value)


def _to_bytes(content: str | bytes) -> bytes:
    return content if isinstance(content, bytes) else content.encode("utf-8")


def _to_text(content: str | bytes) -> str:
    if isinstance(content, str):
        return content
    return content.decode("utf-8", errors="replace")


def shannon_entropy(data: bytes) -> float:
    """Return byte entropy as a descriptive statistic only."""
    if not data:
        return 0.0
    counts = [0] * 256
    for value in data:
        counts[value] += 1
    total = len(data)
    return -sum((count / total) * log2(count / total) for count in counts if count)


def authority_for(document: SourceDocument, *, tampered: bool) -> PredicateAuthority:
    profile = REPRESENTATION_AUTHORITY.get(document.representation.upper(), {})
    metadata = dict(document.metadata)

    integrity = 0
    if document.expected_sha256 is not None:
        integrity = 0 if tampered else 100
    elif metadata.get("hash_verified") is True:
        integrity = 95
    elif metadata.get("content_hash_observed") is True:
        integrity = 40

    custody = 100 if metadata.get("custody_chain_verified") is True else 0

    return PredicateAuthority(
        content=int(profile.get("content", 0)),
        version=int(profile.get("version", 0)),
        authorship=int(profile.get("authorship", 0)),
        publication=int(profile.get("publication", 0)),
        timestamp=int(profile.get("timestamp", 0)),
        execution=int(profile.get("execution", 0)),
        integrity=integrity,
        custody=custody,
    )


class SourceIntake:
    """Normalize heterogeneous source representations without inventing claims."""

    def parse(self, document: SourceDocument) -> ParsedSource:
        if not document.locator.strip():
            raise ValueError("source locator is required")
        representation = document.representation.strip().upper()
        if not representation:
            raise ValueError("source representation is required")

        payload = _to_bytes(document.content)
        digest = sha256(payload).hexdigest()
        expected = document.expected_sha256.lower() if document.expected_sha256 else None
        tampered = expected is not None and digest.lower() != expected

        metadata = dict(document.metadata)
        text = _to_text(document.content)
        signals: list[str] = []

        if representation in {"SAVED_HTML", "LIVE_HTML"}:
            parser = _MetaParser()
            parser.feed(text)
            for key, value in parser.metadata.items():
                metadata.setdefault(key, value)

            visible_parts: list[str] = []
            if parser.text_parts:
                rendered = " ".join(parser.text_parts)
                metadata.setdefault("rendered_text", rendered)
                visible_parts.append(rendered)

            # Metadata descriptions often carry the archived page's factual
            # assertion even when the body is JS-rendered or absent. Include
            # each unique description once, preserving source wording.
            for key in ("description", "og:description", "twitter:description"):
                value = str(metadata.get(key) or "").strip()
                if value and value not in visible_parts:
                    visible_parts.append(value)

            if visible_parts:
                text = "\n".join(visible_parts)

        if representation in {"API_METADATA", "DOI_METADATA"}:
            try:
                parsed = json.loads(text)
                if isinstance(parsed, dict):
                    for key, value in parsed.items():
                        metadata.setdefault(str(key), value)
            except (json.JSONDecodeError, TypeError):
                signals.append("STRUCTURED_PARSE_FAILED")

        metadata.setdefault("observed_sha256", digest)
        metadata.setdefault("size_bytes", len(payload))
        metadata.setdefault("entropy_bits_per_byte", round(shannon_entropy(payload), 6))

        if tampered:
            signals.append("HASH_MISMATCH")
        if metadata.get("model_generated") is True or metadata.get("generated") is True:
            signals.append("GENERATED_REPRESENTATION")

        independent = (
            representation not in NON_INDEPENDENT_REPRESENTATIONS
            and metadata.get("model_generated") is not True
            and metadata.get("generated") is not True
            and metadata.get("derived_representation") is not True
        )

        root_id = (
            document.evidence_root_id
            or str(metadata.get("evidence_root_id") or metadata.get("derived_from_root") or "").strip()
            or digest
        )

        return ParsedSource(
            locator=document.locator,
            representation=representation,
            content_hash=digest,
            root_id=root_id,
            text=text,
            metadata=metadata,
            authority=authority_for(document, tampered=tampered),
            independent=independent,
            tampered=tampered,
            signals=tuple(signals),
        )

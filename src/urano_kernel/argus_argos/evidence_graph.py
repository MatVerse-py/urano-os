"""Evidence-root graph and conservative claim/source comparison for ARGUS."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable, Mapping
import re

from .models import PredicateAuthority
from .source_intake import ParsedSource


class EvidenceRelation(str, Enum):
    SUPPORTS = "SUPPORTS"
    CONTRADICTS = "CONTRADICTS"
    CONTEXTUALIZES = "CONTEXTUALIZES"
    INTEGRITY_WARNING = "INTEGRITY_WARNING"
    NEUTRAL = "NEUTRAL"


@dataclass(frozen=True)
class EvidenceLink:
    claim_ref: str
    root_id: str
    source_ref: str
    relation: EvidenceRelation
    authority: PredicateAuthority
    independent: bool
    signals: tuple[str, ...] = ()
    conflicts: tuple[str, ...] = ()
    metadata: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class EvidenceRootSummary:
    root_id: str
    independent: bool
    authority: PredicateAuthority
    relations: tuple[EvidenceRelation, ...]
    source_refs: tuple[str, ...]
    signals: tuple[str, ...]
    conflicts: tuple[str, ...]


def _normalized(value: str) -> str:
    return " ".join(value.casefold().split())


def _max_authority(values: Iterable[PredicateAuthority]) -> PredicateAuthority:
    rows = [value.as_dict() for value in values]
    if not rows:
        return PredicateAuthority()
    keys = tuple(rows[0].keys())
    merged = {key: max(row[key] for row in rows) for key in keys}
    return PredicateAuthority(**merged)


class EvidenceRootIndex:
    """Deduplicate derivative/duplicate representations by evidence root.

    Different files or renderings do not become independent corroborators merely
    because they exist as separate representations. Authority is aggregated by
    maximum per predicate domain, never by additive voting.
    """

    def __init__(self, links: Iterable[EvidenceLink] = ()) -> None:
        self._links: list[EvidenceLink] = list(links)

    def add(self, link: EvidenceLink) -> None:
        self._links.append(link)

    def summaries(self) -> tuple[EvidenceRootSummary, ...]:
        grouped: dict[str, list[EvidenceLink]] = {}
        for link in self._links:
            grouped.setdefault(link.root_id, []).append(link)

        summaries: list[EvidenceRootSummary] = []
        for root_id in sorted(grouped):
            links = grouped[root_id]
            summaries.append(
                EvidenceRootSummary(
                    root_id=root_id,
                    independent=any(link.independent for link in links),
                    authority=_max_authority(link.authority for link in links),
                    relations=tuple(sorted({link.relation for link in links}, key=lambda item: item.value)),
                    source_refs=tuple(sorted({link.source_ref for link in links})),
                    signals=tuple(sorted({signal for link in links for signal in link.signals})),
                    conflicts=tuple(sorted({conflict for link in links for conflict in link.conflicts})),
                )
            )
        return tuple(summaries)

    def independent_roots(self, relation: EvidenceRelation | None = None) -> tuple[EvidenceRootSummary, ...]:
        roots = self.summaries()
        if relation is None:
            return tuple(root for root in roots if root.independent)
        return tuple(root for root in roots if root.independent and relation in root.relations)

    def aggregate_authority(self) -> PredicateAuthority:
        return _max_authority(root.authority for root in self.independent_roots())

    def conflicts(self) -> tuple[str, ...]:
        return tuple(sorted({conflict for root in self.summaries() for conflict in root.conflicts}))

    def signals(self) -> tuple[str, ...]:
        return tuple(sorted({signal for root in self.summaries() for signal in root.signals}))


class EvidenceComparator:
    """Apply only conservative, inspectable rules.

    The comparator intentionally does not perform free-form semantic inference.
    Richer model-based or web-based analyzers can feed explicit relation/context
    metadata through adapters, while this core remains deterministic and
    replayable.
    """

    _PENDING_DOI_PATTERNS = (
        "doi: será atribuído após publicação",
        "doi será atribuído após publicação",
        "doi will be assigned after publication",
        "doi to be assigned after publication",
    )

    def compare(self, *, claim_ref: str, claim_text: str, source: ParsedSource) -> EvidenceLink:
        metadata = dict(source.metadata)
        signals = list(source.signals)
        conflicts: list[str] = []
        relation = EvidenceRelation.NEUTRAL

        explicit_relation = str(metadata.get("claim_relation") or "").strip().upper()
        if explicit_relation in EvidenceRelation.__members__:
            relation = EvidenceRelation[explicit_relation]
            signals.append(f"EXPLICIT_RELATION:{explicit_relation}")

        if source.tampered:
            relation = EvidenceRelation.INTEGRITY_WARNING
            conflicts.append("HASH_MISMATCH")

        context_status = str(metadata.get("context_status") or "").strip().upper()
        if context_status in {"OUT_OF_CONTEXT", "CONTEXT_LOSS", "CONTEXT_CHANGED"}:
            relation = EvidenceRelation.CONTEXTUALIZES
            signals.append(f"CONTEXT_SIGNAL:{context_status}")

        claim_norm = _normalized(claim_text)
        text_norm = _normalized(source.text)
        if relation is EvidenceRelation.NEUTRAL and claim_norm and claim_norm in text_norm:
            relation = EvidenceRelation.SUPPORTS
            signals.append("EXACT_TEXT_MATCH")

        description = str(metadata.get("description") or metadata.get("og:description") or "")
        citation_doi = str(metadata.get("citation_doi") or "").strip()
        combined = f"{claim_text} {description}".casefold()
        if citation_doi and any(pattern in combined for pattern in self._PENDING_DOI_PATTERNS):
            relation = EvidenceRelation.CONTRADICTS
            signals.append("STRUCTURED_METADATA_CONFLICT:DOI_PRESENT_VS_PENDING_PROSE")
            conflicts.append("DOI_PRESENT_VS_PENDING_PROSE")

        # Adapter-supplied integrity/media signals are treated as observations,
        # not as autonomous proof that media is fabricated.
        integrity_status = str(metadata.get("integrity_status") or "").strip().upper()
        if integrity_status in {"MISMATCH", "TAMPERED", "INVALID"}:
            relation = EvidenceRelation.INTEGRITY_WARNING
            signals.append(f"INTEGRITY_SIGNAL:{integrity_status}")
            conflicts.append(f"INTEGRITY_SIGNAL:{integrity_status}")

        return EvidenceLink(
            claim_ref=claim_ref,
            root_id=source.root_id,
            source_ref=source.locator,
            relation=relation,
            authority=source.authority,
            independent=source.independent,
            signals=tuple(sorted(set(signals))),
            conflicts=tuple(sorted(set(conflicts))),
            metadata={
                "representation": source.representation,
                "content_hash": source.content_hash,
            },
        )

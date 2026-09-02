"""Evidence-root graph and conservative claim/source comparison for ARGUS."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable, Mapping

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

    A root cannot launder properties across representations. A derivative
    SUPPORTS link does not borrow independence from a neutral parent, and a
    high-authority neutral representation does not lend authority to a weaker
    representation that actually supports or contradicts the claim.
    """

    def __init__(self, links: Iterable[EvidenceLink] = ()) -> None:
        self._links: list[EvidenceLink] = list(links)

    def add(self, link: EvidenceLink) -> None:
        self._links.append(link)

    def _grouped(self) -> dict[str, list[EvidenceLink]]:
        grouped: dict[str, list[EvidenceLink]] = {}
        for link in self._links:
            grouped.setdefault(link.root_id, []).append(link)
        return grouped

    def summaries(self) -> tuple[EvidenceRootSummary, ...]:
        grouped = self._grouped()
        summaries: list[EvidenceRootSummary] = []
        for root_id in sorted(grouped):
            links = grouped[root_id]
            independent_links = [link for link in links if link.independent]
            summaries.append(
                EvidenceRootSummary(
                    root_id=root_id,
                    independent=bool(independent_links),
                    authority=_max_authority(link.authority for link in independent_links),
                    relations=tuple(sorted({link.relation for link in links}, key=lambda item: item.value)),
                    source_refs=tuple(sorted({link.source_ref for link in links})),
                    signals=tuple(sorted({signal for link in links for signal in link.signals})),
                    conflicts=tuple(sorted({conflict for link in links for conflict in link.conflicts})),
                )
            )
        return tuple(summaries)

    def independent_roots(self, relation: EvidenceRelation | None = None) -> tuple[EvidenceRootSummary, ...]:
        grouped = self._grouped()
        eligible_root_ids: set[str] = set()
        for root_id, links in grouped.items():
            for link in links:
                if not link.independent:
                    continue
                if relation is None or link.relation is relation:
                    eligible_root_ids.add(root_id)
                    break
        return tuple(root for root in self.summaries() if root.root_id in eligible_root_ids)

    def aggregate_authority(self, relation: EvidenceRelation | None = None) -> PredicateAuthority:
        """Aggregate authority only from independent links relevant to a finding."""
        per_root: list[PredicateAuthority] = []
        for links in self._grouped().values():
            eligible = [
                link.authority
                for link in links
                if link.independent and (relation is None or link.relation is relation)
            ]
            if eligible:
                per_root.append(_max_authority(eligible))
        return _max_authority(per_root)

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
        if (
            relation is EvidenceRelation.NEUTRAL
            and metadata.get("claim_source") is not True
            and metadata.get("bridge_metadata_only") is not True
            and claim_norm
            and claim_norm in text_norm
        ):
            relation = EvidenceRelation.SUPPORTS
            signals.append("EXACT_TEXT_MATCH")

        description = str(metadata.get("description") or metadata.get("og:description") or "")
        citation_doi = str(metadata.get("citation_doi") or "").strip()
        combined = f"{claim_text} {description}".casefold()
        if citation_doi and any(pattern in combined for pattern in self._PENDING_DOI_PATTERNS):
            relation = EvidenceRelation.CONTRADICTS
            signals.append("STRUCTURED_METADATA_CONFLICT:DOI_PRESENT_VS_PENDING_PROSE")
            conflicts.append("DOI_PRESENT_VS_PENDING_PROSE")

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

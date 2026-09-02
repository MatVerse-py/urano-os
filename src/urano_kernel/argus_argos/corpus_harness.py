"""Local corpus harness for ARGUS -> ARGOS.

The harness intentionally operates on caller-controlled files and manifests.
It does not upload corpus content and redacts raw claim/evidence text from its
JSON report by default. Binary files can be evidence, but are not treated as
claim text without an explicit extracted-text representation.
"""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping, Sequence
import argparse
import json

from .pipeline import ArgusPipeline, ClaimCandidate, PipelineResult
from .source_intake import SourceDocument


TEXT_REPRESENTATIONS = {
    ".html": "SAVED_HTML",
    ".htm": "SAVED_HTML",
    ".tex": "LATEX_SOURCE",
    ".md": "CORPUS_COPY",
    ".txt": "CORPUS_COPY",
    ".json": "CORPUS_COPY",
    ".jsonl": "CORPUS_COPY",
    ".csv": "CORPUS_COPY",
}

BINARY_REPRESENTATIONS = {
    ".pdf": "SAVED_PDF",
    ".png": "SAVED_IMAGE",
    ".jpg": "SAVED_IMAGE",
    ".jpeg": "SAVED_IMAGE",
    ".webp": "SAVED_IMAGE",
}


def infer_representation(path: Path) -> str:
    suffix = path.suffix.casefold()
    if suffix in TEXT_REPRESENTATIONS:
        return TEXT_REPRESENTATIONS[suffix]
    if suffix in BINARY_REPRESENTATIONS:
        return BINARY_REPRESENTATIONS[suffix]
    return "CORPUS_COPY"


def is_textual_path(path: Path) -> bool:
    return path.suffix.casefold() in TEXT_REPRESENTATIONS


def _read_content(path: Path, representation: str) -> str | bytes:
    if representation in {"SAVED_PDF", "SAVED_IMAGE", "SCREENSHOT", "GENERATED_IMAGE", "DOCUMENT_PAGE_RENDER"}:
        return path.read_bytes()
    return path.read_text(encoding="utf-8", errors="replace")


def load_source(spec: str | Path | Mapping[str, Any]) -> SourceDocument:
    if isinstance(spec, (str, Path)):
        data: dict[str, Any] = {"path": str(spec)}
    else:
        data = dict(spec)

    path_value = str(data.get("path") or "").strip()
    if not path_value:
        raise ValueError("source manifest entry requires path")
    path = Path(path_value)
    if not path.is_file():
        raise FileNotFoundError(path)

    representation = str(data.get("representation") or infer_representation(path)).strip().upper()
    metadata = dict(data.get("metadata") or {})
    if data.get("claim_relation"):
        metadata["claim_relation"] = str(data["claim_relation"])
    if data.get("context_status"):
        metadata["context_status"] = str(data["context_status"])
    if data.get("integrity_status"):
        metadata["integrity_status"] = str(data["integrity_status"])
    if data.get("model_generated") is True:
        metadata["model_generated"] = True
    if data.get("derived_representation") is True:
        metadata["derived_representation"] = True

    return SourceDocument(
        locator=str(data.get("locator") or path.resolve()),
        representation=representation,
        content=_read_content(path, representation),
        metadata=metadata,
        expected_sha256=data.get("expected_sha256"),
        evidence_root_id=data.get("evidence_root_id"),
    )


def redacted_result(result: PipelineResult, *, include_claim_text: bool = False) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "claim_ref": result.claim.claim_ref,
        "claim_sha256": result.finding.content_hash,
        "source_ref": result.claim.source_ref,
        "finding_id": result.finding.finding_id,
        "finding_type": result.finding.finding_type.value,
        "governance_state": result.governance.state.value,
        "governance_reasons": list(result.governance.reasons),
        "authority": result.finding.authority.as_dict(),
        "signals": list(result.finding.signals),
        "conflicts": list(result.finding.conflicts),
        "evidence_root_count": result.evidence_root_count,
        "independent_root_count": result.independent_root_count,
        "support_root_count": result.support_root_count,
        "contradiction_root_count": result.contradiction_root_count,
        "evidence_root_ids": list(result.evidence_root_ids),
    }
    if include_claim_text:
        payload["claim_text"] = result.claim.text
    return payload


class CorpusHarness:
    def __init__(self, pipeline: ArgusPipeline | None = None) -> None:
        self.pipeline = pipeline or ArgusPipeline()

    def analyze_claim(
        self,
        *,
        claim_text: str,
        evidence_specs: Sequence[str | Path | Mapping[str, Any]] = (),
        claim_ref: str | None = None,
        source_ref: str = "corpus-harness://claim",
    ) -> PipelineResult:
        claim_text = claim_text.strip()
        if not claim_text:
            raise ValueError("claim_text is required")
        if claim_ref is None:
            digest = sha256(claim_text.encode("utf-8")).hexdigest()[:24]
            claim_ref = f"claim://corpus-{digest}"
        evidence = tuple(load_source(spec) for spec in evidence_specs)
        return self.pipeline.analyze_claim(
            claim=ClaimCandidate(
                claim_ref=claim_ref,
                text=claim_text,
                source_ref=source_ref,
                ordinal=1,
            ),
            evidence=evidence,
        )

    def analyze_document(
        self,
        document_spec: str | Path | Mapping[str, Any],
        *,
        evidence_specs: Sequence[str | Path | Mapping[str, Any]] = (),
    ) -> tuple[PipelineResult, ...]:
        document = load_source(document_spec)
        path_value = document_spec if isinstance(document_spec, (str, Path)) else document_spec.get("path")
        if path_value is not None and not is_textual_path(Path(str(path_value))):
            raise ValueError("binary document cannot be a claim source without extracted text")
        evidence = tuple(load_source(spec) for spec in evidence_specs)
        return self.pipeline.analyze_document(document, evidence=evidence)

    def run_manifest(self, manifest: Mapping[str, Any]) -> dict[str, Any]:
        data = dict(manifest)
        include_claim_text = bool(data.get("include_claim_text", False))
        evidence_specs = tuple(data.get("evidence") or ())

        if data.get("claim") is not None:
            result = self.analyze_claim(
                claim_text=str(data["claim"]),
                claim_ref=data.get("claim_ref"),
                source_ref=str(data.get("source_ref") or "corpus-harness://claim"),
                evidence_specs=evidence_specs,
            )
            results = (result,)
        elif data.get("document") is not None:
            results = self.analyze_document(data["document"], evidence_specs=evidence_specs)
        else:
            raise ValueError("manifest requires either claim or document")

        return {
            "schema": "matverse.argus-corpus-audit.v1",
            "result_count": len(results),
            "results": [
                redacted_result(result, include_claim_text=include_claim_text)
                for result in results
            ],
        }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run governed ARGUS/ARGOS audit over a local corpus manifest")
    parser.add_argument("manifest", help="Path to JSON manifest")
    parser.add_argument("--output", help="Optional output JSON path")
    args = parser.parse_args(argv)

    manifest_path = Path(args.manifest)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    report = CorpusHarness().run_manifest(manifest)
    encoded = json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2)

    if args.output:
        Path(args.output).write_text(encoded + "\n", encoding="utf-8")
    else:
        print(encoded)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

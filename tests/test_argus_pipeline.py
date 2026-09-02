"""End-to-end tests for the ARGUS -> ARGOS pipeline."""

import hashlib
import unittest

from src.urano_kernel.argus_argos import ArgusFindingType, GovernanceState
from src.urano_kernel.argus_argos.pipeline import ArgusPipeline, ClaimCandidate, PipelinePolicy
from src.urano_kernel.argus_argos.source_intake import SourceDocument


class TestArgusPipeline(unittest.TestCase):
    def setUp(self):
        self.pipeline = ArgusPipeline()

    def claim(self, text="A alegação possui suporte factual independente."):
        return ClaimCandidate(
            claim_ref="claim://case-1",
            text=text,
            source_ref="corpus://case-1",
            ordinal=1,
        )

    def test_exact_independent_source_supports_and_passes(self):
        claim = self.claim()
        evidence = SourceDocument(
            locator="snapshot://source-a",
            representation="SAVED_HTML",
            content=f"<html><body>{claim.text}</body></html>",
        )
        result = self.pipeline.analyze_claim(claim=claim, evidence=(evidence,))
        self.assertEqual(result.finding.finding_type, ArgusFindingType.SUPPORTED)
        self.assertEqual(result.support_root_count, 1)
        self.assertEqual(result.governance.state, GovernanceState.PASS)

    def test_claim_source_does_not_self_support(self):
        document = SourceDocument(
            locator="corpus://primary",
            representation="CORPUS_COPY",
            content="Esta afirmação existe apenas neste documento e ainda não foi verificada.",
        )
        results = self.pipeline.analyze_document(document)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].finding.finding_type, ArgusFindingType.INSUFFICIENT_EVIDENCE)
        self.assertEqual(results[0].support_root_count, 0)
        self.assertEqual(results[0].governance.state, GovernanceState.HOLD)

    def test_duplicate_bytes_count_as_one_evidence_root(self):
        claim = self.claim()
        body = claim.text
        left = SourceDocument(locator="snapshot://a", representation="SAVED_HTML", content=body)
        right = SourceDocument(locator="snapshot://b", representation="SAVED_HTML", content=body)
        result = self.pipeline.analyze_claim(claim=claim, evidence=(left, right))
        self.assertEqual(result.evidence_root_count, 1)
        self.assertEqual(result.independent_root_count, 1)
        self.assertEqual(result.support_root_count, 1)

    def test_derivative_representations_can_share_explicit_root(self):
        claim = self.claim()
        parent = SourceDocument(
            locator="document://paper.pdf",
            representation="SAVED_PDF",
            content=claim.text,
            evidence_root_id="root://paper",
        )
        render = SourceDocument(
            locator="image://paper-page.png",
            representation="DOCUMENT_PAGE_RENDER",
            content=claim.text,
            evidence_root_id="root://paper",
            metadata={"derived_representation": True},
        )
        result = self.pipeline.analyze_claim(claim=claim, evidence=(parent, render))
        self.assertEqual(result.evidence_root_count, 1)
        self.assertEqual(result.independent_root_count, 1)
        self.assertEqual(result.support_root_count, 1)

    def test_generated_image_never_becomes_independent_support(self):
        claim = self.claim()
        evidence = SourceDocument(
            locator="image://generated.png",
            representation="GENERATED_IMAGE",
            content=claim.text,
            metadata={"model_generated": True},
        )
        result = self.pipeline.analyze_claim(claim=claim, evidence=(evidence,))
        self.assertEqual(result.independent_root_count, 0)
        self.assertEqual(result.support_root_count, 0)
        self.assertEqual(result.finding.finding_type, ArgusFindingType.INSUFFICIENT_EVIDENCE)
        self.assertEqual(result.governance.state, GovernanceState.HOLD)

    def test_hash_mismatch_becomes_integrity_conflict(self):
        claim = self.claim()
        evidence = SourceDocument(
            locator="file://artifact.txt",
            representation="REPOSITORY_FILE",
            content=claim.text,
            expected_sha256="0" * 64,
        )
        result = self.pipeline.analyze_claim(claim=claim, evidence=(evidence,))
        self.assertEqual(result.finding.finding_type, ArgusFindingType.INTEGRITY_CONFLICT)
        self.assertIn("HASH_MISMATCH", result.finding.conflicts)
        self.assertEqual(result.governance.state, GovernanceState.HOLD)

    def test_matching_expected_hash_contributes_integrity_authority(self):
        claim = self.claim()
        digest = hashlib.sha256(claim.text.encode("utf-8")).hexdigest()
        evidence = SourceDocument(
            locator="file://artifact.txt",
            representation="REPOSITORY_FILE",
            content=claim.text,
            expected_sha256=digest,
        )
        result = self.pipeline.analyze_claim(claim=claim, evidence=(evidence,))
        self.assertEqual(result.finding.authority.integrity, 100)
        self.assertEqual(result.finding.finding_type, ArgusFindingType.SUPPORTED)

    def test_context_signal_holds_out_of_context(self):
        claim = self.claim("A frase foi apresentada com seu contexto original completo.")
        evidence = SourceDocument(
            locator="snapshot://full-context",
            representation="SAVED_HTML",
            content="Contexto completo preservado para comparação.",
            metadata={"context_status": "OUT_OF_CONTEXT"},
        )
        result = self.pipeline.analyze_claim(claim=claim, evidence=(evidence,))
        self.assertEqual(result.finding.finding_type, ArgusFindingType.OUT_OF_CONTEXT)
        self.assertEqual(result.governance.state, GovernanceState.HOLD)

    def test_saved_html_detects_doi_pending_vs_citation_doi_conflict(self):
        html = """
        <html><head>
          <meta name="description" content="Paper preservado. DOI: Será atribuído após publicação" />
          <meta name="citation_doi" content="10.5281/zenodo.123456" />
        </head><body>Paper preservado.</body></html>
        """
        document = SourceDocument(
            locator="snapshot://zenodo-record",
            representation="SAVED_HTML",
            content=html,
        )
        results = self.pipeline.analyze_document(document)
        conflict_results = [
            result for result in results
            if "DOI_PRESENT_VS_PENDING_PROSE" in result.finding.conflicts
        ]
        self.assertTrue(conflict_results)
        self.assertTrue(all(result.finding.finding_type is ArgusFindingType.CONTRADICTORY for result in conflict_results))
        self.assertTrue(all(result.governance.state is GovernanceState.HOLD for result in conflict_results))

    def test_explicit_adapter_relation_can_support_non_text_source(self):
        claim = self.claim("O registro externo confirma a publicação declarada.")
        evidence = SourceDocument(
            locator="api://record/1",
            representation="API_METADATA",
            content='{"id": 1}',
            metadata={"claim_relation": "SUPPORTS"},
        )
        result = self.pipeline.analyze_claim(claim=claim, evidence=(evidence,))
        self.assertEqual(result.finding.finding_type, ArgusFindingType.SUPPORTED)
        self.assertEqual(result.governance.state, GovernanceState.HOLD)
        # API metadata is strong for publication, but weak for claim-content;
        # the default policy requires content>=50, preventing scalar authority leak.
        self.assertIn("AUTHORITY_BELOW_THRESHOLD:content", result.governance.reasons)

    def test_no_evidence_is_unverified_and_holds(self):
        result = self.pipeline.analyze_claim(claim=self.claim())
        self.assertEqual(result.finding.finding_type, ArgusFindingType.UNVERIFIED)
        self.assertEqual(result.governance.state, GovernanceState.HOLD)

    def test_claim_extractor_skips_questions(self):
        document = SourceDocument(
            locator="corpus://claims",
            representation="CORPUS_COPY",
            content=(
                "Esta é uma afirmação declarativa suficientemente longa.\n"
                "Esta é uma pergunta que deve ser descartada?\n"
                "Outra afirmação declarativa também deve ser preservada."
            ),
        )
        results = self.pipeline.analyze_document(document)
        self.assertEqual(len(results), 2)
        self.assertFalse(any(result.claim.text.endswith("?") for result in results))


if __name__ == "__main__":
    unittest.main()

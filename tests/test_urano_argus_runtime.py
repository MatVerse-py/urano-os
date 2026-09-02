"""Runtime integration tests for ARGUS/ARGOS inside URANO."""

import json
import unittest

from src.urano_kernel.kernel import (
    MAX_ARGUS_CLAIM_CHARS,
    MAX_ARGUS_EVIDENCE_ITEMS,
    MAX_ARGUS_SOURCE_BYTES,
    UranoKernel,
)


class TestUranoArgusRuntime(unittest.TestCase):
    def setUp(self):
        self.kernel = UranoKernel()

    def test_argus_case_runs_end_to_end_and_redacts_runtime_history(self):
        claim = "A alegação foi confirmada por uma fonte independente preservada."
        result = self.kernel.runtime.emit(
            "argus_case",
            {
                "claim": claim,
                "source_ref": "corpus://runtime-test",
                "evidence": [
                    {
                        "locator": "snapshot://independent-source",
                        "representation": "SAVED_HTML",
                        "content": f"<html><body>{claim}</body></html>",
                    }
                ],
            },
        )
        self.assertEqual(result["finding_type"], "SUPPORTED")
        self.assertEqual(result["governance_state"], "PASS")

        history_event = self.kernel.runtime.history[-1]
        self.assertTrue(history_event.payload["redacted"])
        self.assertIn("payload_sha256", history_event.payload)
        self.assertNotIn(claim, json.dumps(history_event.payload))

        self.assertNotIn(claim, json.dumps(self.kernel.evidence.evidence, default=str))
        self.assertNotIn(claim, json.dumps(self.kernel.memory.chain, default=str))

    def test_document_case_detects_internal_html_metadata_conflict(self):
        html = """
        <html><head>
          <meta name="description" content="Paper preservado. DOI: Será atribuído após publicação" />
          <meta name="citation_doi" content="10.5281/zenodo.123456" />
        </head><body>Paper preservado.</body></html>
        """
        report = self.kernel.runtime.emit(
            "argus_document",
            {
                "document": {
                    "locator": "snapshot://zenodo-like-record",
                    "representation": "SAVED_HTML",
                    "content": html,
                }
            },
        )
        self.assertGreater(report["claim_count"], 0)
        conflicts = [
            item for item in report["results"]
            if item["finding_type"] == "CONTRADICTORY"
        ]
        self.assertTrue(conflicts)
        self.assertTrue(all(item["governance_state"] == "HOLD" for item in conflicts))

    def test_missing_claim_blocks_fail_closed(self):
        result = self.kernel.runtime.emit("argus_case", {"evidence": []})
        self.assertEqual(result["governance_state"], "BLOCK")
        self.assertIn("MISSING_CLAIM", result["governance_reasons"])

    def test_malformed_evidence_blocks_fail_closed(self):
        result = self.kernel.runtime.emit(
            "argus_case",
            {"claim": "Alegação válida para teste.", "evidence": ["not-an-object"]},
        )
        self.assertEqual(result["governance_state"], "BLOCK")
        self.assertIn("MALFORMED_EVIDENCE", result["governance_reasons"])

    def test_oversized_claim_blocks_before_pipeline(self):
        result = self.kernel.runtime.emit(
            "argus_case",
            {"claim": "x" * (MAX_ARGUS_CLAIM_CHARS + 1)},
        )
        self.assertEqual(result["governance_state"], "BLOCK")
        self.assertIn("ARGUS_INPUT_LIMIT_EXCEEDED", result["governance_reasons"])

    def test_too_many_evidence_items_blocks(self):
        evidence = [
            {"locator": f"text://{index}", "representation": "CORPUS_COPY", "content": "small"}
            for index in range(MAX_ARGUS_EVIDENCE_ITEMS + 1)
        ]
        result = self.kernel.runtime.emit(
            "argus_case",
            {"claim": "Alegação suficientemente longa para teste.", "evidence": evidence},
        )
        self.assertEqual(result["governance_state"], "BLOCK")
        self.assertIn("ARGUS_INPUT_LIMIT_EXCEEDED", result["governance_reasons"])

    def test_oversized_source_blocks(self):
        result = self.kernel.runtime.emit(
            "argus_case",
            {
                "claim": "Alegação suficientemente longa para teste.",
                "evidence": [
                    {
                        "locator": "text://large",
                        "representation": "CORPUS_COPY",
                        "content": "x" * (MAX_ARGUS_SOURCE_BYTES + 1),
                    }
                ],
            },
        )
        self.assertEqual(result["governance_state"], "BLOCK")
        self.assertIn("MALFORMED_EVIDENCE", result["governance_reasons"])

    def test_binary_document_cannot_be_claim_source_without_extracted_text(self):
        result = self.kernel.runtime.emit(
            "argus_document",
            {
                "document": {
                    "locator": "file://paper.pdf",
                    "representation": "SAVED_PDF",
                    "content": b"%PDF-1.7 binary",
                }
            },
        )
        self.assertEqual(result["governance_state"], "BLOCK")
        self.assertIn("BINARY_DOCUMENT_REQUIRES_EXTRACTED_TEXT", result["governance_reasons"])

    def test_non_json_shaped_source_content_is_rejected(self):
        result = self.kernel.runtime.emit(
            "argus_case",
            {
                "claim": "Alegação suficientemente longa para teste.",
                "evidence": [
                    {
                        "locator": "object://invalid",
                        "representation": "CORPUS_COPY",
                        "content": {"nested": "object"},
                    }
                ],
            },
        )
        self.assertEqual(result["governance_state"], "BLOCK")
        self.assertIn("MALFORMED_EVIDENCE", result["governance_reasons"])

    def test_legacy_event_types_keep_payload_by_default(self):
        payload = "ordinary perception"
        self.kernel.runtime.emit("perception", payload)
        self.assertEqual(self.kernel.runtime.history[-1].payload, payload)


if __name__ == "__main__":
    unittest.main()

"""Tests for the privacy-preserving local corpus harness."""

import json
import tempfile
import unittest
from pathlib import Path

from src.urano_kernel.argus_argos.corpus_harness import CorpusHarness, infer_representation, load_source


class TestCorpusHarness(unittest.TestCase):
    def test_representation_inference_is_conservative(self):
        self.assertEqual(infer_representation(Path("record.html")), "SAVED_HTML")
        self.assertEqual(infer_representation(Path("paper.tex")), "LATEX_SOURCE")
        self.assertEqual(infer_representation(Path("paper.pdf")), "SAVED_PDF")
        self.assertEqual(infer_representation(Path("screen.png")), "SAVED_IMAGE")
        self.assertEqual(infer_representation(Path("notes.txt")), "CORPUS_COPY")

    def test_manifest_report_is_redacted_by_default(self):
        claim = "A afirmação privada foi confirmada por evidência independente."
        with tempfile.TemporaryDirectory() as tmp:
            source_path = Path(tmp) / "source.html"
            source_path.write_text(f"<html><body>{claim}</body></html>", encoding="utf-8")
            report = CorpusHarness().run_manifest(
                {
                    "claim": claim,
                    "evidence": [{"path": str(source_path)}],
                }
            )
        encoded = json.dumps(report, ensure_ascii=False)
        self.assertNotIn(claim, encoded)
        self.assertEqual(report["results"][0]["finding_type"], "SUPPORTED")
        self.assertEqual(report["results"][0]["governance_state"], "PASS")

    def test_manifest_can_explicitly_include_claim_text(self):
        claim = "Texto de teste que pode ser mostrado explicitamente."
        report = CorpusHarness().run_manifest(
            {
                "claim": claim,
                "include_claim_text": True,
                "evidence": [],
            }
        )
        self.assertEqual(report["results"][0]["claim_text"], claim)
        self.assertEqual(report["results"][0]["finding_type"], "UNVERIFIED")

    def test_binary_document_is_not_used_as_claim_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdf = Path(tmp) / "paper.pdf"
            pdf.write_bytes(b"%PDF-1.7\x00binary")
            with self.assertRaises(ValueError):
                CorpusHarness().analyze_document(pdf)

    def test_expected_hash_and_root_id_are_preserved_from_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "artifact.txt"
            path.write_text("artifact", encoding="utf-8")
            source = load_source(
                {
                    "path": str(path),
                    "expected_sha256": "0" * 64,
                    "evidence_root_id": "root://artifact",
                }
            )
        self.assertEqual(source.expected_sha256, "0" * 64)
        self.assertEqual(source.evidence_root_id, "root://artifact")

    def test_manifest_relation_can_be_explicit_without_changing_content(self):
        claim = "O registro confirma o evento declarado."
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp) / "record.json"
            data.write_text('{"record": 1}', encoding="utf-8")
            report = CorpusHarness().run_manifest(
                {
                    "claim": claim,
                    "evidence": [
                        {
                            "path": str(data),
                            "representation": "REPOSITORY_FILE",
                            "claim_relation": "SUPPORTS",
                        }
                    ],
                }
            )
        self.assertEqual(report["results"][0]["finding_type"], "SUPPORTED")
        self.assertEqual(report["results"][0]["governance_state"], "PASS")


if __name__ == "__main__":
    unittest.main()

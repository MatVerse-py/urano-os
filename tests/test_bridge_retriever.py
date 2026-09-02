import hashlib
import json
import unittest

from src.urano_kernel.argus_argos import (
    BATCH_SCHEMA,
    BridgeEvidenceRetriever,
    BridgeProtocolError,
    ClaimCandidate,
    ArgusPipeline,
)
from src.urano_kernel.kernel import UranoKernel


class TestBridgeEvidenceRetriever(unittest.TestCase):
    def transport_for(self, payload, *, expect_full_text=False):
        def transport(url, request_body, headers, timeout):
            query = json.loads(request_body.decode("utf-8"))
            self.assertEqual(query["schema"], "matverse.argus-evidence-query.v1")
            self.assertIn("claim_ref", query)
            self.assertIn("claim_sha256", query)
            self.assertIn("query_terms", query)
            if expect_full_text:
                self.assertIn("claim_text", query)
            else:
                self.assertNotIn("claim_text", query)
            return json.dumps(payload).encode("utf-8")
        return transport

    def test_default_query_does_not_disclose_full_claim(self):
        captured = {}

        def transport(url, request_body, headers, timeout):
            captured.update(json.loads(request_body.decode("utf-8")))
            return json.dumps({"schema": BATCH_SCHEMA, "items": []}).encode("utf-8")

        retriever = BridgeEvidenceRetriever(
            endpoint="https://bridge.invalid/evidence",
            transport=transport,
        )
        claim = "Esta alegação completa não deve atravessar o Bridge por padrão."
        retriever.retrieve(claim_ref="claim://privacy", claim_text=claim)
        self.assertNotIn("claim_text", captured)
        self.assertEqual(
            captured["claim_sha256"],
            hashlib.sha256(" ".join(claim.split()).encode("utf-8")).hexdigest(),
        )
        self.assertTrue(captured["query_terms"])

    def test_terms_mode_redacts_obvious_sensitive_identifiers(self):
        captured = {}

        def transport(url, request_body, headers, timeout):
            captured.update(json.loads(request_body.decode("utf-8")))
            return json.dumps({"schema": BATCH_SCHEMA, "items": []}).encode("utf-8")

        claim = (
            "Confirme o evento para mateus@example.com com UUID "
            "550e8400-e29b-41d4-a716-446655440000 e segredo ghp_abcdefghijklmnopqrstuvwxyz."
        )
        BridgeEvidenceRetriever(
            endpoint="https://bridge.invalid/evidence",
            transport=transport,
        ).retrieve(claim_ref="claim://privacy", claim_text=claim)
        joined = " ".join(captured["query_terms"])
        self.assertNotIn("mateus", joined)
        self.assertNotIn("example.com", joined)
        self.assertNotIn("550e8400", joined)
        self.assertNotIn("ghp_", joined)
        self.assertIn("confirme", joined)

    def test_hash_only_mode_discloses_no_lexical_terms(self):
        captured = {}

        def transport(url, request_body, headers, timeout):
            captured.update(json.loads(request_body.decode("utf-8")))
            return json.dumps({"schema": BATCH_SCHEMA, "items": []}).encode("utf-8")

        BridgeEvidenceRetriever(
            endpoint="https://bridge.invalid/evidence",
            query_disclosure="HASH_ONLY",
            transport=transport,
        ).retrieve(claim_ref="claim://hash-only", claim_text="Texto sensível para busca por hash.")
        self.assertEqual(captured["query_terms"], [])
        self.assertNotIn("claim_text", captured)

    def test_full_text_disclosure_is_explicit(self):
        batch = {"schema": BATCH_SCHEMA, "items": []}
        retriever = BridgeEvidenceRetriever(
            endpoint="https://bridge.invalid/evidence",
            query_disclosure="FULL_TEXT",
            transport=self.transport_for(batch, expect_full_text=True),
        )
        retriever.retrieve(claim_ref="claim://1", claim_text="Full text is explicitly allowed here.")

    def test_maps_bridge_batch_to_source_document(self):
        observed = "O registro possui DOI 10.5281/zenodo.1."
        batch = {
            "schema": BATCH_SCHEMA,
            "evidence_hash": "evidence-1",
            "state": "VERIFIED_SNAPSHOT",
            "evidence_tier": "P4",
            "items": [
                {
                    "locator": "saved://record.html",
                    "representation": "SAVED_HTML",
                    "source_content_hash": "a" * 64,
                    "observed_text": observed,
                    "observed_text_sha256": hashlib.sha256(observed.encode()).hexdigest(),
                    "evidence_root_id": "root-1",
                    "independent": True,
                    "claim_relation": "SUPPORTS",
                    "relation_claim_ref": "claim://1",
                    "metadata": {"citation_doi": "10.5281/zenodo.1"},
                }
            ],
        }
        retriever = BridgeEvidenceRetriever(
            endpoint="https://bridge.invalid/evidence",
            transport=self.transport_for(batch),
        )
        docs = retriever.retrieve(claim_ref="claim://1", claim_text="claim")
        self.assertEqual(len(docs), 1)
        self.assertEqual(docs[0].representation, "SAVED_HTML")
        self.assertEqual(docs[0].evidence_root_id, "root-1")
        self.assertEqual(docs[0].expected_sha256, batch["items"][0]["observed_text_sha256"])
        self.assertEqual(docs[0].metadata["bridge_evidence_state"], "VERIFIED_SNAPSHOT")
        self.assertEqual(docs[0].metadata["claim_relation"], "SUPPORTS")

    def test_unbound_claim_control_is_dropped_even_if_bridge_sends_it(self):
        batch = {
            "schema": BATCH_SCHEMA,
            "items": [
                {
                    "locator": "api://record/1",
                    "representation": "API_METADATA",
                    "source_content_hash": "a" * 64,
                    "evidence_root_id": "root-1",
                    "independent": True,
                    "claim_relation": "SUPPORTS",
                    "metadata": {"claim_relation": "SUPPORTS", "title": "record"},
                }
            ],
        }
        retriever = BridgeEvidenceRetriever(
            endpoint="https://bridge.invalid/evidence",
            transport=self.transport_for(batch),
        )
        doc = retriever.retrieve(claim_ref="claim://1", claim_text="A factual claim for testing.")[0]
        self.assertNotIn("claim_relation", doc.metadata)
        self.assertTrue(doc.metadata["bridge_unbound_claim_control_dropped"])

    def test_metadata_only_does_not_pretend_source_bytes_were_transferred(self):
        batch = {
            "schema": BATCH_SCHEMA,
            "evidence_hash": "evidence-2",
            "state": "PARTIAL",
            "evidence_tier": "P2",
            "items": [
                {
                    "locator": "doi://10.1/example",
                    "representation": "DOI_METADATA",
                    "source_content_hash": "b" * 64,
                    "evidence_root_id": "root-doi",
                    "independent": True,
                    "metadata": {"citation_doi": "10.1/example"},
                }
            ],
        }
        retriever = BridgeEvidenceRetriever(
            endpoint="https://bridge.invalid/evidence",
            transport=self.transport_for(batch),
        )
        doc = retriever.retrieve(claim_ref="claim://1", claim_text="claim")[0]
        self.assertIsNone(doc.expected_sha256)
        self.assertTrue(doc.metadata["bridge_metadata_only"])
        self.assertEqual(doc.metadata["bridge_source_content_hash"], "b" * 64)

    def test_metadata_only_json_cannot_become_exact_text_support(self):
        claim = "The official record states this exact sentence."
        batch = {
            "schema": BATCH_SCHEMA,
            "evidence_hash": "evidence-meta",
            "state": "PARTIAL",
            "evidence_tier": "P2",
            "items": [
                {
                    "locator": "saved://metadata-only.html",
                    "representation": "SAVED_HTML",
                    "source_content_hash": "d" * 64,
                    "evidence_root_id": "root-meta",
                    "independent": True,
                    "metadata": {"title": claim},
                }
            ],
        }
        retriever = BridgeEvidenceRetriever(
            endpoint="https://bridge.invalid/evidence",
            transport=self.transport_for(batch),
        )
        result = ArgusPipeline(retriever=retriever).analyze_claim(
            claim=ClaimCandidate("claim://meta", claim, "runtime://test", 1)
        )
        self.assertEqual(result.finding.finding_type.value, "INSUFFICIENT_EVIDENCE")
        self.assertEqual(result.support_root_count, 0)
        self.assertEqual(result.governance.state.value, "HOLD")

    def test_rejects_unknown_schema(self):
        retriever = BridgeEvidenceRetriever(
            endpoint="https://bridge.invalid/evidence",
            transport=self.transport_for({"schema": "wrong", "items": []}),
        )
        with self.assertRaises(BridgeProtocolError):
            retriever.retrieve(claim_ref="claim://1", claim_text="claim")

    def test_rejects_invalid_endpoint_and_oversized_response(self):
        with self.assertRaises(BridgeProtocolError):
            BridgeEvidenceRetriever(endpoint="file:///tmp/evidence")

        retriever = BridgeEvidenceRetriever(
            endpoint="https://bridge.invalid/evidence",
            max_response_bytes=1024,
            transport=lambda *_: b"x" * 1025,
        )
        with self.assertRaises(BridgeProtocolError):
            retriever.retrieve(claim_ref="claim://1", claim_text="claim")

    def test_pipeline_uses_bound_bridge_relation_without_bypassing_authority_policy(self):
        batch = {
            "schema": BATCH_SCHEMA,
            "evidence_hash": "evidence-3",
            "state": "VERIFIED",
            "evidence_tier": "P4",
            "items": [
                {
                    "locator": "bridge://source",
                    "representation": "API_METADATA",
                    "source_content_hash": "c" * 64,
                    "evidence_root_id": "root-api",
                    "independent": True,
                    "claim_relation": "SUPPORTS",
                    "relation_claim_ref": "claim://1",
                    "metadata": {"title": "official record"},
                }
            ],
        }
        retriever = BridgeEvidenceRetriever(
            endpoint="https://bridge.invalid/evidence",
            transport=self.transport_for(batch),
        )
        result = ArgusPipeline(retriever=retriever).analyze_claim(
            claim=ClaimCandidate("claim://1", "A sufficiently long factual claim.", "runtime://test", 1)
        )
        self.assertEqual(result.finding.finding_type.value, "SUPPORTED")
        self.assertEqual(result.governance.state.value, "HOLD")
        self.assertIn("AUTHORITY_BELOW_THRESHOLD:content", result.governance.reasons)

    def test_urano_holds_when_bridge_unavailable(self):
        def failing_transport(url, request_body, headers, timeout):
            raise OSError("offline")

        retriever = BridgeEvidenceRetriever(
            endpoint="https://bridge.invalid/evidence",
            transport=failing_transport,
        )
        kernel = UranoKernel(argus_retriever=retriever)
        result = kernel.runtime.emit(
            "argus_case",
            {"claim": "Esta alegação tem tamanho suficiente para análise."},
        )
        self.assertEqual(result["governance_state"], "HOLD")
        self.assertIn("BRIDGE_RETRIEVAL_UNAVAILABLE", result["governance_reasons"])


if __name__ == "__main__":
    unittest.main()

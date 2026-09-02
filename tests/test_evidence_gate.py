"""Testes da fronteira de evidência (evidence_gate) e sua integração."""
import unittest

from src.urano_kernel.evidence_gate import Claim, EvidenceClass, density, judge
from src.urano_kernel.evidence_pack import EvidencePack


class TestEvidenceGate(unittest.TestCase):
    def test_blocks_when_no_claims(self):
        verdict = judge([])
        self.assertFalse(verdict.passed)
        self.assertEqual(verdict.failed_gate, "CanExist")

    def test_blocks_when_no_anchoring_evidence(self):
        claims = [Claim("mercado bilionário", EvidenceClass.INFERRED)]
        verdict = judge(claims)
        self.assertFalse(verdict.passed)
        self.assertEqual(verdict.failed_gate, "CanExist")

    def test_blocks_unverified_even_when_anchored(self):
        claims = [
            Claim("trecho citado", EvidenceClass.OBSERVED_TEXT),
            Claim("alegação solta", EvidenceClass.UNVERIFIED),
        ]
        verdict = judge(claims)
        self.assertFalse(verdict.passed)
        self.assertEqual(verdict.failed_gate, "CanPublish")

    def test_blocks_inferred_claim_from_publish_even_when_bundle_is_anchored(self):
        claims = [
            Claim("trecho citado", EvidenceClass.OBSERVED_TEXT),
            Claim("interpretação ainda não verificada", EvidenceClass.INFERRED),
        ]
        verdict = judge(claims)
        self.assertFalse(verdict.passed)
        self.assertEqual(verdict.failed_gate, "CanPublish")

    def test_passes_with_anchored_and_verifiable_claims(self):
        claims = [
            Claim("trecho citado", EvidenceClass.OBSERVED_TEXT),
            Claim("resultado do cálculo", EvidenceClass.COMPUTED),
        ]
        verdict = judge(claims)
        self.assertTrue(verdict.passed)
        self.assertIsNone(verdict.failed_gate)

    def test_density_counts_only_verifiable_classes(self):
        claims = [
            Claim("a", EvidenceClass.OBSERVED_TEXT),
            Claim("b", EvidenceClass.INFERRED),
        ]
        self.assertEqual(density(claims), 0.5)

    def test_density_is_zero_for_empty_claims(self):
        self.assertEqual(density([]), 0.0)


class TestEvidencePackGate(unittest.TestCase):
    def test_seal_blocks_unverified_evidence_when_required(self):
        pack = EvidencePack("session-1")
        pack.add("source_a", {"x": 1})  # classe padrão: UNVERIFIED
        with self.assertRaises(ValueError):
            pack.seal(require_publishable=True)

    def test_seal_blocks_inferred_evidence_when_required(self):
        pack = EvidencePack("session-1")
        pack.add("source_a", {"x": 1}, EvidenceClass.INFERRED)
        self.assertFalse(pack.can_publish())
        with self.assertRaises(ValueError):
            pack.seal(require_publishable=True)

    def test_seal_allows_classified_evidence_when_required(self):
        pack = EvidencePack("session-1")
        pack.add("source_a", {"x": 1}, EvidenceClass.OBSERVED_TEXT)
        self.assertTrue(pack.can_publish())
        self.assertEqual(len(pack.seal(require_publishable=True)), 64)

    def test_seal_without_requirement_ignores_classification(self):
        pack = EvidencePack("session-1")
        pack.add("source_a", {"x": 1})
        self.assertEqual(len(pack.seal()), 64)


if __name__ == "__main__":
    unittest.main()

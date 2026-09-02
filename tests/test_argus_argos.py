"""Tests for canonical ARGUS and ARGOS role separation."""

import unittest

from src.urano_kernel.argus_argos import (
    Argos,
    ArgosPolicy,
    Argus,
    ArgusFindingType,
    GovernanceEnvelope,
    GovernanceState,
    PredicateAuthority,
)


class TestArgus(unittest.TestCase):
    def setUp(self):
        self.argus = Argus()

    def test_finding_is_deterministic_for_same_evidence(self):
        authority = PredicateAuthority(content=80, integrity=70)
        left = self.argus.inspect(
            claim_ref="claim://1",
            source_ref="repo://example/a",
            representation="REPOSITORY_FILE",
            content={"x": 1, "y": 2},
            finding_type=ArgusFindingType.CONTRADICTORY,
            authority=authority,
            signals=("source-a disagrees with source-b",),
        )
        right = self.argus.inspect(
            claim_ref="claim://1",
            source_ref="repo://example/a",
            representation="REPOSITORY_FILE",
            content={"y": 2, "x": 1},
            finding_type=ArgusFindingType.CONTRADICTORY,
            authority=authority,
            signals=("source-a disagrees with source-b",),
        )
        self.assertEqual(left.content_hash, right.content_hash)
        self.assertEqual(left.finding_id, right.finding_id)

    def test_requires_claim_source_and_representation(self):
        authority = PredicateAuthority()
        for kwargs in (
            {"claim_ref": "", "source_ref": "x", "representation": "SAVED_HTML"},
            {"claim_ref": "c", "source_ref": "", "representation": "SAVED_HTML"},
            {"claim_ref": "c", "source_ref": "x", "representation": ""},
        ):
            with self.assertRaises(ValueError):
                self.argus.inspect(
                    **kwargs,
                    content="x",
                    finding_type=ArgusFindingType.UNVERIFIED,
                    authority=authority,
                )

    def test_suspicious_label_requires_evidence_signal(self):
        with self.assertRaises(ValueError):
            self.argus.inspect(
                claim_ref="claim://1",
                source_ref="image://1",
                representation="SAVED_IMAGE",
                content=b"pixels",
                finding_type=ArgusFindingType.MANIPULATION_SUSPECTED,
                authority=PredicateAuthority(content=50),
            )

    def test_unverified_can_exist_without_detector_signal(self):
        finding = self.argus.inspect(
            claim_ref="claim://1",
            source_ref="text://1",
            representation="OBSERVED_TEXT",
            content="claim",
            finding_type=ArgusFindingType.UNVERIFIED,
            authority=PredicateAuthority(content=30),
        )
        self.assertEqual(finding.finding_type, ArgusFindingType.UNVERIFIED)

    def test_argus_finding_converts_to_argos_envelope(self):
        finding = self.argus.inspect(
            claim_ref="claim://1",
            source_ref="text://1",
            representation="OBSERVED_TEXT",
            content="claim",
            finding_type=ArgusFindingType.OUT_OF_CONTEXT,
            authority=PredicateAuthority(content=80, integrity=70),
            signals=("source context changes the claim meaning",),
        )
        envelope = finding.governance_envelope()
        self.assertEqual(envelope.producer, "ARGUS")
        self.assertEqual(envelope.subject_ref, "claim://1")
        self.assertEqual(envelope.metadata["finding_type"], "OUT_OF_CONTEXT")


class TestArgos(unittest.TestCase):
    def setUp(self):
        self.argos = Argos()

    def envelope(self, *, producer="ARGUS", authority=None, conflicts=()):
        return GovernanceEnvelope(
            record_id="record-1",
            producer=producer,
            subject_ref="subject://1",
            authority=authority or PredicateAuthority(content=80, integrity=90),
            conflicts=conflicts,
        )

    def test_passes_when_policy_is_satisfied(self):
        verdict = self.argos.adjudicate(
            self.envelope(),
            ArgosPolicy(required_authority={"content": 70, "integrity": 80}),
        )
        self.assertEqual(verdict.state, GovernanceState.PASS)

    def test_holds_below_authority_threshold(self):
        verdict = self.argos.adjudicate(
            self.envelope(authority=PredicateAuthority(content=40)),
            ArgosPolicy(required_authority={"content": 70}),
        )
        self.assertEqual(verdict.state, GovernanceState.HOLD)
        self.assertIn("AUTHORITY_BELOW_THRESHOLD:content", verdict.reasons)

    def test_holds_unresolved_conflict_by_default(self):
        verdict = self.argos.adjudicate(self.envelope(conflicts=("DOI_CONFLICT",)))
        self.assertEqual(verdict.state, GovernanceState.HOLD)
        self.assertIn("UNRESOLVED_CONFLICT", verdict.reasons)

    def test_can_block_conflict_under_strict_policy(self):
        verdict = self.argos.adjudicate(
            self.envelope(conflicts=("DOI_CONFLICT",)),
            ArgosPolicy(block_on_conflict=True),
        )
        self.assertEqual(verdict.state, GovernanceState.BLOCK)

    def test_argos_is_not_structurally_coupled_to_argus(self):
        verdict = self.argos.adjudicate(
            self.envelope(producer="MANDELA"),
            ArgosPolicy(allowed_producers=("ARGUS", "MANDELA", "CARTOMANCIA")),
        )
        self.assertEqual(verdict.state, GovernanceState.PASS)

    def test_disallowed_producer_holds(self):
        verdict = self.argos.adjudicate(
            self.envelope(producer="UNKNOWN_TOOL"),
            ArgosPolicy(allowed_producers=("ARGUS", "MANDELA")),
        )
        self.assertEqual(verdict.state, GovernanceState.HOLD)
        self.assertIn("PRODUCER_NOT_ALLOWED:UNKNOWN_TOOL", verdict.reasons)

    def test_unknown_authority_domain_holds(self):
        verdict = self.argos.adjudicate(
            self.envelope(),
            ArgosPolicy(required_authority={"truth": 90}),
        )
        self.assertEqual(verdict.state, GovernanceState.HOLD)
        self.assertIn("UNKNOWN_AUTHORITY_DOMAIN:truth", verdict.reasons)


if __name__ == "__main__":
    unittest.main()

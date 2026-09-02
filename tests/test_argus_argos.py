"""Tests for the ARGUS–ARGOS epistemic subsystem."""

import unittest

from src.urano_kernel.argus_argos import (
    AdjudicationState,
    Argos,
    ArgosPolicy,
    Argus,
    PredicateAuthority,
)


class TestArgus(unittest.TestCase):
    def setUp(self):
        self.argus = Argus()

    def test_observation_is_deterministic_for_same_content(self):
        authority = PredicateAuthority(content=80, integrity=70)
        left = self.argus.observe(
            source_ref="repo://example/a",
            representation="REPOSITORY_FILE",
            content={"x": 1, "y": 2},
            authority=authority,
        )
        right = self.argus.observe(
            source_ref="repo://example/a",
            representation="REPOSITORY_FILE",
            content={"y": 2, "x": 1},
            authority=authority,
        )
        self.assertEqual(left.content_hash, right.content_hash)
        self.assertEqual(left.observation_id, right.observation_id)

    def test_requires_source_and_representation(self):
        authority = PredicateAuthority()
        with self.assertRaises(ValueError):
            self.argus.observe(source_ref="", representation="SAVED_HTML", content="x", authority=authority)
        with self.assertRaises(ValueError):
            self.argus.observe(source_ref="x", representation="", content="x", authority=authority)

    def test_authority_values_are_bounded(self):
        with self.assertRaises(ValueError):
            self.argus.observe(
                source_ref="x",
                representation="SAVED_HTML",
                content="x",
                authority=PredicateAuthority(content=101),
            )


class TestArgos(unittest.TestCase):
    def setUp(self):
        self.argus = Argus()
        self.argos = Argos()

    def observation(self, *, authority=None, conflicts=()):
        return self.argus.observe(
            source_ref="snapshot://artifact-1",
            representation="SAVED_HTML",
            content="payload",
            authority=authority or PredicateAuthority(content=80, integrity=90),
            conflicts=conflicts,
        )

    def test_passes_when_policy_is_satisfied(self):
        obs = self.observation()
        verdict = self.argos.adjudicate(
            obs,
            ArgosPolicy(required_authority={"content": 70, "integrity": 80}),
        )
        self.assertEqual(verdict.state, AdjudicationState.PASS)

    def test_holds_below_authority_threshold(self):
        obs = self.observation(authority=PredicateAuthority(content=40))
        verdict = self.argos.adjudicate(obs, ArgosPolicy(required_authority={"content": 70}))
        self.assertEqual(verdict.state, AdjudicationState.HOLD)
        self.assertIn("AUTHORITY_BELOW_THRESHOLD:content", verdict.reasons)

    def test_holds_unresolved_conflict_by_default(self):
        obs = self.observation(conflicts=("DOI_CONFLICT",))
        verdict = self.argos.adjudicate(obs)
        self.assertEqual(verdict.state, AdjudicationState.HOLD)
        self.assertIn("UNRESOLVED_CONFLICT", verdict.reasons)

    def test_can_block_conflict_under_strict_policy(self):
        obs = self.observation(conflicts=("DOI_CONFLICT",))
        verdict = self.argos.adjudicate(obs, ArgosPolicy(block_on_conflict=True))
        self.assertEqual(verdict.state, AdjudicationState.BLOCK)

    def test_unknown_authority_domain_holds(self):
        obs = self.observation()
        verdict = self.argos.adjudicate(obs, ArgosPolicy(required_authority={"truth": 90}))
        self.assertEqual(verdict.state, AdjudicationState.HOLD)
        self.assertIn("UNKNOWN_AUTHORITY_DOMAIN:truth", verdict.reasons)


if __name__ == "__main__":
    unittest.main()

import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('prancha_demo', ROOT / 'tools/prancha_demo.py')
demo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(demo)


class DemoBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.scene = demo.read_json(ROOT / 'docs/examples/prancha-scene-demo.v1.json')

    def reject(self, path, value):
        data = copy.deepcopy(self.scene)
        target = data
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = value
        with self.assertRaises(demo.InvalidDemo):
            demo.validate_scene(data)

    def test_repository_example_is_demo_only(self):
        demo.validate_scene(self.scene)

    def test_execution_and_fake_approvals_are_rejected(self):
        for path, value in [(['authority', 'may_execute'], True),
                            (['authority', 'gate_decision_ref'], 'APPROVED'),
                            (['authority', 'release_receipt_ref'], 'receipt-1'),
                            (['provenance', 'review_status'], 'PASS'),
                            (['status'], 'PRODUCTION')]:
            with self.subTest(path=path):
                self.reject(path, value)

    def test_boolean_fields_do_not_accept_numbers_or_strings(self):
        for value in [0, 1, 'false', None]:
            with self.subTest(value=value):
                self.reject(['authority', 'may_execute'], value)

    def test_real_data_sources_and_evidence_are_rejected(self):
        for path, value in [(['source_ref'], 'https://example.invalid/real'),
                            (['source_ref'], 'urn:matverse:case:symbiopet:real-lua'),
                            (['provenance', 'synthetic_data'], False),
                            (['claims', 0, 'evidence_refs'], ['sha256:fake']),
                            (['narration', 'asset_ref'], 'https://example.invalid/a.mp3')]:
            with self.subTest(path=path):
                self.reject(path, value)

    def test_unknown_states_and_versions_are_rejected(self):
        for path, value in [(['claims', 0, 'status'], 'FATO'),
                            (['claims', 0, 'status'], 'APPROVED'),
                            (['version'], '1.0.0'),
                            (['schema'], 'matverse.prancha.scene.v1')]:
            with self.subTest(path=path):
                self.reject(path, value)

    def test_hypothesis_hold_demo_are_distinct_accepted_states(self):
        for state in ['HYPOTHESIS', 'HOLD', 'DEMO']:
            with self.subTest(state=state):
                self.scene['claims'][0]['status'] = state
                demo.validate_scene(self.scene)

    def test_unknown_nested_fields_and_missing_authority_are_rejected(self):
        self.reject(['authority', 'release_receipt'], None)
        self.reject(['claims', 0, 'approved'], True)
        del self.scene['authority']
        with self.assertRaises(demo.InvalidDemo):
            demo.validate_scene(self.scene)

    def test_duplicate_claims_and_excessive_strings_are_rejected(self):
        self.reject(['claims'], [self.scene['claims'][0]] * 2)
        self.reject(['narration', 'transcript'], 'x' * 4097)
        self.reject(['claims'], [self.scene['claims'][0]] * 17)

    def test_duplicate_json_keys_nonfinite_values_and_oversize_fail(self):
        payloads = [b'{"status":"DEMO_ONLY","status":"PRODUCTION"}',
                    b'{"number":NaN}', b'{"number":Infinity}', b'\xff',
                    b' ' * (demo.MAX_BYTES + 1), b'[' * 2000 + b']' * 2000]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'scene.json'
            for payload in payloads:
                with self.subTest(size=len(payload)):
                    path.write_bytes(payload)
                    with self.assertRaises(demo.InvalidDemo):
                        demo.read_json(path)

    def test_unsupported_schema_rules_fail_closed(self):
        schema = demo.read_json(demo.SCHEMA)
        schema['$ref'] = 'https://example.invalid/remote-schema'
        with self.assertRaises(demo.InvalidDemo):
            demo.validate_scene(self.scene, schema)


if __name__ == '__main__':
    unittest.main()

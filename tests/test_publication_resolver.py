from __future__ import annotations

import unittest
from unittest.mock import patch

from src.urano_kernel.publication_resolver import extract_doi, resolve_publication


class PublicationResolverTests(unittest.TestCase):
    def test_extracts_doi_from_plain_doi(self):
        self.assertEqual(extract_doi("10.1038/s41586-026-12345-6"), "10.1038/s41586-026-12345-6")

    def test_extracts_doi_from_url(self):
        self.assertEqual(
            extract_doi("https://doi.org/10.1103/PhysRevLett.130.123456"),
            "10.1103/physrevlett.130.123456",
        )

    def test_rejects_non_doi_input_without_fetching_arbitrary_url(self):
        result = resolve_publication("http://127.0.0.1:8080/private")
        self.assertFalse(result["ok"])
        self.assertEqual(result["access_state"], "IDENTIFIER_REQUIRED")

    @patch("src.urano_kernel.publication_resolver._unpaywall", return_value={})
    @patch("src.urano_kernel.publication_resolver._openalex")
    @patch("src.urano_kernel.publication_resolver._crossref")
    def test_open_access_location_is_preferred(self, crossref, openalex, _unpaywall):
        crossref.return_value = {
            "title": ["A governed scientific object"],
            "container-title": ["Example Journal"],
            "publisher": "Example Publisher",
            "author": [{"given": "Ada", "family": "Lovelace"}],
            "type": "journal-article",
        }
        openalex.return_value = {
            "id": "https://openalex.org/W1",
            "title": "A governed scientific object",
            "locations": [
                {
                    "is_oa": True,
                    "version": "publishedVersion",
                    "license": "cc-by",
                    "pdf_url": "https://repository.example/paper.pdf",
                    "landing_page_url": "https://repository.example/paper",
                    "source": {"display_name": "Example Repository"},
                }
            ],
        }

        result = resolve_publication("10.1234/example.1")
        self.assertTrue(result["ok"])
        self.assertEqual(result["access_state"], "OPEN_ACCESS_FOUND")
        self.assertTrue(result["metadata"]["is_open_access"])
        self.assertEqual(result["access_locations"][0]["kind"], "pdf")
        self.assertEqual(result["analysis_handoffs"][0]["id"], "consensus")
        self.assertFalse(result["policy"]["bypass_paywall"])

    @patch("src.urano_kernel.publication_resolver._unpaywall", return_value={})
    @patch("src.urano_kernel.publication_resolver._openalex", return_value={})
    @patch("src.urano_kernel.publication_resolver._crossref")
    def test_metadata_only_does_not_claim_open_access(self, crossref, _openalex, _unpaywall):
        crossref.return_value = {"title": ["Restricted paper"], "type": "journal-article"}
        result = resolve_publication("10.1234/restricted.1")
        self.assertTrue(result["ok"])
        self.assertEqual(result["access_state"], "METADATA_ONLY_OR_RESTRICTED")
        self.assertFalse(result["metadata"]["is_open_access"])
        self.assertEqual(result["access_locations"], [])


if __name__ == "__main__":
    unittest.main()

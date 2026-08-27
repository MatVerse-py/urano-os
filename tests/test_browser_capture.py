import unittest

from src.urano_kernel.browser_capture import BrowserCaptureStore, MAX_TEXT_CHARS


class BrowserCaptureStoreTests(unittest.TestCase):
    def test_requires_url(self):
        store = BrowserCaptureStore()
        with self.assertRaises(ValueError):
            store.add({"title": "missing url"})

    def test_truncates_text_and_hashes_content(self):
        store = BrowserCaptureStore()
        capture = store.add({
            "url": "https://example.org/paper",
            "title": "Paper",
            "doi": "10.1234/example",
            "text": "x" * (MAX_TEXT_CHARS + 1000),
            "selected_text": "selection",
            "metadata": {"journal": "Journal", "cookie": "must-not-pass"},
        })
        self.assertEqual(len(capture.text), MAX_TEXT_CHARS)
        self.assertEqual(len(capture.content_sha256), 64)
        self.assertNotIn("cookie", capture.metadata)
        self.assertEqual(capture.auth_boundary, "browser_session_not_exported")

    def test_store_is_bounded(self):
        store = BrowserCaptureStore(max_captures=2)
        for idx in range(3):
            store.add({"url": f"https://example.org/{idx}", "text": str(idx)})
        items = store.list()
        self.assertEqual(len(items), 2)
        self.assertTrue(items[0]["url"].endswith("/2"))
        self.assertTrue(items[1]["url"].endswith("/1"))

    def test_full_capture_can_be_retrieved_by_id(self):
        store = BrowserCaptureStore()
        capture = store.add({
            "url": "https://example.org/article",
            "text": "authenticated visible text",
        })
        restored = store.get(capture.capture_id)
        self.assertIsNotNone(restored)
        self.assertEqual(restored["text"], "authenticated visible text")


if __name__ == "__main__":
    unittest.main()

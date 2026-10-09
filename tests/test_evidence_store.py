import os
import tempfile
import unittest

import evidence_store


class TestEvidenceStore(unittest.TestCase):
    def test_roundtrip_and_tamper(self):
        with tempfile.TemporaryDirectory() as d:
            store = evidence_store.EvidenceStore(d)
            digest = store.save("t", [{"a": 1}, {"a": 2}], url="https://example/x", note="n")
            self.assertRegex(digest, r"^[0-9a-f]{64}$")
            self.assertTrue(os.path.exists(os.path.join(d, "t.json")))
            self.assertTrue(evidence_store.verify(d))
            with open(os.path.join(d, "t.json"), "a", encoding="utf-8") as fh:
                fh.write(" ")
            self.assertFalse(evidence_store.verify(d))

    def test_history_accumulates(self):
        with tempfile.TemporaryDirectory() as d:
            store = evidence_store.EvidenceStore(d)
            store.save("t", [{"a": 1}])
            store.save("t", [{"a": 2}])
            reloaded = evidence_store.EvidenceStore(d)
            self.assertEqual(len(reloaded.manifest["tables"]["t"]["history"]), 2)

    def test_sanitize_redacts_blob(self):
        blob = "data:image/jpeg;base64," + "A" * 5000
        out = evidence_store.sanitize({"img": blob}, blob_threshold=100)
        self.assertIsInstance(out["img"], dict)
        self.assertEqual(out["img"]["_redacted"], "base64-blob")
        self.assertEqual(out["img"]["bytes"], 5000)

    def test_sanitize_leaves_small_strings(self):
        self.assertEqual(evidence_store.sanitize({"x": "short"}), {"x": "short"})


if __name__ == "__main__":
    unittest.main()

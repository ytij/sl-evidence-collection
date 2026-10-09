import re
import unittest

from tests.common import EVIDENCE, exists, load_json, path, sha256_file

EXPECTED_TABLES = {
    "comments", "user_profiles", "video_submissions", "video_meta",
    "bunny_catalog", "site_config", "poll_votes",
}
RLS_TABLES = {"favorites", "watch_history", "video_reports", "model_requests", "title_suggestions"}


class TestEvidenceManifest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = load_json("evidence/manifest.json")

    def test_manifest_shape(self):
        self.assertIn("tables", self.manifest)
        self.assertGreaterEqual(len(self.manifest["tables"]), 12)

    def test_expected_tables_present(self):
        self.assertTrue(EXPECTED_TABLES.issubset(set(self.manifest["tables"])))

    def test_every_hash_matches(self):
        for name, entry in self.manifest["tables"].items():
            latest = entry["latest"]
            rel = f"evidence/{latest['file']}"
            self.assertTrue(exists(rel), f"missing evidence file {rel}")
            actual = sha256_file(path(rel))
            self.assertEqual(actual, latest["sha256"], f"hash mismatch for {name}")

    def test_row_count_matches_payload(self):
        for name, entry in self.manifest["tables"].items():
            payload = load_json(f"evidence/{entry['latest']['file']}")
            self.assertEqual(payload["row_count"], len(payload["rows"]),
                             f"row_count != len(rows) for {name}")
            self.assertEqual(payload["row_count"], entry["latest"]["row_count"])

    def test_payload_provenance(self):
        for name, entry in self.manifest["tables"].items():
            payload = load_json(f"evidence/{entry['latest']['file']}")
            for key in ("name", "fetched_at", "source_url", "row_count", "rows"):
                self.assertIn(key, payload, f"{name} missing {key}")
            self.assertRegex(payload["fetched_at"], r"^\d{4}-\d{2}-\d{2}T")

    def test_rls_tables_are_empty(self):
        for name in RLS_TABLES:
            self.assertIn(name, self.manifest["tables"])
            self.assertEqual(self.manifest["tables"][name]["latest"]["row_count"], 0,
                             f"{name} unexpectedly has rows")

    def test_history_is_append_only(self):
        for name, entry in self.manifest["tables"].items():
            self.assertIn("history", entry)
            self.assertGreaterEqual(len(entry["history"]), 1)
            self.assertEqual(entry["history"][-1]["sha256"], entry["latest"]["sha256"])

    def test_timestamp_index(self):
        index = load_json("evidence/timestamps/index.json")
        self.assertGreaterEqual(len(index), 2)
        for rec in index:
            self.assertRegex(rec["sha256"], r"^[0-9a-f]{64}$")
            self.assertIn("tsa", rec)
            self.assertTrue(exists(rec["tsr"]), f"missing token {rec['tsr']}")


if __name__ == "__main__":
    unittest.main()

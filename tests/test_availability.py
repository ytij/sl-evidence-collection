import json
import unittest

from tests.common import exists, load_json, path


class TestAvailabilitySnapshot(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index = load_json("evidence/availability/index.json")
        cls.latest = cls.index[-1]
        cls.snapshot = load_json(cls.latest["dir"] + "/snapshot.json")

    def test_index_and_snapshot_exist(self):
        self.assertGreaterEqual(len(self.index), 1)
        self.assertTrue(exists(self.latest["dir"] + "/snapshot.json"))
        self.assertTrue(exists(self.latest["dir"] + "/snapshot.csv"))

    def test_summary_is_consistent(self):
        works = self.snapshot["works"]
        s = self.snapshot["summary"]
        self.assertEqual(s["now_live"], sum(1 for w in works if w["now_live"]))
        self.assertEqual(s["still_live"], sum(1 for w in works if w["delta"] == "STILL_LIVE"))
        self.assertEqual(s["taken_down_since"],
                         sum(1 for w in works if w["delta"] == "TAKEN_DOWN_SINCE"))
        self.assertEqual(s["now_live"], s["still_live"] + s["newly_live"])

    def test_status_types_normalized(self):
        # Regression guard for the int/str bug: any status of 200 must count as live.
        for w in self.snapshot["works"]:
            if str(w["now_status"]) == "200":
                self.assertTrue(w["now_live"], w["guid"])

    def test_index_hash_matches_snapshot(self):
        import hashlib
        p = path(self.latest["dir"] + "/snapshot.json")
        h = hashlib.sha256(open(p, "rb").read()).hexdigest()
        self.assertEqual(h, self.latest["snapshot_json_sha256"])


if __name__ == "__main__":
    unittest.main()

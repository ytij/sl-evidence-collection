import unittest

from tests.common import load_json


class TestDamages(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = load_json("damages/damages.json")
        cls.works = cls.d["works"]

    def test_work_count(self):
        self.assertEqual(self.d["attributed_works"], len(self.works))
        self.assertGreater(self.d["attributed_works"], 0)

    def test_totals_are_consistent(self):
        self.assertEqual(self.d["total_bytes"], sum(w["file_size_bytes"] for w in self.works))
        self.assertEqual(self.d["total_views"], sum(w["views"] for w in self.works))
        self.assertEqual(self.d["total_duration_seconds"], sum(w["duration_seconds"] for w in self.works))

    def test_statutory_constants(self):
        sd = self.d["statutory_damages_usd"]
        n = self.d["attributed_works"]
        self.assertEqual(sd["per_work_min"], 750)
        self.assertEqual(sd["per_work_max"], 30000)
        self.assertEqual(sd["per_work_willful_max"], 150000)
        self.assertEqual(sd["aggregate_min"], 750 * n)
        self.assertEqual(sd["aggregate_max"], 30000 * n)
        self.assertEqual(sd["aggregate_willful_max"], 150000 * n)

    def test_each_work_has_provenance(self):
        for w in self.works:
            self.assertRegex(w["guid"], r"^[0-9a-f-]{36}$")
            self.assertTrue(w["submitted_at"])


if __name__ == "__main__":
    unittest.main()

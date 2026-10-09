import csv
import unittest

import notion_export
from tests.common import exists, path

CSV = "notion/abdlhub_stolen_videos.csv"


class TestNotionExport(unittest.TestCase):
    def test_files_exist(self):
        self.assertTrue(exists(CSV))
        self.assertTrue(exists("notion/NOTION_SCHEMA.md"))
        self.assertTrue(exists("manual/abdlhub_stolen_videos_manual_all.csv"))

    def test_header_matches_schema(self):
        with open(path(CSV), encoding="utf-8") as fh:
            header = next(csv.reader(fh))
        self.assertEqual(header, notion_export.COLUMNS)

    def test_row_counts_by_source(self):
        rows = list(csv.DictReader(open(path(CSV), encoding="utf-8")))
        counts = {}
        for r in rows:
            counts[r["Record Source"]] = counts.get(r["Record Source"], 0) + 1
        self.assertEqual(counts.get("Automated"), 624)
        self.assertEqual(counts.get("Manual-JFF"), 74)

    def test_manual_rows_have_jff_ids(self):
        import re
        rows = list(csv.DictReader(open(path(CSV), encoding="utf-8")))
        manual = [r for r in rows if r["Record Source"] == "Manual-JFF"]
        hex_ids = [r for r in manual if re.match(r"^[0-9a-f]{24}$", r["JFF Video ID"])]
        # Some rows carry free-text notes ("Couldnt find it") instead of an id.
        self.assertGreaterEqual(len(hex_ids), 50)

    def test_norm_title(self):
        self.assertEqual(notion_export.norm_title("VLOG Padded yoga!!.mp4"), "vlog padded yoga")

    def test_automated_live_rows_have_urls(self):
        rows = list(csv.DictReader(open(path(CSV), encoding="utf-8")))
        live = [r for r in rows if r["Record Source"] == "Automated" and r["Status"] == "Live"]
        self.assertEqual(len(live), 14)
        for r in live:
            self.assertTrue(r["Abdlhub Page URL"].startswith("https://abdlhub.com/?v="))


if __name__ == "__main__":
    unittest.main()

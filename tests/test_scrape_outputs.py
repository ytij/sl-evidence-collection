import re
import unittest

from tests.common import ATTRIBUTED_UPLOADER, GUID_RE, PULL_ZONE, load_csv

EXCLUDE = re.compile(r"kiki\s*cali|sophie\s*ladder|sophiaquin", re.I)
ALLOWED_MATCHED_BY = {"tag", "title", "tag+title"}
REQUIRED_COLUMNS = {
    "guid", "title", "matched_by", "page_url", "thumbnail_url", "stream_url",
    "duration_seconds", "views", "upload_date", "tags", "in_catalog",
    "thumbnail_http_status", "stream_http_status",
}


class TestScrapeOutputs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.all_rows = load_csv("sophie_little_all_videos.csv")
        cls.live_rows = load_csv("sophie_little_live_videos.csv")

    def test_nonempty(self):
        self.assertGreater(len(self.all_rows), 0)
        self.assertGreater(len(self.live_rows), 0)

    def test_required_columns(self):
        self.assertTrue(REQUIRED_COLUMNS.issubset(set(self.all_rows[0].keys())))

    def test_guid_and_urls(self):
        for r in self.all_rows:
            self.assertRegex(r["guid"], GUID_RE)
            self.assertEqual(r["page_url"], f"https://abdlhub.com/?v={r['guid']}")
            self.assertTrue(r["stream_url"].endswith("/playlist.m3u8"))
            self.assertIn(PULL_ZONE, r["thumbnail_url"])

    def test_matched_by_values(self):
        for r in self.all_rows:
            self.assertIn(r["matched_by"], ALLOWED_MATCHED_BY)

    def test_no_false_positives(self):
        offenders = [r["title"] for r in self.all_rows if EXCLUDE.search(r["title"])]
        self.assertEqual(offenders, [], f"false positives present: {offenders}")

    def test_live_is_subset_of_all(self):
        all_guids = {r["guid"] for r in self.all_rows}
        for r in self.live_rows:
            self.assertIn(r["guid"], all_guids)

    def test_live_rows_all_http_200(self):
        for r in self.live_rows:
            self.assertEqual(r["stream_http_status"], "200", r["guid"])

    def test_status_vocabulary(self):
        for r in self.all_rows:
            status = r["stream_http_status"]
            self.assertTrue(status == "200" or status == "404" or status.startswith("ERR:")
                            or status == "", f"unexpected status {status!r}")

    def test_attributed_works_are_live(self):
        # Every work attributed to the uploader in the takedown index must be live.
        import takedown
        works = takedown.build_works()
        live = {r["guid"] for r in self.live_rows}
        self.assertGreater(len(works), 0)
        for w in works:
            self.assertIn(w["guid"], live, f"{w['guid']} not live")

    def test_excludes_not_attributed(self):
        import json
        import os
        from tests.common import path
        subs = json.load(open(path("evidence/video_submissions.json"), encoding="utf-8"))["rows"]
        for s in subs:
            if s.get("user_id") != ATTRIBUTED_UPLOADER:
                continue
            self.assertFalse(EXCLUDE.search(s.get("title") or ""), s["title"])


if __name__ == "__main__":
    unittest.main()

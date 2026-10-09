import unittest

from tests.common import exists, load_csv, path

NOTICES = [
    "takedowns/dmca_notice_abdlhub.txt",
    "takedowns/dmca_notice_netlify.txt",
    "takedowns/dmca_notice_bunny.txt",
    "takedowns/dmca_notice_supabase.txt",
]
REQUIRED_ELEMENTS = [
    "signature",
    "identification of the copyrighted work",
    "identification of the infringing material",
    "good-faith belief",
    "penalty of perjury",
    "contact information",
    "[complainant name]",
]


class TestTakedown(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = load_csv("takedowns/takedown_index.csv")

    def test_index_rows(self):
        import takedown
        works = takedown.build_works()
        self.assertGreater(len(works), 0)
        self.assertEqual(len(self.rows), len(works))

    def test_index_columns(self):
        for col in ("guid", "title", "page_url", "stream_url", "uploader_user_id"):
            self.assertIn(col, self.rows[0])

    def test_index_urls_well_formed(self):
        for r in self.rows:
            self.assertTrue(r["page_url"].startswith("https://abdlhub.com/?v="))
            self.assertTrue(r["stream_url"].endswith("/playlist.m3u8"))

    def test_notices_exist(self):
        for n in NOTICES:
            self.assertTrue(exists(n), n)

    def test_notices_contain_512c_elements(self):
        for n in NOTICES:
            text = open(path(n), encoding="utf-8").read().lower()
            for el in REQUIRED_ELEMENTS:
                self.assertIn(el, text, f"{n} missing element: {el}")

    def test_notices_list_every_work(self):
        for n in NOTICES:
            text = open(path(n), encoding="utf-8").read()
            for r in self.rows:
                self.assertIn(r["guid"], text, f"{n} missing guid {r['guid']}")


if __name__ == "__main__":
    unittest.main()

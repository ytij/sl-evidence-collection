import unittest

import numpy as np
from PIL import Image

import match


def gradient_image(seed=0):
    img = Image.new("L", (64, 64))
    for x in range(64):
        for y in range(64):
            img.putpixel((x, y), (x * y + seed) % 256)
    return img


class TestCompare(unittest.TestCase):
    def test_similarity_identity(self):
        self.assertEqual(match.similarity("ballet practice", "ballet practice"), 1.0)

    def test_similarity_disjoint_low(self):
        self.assertLess(match.similarity("aaa bbb", "zzz yyy"), 0.5)

    def test_score_identical_is_high(self):
        orig = {"title": "diapered princess sofia dancing", "duration_seconds": 600,
                "published_at": "2024-01-01"}
        rehost = {"title": "diapered princess sofia dancing", "duration_seconds": 600,
                  "submitted_at": "2026-08-01", "thumbnail_url": ""}
        s = match.score(orig, rehost, None)
        self.assertGreaterEqual(s["total"], 0.95)
        self.assertTrue(s["rehost_postdates_original"])

    def test_score_unrelated_is_low(self):
        orig = {"title": "ballet practice at home", "duration_seconds": 1031,
                "published_at": "2024-01-01"}
        rehost = {"title": "Bunny enrolled in the baby institute", "duration_seconds": 509,
                  "submitted_at": "2026-08-01", "thumbnail_url": ""}
        s = match.score(orig, rehost, None)
        self.assertLess(s["total"], 0.6)

    def test_date_gate(self):
        orig = {"title": "x", "duration_seconds": 100, "published_at": "2026-09-30"}
        rehost = {"title": "x", "duration_seconds": 100, "submitted_at": "2026-08-01",
                  "thumbnail_url": ""}
        s = match.score(orig, rehost, None)
        self.assertFalse(s["rehost_postdates_original"])

    def test_duration_tolerance(self):
        orig = {"title": "same title here", "duration_seconds": 600, "published_at": "2024-01-01"}
        within = {"title": "same title here", "duration_seconds": 602, "submitted_at": "2026-08-01",
                  "thumbnail_url": ""}
        outside = {"title": "same title here", "duration_seconds": 700, "submitted_at": "2026-08-01",
                   "thumbnail_url": ""}
        self.assertEqual(match.score(orig, within, None)["duration_score"], 1.0)
        self.assertEqual(match.score(orig, outside, None)["duration_score"], 0.0)

    def test_phash_deterministic(self):
        if match.cv2 is None:
            self.skipTest("cv2 not available")
        a = match.phash(gradient_image(0))
        b = match.phash(gradient_image(0))
        self.assertTrue(np.array_equal(a, b))
        self.assertEqual(int(np.count_nonzero(a != b)), 0)

    def test_phash_distinguishes(self):
        if match.cv2 is None:
            self.skipTest("cv2 not available")
        a = match.phash(gradient_image(0))
        b = match.phash(gradient_image(77))
        # Not required to always differ, but these two should.
        self.assertGreater(int(np.count_nonzero(a != b)), 0)

    def test_guid_extraction(self):
        url = "https://iframe.mediadelivery.net/embed/621930/8f71399f-5565-497a-944f-466ad42b0271"
        self.assertEqual(match.guid_of(url), "8f71399f-5565-497a-944f-466ad42b0271")
        self.assertIsNone(match.guid_of("no guid here"))


if __name__ == "__main__":
    unittest.main()

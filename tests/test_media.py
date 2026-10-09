import hashlib
import json
import os
import unittest

from tests.common import exists, path

MANIFEST = "captures/media_manifest.json"


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class TestMediaManifest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.entries = json.load(open(path(MANIFEST), encoding="utf-8"))["entries"]

    def test_manifest_exists(self):
        self.assertTrue(exists(MANIFEST))

    def test_all_live_works_preserved(self):
        self.assertGreaterEqual(len(self.entries), 14)
        for guid, e in self.entries.items():
            self.assertEqual(e.get("status"), 200, guid)
            self.assertGreater(e.get("bytes", 0), 0, guid)

    def test_video_bytes_match_hash_when_present(self):
        # Bytes live in staging/ (gitignored); verify only what is on disk.
        checked = 0
        for guid, e in self.entries.items():
            p = path(os.path.join(e["dir"], "video.ts"))
            if os.path.exists(p):
                self.assertEqual(sha256_file(p), e["sha256"], guid)
                checked += 1
        if checked == 0:
            self.skipTest("staging media not present on this checkout")


if __name__ == "__main__":
    unittest.main()

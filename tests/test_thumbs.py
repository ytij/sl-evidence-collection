import os
import unittest

import preserve_thumbs


class TestThumbPreservation(unittest.TestCase):
    def test_ext_mapping(self):
        self.assertEqual(preserve_thumbs.EXT.get("image/jpeg"), ".jpg")
        self.assertEqual(preserve_thumbs.EXT.get("image/png"), ".png")

    def test_targets_are_all_delisted_by_default(self):
        targets = preserve_thumbs.load_targets(include_live=False)
        self.assertGreaterEqual(len(targets), 600)
        for r in targets:
            self.assertNotEqual(r["stream_http_status"], "200")

    def test_include_live_adds_the_live_works(self):
        delisted = preserve_thumbs.load_targets(include_live=False)
        allrows = preserve_thumbs.load_targets(include_live=True)
        self.assertEqual(len(allrows), 624)
        self.assertEqual(len(allrows) - len(delisted), 14)

    @unittest.skipUnless(os.path.exists(preserve_thumbs.MANIFEST), "manifest not created yet")
    def test_manifest_is_self_consistent(self):
        m = preserve_thumbs.load_manifest()
        for guid, e in m["entries"].items():
            if e.get("status") == 200 and e.get("file"):
                p = os.path.join(preserve_thumbs.THUMB_DIR, e["file"])
                if not os.path.exists(p):
                    continue  # image bytes are excluded from the shared repo
                self.assertEqual(preserve_thumbs.sha256(p), e["sha256"], guid)
                self.assertGreater(e["bytes"], 0)

    @unittest.skipUnless(os.path.exists(preserve_thumbs.MANIFEST), "manifest not created yet")
    def test_verify_command_passes(self):
        d = preserve_thumbs.THUMB_DIR
        if not any(os.path.isfile(os.path.join(d, f)) for f in os.listdir(d)):
            self.skipTest("thumbnail bytes excluded from the shared repo")
        self.assertEqual(preserve_thumbs.verify(), 0)


if __name__ == "__main__":
    unittest.main()

import unittest

from tests.common import ROOT, exists, path

REFERENCED = [
    "HANDOVER.md",
    "AGENTS.md",
    "TODO.md",
    "sophie_scrape.py",
    "evidence_store.py",
    "timestamp.py",
    "capture.py",
    "archive.py",
    "preserve_media.py",
    "availability.py",
    "osint_recon.py",
    "osint/public_exposure.py",
    "takedown.py",
    "damages.py",
    "match.py",
    "package.py",
    "legal/AUTHORITIES.md",
    "legal/authorities.json",
    "legal/COMPLAINT.md",
    "legal/exhibits/exhibit_A.md",
    "JFF_MATCHING.md",
    "notion_export.py",
    "notion/abdlhub_stolen_videos.csv",
    "notion/NOTION_SCHEMA.md",
    "manual/abdlhub_stolen_videos_manual_all.csv",
    "osint/PUBLIC_EXPOSURE.md",
    "osint/SITE_CATALOG.md",
    "osint/SUBPOENA_TARGETS.md",
    "takedowns/takedown_index.csv",
    "captures/archive.json",
    "captures/media_manifest.json",
    "evidence/availability/NOTES.md",
    "captures/20261009T050349Z/manifest.json",
    "evidence/manifest.json",
]


class TestDocs(unittest.TestCase):
    def test_referenced_paths_exist(self):
        for rel in REFERENCED:
            self.assertTrue(exists(rel), f"missing referenced path: {rel}")

    def test_handover_mentions_rules(self):
        text = open(path("HANDOVER.md"), encoding="utf-8").read()
        for phrase in ("rules of engagement", "read-only", "invisible", "evidence integrity"):
            self.assertIn(phrase.lower(), text.lower(), phrase)

    def test_agents_md_lists_commands(self):
        text = open(path("AGENTS.md"), encoding="utf-8").read()
        for cmd in ("sophie_scrape.py", "evidence_store.py", "takedown.py", "package.py"):
            self.assertIn(cmd, text)


if __name__ == "__main__":
    unittest.main()

import unittest

from tests.common import exists, load_csv, path

PRESERVATION = [
    "legal/preservation/supabase.txt",
    "legal/preservation/bunny.txt",
    "legal/preservation/netlify.txt",
    "legal/preservation/exoclick.txt",
]


def read(rel):
    return open(path(rel), encoding="utf-8").read()


class TestCourtDocs(unittest.TestCase):
    def test_instruments_exist(self):
        for rel in ["legal/METHODOLOGY.md", "legal/DECLARATION_1746.md",
                    "legal/SUBPOENA_512h.md", "legal/EXHIBIT_INDEX.md"] + PRESERVATION:
            self.assertTrue(exists(rel), rel)

    def test_exhibit_index_covers_all_works(self):
        text = read("legal/EXHIBIT_INDEX.md")
        rows = load_csv("takedowns/takedown_index.csv")
        for tag in "ABCDEFGHI":
            self.assertIn(f"| {tag} |", text, f"exhibit {tag} missing")
        for w in rows:
            self.assertIn(w["page_url"], text, f"{w['page_url']} missing from exhibit index")

    def test_declaration_has_1746_form(self):
        text = read("legal/DECLARATION_1746.md")
        self.assertIn("28 U.S.C. § 1746", text)
        self.assertIn("penalty of perjury", text)
        self.assertIn("Executed on", text)
        self.assertIn("[DECLARANT NAME]", text)
        # 902(13) / 902(14) hooks present
        self.assertIn("902(14)", text)
        self.assertIn("902(13)", text)

    def test_preservation_letters_have_hold_language(self):
        for rel in PRESERVATION:
            text = read(rel)
            low = text.lower()
            self.assertIn("preserve", low, rel)
            self.assertIn("37(e)", low, rel)
            self.assertIn("litigation is reasonably anticipated", low, rel)
            self.assertIn("[date]", low, rel)
            self.assertIn("[client name]", low, rel)

    def test_subpoena_package_has_three_parts(self):
        text = read("legal/SUBPOENA_512h.md")
        self.assertIn("512(c)(3)(A)", text)
        self.assertIn("Proposed subpoena", text)
        self.assertIn("512(h)(2)(C)", text)
        self.assertIn("penalty of perjury", text)
        # must reference the uploader identifier
        self.assertIn("a89bb9dc-d09f-4475-b9ed-ae398edf928b", text)

    def test_methodology_documents_integrity(self):
        text = read("legal/METHODOLOGY.md")
        low = text.lower()
        for phrase in ("sha-256", "rfc 3161", "no authentication", "limitations", "public access"):
            self.assertIn(phrase, low, phrase)

    def test_complaint_shell(self):
        text = read("legal/COMPLAINT.md")
        for cite in ("17 U.S.C. § 501", "28 U.S.C. § 1338", "28 U.S.C. § 1400",
                     "§ 504(c)", "§ 106", "§ 412"):
            self.assertIn(cite, text, cite)
        for section in ("NATURE OF THE ACTION", "JURISDICTION AND VENUE",
                        "CLAIMS FOR RELIEF", "PRAYER FOR RELIEF", "JURY"):
            self.assertIn(section, text, section)
        self.assertIn("[PLAINTIFF NAME]", text)
        self.assertIn("Exhibit B", text)

    def test_exhibit_shells_exist(self):
        for tag in "ABCDEFGHI":
            rel = f"legal/exhibits/exhibit_{tag}.md"
            self.assertTrue(exists(rel), rel)
            text = read(rel)
            self.assertIn(f"Exhibit {tag}", text)
            self.assertIn("Underlying artifact", text)
            self.assertIn("SHA-256", text)


if __name__ == "__main__":
    unittest.main()

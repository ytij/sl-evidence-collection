import re
import unittest
from urllib.parse import urlparse

import jsonschema

from tests.common import exists, load_json

AUTH_SCHEMA = {
    "type": "object",
    "required": ["verification_method", "authoritative_domains", "authorities", "documentation_elements"],
    "properties": {
        "authoritative_domains": {"type": "array", "minItems": 1, "items": {"type": "string"}},
        "authorities": {
            "type": "array", "minItems": 1,
            "items": {
                "type": "object",
                "required": ["id", "type", "citation", "title", "verified", "requirement", "applies_to"],
                "properties": {
                    "id": {"type": "string", "minLength": 1},
                    "type": {"enum": ["statute", "rule", "state-statute", "case"]},
                    "citation": {"type": "string", "minLength": 1},
                    "title": {"type": "string"},
                    "verified": {"type": "boolean"},
                    "verified_at": {"type": ["string", "null"]},
                    "source_url": {"type": ["string", "null"]},
                    "requirement": {"type": "string", "minLength": 1},
                    "applies_to": {"type": "array", "items": {"type": "string"}},
                    "note": {"type": "string"},
                },
                "additionalProperties": True,
            },
        },
        "documentation_elements": {
            "type": "array", "minItems": 1,
            "items": {
                "type": "object",
                "required": ["id", "title", "authority_ids", "repo_artifacts", "status"],
                "properties": {
                    "id": {"type": "string"},
                    "title": {"type": "string"},
                    "authority_ids": {"type": "array", "items": {"type": "string"}},
                    "repo_artifacts": {"type": "array", "items": {"type": "string"}},
                    "status": {"enum": ["satisfied", "partial", "missing"]},
                    "gap": {"type": "string"},
                },
            },
        },
    },
}


class TestLegalAuthorities(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_json("legal/authorities.json")
        cls.authorities = cls.data["authorities"]
        cls.by_id = {a["id"]: a for a in cls.authorities}
        cls.elements = cls.data["documentation_elements"]
        cls.element_ids = {e["id"] for e in cls.elements}

    def test_schema(self):
        jsonschema.validate(self.data, AUTH_SCHEMA)

    def test_unique_ids(self):
        ids = [a["id"] for a in self.authorities]
        self.assertEqual(len(ids), len(set(ids)), "duplicate authority ids")
        eids = [e["id"] for e in self.elements]
        self.assertEqual(len(eids), len(set(eids)), "duplicate element ids")

    def test_verified_entries_have_authoritative_sources(self):
        domains = set(self.data["authoritative_domains"])
        for a in self.authorities:
            if a["verified"]:
                self.assertIsNotNone(a.get("source_url"), a["id"])
                host = urlparse(a["source_url"]).netloc.lower()
                if host.startswith("www."):
                    host = host[4:]
                self.assertIn(host, domains, f"{a['id']} source host {host} not allow-listed")
                self.assertRegex(a["verified_at"], r"^\d{4}-\d{2}-\d{2}$", a["id"])

    def test_unverified_entries_are_flagged(self):
        for a in self.authorities:
            if not a["verified"]:
                self.assertTrue(a.get("note"), f"{a['id']} unverified but not flagged")

    def test_minimum_verified_count(self):
        verified = [a for a in self.authorities if a["verified"]]
        self.assertGreaterEqual(len(verified), 13, f"only {len(verified)} verified authorities")

    def test_citation_formats(self):
        for a in self.authorities:
            c = a["citation"]
            if a["type"] == "statute":
                self.assertRegex(c, r"^\d+ U\.S\.C\. § \d+", a["id"])
            elif a["type"] == "state-statute":
                self.assertRegex(c, r"^Fla\. Stat\. § \d+\.\d+", a["id"])
            elif a["type"] == "rule":
                self.assertRegex(c, r"^Fed\. R\. (Evid\.|Civ\. P\.) \d+", a["id"])
            elif a["type"] == "case":
                self.assertIn(" v. ", c, a["id"])
                self.assertRegex(c, r"\d{4}\)$", a["id"])

    def test_applies_to_references_real_elements(self):
        for a in self.authorities:
            for e in a["applies_to"]:
                self.assertIn(e, self.element_ids, f"{a['id']} applies_to unknown element {e}")

    def test_elements_reference_real_authorities(self):
        for e in self.elements:
            self.assertTrue(e["authority_ids"], f"{e['id']} has no authorities")
            for aid in e["authority_ids"]:
                self.assertIn(aid, self.by_id, f"{e['id']} references unknown authority {aid}")

    def test_element_artifacts_exist(self):
        for e in self.elements:
            for rel in e["repo_artifacts"]:
                self.assertTrue(exists(rel), f"{e['id']} artifact missing: {rel}")

    def test_required_elements_present(self):
        required = {f"E{i}" for i in range(1, 20)}
        self.assertTrue(required.issubset(self.element_ids),
                        f"missing: {sorted(required - self.element_ids)}")

    def test_authorities_md_exists(self):
        self.assertTrue(exists("legal/AUTHORITIES.md"))


if __name__ == "__main__":
    unittest.main()

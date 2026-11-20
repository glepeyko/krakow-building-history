"""Checks on build helpers and on the committed research file.
Run with:  python -m unittest discover tests"""
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import build  # noqa: E402


class RegisterNumberTests(unittest.TestCase):
    def test_gez_style(self):
        self.assertEqual(build.a_numbers("A- 185 25.06.1931"), {"A-185"})
        self.assertEqual(build.a_numbers("A-306, 7.07.1966; A-302/M"), {"A-306", "A-302/M"})

    def test_nid_style(self):
        self.assertEqual(build.nid_numbers("262 z 1968-03-26"), {"A-262"})
        self.assertEqual(build.nid_numbers("A-844 z 1990-04-09, brak numeru z 1995-05-20, A-1526/M z 2019-10-08"),
                         {"A-844", "A-1526/M"})
        # Old-style signatures of other offices are not Kraków A- numbers.
        self.assertEqual(build.nid_numbers("I-4-9/48 z 1949-08-22, A-652 z 1984-04-26"), {"A-652"})


class AiDraftsFileTests(unittest.TestCase):
    PATH = ROOT / "data" / "research" / "ai_drafts.json"

    @unittest.skipUnless(PATH.exists(), "no AI drafts yet")
    def test_schema_and_citations(self):
        drafts = json.loads(self.PATH.read_text(encoding="utf-8"))
        ids = set()
        for d in drafts:
            with self.subTest(entry=d.get("entry_id")):
                self.assertEqual(d["status"], "ai_draft_unverified")
                self.assertRegex(d["researched_at"], r"^\d{4}-\d{2}-\d{2}$")
                self.assertTrue(d["text"].strip())
                self.assertNotIn(d["entry_id"], ids)
                ids.add(d["entry_id"])
                self.assertTrue(d["sources"])
                for s in d["sources"]:
                    self.assertTrue(s["url"].startswith("https://"), s["url"])
                    self.assertTrue(s["title"].strip())
                # Every sentence cites something, and every marker points to a source.
                sentences = [x for x in re.split(r"(?<=\])\s+", d["text"].strip()) if x]
                for sent in sentences:
                    self.assertRegex(sent, r"\[\d+(?:,\s*\d+)*\]$", sent)
                cited = {int(n) for m in re.findall(r"\[(\d+(?:,\s*\d+)*)\]", d["text"])
                         for n in m.split(",")}
                self.assertTrue(cited <= set(range(1, len(d["sources"]) + 1)), cited)
                self.assertEqual(cited, set(range(1, len(d["sources"]) + 1)), "uncited source")



class CorrectionsFileTests(unittest.TestCase):
    PATH = ROOT / "data" / "research" / "corrections.json"

    @unittest.skipUnless(PATH.exists(), "no corrections")
    def test_schema(self):
        for c in json.loads(self.PATH.read_text(encoding="utf-8")):
            with self.subTest(entry=c.get("entry_id")):
                self.assertEqual(c["field"], "building_number")
                self.assertTrue(c["from"] and c["to"] and c["reason"].strip())
                self.assertEqual(c["decided_by"], "owner")
                self.assertTrue(c["sources"])
                for s in c["sources"]:
                    self.assertTrue(s["url"].startswith("https://"))


if __name__ == "__main__":
    unittest.main()

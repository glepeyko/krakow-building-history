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
                self.assertIn(d["status"], ("ai_draft_unverified", "verified"))
                if d["status"] == "verified":
                    # Only the owner approves AI texts (CLAUDE.md).
                    self.assertEqual(d.get("approved_by"), "owner")
                    self.assertRegex(d.get("approved_at", ""), r"^\d{4}-\d{2}-\d{2}$")
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



class Batch2DraftsTests(unittest.TestCase):
    PATH = ROOT / "data" / "research" / "ai_drafts.json"

    @unittest.skipUnless(PATH.exists(), "no AI drafts yet")
    def test_batch2_rules(self):
        drafts = json.loads(self.PATH.read_text(encoding="utf-8"))
        for d in drafts:
            if d.get("batch") != 2:
                continue
            with self.subTest(entry=d["entry_id"]):
                # Agents never approve their own texts; only the owner does.
                if d["status"] == "verified":
                    self.assertEqual(d.get("approved_by"), "owner")
                self.assertIn(d["verification"]["verdict"], ("kept", "corrected"))
                self.assertTrue(d["verification"]["checked_urls"])
                n = len(re.findall(r"\]\s*(?=\S|$)", d["text"]))
                self.assertTrue(2 <= n <= 5, f"{n} sentences")


class StreetHistoryFileTests(unittest.TestCase):
    PATH = ROOT / "data" / "research" / "street_history.json"

    @unittest.skipUnless(PATH.exists(), "no street history")
    def test_schema(self):
        names = {s["name"] for s in json.loads((ROOT / "data" / "streets.json").read_text(encoding="utf-8"))}
        for rec in json.loads(self.PATH.read_text(encoding="utf-8")):
            with self.subTest(street=rec["street"]):
                self.assertIn(rec["street"], names)
                self.assertIn(rec["status"], ("ai_draft_unverified", "verified"))
                self.assertTrue(rec["names"])
                used = set()
                for n in rec["names"]:
                    self.assertTrue(n["name"].strip())
                    for k in ("from", "to"):
                        self.assertTrue(n.get(k) is None or isinstance(n[k], int))
                    if n.get("from") and n.get("to"):
                        self.assertLessEqual(n["from"], n["to"])
                    self.assertTrue(1 <= n["source"] <= len(rec["sources"]))
                    used.add(n["source"])
                self.assertEqual(used, set(range(1, len(rec["sources"]) + 1)), "unused source")
                for s in rec["sources"]:
                    self.assertTrue(s["url"].startswith("https://") and s["title"].strip())


class NearbyDedupTests(unittest.TestCase):
    def poi(self, title, lat=50.0, lon=20.0, street="", number=""):
        return {"title": title, "lat": lat, "lon": lon, "street": street, "number": number}

    def test_same_fort_named_differently(self):
        self.assertTrue(build.same_place(self.poi("Fort 48a Mistrzejowice"), self.poi("Fort pancerny 48a", 50.0001)))

    def test_different_buildings_same_address_kept(self):
        a = self.poi("Synagoga Stara", street="Szeroka", number="24")
        b = self.poi("kamienica", street="Szeroka", number="24")
        self.assertFalse(build.same_place(a, b))

    def test_far_apart_not_merged(self):
        self.assertFalse(build.same_place(self.poi("Kościół św. Anny"), self.poi("Kościół św. Anny", 50.01)))


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

"""Tests for scripts/lib/library.py and the old-number index.

The fixture tests build a tiny fake library in a temp folder, so they run
without the git-ignored source-data/raw/library/. The "known houses" tests use
the real cache and are skipped when it has not been downloaded
(python scripts/sources/fetch_library.py).
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from lib.library import Library, fold  # noqa: E402

REAL_LIB = ROOT / "source-data" / "raw" / "library"


def make_fixture(tmp: Path):
    lib = tmp / "library"
    (lib / "chmiel-test").mkdir(parents=True)
    (lib / "list-test").mkdir(parents=True)
    pages = {
        5: "— 3 —\nL. or. 1, sp. 343, Gm. V. Kamienica na rogu.\nDalej opis.",
        6: "— 4 —\nciąg dalszy domu nr 1, właściciel Jan Kowal\nski kupiec.",
        7: "— 5 —\nkoniec.\nL. or. 3. sp. 344. Kamienica zwana Pod Ry-\nbą, własność Romera.",
        8: "— 6 —\nL. or. 5, sp. 345. Kamienica.\nPor. L. or. 1 wyżej.",
    }
    for n, t in pages.items():
        (lib / "chmiel-test" / f"p{n:04d}.txt").write_text(t, encoding="utf-8")
    (lib / "list-test" / "p0020.txt").write_text(
        "— 21 —\nRomer hr. Bronisław, ul. Floryańska 3 (344).\nInny tekst o ul. Floriańskiej 5 tutaj.",
        encoding="utf-8")
    manifest = {"sources": [
        {"id": "chmiel-test", "author": "A. Chmiel", "title": "Domy krakowskie: ulica Floryańska",
         "year": 1917, "route": "polona", "page_url": "https://polona.pl/item-view/x?page={scan0}",
         "covers": {"streets": ["Floriańska"], "numbers": "odd 1-57"}},
        {"id": "list-test", "author": "A. Nowolecki", "title": "Nowy wykaz", "year": 1884,
         "route": "polona", "page_url": "https://polona.pl/item-view/y?page={scan0}", "covers": {}},
        {"id": "blocked-test", "author": "X", "title": "Not downloaded", "year": 2000,
         "route": "pdf", "url": "https://example.org/a.pdf", "page_url": "https://example.org/a.pdf#page={scan}"},
    ]}
    (tmp / "library.json").write_text(json.dumps(manifest), encoding="utf-8")
    old = {"rows": [{"street": "Floriańska", "street_1884": "Floryańska", "number": "3",
                     "old_number": "344", "owner": "Romer hr. Bronisław", "year": 1884,
                     "source": "list-test", "scan": 20, "page": 21,
                     "page_url": "https://polona.pl/item-view/y?page=19", "confidence": "high",
                     "matched": True}]}
    (tmp / "old_numbers.json").write_text(json.dumps(old), encoding="utf-8")
    return Library(lib_dir=lib, manifest=tmp / "library.json", old_numbers=tmp / "old_numbers.json")


class FixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.lib = make_fixture(Path(cls.tmp.name))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_fold_joins_hyphenation_and_diacritics(self):
        self.assertEqual(fold("Pod Ry-\nbą"), "pod ryba")
        self.assertEqual(fold("Kowal\nski"), "kowalski")

    def test_available_skips_missing_sources(self):
        self.assertEqual(sorted(self.lib.available()), ["chmiel-test", "list-test"])

    def test_house_sections(self):
        sec = self.lib.house_sections("chmiel-test")
        self.assertEqual(sec["1"], [5, 6, 7])  # runs to the page of the next heading
        self.assertEqual(sec["3"], [7, 8])
        self.assertEqual(sec["5"], [8])        # "Por. L. or. 1" later does not override

    def test_find_address_section_first_with_citation(self):
        hits = self.lib.find_address("Floriańska", "3")
        self.assertEqual(hits[0].source, "chmiel-test")
        self.assertEqual(hits[0].scan, 7)
        self.assertEqual(hits[0].page, 5)  # printed page read from the header
        self.assertEqual(hits[0].url, "https://polona.pl/item-view/x?page=6")
        self.assertIn("s. 5", hits[0].citation_title)
        self.assertTrue(any(h.source == "list-test" and "344" in h.reason for h in hits))

    def test_number_outside_coverage_is_not_a_section(self):
        hits = self.lib.find_address("Floriańska", "4")  # even: not in this volume
        self.assertFalse(any(h.score >= 9 for h in hits))

    def test_mentions_match_old_spelling(self):
        hits = self.lib.find_address("Floriańska", "5")
        self.assertTrue(any(h.source == "list-test" for h in hits))

    def test_old_number_lookups(self):
        self.assertEqual(self.lib.old_numbers("ul. Floriańska", "3")[0]["old_number"], "344")
        self.assertEqual(self.lib.by_old_number("344")[0]["number"], "3")
        self.assertEqual(self.lib.by_old_number("344", street="Grodzka"), [])

    def test_find_name(self):
        hits = self.lib.find_name("Pod Rybą")
        self.assertEqual([(h.source, h.scan) for h in hits], [("chmiel-test", 7)])
        self.assertTrue(self.lib.find_name("Romer"))


@unittest.skipUnless((REAL_LIB / "chmiel-florianska-1").is_dir(), "library cache not downloaded")
class KnownHousesTests(unittest.TestCase):
    """Five houses whose pages we checked by hand (2026-11-20)."""

    @classmethod
    def setUpClass(cls):
        cls.lib = Library()

    def first(self, street, number):
        hits = self.lib.find_address(street, number)
        self.assertTrue(hits, f"no hits for {street} {number}")
        return hits[0]

    def test_florianska_19(self):  # Chmiel 1917, heading "L. or. 19, sp. 352"
        h = self.first("Floriańska", "19")
        self.assertEqual((h.source, h.scan), ("chmiel-florianska-1", 82))

    def test_florianska_32(self):  # DBC DjVu, Floriańska cz. 2 (16–44)
        h = self.first("Floriańska", "32")
        self.assertEqual(h.source, "chmiel-florianska-2b")
        self.assertIn("L. or. 32", h.reason)

    def test_grodzka_13(self):
        h = self.first("Grodzka", "13")
        self.assertEqual((h.source, h.page), ("chmiel-grodzka-1", 101))

    def test_swietego_jana_12(self):
        h = self.first("Świętego Jana", "12")
        self.assertEqual((h.source, h.page), ("chmiel-jana-2", 165))

    def test_szeroka_34_old_number(self):  # no monograph; Nowolecki 1884 gives lc. 209
        rows = self.lib.old_numbers("Szeroka", "34")
        self.assertTrue(rows)
        self.assertEqual({r["old_number"] for r in rows}, {"209"})


class OldNumbersFileTests(unittest.TestCase):
    def test_schema_and_stats(self):
        p = ROOT / "data" / "research" / "old_numbers.json"
        d = json.loads(p.read_text(encoding="utf-8"))
        self.assertGreater(d["stats"]["rows"], 1000)
        self.assertGreater(d["stats"]["match_rate"], 0.6)
        keys = {"street", "street_1884", "number", "old_number", "owner", "year", "source",
                "scan", "page", "page_url", "confidence", "matched"}
        for r in d["rows"][:200]:
            self.assertEqual(set(r), keys)
            self.assertIn(r["confidence"], ("high", "medium", "low"))
            self.assertTrue(r["page_url"].startswith("https://polona.pl/item-view/"))


class ManifestTests(unittest.TestCase):
    def test_manifest_records(self):
        m = json.loads((ROOT / "data" / "research" / "library.json").read_text(encoding="utf-8"))
        ids = [s["id"] for s in m["sources"]]
        self.assertEqual(len(ids), len(set(ids)))
        for s in m["sources"]:
            for k in ("author", "title", "year", "licence", "route", "page_url", "item_url"):
                self.assertIn(k, s, f"{s['id']} lacks {k}")
            self.assertIn(s["route"], ("polona", "ia", "pdf", "djvu"))
            self.assertTrue("{scan" in s["page_url"], s["id"])


if __name__ == "__main__":
    unittest.main()

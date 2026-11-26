import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "sources"))
import fetch_library as fl


class LibraryFetch(unittest.TestCase):
    def test_split_pages_drops_empty_tail(self):
        self.assertEqual(fl.split_pages("a\fb\f"), ["a", "b"])

    def test_citation_pdf(self):
        s = {"route": "pdf", "url": "https://x/y.pdf#page=1"}
        self.assertEqual(fl.citation_url(s, 7), "https://x/y.pdf#page=7")

    def test_citation_ia(self):
        s = {"route": "ia", "url": "u", "ia_id": "abc"}
        self.assertEqual(fl.citation_url(s, 3), "https://archive.org/details/abc/page/n2")

    def test_registry_complete(self):
        for sid, s in fl.SOURCES.items():
            for k in ("title", "licence", "route", "url"):
                self.assertIn(k, s, sid)


if __name__ == "__main__":
    unittest.main()

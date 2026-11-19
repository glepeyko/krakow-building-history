"""Run with:  python -m unittest discover tests"""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from lib.geo import DistrictIndex, point_in_polygons, point_in_ring  # noqa: E402

SQUARE = [[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]
HOLE = [[4, 4], [6, 4], [6, 6], [4, 6], [4, 4]]


class PointInPolygonTests(unittest.TestCase):
    def test_ring(self):
        self.assertTrue(point_in_ring(5, 5, SQUARE))
        self.assertFalse(point_in_ring(11, 5, SQUARE))
        self.assertFalse(point_in_ring(5, -1, SQUARE))

    def test_hole_is_outside(self):
        poly = [[SQUARE, HOLE]]
        self.assertTrue(point_in_polygons(2, 2, poly))
        self.assertFalse(point_in_polygons(5, 5, poly))

    def test_multipolygon(self):
        far = [[20, 20], [30, 20], [30, 30], [20, 30], [20, 20]]
        poly = [[SQUARE], [far]]
        self.assertTrue(point_in_polygons(25, 25, poly))
        self.assertFalse(point_in_polygons(15, 15, poly))

    def test_index(self):
        idx = DistrictIndex([
            {"name": "A", "polygons": [[SQUARE]]},
            {"name": "B", "polygons": [[[[10, 0], [20, 0], [20, 10], [10, 10], [10, 0]]]]},
        ])
        # DistrictIndex.find takes (lat, lon): y first.
        self.assertEqual(idx.find(5, 3)["name"], "A")
        self.assertEqual(idx.find(5, 15)["name"], "B")
        self.assertIsNone(idx.find(5, 25))


class RealDistrictTests(unittest.TestCase):
    """Known addresses must land in the right dzielnica. Skipped when the raw
    OSM boundaries have not been downloaded (source-data/raw is git-ignored)."""

    RAW = ROOT / "source-data" / "raw" / "osm_districts.json"

    @unittest.skipUnless(RAW.exists(), "run scripts/sources/fetch_osm.py first")
    def test_known_points(self):
        idx = DistrictIndex(json.loads(self.RAW.read_text(encoding="utf-8")))
        cases = [
            ((50.06165, 19.93723), "Stare Miasto"),        # Rynek Główny 1 (Sukiennice)
            ((50.05165, 19.94830), "Stare Miasto"),        # Szeroka (Kazimierz)
            ((50.07230, 20.03780), "Nowa Huta"),           # Plac Centralny
            ((50.04480, 19.95390), "Podgórze"),            # Rynek Podgórski
            ((50.095163, 20.014951), "Mistrzejowice"),     # Osiedle Piastów 1d (OSM point)
        ]
        for (lat, lon), name in cases:
            d = idx.find(lat, lon)
            self.assertIsNotNone(d, name)
            self.assertEqual(d["name"].strip(), name)


if __name__ == "__main__":
    unittest.main()

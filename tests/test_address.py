"""Run with:  python -m unittest discover tests"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from lib.address import (  # noqa: E402
    StreetIndex, normalize, normalize_number, number_parts, split_street_number, street_key,
)

OSM_STREETS = [
    "Józefa Szujskiego", "aleja Juliusza Słowackiego", "Świętej Agnieszki",
    "28 Lipca 1943", "aleja 29 Listopada", "Grodzka", "Rynek Główny",
    "Osiedle Piastów", "Plac Inwalidów", "Jana Szujskiego",  # fake 2nd Szujski
    "Marszałka Ferdinanda Focha", "Floriańska",
]


class NormalizeTests(unittest.TestCase):
    def test_diacritics(self):
        self.assertEqual(normalize("  Łobzowska  Źródło "), "lobzowska zrodlo")

    def test_street_key_ignores_order_and_titles(self):
        self.assertEqual(street_key("Słowackiego Juliusza"), street_key("aleja Juliusza Słowackiego"))
        self.assertEqual(street_key("Agnieszki św."), street_key("Świętej Agnieszki"))
        self.assertEqual(street_key("os. Piastów"), street_key("Osiedle Piastów"))
        self.assertEqual(street_key("pl. Inwalidów"), street_key("Plac Inwalidów"))

    def test_numbers(self):
        self.assertEqual(normalize_number("11 A"), "11a")
        self.assertEqual(normalize_number("1 a"), "1a")
        self.assertEqual(normalize_number("14 / 16"), "14-16")
        self.assertEqual(number_parts("44-46-48"), ["44", "46", "48"])
        self.assertEqual(number_parts("11 - 13"), ["11", "13"])
        self.assertEqual(number_parts(""), [])


class StreetIndexTests(unittest.TestCase):
    def setUp(self):
        self.idx = StreetIndex(OSM_STREETS)

    def test_exact_and_reordered(self):
        self.assertEqual(self.idx.resolve("Słowackiego Juliusza"), "aleja Juliusza Słowackiego")
        self.assertEqual(self.idx.resolve("Focha Ferdinanda marsz."), "Marszałka Ferdinanda Focha")

    def test_partial_unique(self):
        self.assertEqual(self.idx.resolve("Floriańska"), "Floriańska")
        self.assertEqual(self.idx.resolve("Słowackiego"), "aleja Juliusza Słowackiego")

    def test_partial_ambiguous_is_none(self):
        # Two streets contain "Szujskiego" -> no guess.
        self.assertIsNone(self.idx.resolve("Szujskiego"))

    def test_unknown(self):
        self.assertIsNone(self.idx.resolve("Nieistniejąca"))


class SplitTests(unittest.TestCase):
    def setUp(self):
        self.idx = StreetIndex(OSM_STREETS)

    def test_trailing_words(self):
        self.assertEqual(split_street_number("Grodzka 52 kościół", self.idx), ("Grodzka", "52", "kościół"))

    def test_street_with_number_in_name(self):
        self.assertEqual(split_street_number("28 Lipca 1943 3", self.idx), ("28 Lipca 1943", "3", ""))
        self.assertEqual(split_street_number("al. 29 Listopada 5", self.idx), ("al. 29 Listopada", "5", ""))

    def test_range_and_letter(self):
        self.assertEqual(split_street_number("Słowackiego Juliusza 44-46-48", self.idx)[1], "44-46-48")
        self.assertEqual(split_street_number("Floriańska 1 a", self.idx)[1], "1a")

    def test_no_number(self):
        self.assertEqual(split_street_number("Balicka kościół", self.idx), ("Balicka kościół", "", ""))


if __name__ == "__main__":
    unittest.main()

"""Address normalization and matching, shared by every data source.

All sources (GEZ register, OpenStreetMap, Wikidata) write street names
differently:
    GEZ:       "Słowackiego Juliusza", "Agnieszki św.", "Focha Ferdinanda marsz."
    OSM:       "aleja Juliusza Słowackiego", "Świętej Agnieszki"
    Wikidata:  "ul. Szujskiego 4, 31-123 Kraków"
We compare streets by the *set* of meaningful words, after removing
diacritics, street-type words (ul., al., os., plac ...) and titles
(św., ks., gen. ...). Word order does not matter, so "Słowackiego Juliusza"
and "Juliusza Słowackiego" get the same key.
"""
from __future__ import annotations

import re
from collections import defaultdict

DIACRITICS = str.maketrans("ąćęłńóśźżĄĆĘŁŃÓŚŹŻ", "acelnoszzACELNOSZZ")

# Words that say what kind of street it is, or a person's title. They are
# dropped before comparing, because sources use them inconsistently.
STOP_WORDS = {
    "ul", "ulica", "al", "aleja", "aleje", "os", "osiedle", "pl", "plac",
    "sw", "swietej", "swietego", "swietych", "sw.", "ks", "ksiedza", "ksiezy",
    "gen", "generala", "marsz", "marszalka", "kard", "kardynala", "bl",
    "blogoslawionej", "blogoslawionego", "abp", "arcybiskupa", "bpa", "biskupa",
    "prof", "profesora", "dr", "doktora", "pplk", "plk", "pulkownika", "mjr",
    "majora", "kpt", "kapitana", "por", "porucznika", "o", "ojca", "im",
    "krola", "krolowej", "sw", "sgt", "kr", "w", "krakowie",
}

NUMBER_TOKEN = re.compile(r"^\d+[a-z]?$")


def normalize(text: str) -> str:
    """Lowercase, no diacritics, single spaces. For search keys, not display."""
    text = (text or "").translate(DIACRITICS).lower()
    return re.sub(r"\s+", " ", text).strip()


def street_words(name: str) -> list[str]:
    text = normalize(name)
    text = re.sub(r"[.,()\"'„”]", " ", text)
    text = text.replace(" - ", " ")
    return [w for w in text.split() if w and w not in STOP_WORDS]


def street_key(name: str) -> frozenset:
    """Order-independent key for a street name."""
    return frozenset(street_words(name))


def normalize_number(raw: str) -> str:
    """'11 A' -> '11a', ' 2-3 ' -> '2-3', '14/16' -> '14-16'."""
    n = normalize(raw)
    n = re.sub(r"\s*([-/])\s*", "-", n)
    n = re.sub(r"(\d)\s+([a-z])\b", r"\1\2", n)
    n = n.replace(" ", "")
    return n


def number_parts(raw: str) -> list[str]:
    """Every single number an address covers: '44-46-48' -> ['44','46','48'],
    '2-3' -> ['2','3'], '11a' -> ['11a']. Used so a corner building listed as
    '5-7' is found when someone types '5' or '7'."""
    n = normalize_number(raw)
    return [p for p in n.split("-") if NUMBER_TOKEN.match(p)]


class StreetIndex:
    """Resolves any spelling of a street to one canonical (OSM) street name."""

    def __init__(self, canonical_names):
        self.by_key: dict[frozenset, str] = {}
        self.by_word: dict[str, set] = defaultdict(set)
        for name in canonical_names:
            key = street_key(name)
            if not key:
                continue
            # Keep the first spelling seen; identical keys are the same street.
            self.by_key.setdefault(key, name)
            for w in key:
                self.by_word[w].add(key)

    def resolve(self, name: str) -> str | None:
        key = street_key(name)
        if not key:
            return None
        if key in self.by_key:
            return self.by_key[key]
        # Partial name ("Szujskiego" for "Józefa Szujskiego"): accept only a
        # unique candidate that contains all the given words.
        candidates = None
        for w in key:
            found = self.by_word.get(w, set())
            candidates = found if candidates is None else candidates & found
            if not candidates:
                break
        if candidates and len(candidates) == 1:
            return self.by_key[next(iter(candidates))]
        # Abbreviated first names / initials: "Słowackiego J." - try without
        # one-letter words.
        short = frozenset(w for w in key if len(w) > 1)
        if short != key and short:
            return self.resolve(" ".join(short))
        return None


def split_street_number(text: str, index: StreetIndex | None = None):
    """Split free text like 'ul. Grodzka 52 kościół' into
    (street, number, rest). Returns number '' if none is found.

    With an index, the longest known street prefix wins, so streets whose
    names contain numbers ('28 Lipca 1943 3', 'al. 29 Listopada 5') work.
    """
    text = re.sub(r"\s+", " ", (text or "")).strip()
    tokens = text.split(" ")
    num_re = re.compile(r"^(\d+)\s*([a-zA-Z])?(?:\s*[-/]\s*\d+\s*[a-zA-Z]?)*$")

    def number_at(i):
        # Join tokens like '11', '-', '13' or '1', 'a' into one number.
        best = None
        for j in range(i + 1, min(len(tokens), i + 6) + 1):
            chunk = " ".join(tokens[i:j])
            if num_re.match(chunk):
                best = (chunk, j)
        return best

    if index is not None:
        for i in range(len(tokens) - 1, 0, -1):
            street = " ".join(tokens[:i])
            found = number_at(i)
            if found and index.resolve(street):
                return street, normalize_number(found[0]), " ".join(tokens[found[1]:])

    for i in range(1, len(tokens)):
        found = number_at(i)
        if found:
            return " ".join(tokens[:i]), normalize_number(found[0]), " ".join(tokens[found[1]:])
    return text, "", ""


def address_keys(street: str, number: str) -> list[tuple[str, str]]:
    """(canonical street, single number) pairs for an address."""
    return [(street, p) for p in number_parts(number)]

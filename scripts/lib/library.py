"""Search the cached historians' texts (source-data/raw/library/, filled by
scripts/sources/fetch_library.py) for a Kraków address.

    from lib.library import Library
    lib = Library()
    hits = lib.find_address("Floriańska", "19")
    for h in hits: print(h.citation_title, h.url, h.reason)

Ways in, best first:
  1. House sections in Chmiel's "Domy krakowskie": each house starts with a
     heading "L. or. 19, sp. 352, …" (L. or. = liczba orientacyjna, the street
     number; sp. = the old conscription number). The section runs to the next
     heading, so we return exactly the pages about that house.
  2. The old-number index (data/research/old_numbers.json, Nowolecki 1884):
     old lc. number and 1884 owner of the address, with its page.
  3. Full-text search for the street + number, the old number, a house name
     ("Pod Jaszczurką") or an owner's name, OCR-tolerant (diacritics folded,
     words broken across lines re-joined).

Every hit carries a citation: source title, printed page (when it can be
read from the page header) and a page-level URL from the manifest's page_url.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from .address import normalize, street_key

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "data" / "research" / "library.json"
OLD_NUMBERS = ROOT / "data" / "research" / "old_numbers.json"
LIB = ROOT / "source-data" / "raw" / "library"

HEADING = re.compile(r"(?:^|\n)\s*L\s?\.\s?or\s?\.\s*(\d{1,3}[a-c]?)(?:\s*[/-]\s*(\d{1,3}))?\s*[.,]")
PRINTED_PAGE = re.compile(r"^\s*[-—–_]*\s*(\d{1,3})\s*[-—–_.]*\s*$")
PRINTED_PAGE_LOOSE = re.compile(r"^\s*[-—–_]+\s*(\d{1,3})\s*[-—–_.]*")


def fold(text: str) -> str:
    """Search form: no diacritics, lowercase, line-break hyphenation joined,
    whitespace collapsed. 'Flo-\\nryańska' -> 'floryanska'."""
    text = re.sub(r"[-—]\s*\n\s*", "", text or "")
    text = re.sub(r"(?<=[a-ząćęłńóśźż])\n(?=[a-ząćęłńóśźż])", "", text)  # 'po\nwstają' (no hyphen in OCR)
    return re.sub(r"\s+", " ", normalize(text))


def fold_flat(text: str) -> str:
    """Like fold() but keeps line breaks as spaces (no joining) - for numbers."""
    return re.sub(r"\s+", " ", normalize(text or ""))


@dataclass
class Hit:
    source: str
    scan: int
    page: int | None
    url: str
    citation_title: str
    reason: str
    score: float
    snippet: str = ""
    scans: list = field(default_factory=list)  # all scans of a house section

    def as_dict(self):
        return {k: getattr(self, k) for k in
                ("source", "scan", "page", "url", "citation_title", "reason", "score", "snippet", "scans")}


class Library:
    def __init__(self, root: Path = ROOT, lib_dir: Path | None = None, manifest: Path | None = None,
                 old_numbers: Path | None = None):
        self.lib_dir = lib_dir or LIB
        m = json.loads((manifest or MANIFEST).read_text(encoding="utf-8"))
        self.sources = {s["id"]: s for s in m["sources"]}
        on = old_numbers or OLD_NUMBERS
        self.old_rows = json.loads(on.read_text(encoding="utf-8"))["rows"] if on.exists() else []

    # ---- pages -------------------------------------------------------------
    def available(self) -> list[str]:
        return [sid for sid in self.sources if (self.lib_dir / sid).is_dir()]

    @lru_cache(maxsize=None)
    def pages(self, source_id: str) -> dict:
        d = self.lib_dir / source_id
        if not d.is_dir():
            return {}
        return {int(p.stem[1:]): p.read_text(encoding="utf-8") for p in sorted(d.glob("p*.txt"))}

    def page_text(self, source_id: str, scan: int) -> str:
        return self.pages(source_id).get(scan, "")

    @staticmethod
    def printed_page(text: str) -> int | None:
        for line in text.splitlines()[:3]:
            m = PRINTED_PAGE.match(line) or PRINTED_PAGE_LOOSE.match(line)
            if m:
                return int(m.group(1))
        return None

    def cite(self, source_id: str, scan: int) -> tuple[str, str, int | None]:
        """(title, url, printed page) for one scanned page."""
        src = self.sources[source_id]
        page = self.printed_page(self.page_text(source_id, scan))
        where = f"s. {page}" if page else f"skan {scan}"
        if page and src["route"] == "djvu":
            where += f" (skan {scan})"
        title = f"{src['author']}, {src['title']} ({src['year']}), {where}"
        url = src["page_url"].format(scan=scan, scan0=scan - 1)
        return title, url, page

    def _hit(self, source_id, scan, reason, score, snippet="", scans=None) -> Hit:
        title, url, page = self.cite(source_id, scan)
        return Hit(source_id, scan, page, url, title, reason, score, snippet, scans or [scan])

    # ---- 1. Chmiel-style house sections ------------------------------------
    @lru_cache(maxsize=None)
    def house_sections(self, source_id: str) -> dict:
        """{street number: [scans]} from 'L. or. N' headings, in page order.
        A section runs from its heading page to the page holding the next one."""
        heads = []  # (scan, offset, number)
        for scan, text in self.pages(source_id).items():
            for m in HEADING.finditer(text):
                nums = [m.group(1)] + ([m.group(2)] if m.group(2) else [])
                heads.append((scan, m.start(), nums))
        heads.sort()
        out = {}
        for i, (scan, _, nums) in enumerate(heads):
            end = heads[i + 1][0] if i + 1 < len(heads) else scan
            scans = list(range(scan, max(scan, end) + 1))
            for n in nums:
                n = n.lower()
                # The first heading wins: later "L. or. 5" mentions are usually cross-references.
                if n not in out:
                    out[n] = scans
        return out

    def sources_for_street(self, street: str) -> list[str]:
        key = street_key(street)
        found = []
        for sid, s in self.sources.items():
            for st in (s.get("covers") or {}).get("streets", []):
                if street_key(st) == key:
                    found.append(sid)
        return found

    @staticmethod
    def covers_number(src: dict, number: str) -> bool:
        spec = (src.get("covers") or {}).get("numbers", "")
        m = re.match(r"(odd|even)\s+(\d+)-(\d+)", spec)
        n = re.match(r"\d+", number or "")
        if not m or not n:
            return True
        v = int(n.group())
        parity_ok = (v % 2 == 1) == (m.group(1) == "odd")
        return parity_ok and int(m.group(2)) <= v <= int(m.group(3))

    # ---- 2. old numbers ------------------------------------------------------
    def old_numbers(self, street: str, number: str) -> list[dict]:
        key = street_key(street)
        num = (number or "").lower()
        return [r for r in self.old_rows
                if r.get("street") and street_key(r["street"]) == key and r["number"] == num]

    def by_old_number(self, old_number: str, street: str | None = None) -> list[dict]:
        rows = [r for r in self.old_rows if r["old_number"] == str(old_number)]
        if street:
            key = street_key(street)
            rows = [r for r in rows if r.get("street") and street_key(r["street"]) == key]
        return rows

    # ---- 3. full text --------------------------------------------------------
    def search_text(self, phrase: str, sources: list[str] | None = None, limit: int = 30,
                    reason: str = "") -> list[Hit]:
        """Pages containing the phrase (folded, OCR-tolerant)."""
        needle = fold(phrase)
        if not needle:
            return []
        pat = re.compile(r"(?<![a-z0-9])" + re.escape(needle).replace(r"\ ", r"\s?") + r"(?![a-z0-9])")
        hits = []
        for sid in sources or self.available():
            for scan, text in self.pages(sid).items():
                f = fold(text)
                m = pat.search(f)
                if m:
                    a, b = max(0, m.start() - 120), m.end() + 120
                    hits.append(self._hit(sid, scan, reason or f"tekst: „{phrase}”", 1.0, f[a:b]))
                    if len(hits) >= limit:
                        return hits
        return hits

    def find_name(self, name: str, sources: list[str] | None = None, limit: int = 30) -> list[Hit]:
        """House name ('Pod Jaszczurką') or owner ('Romer'), anywhere."""
        return self.search_text(name, sources, limit, reason=f"nazwa: „{name}”")

    def find_address(self, street: str, number: str, limit: int = 40) -> list[Hit]:
        """Candidate pages for one address, best first."""
        number = (number or "").lower()
        hits: list[Hit] = []
        seen = set()

        def add(h: Hit):
            k = (h.source, h.scan)
            if k not in seen:
                seen.add(k)
                hits.append(h)

        # 1. house sections in street monographs
        for sid in self.sources_for_street(street):
            if not self.covers_number(self.sources[sid], number):
                continue
            scans = self.house_sections(sid).get(number)
            if scans:
                first = scans[0]
                add(self._hit(sid, first, f"rozdział domu L. or. {number}", 10.0,
                              fold(self.page_text(sid, first))[:240], scans))
                for s in scans[1:]:
                    add(self._hit(sid, s, f"rozdział domu L. or. {number} (cd.)", 9.0, scans=scans))

        # 2. old numbers -> owner list page, then pages naming the old number + street
        olds = self.old_numbers(street, number)
        for r in olds:
            if r["source"] in self.sources and (r["source"], r["scan"]) not in seen:
                add(self._hit(r["source"], r["scan"],
                              f"spis właścicieli 1884: {r['owner']}, lc. {r['old_number']}", 6.0))

        # 3. full-text: "<street> <number>" and "<street> l. <number>"
        words = [w for w in fold(street).split() if len(w) > 2]
        core = words[-1] if words else fold(street)
        stem = core[:-1] if len(core) > 5 else core  # 'florianska' ~ 'floryanska' handled below
        variants = {stem, stem.replace("ian", "yan")}  # stem covers declension: floriansk(a|iej)
        num_pat = re.escape(number)
        for sid in self.available():
            for scan, text in self.pages(sid).items():
                f = fold_flat(text)
                for v in variants:
                    m = re.search(re.escape(v) + r"\w{0,3}\.?\s*(?:l\.\s*(?:or\.\s*)?|nr\.?\s*|pod\s+l\.\s*)?"
                                  + num_pat + r"(?![0-9])", f)
                    if m:
                        a, b = max(0, m.start() - 100), m.end() + 140
                        add(self._hit(sid, scan, f"wzmianka: {street} {number}", 3.0, f[a:b]))
                        break
        hits.sort(key=lambda h: (-h.score, h.source, h.scan))
        return hits[:limit]

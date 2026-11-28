"""Build the old-number <-> modern-address index from Nowolecki's 1884
owner list ("Spis właścicieli domów … porządkiem alfabetycznym").

Each line of that list reads (OCR, cleaned here):
    Romer hr. Bronisław, ul. św. Anny 7 (199).
    Reich Ewa, ul. Skawińska 10 (38) 12 (39) 14 (44).
i.e. owner, street, orientation (street) number, and in brackets the
hypothecary/conscription number ("liczba hipoteczna", lc.). The lc. numbers
restart in each district (dzielnica), so an lc. number is only unique
together with its district.

Input:  source-data/raw/library/nowolecki-1884/p*.txt (scripts/sources/fetch_library.py)
        data/streets.json + data/streets/*.json (modern streets and numbers)
Output: data/research/old_numbers.json
        {about, stats{}, rows: [{street (modern OSM name or null), street_1884,
         number, old_number, owner, year, source, page_url, scan, page,
         confidence: high|medium|low, matched: bool}]}

Confidence:
  high    street resolves to a modern street, number exists there today, no OCR repair
  medium  street resolves only through a renamed-street alias, or the number is
          not in today's OSM numbers for that street, or digits were repaired
  low     street not resolved (row kept for search by old number / owner)
Low-confidence rows are meant to be checked by an agent against the page image.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from lib.address import StreetIndex, normalize  # noqa: E402

SRC_ID = "nowolecki-1884"
PAGES = ROOT / "source-data" / "raw" / "library" / SRC_ID
MANIFEST = ROOT / "data" / "research" / "library.json"
OUT = ROOT / "data" / "research" / "old_numbers.json"

# 1884 spellings -> modern OSM street names (only well-attested renames; the
# 1884 list itself already uses the then-new names, see its p. 11 table).
ALIASES = {
    "rynek glowny": "Rynek Główny", "rynek gl": "Rynek Główny", "maly rynek": "Mały Rynek",
    "plac ww swietych": "Plac Wszystkich Świętych", "plac wszystkich swietych": "Plac Wszystkich Świętych",
    "wazka": "Wąska", "wazka ul": "Wąska", "jakuba": "Świętego Jakuba", "szlak": "Szlak",
    "plac wolnica": "Plac Wolnica", "wolnica": "Plac Wolnica", "kupa": "Kupa",
    "plac szczepanski": "Plac Szczepański", "plac dominikanski": "Plac Dominikański",
    "plac mariacki": "Plac Mariacki", "plac na groblach": "Plac Na Groblach",
    "plac matejki": "Plac Jana Matejki", "plac maryacki": "Plac Mariacki",
    "floryanska": "Floriańska", "sw floryana": "Floriańska", "maryi magdaleny": "Plac Świętej Marii Magdaleny",
    "sw marka": "Świętego Marka", "sw jana": "Świętego Jana", "sw anny": "Świętej Anny",
    "sw tomasza": "Świętego Tomasza", "sw krzyza": "Świętego Krzyża", "sw gertrudy": "Świętej Gertrudy",
    "sw sebastyana": "Świętego Sebastiana", "sw wawrzynca": "Świętego Wawrzyńca",
    "sw agnieszki": "Świętej Agnieszki", "sw filipa": "Świętego Filipa",
    "sw idziego": "Świętego Idziego", "nad wisla": "Nadwiślańska",
    "szeroka": "Szeroka", "jozefa": "Józefa", "izaaka": "Izaaka", "ciemna": "Ciemna",
    "lobzowska": "Łobzowska", "sebastyana": "Świętego Sebastiana",
    "augustyanska": "Augustiańska", "dietlowska": "Józefa Dietla", "blichowa": "Blich",
    "jakoba": "Świętego Jakuba", "floryariska": "Floriańska", "kanonna": "Kanonicza",
}
# Common OCR slips inside numbers: letter -> digit
OCR_DIGITS = str.maketrans({"o": "0", "O": "0", "l": "1", "I": "1", "S": "5", "B": "8", ")": "3"})

STREET_START = re.compile(
    r"(?:^|,\s*)((?:ul\.?|Ul\.?|Plac|plac|Pl\.|Rynek|Mały [Rr]ynek|Podbrzezie|Przedmieście|"
    r"Kleparz|Wesoła|Na |Pod |Za |Smoleńsk|Stradom|Rybaki|Groble|Planty|Wolnica|Wawel)"
    r"[^,(]*?)\s+(\d\S{0,5}(?:\s+i\s+\S{1,5})?\s*\(.*)$")
PAIR = re.compile(r"(\S{1,5}(?:\s+i\s+\S{1,5})?)\s*\(\s*([0-9OolIS]{1,4}\s*[a-e]?(?:\s*/\s*\d{1,4})?)\s*\)")
PRINTED_PAGE = re.compile(r"^\s*[-—–_]*\s*(\d{1,3})\s*[-—–_]*\s*$")


def printed_page(text):
    for line in text.splitlines()[:3]:
        m = PRINTED_PAGE.match(line)
        if m:
            return int(m.group(1))
    return None


def entries_of(text):
    """Join wrapped lines; yield one string per owner entry."""
    buf = ""
    for line in text.splitlines():
        line = line.strip()
        if not line or PRINTED_PAGE.match(line):
            continue
        buf = (buf + " " + line).strip() if buf else line
        if re.search(r"\)\s*[.,;_]?\s*$", line) or line.endswith("."):
            yield buf
            buf = ""
    if buf:
        yield buf


def clean_number(raw):
    """'5o' -> ('50', True); '7' -> ('7', False); returns (None, _) if hopeless."""
    raw = raw.strip().strip(".,;:")
    repaired = False
    if not re.fullmatch(r"\d+[a-e]?", raw):
        fixed = raw.translate(OCR_DIGITS)
        fixed = re.sub(r"[^\da-e]", "", fixed)
        if not re.fullmatch(r"\d{1,3}[a-e]?", fixed):
            return None, False
        raw, repaired = fixed, True
    return raw, repaired


def street_candidates(street_text):
    s = re.sub(r"^(ul\.?|Ul\.?|ul ica|ulica|ica)\s+", "", street_text.strip()).strip(" .,")
    s = re.sub(r"\s+", " ", s)
    return s


def load_modern():
    streets = json.loads((ROOT / "data" / "streets.json").read_text(encoding="utf-8"))
    index = StreetIndex([s["name"] for s in streets])
    files = {s["name"]: s["file"] for s in streets}
    return index, files


_numbers_cache = {}


def modern_numbers(files, street):
    if street not in _numbers_cache:
        p = ROOT / "data" / "streets" / f"{files[street]}.json"
        nums = set()
        if p.exists():
            nums = set(json.loads(p.read_text(encoding="utf-8")).get("numbers", {}))
        _numbers_cache[street] = nums
    return _numbers_cache[street]


def resolve(index, files, street_1884):
    key = normalize(re.sub(r"[.,]", " ", street_1884))
    key = re.sub(r"\s+", " ", key).strip()
    alias = ALIASES.get(key)
    if alias and alias in files:
        return alias, normalize(alias) != key
    name = index.resolve(street_1884)
    if name:
        return name, False
    # OCR splits words ("Go łębia", "Szpi talna"): try without inner spaces
    joined = re.sub(r"(?<=[a-ząćęłńóśźż]) (?=[a-ząćęłńóśźż])", "", street_1884)
    if joined != street_1884:
        return resolve(index, files, joined)
    return None, False


def main():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    src = next(s for s in manifest["sources"] if s["id"] == SRC_ID)
    if not PAGES.exists():
        raise SystemExit(f"{PAGES} missing: run scripts/sources/fetch_library.py {SRC_ID}")
    index, files = load_modern()
    rows, unparsed = [], 0
    for path in sorted(PAGES.glob("p*.txt")):
        scan = int(path.stem[1:])
        text = path.read_text(encoding="utf-8")
        if text.count("(") < 8:  # not an owner-list page
            continue
        page = printed_page(text)
        for entry in entries_of(text):
            if "(" not in entry:
                continue
            m = STREET_START.search(entry)
            if not m:
                unparsed += 1
                continue
            owner = entry[:m.start()].strip(" ,.|I")
            street_1884 = street_candidates(m.group(1))
            pairs = PAIR.findall(m.group(2))
            if not pairs or not owner or len(owner) > 120:
                unparsed += 1
                continue
            street, via_alias = resolve(index, files, street_1884)
            for nums, old in pairs:
                old = re.sub(r"\s+", "", old).translate(OCR_DIGITS)
                for n_raw in re.split(r"\s+i\s+", nums):
                    number, repaired = clean_number(n_raw)
                    if number is None:
                        unparsed += 1
                        continue
                    exists = bool(street) and number in modern_numbers(files, street)
                    if not street:
                        conf = "low"
                    elif exists and not repaired and not via_alias:
                        conf = "high"
                    else:
                        conf = "medium"
                    rows.append({
                        "street": street, "street_1884": street_1884, "number": number,
                        "old_number": old, "owner": owner, "year": src["year"],
                        "source": SRC_ID, "scan": scan, "page": page,
                        "page_url": src["page_url"].format(scan=scan, scan0=scan - 1),
                        "confidence": conf, "matched": exists,
                    })
    # Deduplicate (an owner listed twice on wrapped lines etc.)
    seen, uniq = set(), []
    for r in rows:
        k = (r["street_1884"], r["number"], r["old_number"], r["owner"])
        if k not in seen:
            seen.add(k)
            uniq.append(r)
    rows = uniq
    addresses = {(r["street"], r["number"]) for r in rows if r["street"]}
    stats = {
        "rows": len(rows),
        "unparsed_fragments": unparsed,
        "street_resolved": sum(1 for r in rows if r["street"]),
        "matched_modern_address": sum(1 for r in rows if r["matched"]),
        "distinct_modern_addresses": len(addresses),
        "distinct_matched_addresses": len({(r["street"], r["number"]) for r in rows if r["matched"]}),
        "by_confidence": {c: sum(1 for r in rows if r["confidence"] == c) for c in ("high", "medium", "low")},
    }
    stats["match_rate"] = round(stats["matched_modern_address"] / max(1, len(rows)), 3)
    out = {
        "about": ("Old hypothecary/conscription numbers (lc.) and owners in 1884, from "
                  "A. Nowolecki, Nowy wykaz ulic… (1884), owner list; parsed from Polona OCR by "
                  "scripts/sources/parse_old_numbers.py. lc. numbers restart in each district. "
                  "OCR is imperfect: check low/medium rows against the page image (page_url). "
                  "Numbers are 1884 street numbers: some streets were renumbered later (e.g. the odd side "
                  "of Sławkowska after the 1912 demolitions; parts of Szeroka), so a 'matched' row can "
                  "point to a different house today - confirm with the old lc. number in the house history."),
        "stats": stats,
        "rows": rows,
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=0) + "\n", encoding="utf-8")
    print(json.dumps(stats, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

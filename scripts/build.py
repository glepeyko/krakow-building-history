"""Merge all sources into the files the website reads.

Run (after the fetch scripts in scripts/sources/ have filled source-data/raw/):
    python scripts/build.py

Inputs:
    source-data/Buildings_in_Krakow_EXCEL.xlsx   GEZ register (official)
    source-data/raw/osm_addresses.json           every address in Kraków (OSM)
    source-data/raw/osm_notable.json             memorials, plaques, monuments (OSM)
    source-data/raw/wikidata.json                Wikidata items with coordinates
    source-data/raw/wikidata_streets.json        street name origins, former names
    source-data/raw/osm_streets.json             OSM name:etymology / old_name tags
    source-data/raw/osm_districts.json           dzielnica boundaries (OSM)
    source-data/raw/osm_municipalities.json      neighbouring gminy (OSM)
    source-data/raw/nid_krakow.json              NID register of monuments (Kraków rows)
    source-data/raw/commons_images.json          photo thumbnails + author/licence
    data/research/ai_drafts.json                 AI-researched texts (labelled)

Outputs:
    data/streets.json            [{name, search, file, entries}] for the autocomplete
    data/streets/<file>.json     one file per street, loaded on demand
    reports/coverage.md          how much we know, per kind of fact
"""
from __future__ import annotations

import json
import math
import re
import shutil
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8")

from lib.address import StreetIndex, normalize, normalize_number, number_parts, split_street_number, street_key  # noqa: E402
from lib.geo import DistrictIndex  # noqa: E402
from sources import gez  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "source-data" / "raw"
DATA = ROOT / "data"
SHARDS = DATA / "streets"
REPORTS = ROOT / "reports"
RESEARCH = DATA / "research"

NEARBY_RADIUS_M = 150
NEARBY_MAX = 6
# When nothing notable is within NEARBY_RADIUS_M (outer districts), show the
# few closest places within this wider radius instead of an empty list.
NEARBY_FALLBACK_M = 600
NEARBY_FALLBACK_MAX = 3
WD_COORD_MATCH_M = 20

# Wikidata item types that are not a single building or monument.
WD_SKIP_TYPES = {
    "ulica", "przystanek tramwajowy", "przystanek autobusowy", "parafia",
    "wieś w Polsce", "część miasta", "osiedle", "dzielnica Krakowa", "plac",
    "aleja", "rondo", "skrzyżowanie", "część wsi", "kolonia wsi", "przysiółek",
    "sołectwo", "obszar chroniony", "szlak turystyczny", "linia kolejowa",
    "dzielnica", "jednostka pomocnicza gminy", "osiedle mieszkaniowe",
    "przedsiębiorstwo", "organizacja", "klub sportowy", "szkoła wyższa",
    "uczelnia", "wydział", "instytut naukowy", "stowarzyszenie",
}
WD_BUILDING_TYPES = {
    "kamienica", "dom", "budynek", "willa", "pałac", "kościół", "oficyna",
    "zabytek architektury", "budynek mieszkalny", "dwór", "klasztor", "synagoga",
    "kaplica", "hotel", "budynek hotelowy", "gmach", "kamienica czynszowa",
    "dworek", "budynek muzeum", "budynek szkolny", "teatr", "kino", "bank",
}


# ---------------------------------------------------------------- helpers
def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def dist_m(lat1, lon1, lat2, lon2):
    dx = (lon2 - lon1) * 111_320 * math.cos(math.radians((lat1 + lat2) / 2))
    dy = (lat2 - lat1) * 110_540
    return math.hypot(dx, dy)


class Grid:
    """Simple spatial hash, ~200 m cells, for 'what is near this point'."""

    CELL = 0.002

    def __init__(self):
        self.cells = defaultdict(list)

    def add(self, lat, lon, item):
        self.cells[(int(lat / self.CELL), int(lon / self.CELL))].append((lat, lon, item))

    def near(self, lat, lon, radius_m):
        r = int(radius_m / 140) + 1
        cy, cx = int(lat / self.CELL), int(lon / self.CELL)
        out = []
        for y in range(cy - r, cy + r + 1):
            for x in range(cx - r, cx + r + 1):
                for plat, plon, item in self.cells.get((y, x), ()):
                    d = dist_m(lat, lon, plat, plon)
                    if d <= radius_m:
                        out.append((d, item))
        out.sort(key=lambda t: t[0])
        return out


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", normalize(name)).strip("-") or "x"


def roman(n: int) -> str:
    vals = [(1000, "M"), (900, "CM"), (500, "D"), (400, "CD"), (100, "C"), (90, "XC"),
            (50, "L"), (40, "XL"), (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")]
    out = ""
    for v, s in vals:
        while n >= v:
            out += s
            n -= v
    return out


def wd_dating(inception: str, precision: int) -> str:
    m = re.match(r"^(-?)(\d{1,4})-", inception or "")
    if not m or m.group(1):
        return ""
    year = int(m.group(2))
    if precision >= 9:
        return str(year)
    if precision == 8:
        return f"lata {year // 10 * 10}."
    if precision == 7:
        century = year // 100 if year % 100 == 0 else year // 100 + 1
        return f"{roman(century)} w."
    return ""


def commons_file(image_url: str) -> str:
    if not image_url:
        return ""
    from urllib.parse import unquote
    return unquote(image_url.rsplit("/", 1)[-1])


RESIDENTIAL = {"kamienica", "dom", "budynek", "willa", "oficyna", "blok", "kamienice",
               "domy", "budynki", "mieszkalny", "czynszowa", "zabytek", "gmach", "dworek"}
GENERIC_WORDS = {"krakowie", "krakow", "dawny", "dawna", "obecnie", "przy", "ulicy", "wraz",
                 "oraz", "zespol", "obiekt", "architektury", "zabytkowy", "zabytkowa"}


def _stems(text: str) -> set:
    return {w[:5] for w in re.findall(r"[a-z]{4,}", normalize(text)) if w not in GENERIC_WORDS}


def compatible(gez_record, item) -> bool:
    """Does a Wikidata item plausibly describe the same object as a GEZ record?
    Guards against linking, e.g., a church to the power station next door."""
    gez_words = set(re.findall(r"[a-z]+", normalize(gez_record["type_and_name"])))
    wd_text = " ".join([item.get("label", "")] + item.get("types", []))
    wd_words = set(re.findall(r"[a-z]+", normalize(wd_text)))
    if gez_words & RESIDENTIAL and wd_words & RESIDENTIAL:
        return True
    return bool(_stems(gez_record["type_and_name"]) & _stems(wd_text))


def register_key(text: str) -> str:
    m = re.match(r"\s*(A-\d+(?:/M)?)", text or "")
    return m.group(1) if m else ""


# ---------------------------------------------------------------- loading
def load_osm():
    osm = load_json(RAW / "osm_addresses.json")
    for a in osm:
        a["_street"] = a.get("addr:street") or a.get("addr:place") or ""
        a["_number"] = normalize_number(a.get("addr:housenumber", ""))
    return osm


def parse_wd_address(item, index: StreetIndex):
    """Return (canonical street, number) for a Wikidata item, or (None, '')."""
    texts = []
    if item.get("address"):
        texts.append(re.split(r",\s*\d{2}-\d{3}", item["address"])[0])
    if item.get("street") and item.get("number"):
        texts.append(f'{item["street"]} {item["number"]}')
    m = re.search(r"\bprzy (?:ul\.|ulicy|al\.|alei|pl\.|placu)\s+(.+?)(?:\s+w Krakowie)?$", item.get("label", ""))
    if m:
        texts.append(m.group(1))
    for t in texts:
        t = re.sub(r"^(?:ul\.|al\.|pl\.|os\.)\s*", "", t.strip())
        street, number, _ = split_street_number(t, index)
        canonical = index.resolve(street)
        if canonical and number:
            return canonical, number
    return None, ""


# ---------------------------------------------------------------- street stories
def wiki_url(tag: str) -> str:
    """OSM wikipedia tag 'pl:Ulica X w Krakowie' -> article URL."""
    from urllib.parse import quote
    lang, _, title = tag.partition(":")
    if not title or lang != "pl":
        return ""
    return "https://pl.wikipedia.org/wiki/" + quote(title.replace(" ", "_"))


def street_label(label: str) -> str:
    return re.sub(r"\s+w Krakowie$", "", label or "").strip()


def load_street_stories(index: StreetIndex):
    """{canonical street: story} from Wikidata street items and OSM tags.
    A story holds facts only (named after, historical names, article link);
    the page writes the sentences, so no Wikipedia text is copied."""
    stats = Counter()
    wd_path, osm_path = RAW / "wikidata_streets.json", RAW / "osm_streets.json"
    if not wd_path.exists() or not osm_path.exists():
        print("! street stories skipped: run fetch_osm.py and fetch_wikidata_streets.py")
        return {}, stats
    wd = load_json(wd_path)
    patrons = wd["patrons"]
    items = {s["qid"]: s for s in wd["streets"]}
    stories = defaultdict(lambda: {"named_after": {}, "names": [], "old_names": [], "wikidata": "", "wikipedia": ""})

    def add_patron(story, qid, via):
        p = patrons.get(qid)
        if not p or not p.get("label"):
            return
        if qid in story["named_after"]:
            story["named_after"][qid]["via"] = sorted(set(story["named_after"][qid]["via"]) | {via})
            return
        years = ""
        if p.get("human") and p.get("birth") and p["birth"] > 0:
            years = f'{p["birth"]}–{p["death"]}' if p.get("death") else f'ur. {p["birth"]}'
        story["named_after"][qid] = {"wikidata": qid, "label": p["label"], "description": p.get("description", ""),
                                     "years": years, "wikipedia": p.get("wikipedia", ""),
                                     "person": bool(p.get("human")), "via": [via]}

    def add_item(story, item):
        if not story["wikidata"]:
            story["wikidata"] = item["qid"]
        if item.get("wikipedia") and not story["wikipedia"]:
            story["wikipedia"] = item["wikipedia"]
        for q in item["named_after"]:
            add_patron(story, q, "wikidata")
        for n in item["names"]:
            if n not in story["names"]:
                story["names"].append(n)

    linked = set()
    # 1. OSM street ways carry the strongest links: wikidata=<street item>.
    for o in load_json(osm_path):
        canonical = index.resolve(o["name"])
        if not canonical:
            continue
        story = stories[canonical]
        for q in o.get("wikidata", {}):
            if q in items:
                add_item(story, items[q])
                linked.add(q)
        for v in o.get("name:etymology:wikidata", {}):
            for q in v.split(";"):
                add_patron(story, q.strip(), "osm")
        for v in o.get("old_name", {}):
            for n in v.split(";"):
                n = n.strip()
                if n and normalize(n) != normalize(canonical) and n not in story["old_names"]:
                    story["old_names"].append(n)
        for v in o.get("wikipedia", {}):
            if not story["wikipedia"] and wiki_url(v):
                story["wikipedia"] = wiki_url(v)
    # 2. Remaining Wikidata street items, matched by name.
    for q, item in items.items():
        if q in linked:
            continue
        canonical = index.resolve(street_label(item["label"]))
        if canonical:
            add_item(stories[canonical], item)
            stats["wd_items_matched_by_name"] += 1
        else:
            stats["wd_items_unmatched"] += 1
    stats["wd_items_linked_from_osm"] = len(linked)

    out = {}
    for canonical, st in stories.items():
        names = sorted(st["names"], key=lambda n: (n["from"] is None, n["from"] or 0, n["to"] or 9999))
        # Only a name history says something; a single undated current name does not.
        if not any(n["from"] or n["to"] for n in names) and all(
                normalize(street_label(n["name"])).replace("ulica ", "") == normalize(canonical) for n in names):
            names = []
        # OSM old_name values already in the dated history add nothing.
        hist_keys = [street_key(n["name"]) for n in names]
        old_names = [o for o in st["old_names"]
                     if not any(street_key(o) <= k or k <= street_key(o) for k in hist_keys if k)]
        story = {k: v for k, v in {
            "named_after": list(st["named_after"].values()),
            "names": names,
            "old_names": old_names,
            "wikidata": st["wikidata"],
            "wikipedia": st["wikipedia"],
        }.items() if v}
        if story.get("named_after") or story.get("names") or story.get("old_names") or story.get("wikipedia"):
            out[canonical] = story
    return out, stats


# ---------------------------------------------------------------- districts
def load_districts():
    path = RAW / "osm_districts.json"
    if not path.exists():
        print("! districts skipped: run fetch_osm.py")
        return None, {}
    raw = load_json(path)
    by_name = {normalize(v): k for k, v in gez.DISTRICT_NAMES.items()}
    for d in raw:
        d["number"] = by_name.get(normalize(d["name"]))
        if d["number"] is None:
            print(f'! unknown district name in OSM: {d["name"]!r}')
    return DistrictIndex([d for d in raw if d["number"]]), {d["number"]: d for d in raw if d["number"]}


# ---------------------------------------------------------------- NID register
A_NUM = re.compile(r"A-\s*(\d+)\s*(/M)?")


# NID lists documents as "A-185 z 1931-06-25, 262 z 1968-03-26, I-4-9/48 z ..."
# and often omits the "A-" prefix of the Kraków register.
NID_DOC = re.compile(r"(?:^|,)\s*(?:A-\s*)?(\d+)\s*(/M)?\s+z\s+\d{4}")


def a_numbers(text: str) -> set:
    """All register numbers in a text: 'A- 185 25.06.1931; A-1431/M' -> {'A-185', 'A-1431/M'}."""
    return {f"A-{m.group(1)}{m.group(2) or ''}" for m in A_NUM.finditer(text or "")}


def nid_numbers(text: str) -> set:
    return a_numbers(text) | {f"A-{m.group(1)}{m.group(2) or ''}" for m in NID_DOC.finditer(text or "")}


NID_STYLE_SKIP = {"", "nieznany", "inny"}


def link_nid(entries, index: StreetIndex):
    """Attach NID register rows (official name, register entry, date, style,
    zabytek.pl link) to entries: by address (confirmed by register number or
    by type), else by a register number unique on both sides."""
    stats = Counter()
    path = RAW / "nid_krakow.json"
    if not path.exists():
        print("! NID register skipped: run scripts/sources/fetch_nid.py")
        return stats
    rows = load_json(path)["rows"]
    stats["rows"] = len(rows)
    by_key = defaultdict(list)
    by_anum = defaultdict(list)
    for e in entries:
        for p in number_parts(e["building_number"]):
            by_key[(e["street"], p)].append(e)
        for a in a_numbers(e.get("register_number", "")):
            by_anum[a].append(e)
    nid_by_anum = defaultdict(list)
    for r in rows:
        for a in nid_numbers(r["WYKAZ_DOKUMENTOW"]):
            nid_by_anum[a].append(r)

    links = {}  # entry id -> (rank, row, how)

    def offer(e, r, rank, how):
        cur = links.get(id(e))
        if cur is None or rank > cur[0]:
            links[id(e)] = (rank, r, how, e)

    for r in rows:
        anums = nid_numbers(r["WYKAZ_DOKUMENTOW"])
        street = index.resolve(r["ULICA"]) if r["ULICA"] else None
        parts = number_parts(r["NR_ADRESOWY"]) if r["NR_ADRESOWY"] else []
        cands = []
        if street:
            for p in parts:
                cands.extend(by_key.get((street, p), []))
            cands = list({id(c): c for c in cands}.values())
        if cands:
            confirmed = [c for c in cands if a_numbers(c.get("register_number", "")) & anums]
            typed = [c for c in cands if compatible(c, {"label": r["NAZWA"], "types": []})]
            if len(confirmed) == 1:
                offer(confirmed[0], r, 3, "address+register")
            elif len(cands) == 1 and (typed or not cands[0].get("register_number")):
                offer(cands[0], r, 2, "address")
            elif len(typed) == 1:
                offer(typed[0], r, 2, "address+type")
            else:
                stats["ambiguous_address"] += 1
            continue
        if street and parts:
            stats["address_not_in_entries"] += 1
            continue
        unique = [a for a in anums if len(by_anum.get(a, [])) == 1 and len(nid_by_anum[a]) == 1]
        if len(unique) == 1:
            offer(by_anum[unique[0]][0], r, 1, "register")
        else:
            stats["no_address_no_unique_register"] += 1

    for rank, r, how, e in links.values():
        stats[f"linked_by_{how}"] += 1
        url = r["LINK"] if r["LINK"].startswith("https://zabytek.pl/") else ""
        e["nid_name"] = r["NAZWA"]
        e["nid_register"] = r["WYKAZ_DOKUMENTOW"]
        e["nid_register_date"] = r["DATA_WPISU"]
        e["nid_chronology"] = r["CHRONOLOGIA"]
        if r["STYL_ARCHITEKTONICZNY"] not in NID_STYLE_SKIP:
            e["nid_style"] = r["STYL_ARCHITEKTONICZNY"]
        if url:
            e["nid_url"] = url
        e["nid_inspire_id"] = r["INSPIRE_ID"]
    stats["entries_linked"] = len(links)
    return stats


# ---------------------------------------------------------------- photos
def attach_photos(entries):
    """Medium Commons thumbnail + credit for entries with an image. Only
    photos with a known author and licence are shown (CC licences require
    the credit); the rest keep the plain Commons link."""
    path = RAW / "commons_images.json"
    if not path.exists():
        print("! photos skipped: run scripts/sources/fetch_commons.py")
        return 0
    meta = load_json(path)
    n = 0
    for e in entries:
        m = meta.get(e.get("image", ""))
        if m and m["thumb"].startswith("https://") and m["author"] and m["license"]:
            e["photo"] = {k: m[k] for k in ("thumb", "width", "height", "author", "license", "license_url", "page")}
            n += 1
    return n


# ---------------------------------------------------------------- corrections
def apply_corrections(records):
    """Owner-approved fixes to register data (data/research/corrections.json).
    The register's own text stays in address_raw; the entry records what
    changed and why, and the page says so."""
    path = RESEARCH / "corrections.json"
    if not path.exists():
        return
    by_id = {str(r["id"]): r for r in records}
    for c in load_json(path):
        r = by_id.get(str(c["entry_id"]))
        if not r or c["field"] != "building_number" or r["building_number"] != c["from"]:
            print(f"! correction not applied: {c}")
            continue
        r["building_number"] = c["to"]
        r["correction"] = {"field": c["field"], "from": c["from"], "to": c["to"],
                           "reason": c["reason"], "sources": c["sources"]}


def load_municipalities():
    """Gminy around Kraków, for addresses with a Kraków postcode that lie
    outside the city (the OSM import filters by postcode)."""
    path = RAW / "osm_municipalities.json"
    if not path.exists():
        print("! municipalities skipped: run fetch_osm.py")
        return None
    return DistrictIndex([m for m in load_json(path) if normalize(m["name"]) != "krakow"])


# ---------------------------------------------------------------- AI drafts
def load_ai_drafts():
    path = RESEARCH / "ai_drafts.json"
    if not path.exists():
        return {}
    drafts = {}
    for d in load_json(path):
        # "verified" = the owner approved the text; it is then shown without
        # the AI label (sources stay visible).
        if d.get("status") not in ("ai_draft_unverified", "verified") or not d.get("text") or not d.get("sources"):
            continue
        drafts[str(d["entry_id"])] = d
    return drafts


# ---------------------------------------------------------------- build
def main():
    osm = load_osm()
    wd = load_json(RAW / "wikidata.json")
    notable = load_json(RAW / "osm_notable.json")

    street_names = sorted({a["_street"] for a in osm if a["_street"]})
    index = StreetIndex(street_names)
    records, gez_stats = gez.load(index)
    # The GEZ sheet reuses some ids (52 ids on 104 rows). The page looks
    # entries up by id, so later duplicates get a suffix: "1939" -> "1939-2".
    seen_ids = Counter()
    for r in records:
        seen_ids[str(r["id"])] += 1
        if seen_ids[str(r["id"])] > 1:
            r["id"] = f'{r["id"]}-{seen_ids[str(r["id"])]}'
            gez_stats["duplicate_ids_renamed"] = gez_stats.get("duplicate_ids_renamed", 0) + 1
    apply_corrections(records)

    # OSM address lookup: (street, number) -> osm record
    osm_by_key = {}
    for a in osm:
        if a["_street"] and a["_number"]:
            for p in number_parts(a["_number"]) or [a["_number"]]:
                osm_by_key.setdefault((a["_street"], p), a)
    osm_grid = Grid()
    for a in osm:
        osm_grid.add(a["lat"], a["lon"], a)

    # ---- GEZ -> coordinates via OSM address
    gez_by_key = defaultdict(list)
    for r in records:
        r["_parts"] = number_parts(r["building_number"])
        for p in r["_parts"]:
            gez_by_key[(r["street"], p)].append(r)
            o = osm_by_key.get((r["street"], p))
            if o and "lat" not in r:
                r["lat"], r["lon"], r["osm"] = o["lat"], o["lon"], o["osm"]

    # ---- Wikidata -> address (by text, then by coordinates)
    gez_by_register = defaultdict(list)
    for r in records:
        k = register_key(r["register_number"])
        if k:
            gez_by_register[k].append(r)
    wd_by_register = defaultdict(list)
    for item in wd:
        k = register_key(item.get("nid", ""))
        if k:
            wd_by_register[k].append(item)

    wd_stats = Counter()
    wd_entries = []
    for item in wd:
        types = set(item["types"])
        if types and types <= WD_SKIP_TYPES:
            item["_skip"] = True
            continue
        street, number = parse_wd_address(item, index)
        how = "address"
        if not street and types & WD_BUILDING_TYPES:
            hits = osm_grid.near(item["lat"], item["lon"], WD_COORD_MATCH_M)
            hits = [h for h in hits if h[1]["_street"] and h[1]["_number"]]
            if hits:
                street, number, how = hits[0][1]["_street"], hits[0][1]["_number"], "coords"
        item["_street"], item["_number"] = street, number

        # Link to GEZ: by register number (unique on both sides) or by address.
        target = None
        rk = register_key(item.get("nid", ""))
        if (rk and len(gez_by_register.get(rk, [])) == 1 and len(wd_by_register[rk]) == 1
                and compatible(gez_by_register[rk][0], item)):
            target = gez_by_register[rk][0]
            how = "register"
        elif street and number:
            cands = []
            for p in number_parts(number):
                cands.extend(gez_by_key.get((street, p), []))
            cands = [c for c in {id(c): c for c in cands}.values() if compatible(c, item)]
            if len(cands) > 1:
                # Several plausible records at one address (e.g. a mikveh and a
                # kamienica): prefer the single one that shares a real word with
                # the item's name/type, not just "residential".
                wd_text = " ".join([item.get("label", "")] + item.get("types", []))
                named = [c for c in cands if _stems(c["type_and_name"]) & _stems(wd_text)]
                if len(named) == 1:
                    cands = named
            if len(cands) == 1:
                target = cands[0]
            elif cands:
                wd_stats["ambiguous"] += 1
        if target is not None:
            # Several items can describe one building (e.g. "Hotel Pod Różą"
            # and the kamienica it occupies). Collect them; pick one below.
            target.setdefault("_wd_items", []).append((item, how))
            item["_gez"] = target
            continue
        if street and number and (item.get("wikipedia") or types & WD_BUILDING_TYPES):
            wd_entries.append(wd_entry(item, street, number))
            wd_stats[f"new_entry_by_{how}"] += 1

    def wd_rank(pair):
        item = pair[0]
        return (bool(item.get("wikipedia")), bool(proper_name(item.get("label", ""))),
                bool(item.get("image")), bool(item.get("nid")))

    for r in records:
        pairs = r.pop("_wd_items", None)
        if not pairs:
            continue
        pairs.sort(key=wd_rank, reverse=True)
        best, how = pairs[0]
        wd_stats[f"linked_by_{how}"] += 1
        enrich_from_wd(r, best)
        for other, _ in pairs[1:]:  # fill gaps from the other items
            if other.get("wikipedia") and "wikipedia" not in r:
                r["wikipedia"] = other["wikipedia"]
            if other.get("image") and "image" not in r:
                r["image"] = commons_file(other["image"])
        if "lat" not in r:
            r["lat"], r["lon"] = best["lat"], best["lon"]

    # ---- Points of interest for "nearby"
    pois, poi_grid = [], Grid()

    def add_poi(p):
        p["pid"] = len(pois)
        pois.append(p)
        poi_grid.add(p["lat"], p["lon"], p)

    for r in records:
        if "lat" in r:
            add_poi({"lat": r["lat"], "lon": r["lon"], "kind": "gez",
                     "title": r.get("name") or r["type_and_name"] or "obiekt zabytkowy",
                     "street": r["street"], "number": r["building_number"],
                     "dating": r["dating"], "wikipedia": r.get("wikipedia", ""),
                     "self": {(r["street"], p) for p in r["_parts"]}})
    for e in wd_entries:
        add_poi({"lat": e["lat"], "lon": e["lon"], "kind": "wikidata", "title": e["type_and_name"],
                 "street": e["street"], "number": e["building_number"], "dating": e["dating"],
                 "wikipedia": e.get("wikipedia", ""),
                 "self": {(e["street"], p) for p in number_parts(e["building_number"])}})
    for item in wd:
        if item.get("_skip") or item.get("_gez") or item.get("_street"):
            continue
        if not item.get("wikipedia") or not item.get("label"):
            continue
        add_poi({"lat": item["lat"], "lon": item["lon"], "kind": "wikidata", "title": item["label"],
                 "street": "", "number": "", "dating": wd_dating(item["inception"], item["inception_precision"]),
                 "wikipedia": item["wikipedia"], "self": set()})
    for n in notable:
        title = n.get("name") or (n.get("inscription", "")[:140] + ("…" if len(n.get("inscription", "")) > 140 else ""))
        kind = {"memorial": "pamiątka", "monument": "pomnik", "wayside_shrine": "kapliczka",
                "wayside_cross": "krzyż przydrożny"}.get(n.get("historic"), "obiekt historyczny")
        if n.get("memorial") == "plaque":
            kind = "tablica pamiątkowa"
        add_poi({"lat": n["lat"], "lon": n["lon"], "kind": "osm", "title": title, "label": kind,
                 "street": "", "number": "", "dating": "", "wikipedia": "", "self": set()})

    # ---- Assemble per-street shards
    streets = defaultdict(lambda: {"numbers": {}, "entries": []})

    def number_slot(street, num):
        return streets[street]["numbers"].setdefault(num, {})

    # Building outlines first: their position and tags describe the building.
    # A bare point with a name/start_date is usually a shop or company at that
    # address, so its tags are not used as building facts.
    for a in sorted(osm, key=lambda a: 0 if a.get("building") else 1):
        if not (a["_street"] and a["_number"]):
            continue
        slot = number_slot(a["_street"], a["_number"])
        if "lat" not in slot:
            slot.update({"lat": a["lat"], "lon": a["lon"], "osm": a["osm"]})
        if not a.get("building"):
            continue
        for src, dst in (("building", "building"), ("building:levels", "levels"),
                         ("start_date", "start_date"), ("architect", "architect"), ("name", "name")):
            if a.get(src) and a.get(src) != "yes" and dst not in slot:
                slot[dst] = a[src]

    all_entries = records + wd_entries
    nid_stats = link_nid(all_entries, index)
    photo_count = attach_photos(all_entries)

    # The register's old number keeps its own page (whatever we know about
    # it) plus a suggestion to look at the corrected number. No redirect.
    for r in records:
        c = r.get("correction")
        if c and c["field"] == "building_number":
            for p in number_parts(c["from"]):
                streets[r["street"]]["numbers"].setdefault(p, {})["moved_to"] = c["to"]

    # ---- AI drafts (labelled, unverified) merged into their entries
    drafts = load_ai_drafts()
    draft_stats = Counter()
    for e in all_entries:
        d = drafts.get(str(e["id"]))
        if d:
            e["ai_description"] = d["text"]
            e["ai_sources"] = d["sources"]
            e["ai_researched_at"] = d.get("researched_at", "")
            e["status"] = d["status"]
            if d["status"] == "verified":
                e["ai_approved"] = True
            if d.get("wikipedia") and not e.get("wikipedia"):
                e["wikipedia"] = d["wikipedia"]
            draft_stats["merged"] += 1
    draft_stats["unmatched"] = len(drafts) - draft_stats["merged"]

    # ---- District for every entry without one (Wikidata-only entries,
    # GEZ rows with an empty district column); compare where GEZ has one.
    district_index, districts_by_number = load_districts()
    district_stats = Counter()
    if district_index:
        for e in all_entries:
            if "lat" not in e:
                continue
            d = district_index.find(e["lat"], e["lon"])
            if not d:
                continue
            if e.get("district_number"):
                district_stats["gez_agree" if e["district_number"] == d["number"] else "gez_disagree"] += 1
            else:
                e["district_number"], e["district_name"] = d["number"], gez.DISTRICT_NAMES[d["number"]]
                e["district_source"] = "OpenStreetMap"
                district_stats["entries_filled"] += 1
    for e in all_entries:
        st = streets[e["street"]]
        st["entries"].append(e)
        for p in number_parts(e["building_number"]):
            slot = number_slot(e["street"], p)
            slot.setdefault("entries", []).append(e["id"])
            if "lat" not in slot and "lat" in e:
                slot["lat"], slot["lon"] = e["lat"], e["lon"]

    if SHARDS.exists():
        shutil.rmtree(SHARDS)
    SHARDS.mkdir(parents=True)
    street_list, used_slugs = [], set()
    nearby_counts = Counter()
    stories, story_stats = load_street_stories(index)
    municipality_index = load_municipalities()
    for name, st in sorted(streets.items()):
        if not name:
            continue
        slug = slugify(name)
        street_districts = Counter()
        street_munis = Counter()
        if district_index:
            for slot in st["numbers"].values():
                if "lat" in slot:
                    d = district_index.find(slot["lat"], slot["lon"])
                    if d:
                        slot["district"] = d["number"]
                        street_districts[d["number"]] += 1
                        district_stats["numbers_with_district"] += 1
                    else:
                        district_stats["numbers_outside"] += 1
                        m = municipality_index.find(slot["lat"], slot["lon"]) if municipality_index else None
                        if m:
                            slot["municipality"] = m["name"]
                            street_munis[m["name"]] += 1
                            district_stats["outside_with_municipality"] += 1
        while slug in used_slugs:
            slug += "-2"
        used_slugs.add(slug)

        shard_pois = {}
        for num, slot in st["numbers"].items():
            if "lat" not in slot:
                continue
            near, seen = [], set()
            found = poi_grid.near(slot["lat"], slot["lon"], NEARBY_RADIUS_M)
            limit = NEARBY_MAX
            if not any(not ((name, num) in p["self"] or any((name, q) in p["self"] for q in number_parts(num)))
                       for _, p in found):
                found = poi_grid.near(slot["lat"], slot["lon"], NEARBY_FALLBACK_M)
                limit = NEARBY_FALLBACK_MAX
            for d, p in found:
                if (name, num) in p["self"] or any((name, q) in p["self"] for q in number_parts(num)):
                    continue
                # Two GEZ rows for one address (e.g. a house and its annex with
                # the same title) would otherwise show as identical lines.
                key = (normalize(p["title"]), p["street"], p["number"])
                if key in seen:
                    continue
                seen.add(key)
                near.append([p["pid"], round(d)])
                shard_pois[p["pid"]] = p
                if len(near) >= limit:
                    break
            if near:
                slot["nearby"] = near
            if near and limit == NEARBY_FALLBACK_MAX:
                nearby_counts["with_fallback"] += 1
            else:
                nearby_counts["with_nearby" if near else "without_nearby"] += 1

        story = dict(stories.get(name, {}))
        if street_districts:
            story["districts"] = [n for n, _ in street_districts.most_common()]
        if street_munis:
            story["municipalities"] = [n for n, _ in street_munis.most_common()]
        out = {
            "name": name,
            "search": normalize(name),
            "story": story,
            "districts": {str(n): gez.DISTRICT_NAMES[n] for n in street_districts},
            "entries": [public_entry(e) for e in st["entries"]],
            "numbers": st["numbers"],
            "pois": {str(pid): {k: v for k, v in p.items() if k not in ("self", "pid") and v != ""}
                     for pid, p in shard_pois.items()},
        }
        (SHARDS / f"{slug}.json").write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        street_list.append({"name": name, "search": normalize(name), "file": slug, "entries": len(st["entries"])})

    (DATA / "streets.json").write_text(json.dumps(street_list, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    old = DATA / "buildings.json"
    if old.exists():
        old.unlink()

    extra = {"photo_count": photo_count, "nid_stats": nid_stats, "stories": stories, "story_stats": story_stats, "district_stats": district_stats,
             "draft_stats": draft_stats, "street_list": street_list}
    write_report(records, wd_entries, osm, wd, wd_stats, gez_stats, street_list, nearby_counts, streets, extra)


def enrich_from_wd(r, item):
    r["wikidata"] = item["qid"]
    if item.get("wikipedia"):
        r["wikipedia"] = item["wikipedia"]
    if item.get("image"):
        r["image"] = commons_file(item["image"])
    label = item.get("label", "")
    # A real proper name ("Kamienica Pod Jaszczurką"), not "budynek przy ul. X".
    name = proper_name(label)
    if name:
        r["name"] = name
    if item.get("styles"):
        r["styles"] = item["styles"]
    if item.get("description"):
        r["wd_description"] = item["description"]
    if not r["author"] and item.get("architects"):
        r["author_wikidata"] = ", ".join(item["architects"])


ROMAN = re.compile(r"^[IVXL]+(/[IVXL]+)?$")


def proper_name(label: str) -> str:
    """Return the label if it is a real name ("Kamienica Pod Jaszczurką",
    "Dom Erazma Barącza"), else ''. Rejects labels that only repeat an
    address or describe the type ("Sławkowska 30", "Kamienica z oficyną",
    "Kamienica, XV")."""
    if not label or re.search(r"\d", label):
        return ""
    name = re.sub(r"\s+w Krakowie\b.*$", "", label).strip()
    name = re.sub(r"\s*\(.*?\)\s*$", "", name).strip()
    words = re.split(r"[\s,]+", name)
    later = [w.strip("\"„”'") for w in words[1:]]
    if any(ROMAN.match(w) for w in later):
        return ""
    if any(w[:1].isupper() for w in later) or "„" in name or '"' in name:
        return name
    return ""


def wd_entry(item, street, number):
    e = {
        "id": f'wd-{item["qid"]}',
        "street": street,
        "street_search": normalize(street),
        "building_number": number,
        "address_raw": f"{street} {number}",
        "alt_address": "",
        "district_number": None,
        "district_name": "",
        "type_and_name": re.sub(r"\s+w Krakowie$", "", item["label"]) or ", ".join(item["types"]),
        "dating": wd_dating(item["inception"], item["inception_precision"]),
        "author": ", ".join(item["architects"]),
        "register_number": item.get("nid", ""),
        "source": "Wikidata",
        "status": "verified",
        "lat": item["lat"], "lon": item["lon"],
    }
    enrich_from_wd(e, item)
    e.pop("name", None)
    e.pop("author_wikidata", None)
    return e


def public_entry(e):
    return {k: v for k, v in e.items() if not k.startswith("_") and v not in ("", None, [])
            or k in ("id", "street", "building_number", "type_and_name")}


def pct(a, b):
    return f"{(100 * a / b):.1f}%" if b else "–"


def write_report(records, wd_entries, osm, wd, wd_stats, gez_stats, street_list, nearby_counts, streets, extra):
    REPORTS.mkdir(exist_ok=True)
    n = len(records)
    c = lambda f: sum(1 for r in records if f(r))
    numbers_total = sum(len(s["numbers"]) for s in streets.values())
    numbers_with_entry = sum(1 for s in streets.values() for v in s["numbers"].values() if v.get("entries"))
    numbers_with_any = sum(1 for s in streets.values() for v in s["numbers"].values()
                           if v.get("entries") or v.get("nearby") or v.get("start_date") or v.get("name"))
    ds = extra["district_stats"]
    stories = extra["stories"]
    numbers_with_any_story = sum(1 for name, s in streets.items() for v in s["numbers"].values()
                                 if v.get("entries") or v.get("nearby") or v.get("start_date") or v.get("name")
                                 or name in stories)
    story_streets = [s for s in street_list if s["name"] in stories]
    sc = lambda k: sum(1 for s in story_streets if stories[s["name"]].get(k))
    numbers_story = sum(len(s["numbers"]) for name, s in streets.items() if name in stories)
    ai_ids = {str(e["id"]) for e in records + wd_entries if e.get("ai_description")}
    numbers_ai = sum(1 for s in streets.values() for v in s["numbers"].values()
                     if any(str(i) in ai_ids for i in v.get("entries", [])))
    lines = [
        f"# Coverage report — {date.today().isoformat()}",
        "",
        "Generated by `scripts/build.py`. Compare with the previous version in git",
        "to see what an iteration changed.",
        "",
        "## Addresses (what a visitor can search)",
        "",
        "| Measure | Count | Share |",
        "|---|---:|---:|",
        f"| Streets in autocomplete | {len(street_list)} | |",
        f"| Searchable addresses (street + number) | {numbers_total} | 100% |",
        f"| … with a building entry (GEZ or Wikidata) | {numbers_with_entry} | {pct(numbers_with_entry, numbers_total)} |",
        f"| … with at least something to show (entry, nearby place, OSM fact) | {numbers_with_any} | {pct(numbers_with_any, numbers_total)} |",
        f"| … with something to show incl. the street story (district not counted) | {numbers_with_any_story} | {pct(numbers_with_any_story, numbers_total)} |",
        f"| … with notable places within {NEARBY_RADIUS_M} m | {nearby_counts['with_nearby']} | {pct(nearby_counts['with_nearby'], numbers_total)} |",
        f"| … with none within {NEARBY_RADIUS_M} m but some within {NEARBY_FALLBACK_M} m (shown instead) | {nearby_counts['with_fallback']} | {pct(nearby_counts['with_fallback'], numbers_total)} |",
        f"| … with a district (dzielnica) | {ds['numbers_with_district']} | {pct(ds['numbers_with_district'], numbers_total)} |",
        f"| … on a street with a street story (\"O ulicy\") | {numbers_story} | {pct(numbers_story, numbers_total)} |",
        f"| … with an AI-drafted description (unverified) | {numbers_ai} | {pct(numbers_ai, numbers_total)} |",
        "",
        "## Streets (\"O ulicy\")",
        "",
        "| Measure | Streets | Share |",
        "|---|---:|---:|",
        f"| Streets with any street story | {len(story_streets)} | {pct(len(story_streets), len(street_list))} |",
        f"| … named after a person/place/event (Wikidata P138 or OSM name:etymology) | {sc('named_after')} | {pct(sc('named_after'), len(street_list))} |",
        f"| … with dated name history (Wikidata) | {sc('names')} | {pct(sc('names'), len(street_list))} |",
        f"| … with a former name (OSM old_name) | {sc('old_names')} | {pct(sc('old_names'), len(street_list))} |",
        f"| … with a Wikipedia article about the street | {sc('wikipedia')} | {pct(sc('wikipedia'), len(street_list))} |",
        "",
        "Street items from Wikidata: " + ", ".join(f"{k} {v}" for k, v in sorted(extra["story_stats"].items())) + ".",
        "",
        "## GEZ register records",
        "",
        f"Excel rows: {gez_stats['rows']}, cross-reference rows skipped: {gez_stats['cross_refs']}, "
        f"duplicate ids renamed (\"<id>-2\"): {gez_stats.get('duplicate_ids_renamed', 0)}.",
        "",
        "| Field | Records | Share |",
        "|---|---:|---:|",
        f"| Total | {n} | 100% |",
        f"| Street matched to an OSM street | {c(lambda r: r['_street_resolved'])} | {pct(c(lambda r: r['_street_resolved']), n)} |",
        f"| Building number parsed | {c(lambda r: r['building_number'])} | {pct(c(lambda r: r['building_number']), n)} |",
        f"| Coordinates | {c(lambda r: 'lat' in r)} | {pct(c(lambda r: 'lat' in r), n)} |",
        f"| Dating | {c(lambda r: r['dating'])} | {pct(c(lambda r: r['dating']), n)} |",
        f"| Architect (GEZ) | {c(lambda r: r['author'])} | {pct(c(lambda r: r['author']), n)} |",
        f"| Architect (from Wikidata, GEZ empty) | {c(lambda r: r.get('author_wikidata'))} | {pct(c(lambda r: r.get('author_wikidata')), n)} |",
        f"| Linked to Wikidata | {c(lambda r: r.get('wikidata'))} | {pct(c(lambda r: r.get('wikidata')), n)} |",
        f"| Proper name (e.g. \"Kamienica Pod Jaszczurką\") | {c(lambda r: r.get('name'))} | {pct(c(lambda r: r.get('name')), n)} |",
        f"| Wikipedia article | {c(lambda r: r.get('wikipedia'))} | {pct(c(lambda r: r.get('wikipedia')), n)} |",
        f"| Photo (Wikimedia Commons) | {c(lambda r: r.get('image'))} | {pct(c(lambda r: r.get('image')), n)} |",
        f"| … shown on the page (author + licence known) | {c(lambda r: r.get('photo'))} | {pct(c(lambda r: r.get('photo')), n)} |",
        f"| Linked to the NID register (official name, register date, zabytek.pl) | {c(lambda r: r.get('nid_name'))} | {pct(c(lambda r: r.get('nid_name')), n)} |",
        f"| AI-drafted description (unverified, labelled) | {c(lambda r: r.get('ai_description'))} | {pct(c(lambda r: r.get('ai_description')), n)} |",
        f"| … of which approved by the owner (no AI label) | {c(lambda r: r.get('ai_approved'))} | {pct(c(lambda r: r.get('ai_approved')), n)} |",
        "",
        f"District check (GEZ district column vs. OSM boundary, records with coordinates): "
        f"agree {ds['gez_agree']}, disagree {ds['gez_disagree']}. "
        f"Entries that got their district from OSM: {ds['entries_filled']}. "
        f"Addresses outside every district polygon: {ds['numbers_outside']}, "
        f"of which in a neighbouring gmina: {ds['outside_with_municipality']} (named on the page).",
        "",
        "## Other sources",
        "",
        f"- OSM address points in Kraków: {len(osm)}",
        f"- Wikidata items with coordinates in the Kraków area: {len(wd)}",
        f"- Wikidata → GEZ links: " + ", ".join(f"{k} {v}" for k, v in sorted(wd_stats.items()) if k.startswith("linked")),
        f"- New building entries from Wikidata (not in GEZ): {len(wd_entries)}",
        f"- NID register (dane.gov.pl): " + ", ".join(f"{k} {v}" for k, v in sorted(extra["nid_stats"].items())),
        "",
    ]
    (REPORTS / "coverage.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()

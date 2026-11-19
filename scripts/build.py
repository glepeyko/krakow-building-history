"""Merge all sources into the files the website reads.

Run (after the fetch scripts in scripts/sources/ have filled source-data/raw/):
    python scripts/build.py

Inputs:
    source-data/Buildings_in_Krakow_EXCEL.xlsx   GEZ register (official)
    source-data/raw/osm_addresses.json           every address in Kraków (OSM)
    source-data/raw/osm_notable.json             memorials, plaques, monuments (OSM)
    source-data/raw/wikidata.json                Wikidata items with coordinates

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

from lib.address import StreetIndex, normalize, normalize_number, number_parts, split_street_number  # noqa: E402
from sources import gez  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "source-data" / "raw"
DATA = ROOT / "data"
SHARDS = DATA / "streets"
REPORTS = ROOT / "reports"

NEARBY_RADIUS_M = 150
NEARBY_MAX = 6
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


# ---------------------------------------------------------------- build
def main():
    osm = load_osm()
    wd = load_json(RAW / "wikidata.json")
    notable = load_json(RAW / "osm_notable.json")

    street_names = sorted({a["_street"] for a in osm if a["_street"]})
    index = StreetIndex(street_names)
    records, gez_stats = gez.load(index)

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
    for name, st in sorted(streets.items()):
        if not name:
            continue
        slug = slugify(name)
        while slug in used_slugs:
            slug += "-2"
        used_slugs.add(slug)

        shard_pois = {}
        for num, slot in st["numbers"].items():
            if "lat" not in slot:
                continue
            near = []
            for d, p in poi_grid.near(slot["lat"], slot["lon"], NEARBY_RADIUS_M):
                if (name, num) in p["self"] or any((name, q) in p["self"] for q in number_parts(num)):
                    continue
                near.append([p["pid"], round(d)])
                shard_pois[p["pid"]] = p
                if len(near) >= NEARBY_MAX:
                    break
            if near:
                slot["nearby"] = near
            nearby_counts["with_nearby" if near else "without_nearby"] += 1

        out = {
            "name": name,
            "search": normalize(name),
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

    write_report(records, wd_entries, osm, wd, wd_stats, gez_stats, street_list, nearby_counts, streets)


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


def write_report(records, wd_entries, osm, wd, wd_stats, gez_stats, street_list, nearby_counts, streets):
    REPORTS.mkdir(exist_ok=True)
    n = len(records)
    c = lambda f: sum(1 for r in records if f(r))
    numbers_total = sum(len(s["numbers"]) for s in streets.values())
    numbers_with_entry = sum(1 for s in streets.values() for v in s["numbers"].values() if v.get("entries"))
    numbers_with_any = sum(1 for s in streets.values() for v in s["numbers"].values()
                           if v.get("entries") or v.get("nearby") or v.get("start_date") or v.get("name"))
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
        f"| … with notable places within {NEARBY_RADIUS_M} m | {nearby_counts['with_nearby']} | {pct(nearby_counts['with_nearby'], numbers_total)} |",
        "",
        "## GEZ register records",
        "",
        f"Excel rows: {gez_stats['rows']}, cross-reference rows skipped: {gez_stats['cross_refs']}.",
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
        "",
        "## Other sources",
        "",
        f"- OSM address points in Kraków: {len(osm)}",
        f"- Wikidata items with coordinates in the Kraków area: {len(wd)}",
        f"- Wikidata → GEZ links: " + ", ".join(f"{k} {v}" for k, v in sorted(wd_stats.items()) if k.startswith("linked")),
        f"- New building entries from Wikidata (not in GEZ): {len(wd_entries)}",
        "",
    ]
    (REPORTS / "coverage.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()

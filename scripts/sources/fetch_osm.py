"""Extract every address point and addressed building in Kraków from OpenStreetMap.

Input:  the Małopolska extract (downloaded if missing) from Geofabrik, or
        from the openstreetmap.fr mirror if Geofabrik is unreachable.
Output: source-data/raw/osm_addresses.json, osm_notable.json,
        osm_streets.json (name-origin tags of streets),
        osm_districts.json (dzielnica boundaries, admin_level=9),
        osm_municipalities.json (neighbouring gminy, admin_level=7)

The public Overpass API often times out for a whole-city query, so we parse
the regional extract locally with pyosmium. An element counts as "in Kraków"
when it is inside the city bounding box AND has addr:city=Kraków or a
Kraków postcode (30-xxx / 31-xxx).

OSM data is (c) OpenStreetMap contributors, ODbL - the site must credit it.
"""
import json
import sys
from pathlib import Path

import osmium
import requests

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "source-data" / "raw"
PBF = RAW / "malopolskie-latest.osm.pbf"
PBF_URLS = [
    "https://download.geofabrik.de/europe/poland/malopolskie-latest.osm.pbf",
    # Mirror of the same regional extract, used when Geofabrik is unreachable.
    "https://download.openstreetmap.fr/extracts/europe/poland/malopolskie-latest.osm.pbf",
]
OUT = RAW / "osm_addresses.json"
BBOX = (19.79, 49.96, 20.22, 50.13)  # lon_min, lat_min, lon_max, lat_max

KEEP = ("addr:street", "addr:place", "addr:housenumber", "addr:postcode", "addr:city",
        "building", "building:levels", "start_date", "construction_date",
        "architect", "name", "heritage", "ref:gez", "wikidata", "wikipedia",
        "historic", "amenity", "tourism")

# Notable non-address features (plaques, memorials, monuments) for "nearby" facts.
NOTABLE_HISTORIC = {"memorial", "monument", "wayside_shrine", "wayside_cross",
                    "building", "castle", "church", "city_gate", "fort", "ruins", "tomb"}


def in_krakow(tags, lat, lon):
    if not (BBOX[0] <= lon <= BBOX[2] and BBOX[1] <= lat <= BBOX[3]):
        return False
    city = tags.get("addr:city", "")
    pc = tags.get("addr:postcode", "")
    return city == "Kraków" or pc.startswith(("30-", "31-"))


# Street-level tags used for the "O ulicy" block (street name origin).
STREET_TAGS = ("name:etymology:wikidata", "name:etymology", "old_name", "wikidata", "wikipedia")


class Handler(osmium.SimpleHandler):
    def __init__(self):
        super().__init__()
        self.addresses = []
        self.notable = []
        self.streets = {}

    def _street(self, w):
        """Collect name-origin tags of named streets (highway ways) in the bbox."""
        name = w.tags.get("name")
        if not name:
            return
        found = {k: w.tags[k] for k in STREET_TAGS if k in w.tags}
        if not found:
            return
        nd = next((n for n in w.nodes if n.location.valid()), None)
        if nd is None or not (BBOX[0] <= nd.lon <= BBOX[2] and BBOX[1] <= nd.lat <= BBOX[3]):
            return
        s = self.streets.setdefault(name, {"name": name, "ways": 0})
        s["ways"] += 1
        for k, v in found.items():
            vals = s.setdefault(k, {})
            vals[v] = vals.get(v, 0) + 1

    def _add(self, kind, oid, tags, lat, lon):
        t = {k: v for k, v in tags if k in KEEP or k in ("memorial", "inscription")}
        if "addr:housenumber" in t:
            if in_krakow(t, lat, lon):
                self.addresses.append({"osm": f"{kind}{oid}", "lat": round(lat, 6), "lon": round(lon, 6), **{k: v for k, v in t.items() if k in KEEP}})
        elif t.get("historic") in NOTABLE_HISTORIC and (t.get("name") or t.get("inscription")):
            if BBOX[0] <= lon <= BBOX[2] and BBOX[1] <= lat <= BBOX[3]:
                self.notable.append({"osm": f"{kind}{oid}", "lat": round(lat, 6), "lon": round(lon, 6), **t})

    def node(self, n):
        if n.tags and n.location.valid():
            self._add("n", n.id, n.tags, n.location.lat, n.location.lon)

    def way(self, w):
        if w.tags and "highway" in w.tags:
            self._street(w)
        if not w.tags or not ("addr:housenumber" in w.tags or "historic" in w.tags):
            return
        pts = [(nd.lat, nd.lon) for nd in w.nodes if nd.location.valid()]
        if pts:
            lat = sum(p[0] for p in pts) / len(pts)
            lon = sum(p[1] for p in pts) / len(pts)
            self._add("w", w.id, w.tags, lat, lon)


# Gminy around Kraków: addresses with a Kraków postcode can lie in them.
MUNICIPALITY_BBOX = (19.6, 49.85, 20.4, 50.25)


class DistrictHandler(osmium.SimpleHandler):
    """Kraków's 18 dzielnice (boundary=administrative, admin_level=9) and the
    neighbouring gminy (admin_level=7)."""

    def __init__(self):
        super().__init__()
        self.districts = []
        self.municipalities = []

    def area(self, a):
        t = a.tags
        level = t.get("admin_level")
        if a.from_way() or t.get("boundary") != "administrative" or level not in ("7", "9"):
            return
        polys = []
        for outer in a.outer_rings():
            rings = [[[round(n.lon, 6), round(n.lat, 6)] for n in outer]]
            for inner in a.inner_rings(outer):
                rings.append([[round(n.lon, 6), round(n.lat, 6)] for n in inner])
            polys.append(rings)
        if not polys:
            return
        lons = [p[0] for poly in polys for p in poly[0]]
        lats = [p[1] for poly in polys for p in poly[0]]
        clon, clat = sum(lons) / len(lons), sum(lats) / len(lats)
        if level == "7":
            mb = MUNICIPALITY_BBOX
            if mb[0] <= clon <= mb[2] and mb[1] <= clat <= mb[3]:
                self.municipalities.append({"osm": f"r{a.orig_id()}", "name": t.get("name", ""),
                                            "polygons": polys})
            return
        if not (BBOX[0] <= clon <= BBOX[2] and BBOX[1] <= clat <= BBOX[3]):
            return
        self.districts.append({"osm": f"r{a.orig_id()}", "name": t.get("name", ""),
                               "ref": t.get("ref", ""), "wikidata": t.get("wikidata", ""),
                               "wikipedia": t.get("wikipedia", ""), "polygons": polys})


def download_extract():
    tmp = PBF.with_suffix(".part")
    for url in PBF_URLS:
        print(f"Downloading {url} ...")
        try:
            with requests.get(url, stream=True, timeout=600) as r:
                r.raise_for_status()
                with open(tmp, "wb") as f:
                    for chunk in r.iter_content(1 << 20):
                        f.write(chunk)
            tmp.replace(PBF)
            (RAW / "osm_source.txt").write_text(url + "\n", encoding="utf-8")
            return
        except requests.RequestException as err:
            print(f"  failed: {err}")
    raise SystemExit("Could not download the OSM extract from any mirror.")


def main():
    if not PBF.exists():
        download_extract()
    h = Handler()
    h.apply_file(str(PBF), locations=True, idx="flex_mem")
    OUT.write_text(json.dumps(h.addresses, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    (RAW / "osm_notable.json").write_text(json.dumps(h.notable, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"OSM addresses in Krakow: {len(h.addresses)} -> {OUT}")
    print(f"OSM notable historic features: {len(h.notable)}")
    streets = sorted(h.streets.values(), key=lambda s: s["name"])
    (RAW / "osm_streets.json").write_text(json.dumps(streets, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"OSM named streets with name-origin tags: {len(streets)}")

    d = DistrictHandler()
    d.apply_file(str(PBF), locations=True, idx="flex_mem")
    (RAW / "osm_districts.json").write_text(json.dumps(d.districts, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"OSM admin_level=9 areas in the Krakow bbox: {len(d.districts)}")
    (RAW / "osm_municipalities.json").write_text(json.dumps(d.municipalities, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"OSM gminy (admin_level=7) around Krakow: {len(d.municipalities)}")


if __name__ == "__main__":
    sys.exit(main())

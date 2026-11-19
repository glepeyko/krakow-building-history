"""Extract every address point and addressed building in Kraków from OpenStreetMap.

Input:  the Małopolska extract (downloaded if missing) from Geofabrik, or
        from the openstreetmap.fr mirror if Geofabrik is unreachable.
Output: source-data/raw/osm_addresses.json

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


class Handler(osmium.SimpleHandler):
    def __init__(self):
        super().__init__()
        self.addresses = []
        self.notable = []

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
        if not w.tags or not ("addr:housenumber" in w.tags or "historic" in w.tags):
            return
        pts = [(nd.lat, nd.lon) for nd in w.nodes if nd.location.valid()]
        if pts:
            lat = sum(p[0] for p in pts) / len(pts)
            lon = sum(p[1] for p in pts) / len(pts)
            self._add("w", w.id, w.tags, lat, lon)


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


if __name__ == "__main__":
    sys.exit(main())

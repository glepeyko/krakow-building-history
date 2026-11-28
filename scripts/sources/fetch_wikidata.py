"""Download Wikidata items located in Kraków that have coordinates.

Output: source-data/raw/wikidata.json (list of dicts, one per item).
Wikidata content is CC0, so it can be reused freely.
"""
import json
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "source-data" / "raw" / "wikidata.json"
ENDPOINT = "https://query.wikidata.org/sparql"
HEADERS = {"User-Agent": "historia-twojego-domu/0.1 (static heritage site; python-requests)",
           "Accept": "application/sparql-results+json"}

# Step 1: every item with coordinates inside Kraków's bounding box (fast
# geo index). Step 2: details for those items in batches. A single big query
# with P131+ and label joins times out on the public endpoint.
BBOX_QUERY = """
SELECT DISTINCT ?item ?coord WHERE {
  SERVICE wikibase:box {
    ?item wdt:P625 ?coord .
    bd:serviceParam wikibase:cornerSouthWest "Point(19.79 49.96)"^^geo:wktLiteral .
    bd:serviceParam wikibase:cornerNorthEast "Point(20.22 50.13)"^^geo:wktLiteral .
  }
}
"""

DETAIL_QUERY = """
SELECT ?item
  (SAMPLE(?label_) AS ?label)
  (SAMPLE(?addr) AS ?address)
  (SAMPLE(?streetLabel_) AS ?street) (SAMPLE(?num) AS ?number)
  (GROUP_CONCAT(DISTINCT ?archLabel_; separator="|") AS ?architects)
  (SAMPLE(?inception_) AS ?inception) (MAX(?prec_) AS ?inception_precision)
  (GROUP_CONCAT(DISTINCT ?styleLabel_; separator="|") AS ?styles)
  (GROUP_CONCAT(DISTINCT ?typeLabel_; separator="|") AS ?types)
  (SAMPLE(?img) AS ?image) (SAMPLE(?article_) AS ?article)
  (SAMPLE(?desc_) AS ?description) (SAMPLE(?nid_) AS ?nid)
WHERE {
  VALUES ?item { %s }
  OPTIONAL { ?item rdfs:label ?label_ . FILTER(LANG(?label_) = "pl") }
  OPTIONAL { ?item wdt:P6375 ?addr }
  OPTIONAL { ?item p:P669 ?st . ?st ps:P669 ?streetItem .
             ?streetItem rdfs:label ?streetLabel_ . FILTER(LANG(?streetLabel_) = "pl")
             OPTIONAL { ?st pq:P670 ?num } }
  OPTIONAL { ?item wdt:P84 ?arch . ?arch rdfs:label ?archLabel_ . FILTER(LANG(?archLabel_) = "pl") }
  OPTIONAL { ?item wdt:P571 ?inception_ . ?item p:P571/psv:P571/wikibase:timePrecision ?prec_ }
  OPTIONAL { ?item wdt:P149 ?style . ?style rdfs:label ?styleLabel_ . FILTER(LANG(?styleLabel_) = "pl") }
  OPTIONAL { ?item wdt:P31 ?type . ?type rdfs:label ?typeLabel_ . FILTER(LANG(?typeLabel_) = "pl") }
  OPTIONAL { ?item wdt:P18 ?img }
  OPTIONAL { ?article_ schema:about ?item ; schema:isPartOf <https://pl.wikipedia.org/> }
  OPTIONAL { ?item schema:description ?desc_ . FILTER(LANG(?desc_) = "pl") }
  OPTIONAL { ?item wdt:P3424 ?nid_ }
}
GROUP BY ?item
"""


def sparql(query):
    for attempt in range(3):
        r = requests.post(ENDPOINT, data={"query": query}, headers=HEADERS, timeout=120)
        if r.status_code == 200:
            return json.loads(r.text, strict=False)["results"]["bindings"]  # labels may hold raw control chars
        print(f"  HTTP {r.status_code}, retry {attempt + 1}")
        time.sleep(5 * (attempt + 1))
    r.raise_for_status()


def main():
    coords = {}
    for row in sparql(BBOX_QUERY):
        qid = row["item"]["value"].rsplit("/", 1)[-1]
        c = row["coord"]["value"]
        try:
            lon, lat = map(float, c[c.index("(") + 1:-1].split())
        except ValueError:
            continue
        coords.setdefault(qid, (lat, lon))
    print(f"Items with coordinates in bbox: {len(coords)}")

    qids = sorted(coords)
    items = []
    for i in range(0, len(qids), 250):
        batch = qids[i:i + 250]
        rows = sparql(DETAIL_QUERY % " ".join(f"wd:{q}" for q in batch))
        for row in rows:
            get = lambda k: row.get(k, {}).get("value", "")
            qid = get("item").rsplit("/", 1)[-1]
            lat, lon = coords[qid]
            items.append({
                "qid": qid, "label": get("label"), "lat": lat, "lon": lon,
                "address": get("address"), "street": get("street"), "number": get("number"),
                "architects": [a for a in get("architects").split("|") if a],
                "inception": get("inception"),
                "inception_precision": int(get("inception_precision") or 0),
                "styles": [s for s in get("styles").split("|") if s],
                "types": [t for t in get("types").split("|") if t],
                "image": get("image"), "wikipedia": get("article"),
                "description": get("description"), "nid": get("nid"),
            })
        print(f"  details {min(i + 250, len(qids))}/{len(qids)}")
    OUT.write_text(json.dumps(items, ensure_ascii=False, indent=0), encoding="utf-8")
    print(f"Wikidata items: {len(items)} -> {OUT}")


if __name__ == "__main__":
    sys.exit(main())

"""Download Wikidata facts about Kraków streets: what each street is named
after (P138), its historical names with dates (P1448 + P580/P582), and the
Polish Wikipedia article ("Ulica X w Krakowie").

Also fetches the people/places streets are named after, both from Wikidata
P138 and from OSM name:etymology:wikidata tags (osm_streets.json, written by
fetch_osm.py - run that first).

Output: source-data/raw/wikidata_streets.json
    {"streets": [...], "patrons": {qid: {...}}}
Wikidata content is CC0.
"""
import json
import re
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "source-data" / "raw"
OUT = RAW / "wikidata_streets.json"
ENDPOINT = "https://query.wikidata.org/sparql"
HEADERS = {"User-Agent": "historia-twojego-domu/0.1 (static heritage site; python-requests)",
           "Accept": "application/sparql-results+json"}

# Every thoroughfare (Q83620 and subclasses: ulica, aleja, plac, rondo, ...)
# located in Kraków or directly in one of its parts. (A fully transitive
# P131* query times out on the public endpoint.)
STREETS_QUERY = """
SELECT DISTINCT ?item WHERE {
  { ?item wdt:P131 wd:Q31487 } UNION { ?part wdt:P131 wd:Q31487 . ?item wdt:P131 ?part }
  ?item wdt:P31 ?type . ?type wdt:P279* wd:Q83620 .
}
"""

STREET_DETAILS = """
SELECT ?item ?label ?type ?patron ?name ?start ?end ?article WHERE {
  VALUES ?item { %s }
  OPTIONAL { ?item rdfs:label ?label . FILTER(LANG(?label) = "pl") }
  OPTIONAL { ?item wdt:P31 ?t . ?t rdfs:label ?type . FILTER(LANG(?type) = "pl") }
  OPTIONAL { ?item wdt:P138 ?patron }
  OPTIONAL { ?item p:P1448 ?ns . ?ns ps:P1448 ?name .
             OPTIONAL { ?ns pq:P580 ?start } OPTIONAL { ?ns pq:P582 ?end } }
  OPTIONAL { ?article schema:about ?item ; schema:isPartOf <https://pl.wikipedia.org/> }
}
"""

PATRON_DETAILS = """
SELECT ?item ?label ?desc ?birth ?death ?article ?human WHERE {
  VALUES ?item { %s }
  OPTIONAL { ?item rdfs:label ?label . FILTER(LANG(?label) = "pl") }
  OPTIONAL { ?item schema:description ?desc . FILTER(LANG(?desc) = "pl") }
  OPTIONAL { ?item wdt:P569 ?birth }
  OPTIONAL { ?item wdt:P570 ?death }
  OPTIONAL { ?article schema:about ?item ; schema:isPartOf <https://pl.wikipedia.org/> }
  BIND(EXISTS { ?item wdt:P31 wd:Q5 } AS ?human)
}
"""

QID = re.compile(r"^Q\d+$")


def sparql(query):
    for attempt in range(6):
        r = requests.post(ENDPOINT, data={"query": query}, headers=HEADERS, timeout=180)
        if r.status_code == 200:
            try:  # labels may hold raw control chars; a WDQS timeout truncates the stream
                return json.loads(r.text, strict=False)["results"]["bindings"]
            except ValueError as e:
                print(f"  truncated/invalid JSON ({e}), retry {attempt + 1}")
        else:
            print(f"  HTTP {r.status_code}, retry {attempt + 1}")
        time.sleep(5 * (attempt + 1))
    r.raise_for_status()


def qid_of(uri):
    return uri.rsplit("/", 1)[-1]


def year(value):
    m = re.match(r"^(-?)(\d{1,4})-", value or "")
    if not m:
        return None
    return -int(m.group(2)) if m.group(1) else int(m.group(2))


def batched(seq, n=200):
    seq = sorted(seq)
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


def main():
    osm_streets = json.loads((RAW / "osm_streets.json").read_text(encoding="utf-8"))

    qids = {qid_of(r["item"]["value"]) for r in sparql(STREETS_QUERY)}
    print(f"Thoroughfares in Kraków on Wikidata: {len(qids)}")
    for s in osm_streets:  # street items linked from OSM (wikidata=Q...)
        qids.update(q for q in s.get("wikidata", {}) if QID.match(q))
    print(f"  plus items linked from OSM: {len(qids)}")

    streets = {}
    for batch in batched(qids):
        for row in sparql(STREET_DETAILS % " ".join(f"wd:{q}" for q in batch)):
            get = lambda k: row.get(k, {}).get("value", "")
            q = qid_of(get("item"))
            s = streets.setdefault(q, {"qid": q, "label": "", "types": [], "named_after": [],
                                       "names": [], "wikipedia": ""})
            s["label"] = s["label"] or get("label")
            s["wikipedia"] = s["wikipedia"] or get("article")
            if get("type") and get("type") not in s["types"]:
                s["types"].append(get("type"))
            if get("patron"):
                p = qid_of(get("patron"))
                if p not in s["named_after"]:
                    s["named_after"].append(p)
            if get("name"):
                n = {"name": get("name"), "from": year(get("start")), "to": year(get("end"))}
                if n not in s["names"]:
                    s["names"].append(n)
    print(f"Street items with details: {len(streets)}")

    patron_qids = {p for s in streets.values() for p in s["named_after"]}
    for s in osm_streets:
        for v in s.get("name:etymology:wikidata", {}):
            patron_qids.update(q.strip() for q in v.split(";") if QID.match(q.strip()))
    patrons = {}
    for batch in batched(patron_qids):
        for row in sparql(PATRON_DETAILS % " ".join(f"wd:{q}" for q in batch)):
            get = lambda k: row.get(k, {}).get("value", "")
            q = qid_of(get("item"))
            p = patrons.setdefault(q, {"qid": q, "label": get("label"), "description": get("desc"),
                                       "birth": year(get("birth")), "death": year(get("death")),
                                       "wikipedia": get("article"), "human": get("human") == "true"})
            # Several birth/death values: keep the earliest, it is usually the precise one.
            for k in ("birth", "death"):
                y = year(get(k))
                if y is not None and (p[k] is None or y < p[k]):
                    p[k] = y
    print(f"Patrons (people, places, events): {len(patrons)}")

    OUT.write_text(json.dumps({"streets": sorted(streets.values(), key=lambda s: s["qid"]),
                               "patrons": patrons}, ensure_ascii=False, indent=0), encoding="utf-8")
    print(f"-> {OUT}")


if __name__ == "__main__":
    sys.exit(main())

"""Cache the pl.wikipedia "Ulica X w Krakowie" articles linked from street
stories and pull out the sentences about the street's names.

The article text is CC BY-SA: it is cached only in the git-ignored
source-data/raw/wiki_streets/ and used to find facts (former names and their
dates). Those facts are restated in data/research/street_history.json, with the
article as the source; no article text goes into data/.

Input:  data/streets/*.json (story.wikipedia, written by build.py)
Output: source-data/raw/wiki_streets/<slug>.txt   raw wikitext
        source-data/raw/wiki_street_names.json    {street: {url, sentences: [...]}}

Wikipedia rate-limits bursts: one request every 4 s.
"""
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import unquote

import requests

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "source-data" / "raw"
CACHE = RAW / "wiki_streets"
OUT = RAW / "wiki_street_names.json"
HEADERS = {"User-Agent": "historia-twojego-domu/0.1 (static heritage site; python-requests)"}
PAUSE = 4

NAME_WORDS = re.compile(
    r"(nazw|nazyw|przemianow|zwan[aey]|zwano|nosił|nosi |dawniej|pierwotnie|okupacj|"
    r"Stra(ss|ß)e|Platz|Gasse|patron|upamiętni)", re.I)


def plain(wikitext: str) -> str:
    t = re.sub(r"<ref[^>]*/>", "", wikitext)
    t = re.sub(r"<ref[^>]*>.*?</ref>", "", t, flags=re.S)
    t = re.sub(r"\{\{[^{}]*\}\}", "", t)
    t = re.sub(r"\{\{[^{}]*\}\}", "", t)
    t = re.sub(r"\[\[(?:Plik|File|Kategoria|Category):[^\]]*\]\]", "", t)
    t = re.sub(r"\[\[([^|\]]*\|)?([^\]]*)\]\]", r"\2", t)
    t = re.sub(r"'{2,}", "", t)
    t = re.sub(r"<[^>]+>", "", t)
    return t


def name_sentences(wikitext: str) -> list[str]:
    text = plain(wikitext)
    out = []
    for para in text.split("\n"):
        if para.startswith(("|", "{", "!", "=")) and not para.startswith("=="):
            continue
        for s in re.split(r"(?<=[.!?])\s+(?=[A-ZŁŚŻŹĆ])", para):
            s = s.strip()
            if 20 < len(s) < 600 and NAME_WORDS.search(s) and re.search(r"\d{4}|\bXV|\bXIV|\bXIII", s):
                out.append(s)
    return out


def main():
    CACHE.mkdir(parents=True, exist_ok=True)
    streets = {}
    for f in sorted((ROOT / "data" / "streets").glob("*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        url = (d.get("story") or {}).get("wikipedia", "")
        if url.startswith("https://pl.wikipedia.org/wiki/"):
            streets[d["name"]] = (f.stem, url)
    print(f"{len(streets)} street articles")
    result = {}
    for i, (name, (slug, url)) in enumerate(sorted(streets.items())):
        path = CACHE / f"{slug}.txt"
        if not path.exists():
            title = unquote(url.rsplit("/wiki/", 1)[1])
            for attempt in range(3):
                r = requests.get("https://pl.wikipedia.org/w/index.php",
                                 params={"title": title, "action": "raw"}, headers=HEADERS, timeout=60)
                if r.status_code == 429:
                    time.sleep(60)
                    continue
                break
            time.sleep(PAUSE)
            if r.status_code != 200:
                print(f"  {name}: HTTP {r.status_code}")
                continue
            path.write_text(r.text, encoding="utf-8")
        sents = name_sentences(path.read_text(encoding="utf-8"))
        if sents:
            result[name] = {"url": url, "sentences": sents}
        if i % 50 == 0:
            print(f"  {i}/{len(streets)}")
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(result)} streets with naming sentences -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

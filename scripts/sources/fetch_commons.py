"""Fetch a medium-size thumbnail and the credit (author, licence) for every
Wikimedia Commons photo referenced by our Wikidata items.

Run after fetch_wikidata.py. Output: source-data/raw/commons_images.json
    {file name: {thumb, width, height, author, license, license_url, page}}
The page shows a photo only when author and licence are known; Commons
licences (CC BY, CC BY-SA, ...) require that credit next to the image.
"""
import html
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import unquote

import requests

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "source-data" / "raw"
OUT = RAW / "commons_images.json"
API = "https://commons.wikimedia.org/w/api.php"
HEADERS = {"User-Agent": "historia-twojego-domu/0.1 (static heritage site; python-requests)"}
THUMB_WIDTH = 800  # Commons serves the nearest standard size (960 px)


def plain(text: str) -> str:
    """Commons metadata is HTML ('<a href=...>Jan Kowalski</a>'): keep the words."""
    text = re.sub(r"<[^>]+>", " ", text or "")
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def strip_tracking(url: str) -> str:
    return url.split("?", 1)[0]


def main():
    items = json.loads((RAW / "wikidata.json").read_text(encoding="utf-8"))
    files = sorted({unquote(i["image"].rsplit("/", 1)[-1]) for i in items if i.get("image")})
    print(f"Commons files referenced: {len(files)}")
    out = {}
    for start in range(0, len(files), 50):
        batch = files[start:start + 50]
        params = {
            "action": "query", "format": "json", "prop": "imageinfo",
            "iiprop": "url|size|extmetadata", "iiurlwidth": THUMB_WIDTH,
            "iiextmetadatafilter": "Artist|LicenseShortName|LicenseUrl",
            "titles": "|".join("File:" + f for f in batch),
        }
        for attempt in range(5):
            r = requests.post(API, data=params, headers=HEADERS, timeout=60)
            if r.status_code == 200:
                break
            time.sleep(5 * (attempt + 1))
        r.raise_for_status()
        data = r.json()["query"]
        # The API normalizes titles (underscores, first letter); map back.
        back = {n["to"]: n["from"] for n in data.get("normalized", [])}
        for page in data.get("pages", {}).values():
            info = (page.get("imageinfo") or [None])[0]
            if not info:
                continue
            title = back.get(page["title"], page["title"])
            name = title.split(":", 1)[1]
            meta = info.get("extmetadata", {})
            out[name] = {
                "thumb": strip_tracking(info.get("thumburl", "")),
                "width": info.get("thumbwidth"), "height": info.get("thumbheight"),
                "author": plain(meta.get("Artist", {}).get("value", ""))[:120],
                "license": plain(meta.get("LicenseShortName", {}).get("value", "")),
                "license_url": meta.get("LicenseUrl", {}).get("value", ""),
                "page": strip_tracking(info.get("descriptionurl", "")),
            }
        print(f"  {min(start + 50, len(files))}/{len(files)}")
        time.sleep(1)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=0), encoding="utf-8")
    print(f"Commons images with metadata: {len(out)} -> {OUT}")


if __name__ == "__main__":
    sys.exit(main())

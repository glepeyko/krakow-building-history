"""Download historians' texts into a local library, one text file per page,
and keep a committed manifest so every claim can cite a page.

Usage:
    python scripts/sources/fetch_library.py [--list] [--url ID=URL ...]
                                            [--force] ID [ID ...]

Output:
    source-data/raw/library/<id>/source.<ext>   original download (git-ignored)
    source-data/raw/library/<id>/pages/0001.txt one text file per page
    data/research/library.json                  committed manifest

Routes (SOURCES[id]["route"]):
    pdf   direct PDF -> `pdftotext -enc UTF-8 -layout` per page
    ia    Internet Archive item; fetches <id>_djvu.txt (pages split on \\f)
    djvu  direct DjVu -> `djvutxt` (apt-get install djvulibre-bin)

Licence rule (PLAN.md): full texts stay in source-data/raw/ (git-ignored);
only the manifest is committed. "restricted" sources may be paraphrased and
cited, never quoted at length.

URLs: source locations are listed in SOURCES. Where a URL is None it has not
been verified yet; give it with --url ID=URL (or put it in the registry once
checked). The script never guesses a URL.
"""
import argparse
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "source-data" / "raw" / "library"
MANIFEST = ROOT / "data" / "research" / "library.json"
HEADERS = {"User-Agent": "historia-twojego-domu/0.1 (static heritage site; python-requests)"}

# One record per source. "licence": public_domain | restricted.
# Titles only state what PLAN.md names; fill the rest when the URL is verified.
SOURCES = {
    "kzs-iv-10": {
        "author": "Instytut Sztuki PAN",
        "title": "Katalog zabytków sztuki w Polsce, t. IV: Miasto Kraków (część 10 — do potwierdzenia)",
        "year": None, "licence": "restricted", "route": "pdf", "url": None,
    },
    "klas-nowa-huta-2018": {
        "author": "Klaś", "title": "Nowa Huta", "year": 2018,
        "licence": "restricted", "route": "pdf", "url": None,
    },
    "ksiega-adresowa-1913": {
        "author": None, "title": "Księga adresowa Krakowa 1913", "year": 1913,
        "licence": "public_domain", "route": "pdf", "url": None,
    },
    "rocznik-krakowski-akademicka": {
        "author": None, "title": "Rocznik Krakowski (journals.akademicka.pl)", "year": None,
        "licence": "restricted", "route": "pdf", "url": None,  # CC BY-NC-ND
    },
}


def split_pages(text):
    """Split pdftotext / djvu text on form feeds; drop the empty tail."""
    pages = text.split("\f")
    if pages and not pages[-1].strip():
        pages.pop()
    return pages


def citation_url(source, page):
    """Page-level URL for a 1-based page number."""
    route, url = source["route"], source["url"]
    if route == "ia":
        return f"https://archive.org/details/{source['ia_id']}/page/n{page - 1}"
    return f"{url.split('#')[0]}#page={page}"


def download(url, dest):
    with requests.get(url, headers=HEADERS, stream=True, timeout=120) as r:
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)


def extract(route, src, source):
    """Return list of page texts."""
    if route == "pdf":
        out = subprocess.run(["pdftotext", "-enc", "UTF-8", "-layout", str(src), "-"],
                             check=True, capture_output=True).stdout.decode("utf-8", "replace")
        return split_pages(out)
    if route == "djvu":
        out = subprocess.run(["djvutxt", str(src)], check=True,
                             capture_output=True).stdout.decode("utf-8", "replace")
        return split_pages(out)
    raise SystemExit(f"Unknown route {route}")


def fetch_one(sid, source, force=False):
    d = LIB / sid
    pages_dir = d / "pages"
    if pages_dir.exists() and any(pages_dir.iterdir()) and not force:
        n = len(list(pages_dir.glob("*.txt")))
        print(f"{sid}: already fetched ({n} pages); use --force to redo")
        return n
    if not source.get("url"):
        raise SystemExit(f"{sid}: no URL set. Pass --url {sid}=<url> (the script does not guess).")
    d.mkdir(parents=True, exist_ok=True)
    route = source["route"]
    if route == "ia":
        ident = source["ia_id"] = source.get("ia_id") or source["url"].rstrip("/").split("/")[-1]
        url = f"https://archive.org/download/{ident}/{ident}_djvu.txt"
        print(f"{sid}: {url}")
        r = requests.get(url, headers=HEADERS, timeout=300)
        r.raise_for_status()
        pages = split_pages(r.content.decode("utf-8", "replace"))
    else:
        ext = "pdf" if route == "pdf" else "djvu"
        src = d / f"source.{ext}"
        print(f"{sid}: downloading {source['url']}")
        download(source["url"], src)
        pages = extract(route, src, source)
    pages_dir.mkdir(exist_ok=True)
    for old in pages_dir.glob("*.txt"):
        old.unlink()
    for i, text in enumerate(pages, 1):
        (pages_dir / f"{i:04d}.txt").write_text(text, encoding="utf-8")
    empty = sum(1 for t in pages if len(t.strip()) < 20)
    print(f"{sid}: {len(pages)} pages ({empty} with no text layer)")
    return len(pages)


def load_manifest():
    if MANIFEST.exists():
        return json.loads(MANIFEST.read_text(encoding="utf-8"))
    return {"sources": []}


def update_manifest(sid, source, n_pages):
    m = load_manifest()
    rec = {
        "id": sid, "author": source["author"], "title": source["title"],
        "year": source["year"], "licence": source["licence"], "route": source["route"],
        "url": source["url"],
        "citation_pattern": (f"https://archive.org/details/{source.get('ia_id')}/page/n{{page-1}}"
                             if source["route"] == "ia" else f"{source['url'].split('#')[0]}#page={{page}}"),
        "local_dir": f"source-data/raw/library/{sid}/pages", "pages": n_pages,
        "fetched_at": date.today().isoformat(),
    }
    m["sources"] = [s for s in m["sources"] if s["id"] != sid] + [rec]
    m["sources"].sort(key=lambda s: s["id"])
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(m, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("ids", nargs="*")
    ap.add_argument("--list", action="store_true", help="list known source ids")
    ap.add_argument("--url", action="append", default=[], metavar="ID=URL")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args(argv)
    for pair in a.url:
        sid, _, url = pair.partition("=")
        if sid not in SOURCES or not url:
            ap.error(f"bad --url {pair!r}")
        SOURCES[sid]["url"] = url
    if a.list or not a.ids:
        for sid, s in SOURCES.items():
            print(f"{sid:32} {s['licence']:14} {s['route']:5} {s['url'] or '(no URL yet)'}")
        return 0
    unknown = [i for i in a.ids if i not in SOURCES]
    if unknown:
        ap.error(f"unknown ids: {', '.join(unknown)} (see --list)")
    failed = 0
    for sid in a.ids:
        try:
            n = fetch_one(sid, SOURCES[sid], a.force)
            update_manifest(sid, SOURCES[sid], n)
        except (SystemExit, requests.RequestException, subprocess.CalledProcessError, OSError) as e:
            failed += 1
            print(f"{sid}: FAILED — {e}", file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

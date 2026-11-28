"""Download the historians' texts listed in data/research/library.json into
the git-ignored source-data/raw/library/<source id>/, one UTF-8 text file per
scanned page (p0001.txt = scan 1), so every claim can cite a page.

Routes (the manifest field "route"):
  polona  Polona (Biblioteka Narodowa) full-text ZIP:
          https://polona.pl/api/search-service/fulltext/polona/fulltext/content/<uuid>
          The ZIP holds pages/page<N>.txt with N = 1-based scan number (blank
          scans are left out). The item viewer takes a 0-based scan index:
          https://polona.pl/item-view/<uuid>?page=<N-1>.
  ia      Internet Archive OCR: https://archive.org/download/<id>/<file>_djvu.txt
          (pages are separated by form feeds).
  pdf     A PDF with a text layer -> `pdftotext -enc UTF-8 -layout`, page by page
          (pages are separated by form feeds). Cited as <url>#page=N.
  djvu    A DjVu file with a text layer (e.g. dbc.wroc.pl) -> `djvutxt`
          (needs `apt-get install djvulibre-bin`).

The manifest is committed; the texts are not (copyright: IS PAN Katalog and
CC BY-NC-ND journals may only be stored in source-data/raw/). The script
updates each manifest record's "fetch" block: status ("ok", "blocked",
"error", "skipped"), pages, fetched_at, and the error message if any.

Usage:
  python scripts/sources/fetch_library.py            # every source not yet cached
  python scripts/sources/fetch_library.py --force    # download again
  python scripts/sources/fetch_library.py chmiel-florianska-1   # only these ids
  python scripts/sources/fetch_library.py --check-hosts           # reachability only
"""
import argparse
import datetime as dt
import io
import json
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path
from urllib.parse import urlparse

import requests

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "data" / "research" / "library.json"
LIB = ROOT / "source-data" / "raw" / "library"
HEADERS = {"User-Agent": "Mozilla/5.0 (historia-twojego-domu; research library fetcher)"}
PAUSE = 4  # seconds between downloads: several hosts throttle bursts

POLONA_ZIP = "https://polona.pl/api/search-service/fulltext/polona/fulltext/content/{uuid}"


def page_file(dir_: Path, n: int) -> Path:
    return dir_ / f"p{n:04d}.txt"


def write_pages(dest: Path, pages: dict) -> int:
    """pages: {scan number (1-based): text}. Replaces the folder content."""
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    for n, text in pages.items():
        if text.strip():
            page_file(dest, n).write_text(text, encoding="utf-8")
    return sum(1 for t in pages.values() if t.strip())


def split_formfeed(text: str) -> dict:
    return {i + 1: t for i, t in enumerate(text.split("\f"))}


def get(url, **kw):
    r = requests.get(url, headers=HEADERS, timeout=kw.pop("timeout", 300), **kw)
    r.raise_for_status()
    return r


def fetch_polona(src) -> dict:
    data = get(POLONA_ZIP.format(uuid=src["polona_uuid"])).content
    pages = {}
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for name in z.namelist():
            if name.startswith("pages/page") and name.endswith(".txt"):
                n = int(name[len("pages/page"):-4])
                pages[n] = z.read(name).decode("utf-8", "replace")
    if not pages:
        raise RuntimeError("Polona ZIP has no per-page texts (no OCR?)")
    return pages


def fetch_ia(src) -> dict:
    ident = src["ia_id"]
    meta = get(f"https://archive.org/metadata/{ident}", timeout=60).json()
    names = [f["name"] for f in meta.get("files", []) if f["name"].endswith("_djvu.txt")]
    if not names:
        raise RuntimeError("no _djvu.txt file in the item")
    text = get(f"https://archive.org/download/{ident}/{names[0]}").text
    return split_formfeed(text)


def download_to(url, path: Path):
    with requests.get(url, headers=HEADERS, timeout=600, stream=True) as r:
        r.raise_for_status()
        with open(path, "wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)


def fetch_pdf(src) -> dict:
    if not shutil.which("pdftotext"):
        raise RuntimeError("pdftotext not installed (poppler-utils)")
    with tempfile.TemporaryDirectory() as tmp:
        pdf = Path(tmp) / "doc.pdf"
        download_to(src["url"], pdf)
        out = subprocess.run(["pdftotext", "-enc", "UTF-8", "-layout", str(pdf), "-"],
                             capture_output=True, check=True).stdout.decode("utf-8", "replace")
    return split_formfeed(out)


def fetch_djvu(src) -> dict:
    if not shutil.which("djvutxt"):
        raise RuntimeError("djvutxt not installed (apt-get install djvulibre-bin)")
    with tempfile.TemporaryDirectory() as tmp:
        f = Path(tmp) / "doc.djvu"
        download_to(src["url"], f)
        n_pages = int(subprocess.run(["djvused", "-e", "n", str(f)], capture_output=True,
                                     check=True).stdout.strip() or 0)
        pages = {}
        for n in range(1, n_pages + 1):
            pages[n] = subprocess.run(["djvutxt", f"--page={n}", str(f)], capture_output=True
                                      ).stdout.decode("utf-8", "replace")
    return pages


ROUTES = {"polona": fetch_polona, "ia": fetch_ia, "pdf": fetch_pdf, "djvu": fetch_djvu}


def route_host(src) -> str:
    if src["route"] == "polona":
        return "polona.pl"
    if src["route"] == "ia":
        return "archive.org"
    return urlparse(src["url"]).hostname


def host_ok(host) -> bool:
    try:
        requests.head(f"https://{host}/", headers=HEADERS, timeout=20, allow_redirects=False)
        return True
    except requests.RequestException:
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ids", nargs="*")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--check-hosts", action="store_true")
    args = ap.parse_args()

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    sources = manifest["sources"]
    hosts = {}
    for src in sources:
        h = route_host(src)
        if h not in hosts:
            hosts[h] = host_ok(h)
    print("Host reachability:", ", ".join(f"{h}={'ok' if ok else 'BLOCKED'}" for h, ok in sorted(hosts.items())))
    if args.check_hosts:
        return 0

    today = dt.date.today().isoformat()
    for src in sources:
        if args.ids and src["id"] not in args.ids:
            continue
        dest = LIB / src["id"]
        fetch = src.setdefault("fetch", {})
        if dest.exists() and any(dest.iterdir()) and not args.force:
            fetch.update(status="ok", pages=sum(1 for _ in dest.glob("p*.txt")))
            print(f"  {src['id']}: cached ({fetch['pages']} pages)")
            continue
        if not hosts[route_host(src)]:
            fetch.update(status="blocked", error=f"host {route_host(src)} not reachable from this environment",
                         checked_at=today)
            fetch.pop("pages", None)
            print(f"  {src['id']}: BLOCKED ({route_host(src)})")
            continue
        try:
            pages = ROUTES[src["route"]](src)
            n = write_pages(dest, pages)
            fetch.clear()
            fetch.update(status="ok", pages=n, fetched_at=today)
            print(f"  {src['id']}: {n} pages")
        except Exception as e:  # keep going: one broken source must not stop the rest
            fetch.update(status="error", error=str(e)[:300], checked_at=today)
            print(f"  {src['id']}: ERROR {e}")
        time.sleep(PAUSE)

    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    ok = sum(1 for s in sources if s.get("fetch", {}).get("status") == "ok")
    print(f"{ok}/{len(sources)} sources cached in {LIB}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

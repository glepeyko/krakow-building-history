"""Command-line search of the cached library (for research agents).

  python scripts/library_search.py Floriańska 19            # candidate pages + citations
  python scripts/library_search.py Floriańska 19 --text     # ... with the full page texts
  python scripts/library_search.py --name "Pod Jaszczurką"  # house name or owner
  python scripts/library_search.py --old 352 --street Floriańska
  python scripts/library_search.py --page chmiel-florianska-1 82   # one page + its citation
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.library import Library  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("street", nargs="?")
    ap.add_argument("number", nargs="?")
    ap.add_argument("--name")
    ap.add_argument("--old")
    ap.add_argument("--street", dest="street_opt")
    ap.add_argument("--page", nargs=2, metavar=("SOURCE", "SCAN"))
    ap.add_argument("--text", action="store_true", help="print page texts")
    ap.add_argument("--limit", type=int, default=25)
    a = ap.parse_args()
    lib = Library()

    if a.page:
        sid, scan = a.page[0], int(a.page[1])
        title, url, _ = lib.cite(sid, scan)
        print(f"{title}\n{url}\n" + "-" * 70 + "\n" + lib.page_text(sid, scan))
        return 0
    if a.old:
        print(json.dumps(lib.by_old_number(a.old, a.street_opt), ensure_ascii=False, indent=1))
        return 0
    if a.name:
        hits = lib.find_name(a.name, limit=a.limit)
    else:
        if not (a.street and a.number):
            ap.error("give STREET NUMBER, --name, --old or --page")
        olds = lib.old_numbers(a.street, a.number)
        if olds:
            print("[old number] NOTE: 1884 street numbering; some streets were renumbered later "
                  "(odd side of Sławkowska, Szeroka). Confirm with the lc. number in the house chapter.")
        for r in olds:
            print(f"[old number] lc. {r['old_number']} — owner 1884: {r['owner']} ({r['confidence']}) {r['page_url']}")
        hits = lib.find_address(a.street, a.number, limit=a.limit)
    for h in hits:
        print(f"\n[{h.score:g}] {h.reason}\n  {h.citation_title}\n  {h.url}")
        if a.text:
            print("-" * 70 + "\n" + lib.page_text(h.source, h.scan))
        elif h.snippet:
            print(f"  … {h.snippet[:260]} …")
    return 0


if __name__ == "__main__":
    sys.exit(main())

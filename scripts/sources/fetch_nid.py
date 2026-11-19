"""Download the national register of immovable monuments (NID, "rejestr
zabytków nieruchomych") as published on dane.gov.pl, keep the Kraków rows.

Dataset: https://dane.gov.pl/pl/dataset/1130 (Narodowy Instytut Dziedzictwa).
The CSV URL changes with every release, so we ask the dane.gov.pl API for
the current CSV resource of the dataset.

Output: source-data/raw/nid_krakow.json (list of dicts, UTF-8)
"""
import csv
import io
import json
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "source-data" / "raw"
OUT = RAW / "nid_krakow.json"
DATASET_API = "https://api.dane.gov.pl/1.4/datasets/1130/resources"
HEADERS = {"User-Agent": "historia-twojego-domu/0.1 (static heritage site; python-requests)"}
KEEP = ("INSPIRE_ID", "NAZWA", "CHRONOLOGIA", "FUNKCJA", "STYL_ARCHITEKTONICZNY",
        "WYKAZ_DOKUMENTOW", "DATA_WPISU", "ULICA", "NR_ADRESOWY", "LINK")


def csv_url():
    data = requests.get(DATASET_API, headers=HEADERS, timeout=60).json()["data"]
    for res in data:
        a = res["attributes"]
        url = a.get("link") or a.get("file_url") or ""
        if (a.get("format") or "").lower() == "csv" and url.startswith("https://"):
            return url, a.get("title", "")
    raise SystemExit("No CSV resource found in dataset 1130")


def main():
    url, title = csv_url()
    print(f"Downloading {title}: {url}")
    r = requests.get(url, headers=HEADERS, timeout=600)
    r.raise_for_status()
    text = r.content.decode("cp1250")  # the NID export is Windows-1250
    rows = csv.DictReader(io.StringIO(text, newline=""), delimiter=";")
    krakow = [{k: (row.get(k) or "").strip() for k in KEEP}
              for row in rows if row.get("MIEJSCOWOSC") == "Kraków" and row.get("POWIAT", "Kraków") == "Kraków"]
    OUT.write_text(json.dumps({"source": url, "rows": krakow}, ensure_ascii=False, indent=0), encoding="utf-8")
    print(f"NID register rows in Kraków: {len(krakow)} -> {OUT}")


if __name__ == "__main__":
    sys.exit(main())

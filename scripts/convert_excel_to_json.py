"""
Converts the Kraków buildings Excel database into the JSON files used by the website.

Usage:
    python convert_excel_to_json.py path/to/Buildings_in_Krakow_EXCEL.xlsx

Produces:
    data/buildings.json  - one record per building entry
    data/streets.json    - unique, sorted list of street names (for the autocomplete)

Expected source format (as in the current file):
    Sheets: any number of sheets, all with the same columns, concatenated in order.
    Columns: 'Lp.', 'Numer dzielnicy', 'Adres', 'Typologia i nazwa',
             'Datowanie', 'Autor', 'Numer rejestru'

    'Adres' mixes street name and building number in one free-text cell, sometimes
    with a second, alternate address after a '/' (corner buildings), e.g.:
        "ul. Cystersów 21"
        "al. 29 Listopada 5 / Kątowa 2"
    A number of rows are pure cross-references ("ul. X - patrz Y") pointing to another
    entry rather than describing a building themselves; these are skipped.

If your column names differ, edit COLUMN_MAP below to match your file - no other
code needs to change.
"""

import sys
import re
import json
from pathlib import Path
import pandas as pd

COLUMN_MAP = {
    "id": "Lp.",
    "district_number": "Numer dzielnicy",
    "address_raw": "Adres",
    "type_and_name": "Typologia i nazwa",
    "dating": "Datowanie",
    "author": "Autor",
    "register_number": "Numer rejestru",
}

# Kraków's 18 administrative districts (dzielnice), stable since 1991.
DISTRICT_NAMES = {
    1: "Stare Miasto", 2: "Grzegórzki", 3: "Prądnik Czerwony", 4: "Prądnik Biały",
    5: "Krowodrza", 6: "Bronowice", 7: "Zwierzyniec", 8: "Dębniki",
    9: "Łagiewniki-Borek Fałęcki", 10: "Swoszowice", 11: "Podgórze Duchackie",
    12: "Bieżanów-Prokocim", 13: "Podgórze", 14: "Czyżyny", 15: "Mistrzejowice",
    16: "Bieńczyce", 17: "Wzgórza Krzesławickie", 18: "Nowa Huta",
}

STREET_PREFIXES = r"(?:ul\.|al\.|os\.|pl\.|rondo|bulwar|wybrzeże|wzgórze)"

# Matches: [prefix] STREET NAME , NUMBER(letter)?
ADDRESS_RE = re.compile(
    rf"^\s*(?P<prefix>{STREET_PREFIXES})?\s*(?P<street>.*?)\s+"
    rf"(?P<number>\d+[a-zA-Z]?(?:[-/]\d+[a-zA-Z]?)?)\s*$"
)

DIACRITICS = str.maketrans("ąćęłńóśźżĄĆĘŁŃÓŚŹŻ", "acelnoszzACELNOSZZ")


def normalize(text: str) -> str:
    """Lowercase, strip Polish diacritics - used for search matching, not for display."""
    return text.translate(DIACRITICS).lower().strip()


def clean_text(value) -> str:
    if pd.isna(value):
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def parse_address(raw: str):
    """Split one 'Adres' cell into (street_name, building_number, alt_address_raw)."""
    raw = clean_text(raw)
    if not raw:
        return "", "", ""

    primary, _, alt = raw.partition("/")
    primary = primary.strip()
    alt = alt.strip()

    m = ADDRESS_RE.match(primary)
    if m and m.group("street"):
        street = m.group("street").strip(" ,-")
        number = m.group("number").strip()
    else:
        # No clean trailing number found (e.g. "ul. Łokietka wiadukt") - keep the
        # whole thing as the street/location name with no separate number.
        street = re.sub(rf"^{STREET_PREFIXES}\s*", "", primary).strip(" ,-")
        number = ""

    return street, number, alt


def load_all_sheets(xlsx_path: str) -> pd.DataFrame:
    xl = pd.ExcelFile(xlsx_path)
    frames = [xl.parse(s) for s in xl.sheet_names]
    df = pd.concat(frames, ignore_index=True, sort=False)
    # Drop stray unnamed columns some sheets may carry (merged-cell artifacts).
    df = df[[c for c in df.columns if not str(c).startswith("Unnamed")]]
    return df


def main():
    if len(sys.argv) != 2:
        print("Usage: python convert_excel_to_json.py path/to/file.xlsx")
        sys.exit(1)

    xlsx_path = sys.argv[1]
    df = load_all_sheets(xlsx_path)

    buildings = []
    skipped_cross_refs = 0

    for _, row in df.iterrows():
        address_raw = clean_text(row.get(COLUMN_MAP["address_raw"]))
        type_and_name = clean_text(row.get(COLUMN_MAP["type_and_name"]))

        if not address_raw:
            continue
        # Pure cross-reference rows ("ul. X - patrz Y") have no content of their own.
        if not type_and_name and ("patrz" in address_raw.lower()):
            skipped_cross_refs += 1
            continue

        street, number, alt_address = parse_address(address_raw)

        district_raw = row.get(COLUMN_MAP["district_number"])
        district_number = int(district_raw) if pd.notna(district_raw) else None

        record = {
            "id": int(row[COLUMN_MAP["id"]]) if pd.notna(row.get(COLUMN_MAP["id"])) else len(buildings) + 1,
            "street": street,
            "street_search": normalize(street),
            "building_number": number,
            "address_raw": address_raw,
            "alt_address": alt_address,
            "district_number": district_number,
            "district_name": DISTRICT_NAMES.get(district_number, ""),
            "type_and_name": type_and_name,
            "dating": clean_text(row.get(COLUMN_MAP["dating"])),
            "author": clean_text(row.get(COLUMN_MAP["author"])),
            "register_number": clean_text(row.get(COLUMN_MAP["register_number"])),
            "source": "Gminna Ewidencja Zabytków Miasta Krakowa",
            "status": "verified",  # this dataset is an official register, not AI-drafted
        }
        buildings.append(record)

    # Unique street list for the autocomplete, each with a normalized search key.
    seen = {}
    for b in buildings:
        if b["street"] and b["street_search"] not in seen:
            seen[b["street_search"]] = b["street"]
    streets = [{"name": name, "search": key} for key, name in sorted(seen.items(), key=lambda kv: kv[1])]

    out_dir = Path(__file__).resolve().parent.parent / "data"
    out_dir.mkdir(exist_ok=True)

    with open(out_dir / "buildings.json", "w", encoding="utf-8") as f:
        json.dump(buildings, f, ensure_ascii=False, indent=None, separators=(",", ":"))

    with open(out_dir / "streets.json", "w", encoding="utf-8") as f:
        json.dump(streets, f, ensure_ascii=False, indent=None, separators=(",", ":"))

    print(f"Loaded rows: {len(df)}")
    print(f"Skipped cross-reference rows: {skipped_cross_refs}")
    print(f"Building records written: {len(buildings)}")
    print(f"Unique streets written: {len(streets)}")
    print(f"Output: {out_dir / 'buildings.json'}")
    print(f"Output: {out_dir / 'streets.json'}")


if __name__ == "__main__":
    main()

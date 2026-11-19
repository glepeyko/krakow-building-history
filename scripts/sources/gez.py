"""Read the Gminna Ewidencja Zabytków (GEZ) Excel file into record dicts.

Schema of each record (unchanged from the first test version, so the site
and CLAUDE.md conventions stay valid):
    id, street, street_search, building_number, address_raw, alt_address,
    district_number, district_name, type_and_name, dating, author,
    register_number, source, status
"""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from lib.address import StreetIndex, normalize, split_street_number

ROOT = Path(__file__).resolve().parents[2]
XLSX = ROOT / "source-data" / "Buildings_in_Krakow_EXCEL.xlsx"

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

PREFIX_RE = re.compile(r"^\s*(?:ul\.?|al\.|os\.|pl\.)\s+", re.I)


def clean(value) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def load(index: StreetIndex) -> tuple[list[dict], dict]:
    xl = pd.ExcelFile(XLSX)
    df = pd.concat([xl.parse(s) for s in xl.sheet_names], ignore_index=True, sort=False)
    df = df[[c for c in df.columns if not str(c).startswith("Unnamed")]]

    records, stats = [], {"rows": len(df), "cross_refs": 0}
    for _, row in df.iterrows():
        address_raw = clean(row.get(COLUMN_MAP["address_raw"]))
        type_and_name = clean(row.get(COLUMN_MAP["type_and_name"]))
        if not address_raw:
            continue
        if not type_and_name and "patrz" in address_raw.lower():
            stats["cross_refs"] += 1
            continue

        primary, _, alt = address_raw.partition(" / ")
        primary = PREFIX_RE.sub("", primary.strip())
        # "(porównaj Stradomska 21)" and similar notes are not part of the address.
        primary_clean = re.sub(r"\(.*?\)", " ", primary).strip()
        street_text, number, _rest = split_street_number(primary_clean, index)
        street_text = street_text.strip(" ,-")
        canonical = index.resolve(street_text)
        if not canonical and not number:
            # e.g. "Balicka kościół": try the words before the description.
            words = street_text.split(" ")
            for i in range(len(words) - 1, 0, -1):
                canonical = index.resolve(" ".join(words[:i]))
                if canonical:
                    break
        street = canonical or street_text

        district_raw = row.get(COLUMN_MAP["district_number"])
        district_number = int(district_raw) if pd.notna(district_raw) else None
        rid = row.get(COLUMN_MAP["id"])

        records.append({
            "id": int(rid) if pd.notna(rid) else len(records) + 1,
            "street": street,
            "street_search": normalize(street),
            "building_number": number,
            "address_raw": address_raw,
            "alt_address": alt.strip(),
            "district_number": district_number,
            "district_name": DISTRICT_NAMES.get(district_number, ""),
            "type_and_name": type_and_name,
            "dating": clean(row.get(COLUMN_MAP["dating"])),
            "author": clean(row.get(COLUMN_MAP["author"])),
            "register_number": clean(row.get(COLUMN_MAP["register_number"])),
            "source": "Gminna Ewidencja Zabytków Miasta Krakowa",
            "status": "verified",
            "_street_resolved": bool(canonical),
        })
    return records, stats

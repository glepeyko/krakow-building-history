# Historia Twojego Domu — test version

A one-page site where a visitor types a Kraków street + building number and
sees whatever historical/architectural record exists for it. This is a static
site (no server, no database) — good enough for a first test on GitHub Pages,
not yet the production architecture from the full plan.

## What's in here

```
index.html                    the page
assets/style.css              styling
assets/script.js               autocomplete + search logic
data/buildings.json            6,364 building records (generated)
data/streets.json              1,192 unique street names, for the autocomplete (generated)
scripts/convert_excel_to_json.py   turns the source Excel into the two JSON files above
source-data/Buildings_in_Krakow_EXCEL.xlsx   your original file, kept for reproducibility
```

## Where the current data comes from

Your Excel file is the **Gminna Ewidencja Zabytków Miasta Krakowa** (the city's
municipal register of heritage buildings) — for each entry it has: district,
address, building type/name, dating, architect (when known), and a formal
register number (only for legally protected monuments). That's why most
buildings *don't* have an architect listed, and only some have a register
number — that's true to the source, not a gap in the conversion.

About 1 in 7 rows were cross-reference lines ("ul. X — patrz Y", i.e. "see Y")
that just point to another entry rather than describing a building — those
are skipped automatically.

## Running it locally

Browsers block `fetch()` on files opened directly (`file://`), so you need a
tiny local server — no build step, no npm install:

```bash
cd krakow-house-history
python3 -m http.server 8000
# then open http://localhost:8000
```

## Putting it on GitHub Pages

1. Push this folder as a repo.
2. Repo → Settings → Pages → Deploy from branch → `main`, folder `/ (root)`.
3. Your site will be live at `https://<username>.github.io/<repo-name>/`.

## Updating the data

If you correct or extend `source-data/Buildings_in_Krakow_EXCEL.xlsx` (or add
a new Excel with the same columns), regenerate the JSON with:

```bash
python3 -m pip install pandas openpyxl   # first time only
python3 scripts/convert_excel_to_json.py source-data/Buildings_in_Krakow_EXCEL.xlsx
```

This overwrites `data/buildings.json` and `data/streets.json`. If your future
column names differ, edit `COLUMN_MAP` at the top of the script — nothing
else needs to change.

## Known limitations of this test version

- **Contact form has no backend.** It currently opens the visitor's email
  client via a `mailto:` link (edit `CONTACT_EMAIL` in `assets/script.js`).
  For a real deployment, swap this for a form service like Formspree, or a
  small serverless function — no code changes needed elsewhere on the page.
- **~5% of addresses (328 of 6,364) have no cleanly parsed building number** —
  these are entries like "wiadukt" or "bateria fortu" that describe a
  structure rather than a standard street address. They're still in the data
  but won't surface through the number-based search.
- **`buildings.json` is ~2.4 MB.** Fine for a test/demo load, but worth
  splitting (e.g. by first letter of street) if the dataset grows a lot once
  you start adding AI-researched entries for non-heritage buildings.
- **No AI-enrichment pipeline yet.** This version only surfaces what's
  already in your Excel file. The next step, per the earlier plan, is adding
  the research pipeline for addresses not covered by this heritage register.

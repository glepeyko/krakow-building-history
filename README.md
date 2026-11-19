# Historia Twojego Domu — test version

A one-page site where a visitor types a Kraków street + building number and
sees whatever historical/architectural record exists for it. This is a static
site (no server, no database) — good enough for a first test on GitHub Pages,
not yet the production architecture from the full plan.

## What's in here

```
index.html                     the page
assets/style.css               styling
assets/script.js               autocomplete + search logic
data/streets.json              all streets, for the autocomplete (generated)
data/streets/*.json            one data file per street (generated)
scripts/sources/gez.py         reads the GEZ Excel register
scripts/sources/fetch_wikidata.py   downloads Wikidata items in Kraków
scripts/sources/fetch_osm.py   extracts Kraków addresses, street tags and district boundaries from OpenStreetMap
scripts/sources/fetch_wikidata_streets.py   street name origins and former names (Wikidata)
scripts/sources/fetch_nid.py   NID register of monuments, Kraków rows (dane.gov.pl)
data/research/ai_drafts.json   AI-researched, source-cited texts (labelled, unverified)
scripts/lib/address.py         address normalization + street matching
scripts/build.py               merges all sources into data/
tests/                         unit tests (python -m unittest discover tests)
reports/coverage.md            how much we know (generated)
source-data/Buildings_in_Krakow_EXCEL.xlsx   the GEZ register
PLAN.md                        development plan
CLAUDE.md                      project brief for Claude Code
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

```bash
python -m pip install -r requirements.txt     # first time only
python scripts/sources/fetch_wikidata.py      # ~2 min
python scripts/sources/fetch_osm.py           # downloads ~220 MB, ~4 min
python scripts/sources/fetch_wikidata_streets.py  # ~2 min, after fetch_osm
python scripts/sources/fetch_nid.py           # ~30 MB CSV, <1 min
python scripts/build.py                       # ~10 s, writes data/ and reports/
```

Sources: GEZ (city register), Wikidata (CC0), OpenStreetMap
(© OpenStreetMap contributors, ODbL — the footer credits it).

## Working with Claude Code

`CLAUDE.md` in this folder is a project brief written for Claude Code, so it
has working context without you re-explaining the project each session.

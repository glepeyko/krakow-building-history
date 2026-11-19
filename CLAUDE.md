# Historia Twojego Domu — project brief for Claude Code

## What this project is
A one-page Polish-language website. A visitor types a Kraków street and a
building number. The site shows historical and architectural information
about that building, if the database has it.

## Current state (test version)
- Static site. Files: `index.html`, `assets/style.css`, `assets/script.js`.
- No backend and no database server.
- Data files: `data/buildings.json` (6,364 records), `data/streets.json`
  (1,192 street names for the autocomplete).
- Data source: Gminna Ewidencja Zabytków Miasta Krakowa (the city's heritage
  register). The file `scripts/convert_excel_to_json.py` builds the JSON
  files from `source-data/Buildings_in_Krakow_EXCEL.xlsx`.
- The autocomplete matches street names without Polish diacritics, and
  matches on any part of the name, not just the start.
- The contact form only opens a `mailto:` link right now. It has no
  real backend. The placeholder address is `CONTACT_EMAIL` in `script.js`.

## Known limitations
- The database only has heritage-listed buildings. Most Kraków addresses
  will show "not found." This is expected, not a bug.
- 328 addresses (about 5%) have no parsed building number. These are
  entries like "wiadukt" or "bateria fortu" — a structure, not a normal
  street address.
- `buildings.json` is about 2.4 MB. The browser loads the whole file at
  once. This is fine for a test site. It will need a better approach
  (such as splitting the file, or a real backend) if the dataset grows.
- There is no AI-research step yet. The site only shows what is already
  in the Excel file.

## Longer-term plan (for context — do not build all of this at once)
1. Add a "research on demand" path: when a visitor searches an address
   with no entry, queue the address, or show an AI-drafted entry marked
   "AI-generated, unverified."
2. Give each entry a status field: `not_researched`, `ai_draft_unverified`,
   or `verified`.
3. Add a real backend for the contact form, and a "report a mistake" link
   on each building that is tied to that building's id.
4. Consider a small database (such as Supabase/Postgres) once the data
   grows past flat JSON files, or once more than one person edits entries.

## Working conventions — please follow these
- Keep the site in Polish. Keep it text-focused. Keep it one page.
- Keep the diacritic-normalized, substring-match autocomplete. Do not
  replace it with an exact-match-only search.
- New building records must match the field names already used in
  `data/buildings.json`. Open that file and check one record for the
  exact schema before you add new records.
- The visual design is a deliberate choice: warm paper background,
  Fraunces + Source Sans 3 + JetBrains Mono fonts, a patina-green and
  brass accent color. Ask the user before you change this direction.
- Before each work session, read this file first.
- At the end of a work session, update this file: add what changed, and
  update "Known limitations" if something was fixed or something new
  came up. This file is how the next session knows the current state.

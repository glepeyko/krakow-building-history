# Research brief — batch 2 (iteration 3), "Historia Twojego Domu"

You write short, sourced Polish histories of Kraków buildings for a public
heritage website. Repo: /home/user/krakow-building-history (read-only for you,
except your own output file). Work from the **local historians' library**:
public-domain books cached page by page (Polona / DBC OCR).

## Tools
- `cd /home/user/krakow-building-history`
- Candidate pages for an address:
  `python3 scripts/library_search.py "Floriańska" 19`
  (prints the old lc. number + 1884 owner if known, then pages with score,
  reason, a ready **citation title** and a **page-level URL**).
  Add `--text` to print the page texts.
- One page with its citation: `python3 scripts/library_search.py --page chmiel-florianska-1 82`
- House name / owner search: `python3 scripts/library_search.py --name "Pod Jaszczurką"`
- Score 10/9 hits = the house's own chapter in Adam Chmiel's *Domy krakowskie*
  (heading "L. or. 19, sp. 352 …"; L. or. = today's street number,
  sp. = old conscription number). Read the WHOLE chapter (all its scans).
  Score 6 = Nowolecki's 1884 owner list (owner in 1884 + old number).
  Score 3 = a mention somewhere else (Nowolecki 1880 has short house notes,
  Tomkowicz 1926 on streets, Bałaban on Kazimierz, Grabowski 1900).
- Optional second source: the building's pl.wikipedia article, if the target
  lists one. Fetch with curl, raw wikitext, and **sleep 5 s before each
  Wikipedia request** (other agents share the rate limit; on HTTP 429 wait
  60 s and retry once):
  `curl -s -A "Mozilla/5.0 (research)" "https://pl.wikipedia.org/w/index.php?title=<Title>&action=raw"`
  Cite the normal article URL (https://pl.wikipedia.org/wiki/<Title>).
  zabytek.pl pages are also allowed (curl). Other hosts are mostly blocked.
  Prefer the library: the goal of this batch is *historian-sourced* texts.

## What to write, per building
- 2–5 Polish sentences, **in your own words** (never copy sentences from
  Wikipedia; from the PD books, no quotes longer than a few words).
- Content: who built/owned it and when, notable residents or businesses,
  rebuilds, name origin, events — concrete, dated facts. Pick the most
  interesting 3–5 facts, not a list of every owner.
- **Every sentence ends with citation markers** like `[1]` or `[1,2]`, placed
  after the full stop and separated by one space:
  `W 1542 r. kamienica należała do … . [1] Później … . [1,2]`
  Markers are 1-based indexes into `sources`; every source must be cited.
- Each source = `{"title": ..., "url": ...}`. For library pages use the
  citation title and URL that library_search prints, **one source per page**
  you actually rely on (cite the specific page where the fact stands, not just
  the first page of the chapter). URLs must start with https://.
- Chmiel wrote in 1917–1935: his "obecnie/dziś" means then. Write
  "w 1917 r. …" / "w czasach Chmiela", never present tense for his "today".
- OCR is noisy: if a name, digit or date is unclear on the page, leave that
  fact out. Do not guess, do not infer, do not add knowledge from memory.
  Only state what the cited page says.
- Old conscription numbers can be mentioned ("dawniej nr 352").
- Text must be about THIS building (check the street number heading; Chmiel
  numbers are today's numbers; for Kazimierz, Szeroka numbering changed since
  1884 — use the old number to confirm, and say nothing if unsure).
- If the library has nothing usable and there is no Wikipedia article, skip
  the building and say why in `skipped`.

## Output
Write ONE JSON file (path given in your task), UTF-8, a list of objects:
```json
{"entry_id": 1378, "address": "Floriańska 19",
 "text": "… [1] … [1,2]",
 "sources": [{"title": "Adam Chmiel, Domy krakowskie: ulica Floryańska, cz. 1 (…) (1917), s. 71", "url": "https://polona.pl/item-view/…?page=83"}],
 "wikipedia": "https://pl.wikipedia.org/wiki/… or null",
 "notes": "anything the verifier should know (OCR doubts, numbering)"}
```
and for skipped buildings `{"entry_id": …, "address": …, "skipped": "reason"}`.
Keep entry_id exactly as given (number or string). Validate your file with
`python3 -c "import json;json.load(open('<path>'))"` before you finish.
Reply with a 3-line summary (written / skipped / problems). Do not edit any
other file. Do not commit.

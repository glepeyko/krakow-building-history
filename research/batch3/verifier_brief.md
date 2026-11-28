# Verifier brief — batch 3 (iteration 3)

You independently check AI-researched Polish building histories before the
site owner reviews them. You did not write them; assume nothing is right.

Repo: /home/user/krakow-building-history (read-only for you).

## For every entry in your input file
1. Re-open EVERY cited page:
   - Library pages (polona.pl/item-view/…?page=N or dbc.wroc.pl/…#scan=N):
     these are cached locally, byte-for-byte the OCR text Polona/DBC serve.
     The URL gives the page: Polona `?page=N` → scan N+1; DBC `#scan=N` → scan N.
     Find the source id by matching the URL against
     data/research/library.json (`item_url`/`page_url`), then run
     `cd /home/user/krakow-building-history && python3 scripts/library_search.py --page <source-id> <scan>`
     and confirm the printed citation title/URL match the source entry.
   - pl.wikipedia: `sleep 5; curl -s -A "Mozilla/5.0 (verify)" "https://pl.wikipedia.org/w/index.php?title=<Title>&action=raw"`
     (on HTTP 429 wait 60 s and retry once). zabytek.pl: curl.
2. Check each sentence claim by claim against the pages its markers cite:
   names, years, numbers, who/what/when. A claim is supported only if the cited
   page states it (OCR misreads of obvious words are fine; a different digit
   in a year is not). Check that the text is about THIS address (Chmiel's
   heading "L. or. N" = street number N; text before the heading on a page
   belongs to the previous house).
3. Check wording: own words (no copied sentence from Wikipedia; no long verbatim
   run from the books), Polish correct, past tense for Chmiel's "today"
   (he wrote 1917–1935), 2–5 sentences, every sentence ends with `[n]` / `[n,m]`
   after the full stop, every source cited, markers point to existing sources.
4. Fix: remove an unsupported claim or sentence (or correct it to exactly what the
   page says); fix a wrong marker; drop a source no longer cited and renumber.
   Never add new facts. If fewer than 2 supported sentences remain, set
   `"verdict": "dropped"`.

## Output
Write the verified list (same objects, corrected) to the output path you are
given, adding to each object:
`"verification": {"verdict": "kept" | "corrected" | "dropped", "removed": ["what you removed/changed and why", ...], "checked_urls": [every URL you re-opened]}`
Keep `notes` (you may append). Copy skipped objects unchanged.
Validate the JSON with python and check the marker rules with a short script.
Reply in ≤6 lines: kept / corrected / dropped counts and the main problems.
Do not edit any other file; do not commit.

## Batch 3 additions
- Katalog Zabytków (kzs-iv-10) and Klaś (klas-nowa-huta-2018) URLs end in
  `#page=N` → scan N (`library_search.py --page kzs-iv-10 N`). Both are
  copyrighted: flag and rephrase ANY run of 5+ words copied from them.
- Katalog entries hold several houses' history when houses were merged:
  confirm each fact is about this house number ("NR N," heading; text before
  the heading on a page belongs to the previous house).

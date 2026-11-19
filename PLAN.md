# Development plan — Historia Twojego Domu

Goal: a visitor types any Kraków address and finds **something interesting**
about that building — and, when we know nothing about the building itself,
about its street, its block, and what stands nearby.

## Progress

- **Iteration 1 — done (2026-11-19).** Phase 0 complete; Phase 1 partly
  (Wikidata + OSM; NID register, Wikipedia street articles and photos on the
  page still open); Phase 2 partly (all OSM addresses searchable, "nearby"
  places; street history and districts still open).
  Numbers: see `reports/coverage.md`.
- **Iteration 2 — done (2026-11-19).** Phase 1: NID register linked
  (1,113 entries). Phase 2: street stories for 550 streets (named after,
  former names, article link), a district for 95% of addresses, nearby
  places for ~95% of addresses (600 m fallback). Phase 3 started: pilot of
  26 AI-drafted, source-cited, verifier-checked descriptions (labelled).
  Numbers: `reports/coverage.md`.
- **Next (iteration 3 proposal):**
  1. More street stories: parse former names and naming dates from the
     "Ulica X w Krakowie" articles (facts only, own wording), and link
     street articles that have no Wikidata P131 Kraków.
  2. Fix the Wikidata ↔ GEZ gap the pilot exposed (famous Rynek houses
     with an article but no link): match by Wikipedia article title /
     NID inspire id.
  3. 166 NID rows whose address has no entry → new entries
     (`source: "Rejestr zabytków NID"`).
  4. AI research batch 2 (~50–100 buildings: Kazimierz, Podgórze, Kleparz),
     same research → verifier flow; owner review of batch 1.
  5. Deduplicate "nearby" across sources (same object from GEZ/Wikidata/OSM).
  6. Drop addresses outside Kraków (postcode filter leaks neighbours) or
     label them with their municipality.

## Where we started (Nov 2026)

- 6,364 records from the Gminna Ewidencja Zabytków (GEZ). Per record we only
  have: type/name (~23 chars), dating, architect (44% of records), register
  number (19%), district. No descriptions, coordinates, photos or sources
  beyond GEZ.
- GEZ covers only heritage-listed buildings, a small share of Kraków's
  addresses. Everything else returns "not found".
- Static site, no git repo, no tests, no deployment yet.

The two problems are **depth** (thin records) and **coverage** (most addresses
missing). The plan attacks both, cheapest and most reliable sources first,
AI-written content last and always labelled.

## Guiding rules

1. **Every fact carries its source.** Records move from flat fields to
   "facts with citations" (source name + URL). That is what makes the site
   trustworthy and makes AI drafts reviewable.
2. **Structured open data before AI.** Wikidata, OpenStreetMap, the national
   heritage register and Wikipedia are free, attributable and mostly correct.
   AI research fills gaps afterwards.
3. **Never show "nothing".** If the building has no entry, show street
   history, the district, and notable buildings within ~150 m.
4. **Licences respected.** Wikidata = CC0; OSM = ODbL (attribution);
   Wikipedia text = CC BY-SA (we write our own summaries and link, rather
   than copying text); Commons photos = per-file licence, shown with credit.
5. **Static as long as possible.** Data split into per-street files so the
   site stays fast on GitHub Pages; a backend only when we need writes
   (reports, research queue).

## Phases

### Phase 0 — Foundation (iteration 1, small)
- `git init`, `.gitignore`, first commit; optional GitHub repo + Pages deploy.
- Restructure the pipeline: `scripts/sources/*` (one fetcher per source,
  raw downloads cached in `source-data/raw/`), `scripts/build.py` (merge →
  site JSON). Re-runnable end to end.
- Canonical **address key** (normalized street + number, handling `ul.`/`al.`,
  diacritics, "12a" vs "12 A", ranges "5-7", corner buildings with two
  addresses). Every source gets matched through this one function.
- Small test suite for the address normalizer and the build output.
- A **coverage report** (`reports/coverage.md`): how many addresses have
  which kinds of facts. This is the scoreboard for every later iteration.

### Phase 1 — Enrich the 6,364 known buildings (iterations 1–2)
Sources, matched by address and/or coordinates:
- **Wikidata (SPARQL):** every item located in Kraków with a street address
  or coordinates → coordinates, architect, construction date, style,
  heritage designation, Wikipedia article link, Commons image/category.
- **Polish Wikipedia:** articles for buildings and the
  "Ulica X w Krakowie" articles, many of which list buildings with notes.
  We store a link plus a short summary we write ourselves.
- **National heritage register (NID, rejestr zabytków)** open data:
  official names, register dates, coordinates, sometimes descriptions.
- **Wikimedia Commons:** one representative photo per building, with credit.
- **OSM:** coordinates and `wikidata`/`heritage` tags for matching.

Site changes: show sources and links per fact, a photo when available, a
"Na mapie" link. (Design check with you before adding photos/map — the brief
says text-focused.)

### Phase 2 — Cover every address (iteration 3)
- Import **all address points in Kraków from OpenStreetMap** (tens of
  thousands; exact count measured in iteration 1) with whatever OSM knows:
  building type, levels, `start_date`, architect, name.
- For every address, compute:
  - **nearby notable places** (heritage buildings, plaques, monuments within
    ~150 m) — so a 1970s block still gets "you live 80 m from the 1912 villa
    by X";
  - **street story:** patron of the street name, when it was named, former
    names (German occupation, PRL renamings) — Wikipedia street articles,
    Wikidata `named after`, city resolutions;
  - **district/osiedle context:** when the area was incorporated into
    Kraków, what it was before.
- Search then never dead-ends; "not found" becomes "Nie mamy jeszcze
  opisu tego budynku — oto co wiemy o okolicy".
- Data split into per-street JSON shards loaded on demand.

### Phase 3 — Deep research with AI, labelled (iterations 4+, ongoing)
Run inside our work sessions (no API costs on the site itself):
- **Research agents** take a batch of addresses (priority: Stare Miasto,
  Kazimierz, Podgórze, Kleparz, Piasek, then by search demand), search the
  web/digital libraries, and write a 2–5 sentence Polish entry: who built it,
  who lived there, events, curiosities — **every sentence tied to a source
  URL**.
- A separate **verifier agent** re-checks each claim against the cited
  source and drops anything unsupported.
- Entries get `status: "ai_draft_unverified"` and a visible label. You (or a
  later reviewer) can promote them to `verified`.
- Useful sources: Wikipedia, Encyklopedia Krakowa, Muzeum Krakowa,
  Małopolska Biblioteka Cyfrowa / Polona (old address books, newspapers),
  Wirtualny Sztetl (Jewish Kraków), lists of memorial plaques, Kraków
  heritage office publications.
- Realistic pace: roughly 50–150 well-sourced entries per session, so we
  prioritize instead of trying to cover everything.

### Phase 4 — Feedback loop (when you want the site public)
- "Zgłoś błąd / dodaj informację" per building, tied to its id — via a free
  form service (Formspree / Google Form) first, Supabase later.
- Log **searched-but-empty addresses** (needs a tiny backend or a form
  endpoint) → this becomes the research queue for Phase 3.
- Optional "zaproponuj badanie tego adresu" button feeding the same queue.

### Phase 5 — Nice-to-haves (later)
- Historical maps overlay (Kraków MSIP archival maps), "then and now".
- Permalinks per building (`?ul=Floriańska&nr=14`) for sharing.
- SEO: static per-building pages so Google finds "historia kamienicy
  Floriańska 14".
- Thematic walks generated from the data (e.g. "Secesja na Piasku").

## How we work with sub-agents

| Agent | Job | Runs |
|---|---|---|
| Source fetchers (1 per source) | Download + parse Wikidata / OSM / NID / Wikipedia | in parallel, Phase 1–2 |
| Matcher | Link source records to addresses, report ambiguous matches | after fetchers |
| Frontend | Page changes, keeps design and Polish copy | parallel with data work |
| Researchers (N in parallel) | Write sourced entries for address batches | Phase 3 |
| Verifier | Check every AI claim against its citation | after each research batch |
| Reviewer | Code review + coverage report before I hand an iteration to you | end of each iteration |

## Iteration rhythm
Each iteration ends with: a git commit, an updated `reports/coverage.md`
(before/after numbers), 10 sample addresses for you to spot-check, an
updated `CLAUDE.md`, and a short list of decisions I need from you.

## Decisions I need from you
1. OK to `git init` and, later, create a GitHub repo + Pages deploy?
2. OK to add photos and a small map link (a change to the text-only design)?
3. Are AI-drafted entries acceptable on the public site if clearly labelled,
   or should they stay hidden until you approve them?
4. A real contact e-mail for the form (replaces `CONTACT_EMAIL`).

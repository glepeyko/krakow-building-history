# Free online books and studies on Kraków buildings: source survey

Checked 2026-11-20 from a home connection in Poland (Windows, curl + WebFetch).
I opened every source listed in sections 1–3 and fetched a page, PDF or OCR
text from it. "Script-fetchable" means plain `curl` with a browser User-Agent
worked, with no login, CAPTCHA or JS challenge.

Already in use and not re-surveyed in depth: Chmiel "Domy krakowskie" (DBC),
Krasnowolski 2017 (Muzeum Krakowa PDF), Wikipedia, Wikidata, GEZ, NID. New
text routes for Chmiel are listed below (Polona OCR, Internet Archive OCR).

**Copyright rule of thumb used below.** In Poland, a work becomes public domain
(PD) 70 years after the author's death. So authors who died before 1 Jan 1956
are PD. Anonymous or corporate works such as address books and street lists
become PD 70 years after publication. Facts are not protected by copyright in
any case. Short facts restated in our own words, with a citation, are fine for
every source here, including CC BY-NC-ND and all-rights-reserved works. Long
verbatim quotes are fine only from PD works.

---

## 1. Ranked table (most useful first)

| # | Source (author, title, year) | Covers | Access URL | Format | Licence | Script | Use |
|---|---|---|---|---|---|---|---|
| 1 | Instytut Sztuki PAN, *Katalog Zabytków Sztuki w Polsce, t. IV: Miasto Kraków*, cz. 1–8, 10–12 (1965–2016) | House-by-house entries for Rynek Główny + walls/Planty (cz. 10), ul. Sławkowska (cz. 11), ul. św. Jana (cz. 12). Also churches/monasteries of Śródmieście, Kazimierz, Stradom, Kleparz, Zwierzyniec; Judaica of Kazimierz; Wawel | https://repozytorium.ispan.pl/dlibra/collectiondescription/68 | Searchable PDF (text layer), 40–120 MB per part | © Instytut Sztuki PAN, "dostęp nieograniczony" (open access, all rights reserved) | Yes (PDFs via `/Content/<id>/<file>.pdf`); HTML pages show a "High Load" JS wall after a few quick requests | **High** |
| 2 | Aleksander Nowolecki (ed.), *Wykaz ulic, placów, kościołów i domów miasta Krakowa…* (1878, 1880) and *Nowy wykaz ulic, placów, kościołów i właścicieli domów miasta Krakowa…* (1884) | Every house in Kraków, its suburbs and Podgórze: old conscription number ↔ street number, owner names, notes on former uses (e.g. "in 1813 a hospital for the poor") | Polona: https://polona.pl/item-view/1543c6ff-7fbc-4d5a-a4b9-d50b3e6e702d (1878), https://polona.pl/item-view/d01c8711-8acb-4c77-9fce-d7225282250d (1880), https://polona.pl/item-view/9ee2b213-1bd9-4b66-87bb-c489c0a987d4 (1884) | OCR text (Polona full-text ZIP) | PD | Yes (Polona API) | **High** |
| 3 | Adam Chmiel, *Domy krakowskie* (Biblioteka Krakowska, 1917–1932): Floriańska, św. Jana, Sławkowska parts | House-by-house owner histories, from the medieval period to the 19th c. | Polona OCR: Sławkowska cz. 1 https://polona.pl/item-view/52d1945f-f916-486f-8d0e-e67054d0286c, cz. 2 https://polona.pl/item-view/db15e53d-3db9-48cb-99b1-5d7d06bb6896 ; IA OCR of DBC copies: https://archive.org/details/dbc.wroc.pl.006422 (Floriańska 16–44), https://archive.org/details/dbc.wroc.pl.004593 (Floriańska 2–14), https://archive.org/details/dbc.wroc.pl.006421 (św. Jana 2–32) | OCR text | PD (Chmiel d. 1934) | Yes | **High** (already used; new text routes) |
| 4 | *Księga adresowa Królewskiego Stołecznego Miasta Krakowa* (and Podgórze), annual volumes 1906, 1907, 1908, 1909, 1910, 1912, 1913, 1914, 1925, 1926, 1932 (hosted by Małopolskie Towarzystwo Genealogiczne); 1933/34 volume in Śląska BC | Residents and businesses with street addresses; "who lived here" for every street | Index: https://genealogyindexer.org/directories (Kraków section). Example: https://www.mtg-malopolska.org.pl/images/skany/ksiegaadresowa1913djvu/ksiegaadresowa1913.pdf ; 1933/34: https://sbc.org.pl/dlibra/publication/edition/567644 | PDF with OCR text layer (noisy: about 390k words in 1913, many OCR errors) | PD (corporate/anonymous, >70 years) | Yes (40–116 MB PDFs) | **High** for residents; needs care with OCR |
| 5 | Towarzystwo Miłośników Historii i Zabytków Krakowa, *Rocznik Krakowski*, t. 1–83 (1898–2017) and t. 85–91 (2019–2025) | The main scholarly yearbook on Kraków history: house monographs, streets, architects, districts | t. 1–83: http://old.mbc.malopolska.pl/dlibra/publication?id=13440&tab=3 (PDF per volume, e.g. `/Content/12212/rocznik_krakowski_1898_001.pdf`, `/Content/107703/rocznik_krakowski_2014_080.pdf`); prewar vols also on IA with OCR, e.g. https://archive.org/details/jbc.bj.uj.edu.pl.NDIGCZAS102384_6_006 ; t. 85+: https://journals.akademicka.pl/rocznikkrakowski/issue/archive | PDF with text (MBC), clean OCR djvu.txt (IA), born-digital PDF (2019+) | Pre-1956 authors PD; later volumes in copyright, open access; 2019+ CC BY-NC-ND 4.0 | Yes. old.mbc works **only over http://** and was intermittent (worked, then timed out later the same evening); IA and akademicka are reliable | **High** |
| 6 | Stanisław Tomkowicz, *Ulice i place Krakowa w ciągu dziejów: ich nazwy i zmiany postaci* (1926) | History and former names of every Old Town and inner-suburb street and square | https://polona.pl/item-view/199fcdeb-c01d-4c30-8874-a5296572674b | OCR text (424 KB, good quality) | PD (Tomkowicz d. 1933) | Yes | **High** (street stories) |
| 7 | Majer Bałaban, *Historja Żydów w Krakowie i na Kazimierzu 1304–1868*, t. 1 (1931), t. 2 (1936) | Kazimierz: houses, synagogues, streets, families | t. 1 https://polona.pl/item-view/50e2db2c-a4c8-4bd8-b1af-05b381186fcb ; t. 2 https://polona.pl/item-view/4f595d2a-1107-4c4f-a829-a572c4e44e51 | OCR text (1.2 MB for t. 1) | PD (Bałaban d. 1943) | Yes | **High** for Kazimierz |
| 8 | *Teka Grona Konserwatorów Galicyi Zachodniej*, t. I–V (1900–1913; t. IV by Tomkowicz on Wawel buildings) | Conservation reports on Kraków buildings around 1900 | t. I https://archive.org/details/dbc.wroc.pl.005019 ; t. II https://archive.org/details/dbc.wroc.pl.004999 ; t. II–V JBC copies on IA, e.g. https://archive.org/details/jbc.bj.uj.edu.pl.NDIGDRUK001749_04 | OCR text (IA djvu.txt) | PD | Yes | Medium-high |
| 9 | *Krzysztofory. Zeszyty Naukowe Muzeum Historycznego Miasta Krakowa* (Muzeum Krakowa), t. 17 (1990) onward | Museum-yearbook articles on buildings, conservation (e.g. Pałac Krzysztofory 1917–2005), Kraków guidebook bibliography | https://journals.akademicka.pl/krzysztofory/issue/archive ; individual PDFs also at https://muzeumkrakowa.pl/plik-do-pobrania/297 (and other ids) | Born-digital PDF with text | CC BY-NC-ND 4.0 (journal policy) | Yes | Medium-high |
| 10 | Jarosław Klaś (ed.), *Nowa Huta: architektoniczny portret miasta drugiej połowy XX wieku* (2018, OK Norwida) | Nowa Huta estates and buildings, block by block (e.g. "Blok na os. Wandy") | https://ruj.uj.edu.pl/handle/item/63868 (PDF: https://ruj.uj.edu.pl/server/api/core/bitstreams/007a4b1d-31a8-487b-918f-4e477f49304b/content) | Born-digital PDF, 22 MB | CC BY-NC-ND 3.0 | Yes | **High** for Nowa Huta |
| 11 | Stanisław Tomkowicz, *Domy i mieszkania w Krakowie w pierwszej połowie XVII wieku* (1922) | Burgher houses, room layouts, inventories, 17th c. | https://archive.org/details/dbc.wroc.pl.011242 | OCR text | PD | Yes | Medium |
| 12 | Józef Jezierski (publ.), *Ilustrowany przewodnik po Krakowie i okolicy* (annual, 1903–1909); *Najnowszy illustrowany przewodnik po Krakowie* (1883); *Najnowszy zwięzły przewodnik po Krakowie* (1930, 1936); *Ilustrowany przewodnik po Krakowie* (1932) | Period guidebooks: notable buildings and institutions with addresses | e.g. https://polona.pl/item-view/5dc32a12-1672-48a3-bf91-fd6576305174 (1908–09), https://polona.pl/item-view/cc79a55f-e1fb-457f-9161-f4426b42610a (1883), https://polona.pl/item-view/f0a856a3-43a0-4a87-af6a-ebd0deca5a36 (1936), https://polona.pl/item-view/1fdfc279-e0c5-4941-a791-529c3fb48aa1 (1932) | OCR text | PD per Polona (check author per volume for interwar ones) | Yes | Medium |
| 13 | Ambroży Grabowski, *Kraków i jego okolice* (editions 1844, 1866, 1900) | Classic 19th-c. description of the city, churches, houses, suburbs | https://polona.pl/item-view/74ea4ffd-a4f9-435e-91f7-99036338ecd8 (1866, OCR), https://polona.pl/item-view/285d55bc-70d2-4a60-b8ab-1eaa56d49951 (1900, OCR) | OCR text | PD (d. 1868) | Yes | Medium |
| 14 | August Essenwein, *Die mittelalterlichen Kunstdenkmale der Stadt Krakau* (1866/1869) | Medieval buildings of the Old Town (German) | https://polona.pl/item-view/d1e2ddc2-1bc6-401c-a878-56a4c3db0f48 (1869, OCR) | OCR text | PD | Yes | Medium (Old Town medieval only) |
| 15 | Internet Archive, collection `polishpublicdomain` plus mirrors of JBC and DBC (access channel, not a single work) | Over 51,000 Kraków-related PD texts: books, newspapers, yearbooks | e.g. search `https://archive.org/advancedsearch.php?q=title:("rocznik krakowski")&fl[]=identifier&output=json` | Clean OCR (`<id>_djvu.txt`) + PDF | Items marked "Domena publiczna" | Yes, very script-friendly (metadata API, stable URLs) | **High** (infrastructure) |
| 16 | Polona (Biblioteka Narodowa) (access channel, not a single work) | Aggregates BN + JBC + other libraries; most PD items have OCR | Search API: `POST https://polona.pl/api/search-service/search/simple?query=…&page=0&pageSize=…` (body `{}`); full text: `https://polona.pl/api/search-service/fulltext/polona/fulltext/content/<uuid>` (ZIP with .txt); ALTO: `…/download/library-objects/<uuid>/ocr_alto`; item page: `https://polona.pl/item-view/<uuid>` | JSON / OCR text / ALTO XML | Each record carries `copyrightProtected` and `licenseName` | Yes, no key, no login | **High** (infrastructure) |
| 17 | *Architekt: Pismo o Architekturze, Budownictwie i Przemyśle Artystycznym* (Kraków, ed. W. Ekielski), 1900 onward | Contemporary reports on new Kraków buildings and competitions around 1900 | e.g. https://archive.org/details/dbc.wroc.pl.002511 (1900 nr 3); only a few issues found on IA (nr 3, 6, 9 of 1900) | OCR text | PD | Yes | Medium (few issues found online so far) |
| 18 | *Jan Zawiejski – architekt przełomu XIX i XX w.* (1986; author not shown in the API record: confirm on the item page) | Monograph of the architect of the Słowacki Theatre and many Kraków buildings | https://polona.pl/item-view/d6b20bfb-3013-4046-8ac4-f617f14df255 | OCR text (750 KB) | "Zawartość chroniona – licencja otwarta" (in copyright, open licence on Polona) | Yes | Medium (architect attributions) |
| 19 | Czasopismo Techniczne / Technical Transactions, Architektura series (Politechnika Krakowska, on ejournals.eu) | Articles on Kraków architecture, incl. interwar tenements and Nowa Huta (e.g. A. Sumorok, "Idea miasta socjalistycznego. Przypadek Nowej Huty", 12-A/2015) | https://www.ejournals.eu/Czasopismo-Techniczne/ ; example PDF https://ejournals.eu/en/journal_article_files/full_text/018eced7-7338-73c2-a8ac-2376167efca0/download | Born-digital PDF | Open access ("Licencja: Żadna, open access" on journal page = all rights reserved, free to read) | Yes | Medium (20th-c. districts) |
| 20 | Rocznik Krakowski, modern articles on outer districts. Example: P. Dettloff, "Zapomniana enklawa domów w ogrodach na Krowodrzy" (RK 89, 2023) | Villas and estates outside the Old Town | https://journals.akademicka.pl/rocznikkrakowski/article/download/5645/5258/7642 | Born-digital PDF | CC BY-NC-ND 4.0 | Yes | Medium-high (see #5) |
| 21 | Google Books full view: A. Grabowski *Starożytnicze wiadomości o Krakowie* (1852); J. Łepkowski *Starożytności i pomniki Krakowa* (1847); W. Łuszczkiewicz *Zabytki sztuk pięknych Krakowa* (1872); J. Mączyński *Kraków dawny i teraźniejszy* (1854); K. Bartoszewicz *Przewodnik po Krakowie… 600 adresów* (1890); J. Rostafiński *Przewodnik po Krakowie i okolicy wraz ze spis. ulic i skorowidzem adresów* (1891); A. Nowolecki *Wykaz ulic…* (1878); A. Chmiel *Domy krakowskie: ulica Sławkowska* (1932) | 19th-c. descriptions, guidebooks with address lists | e.g. https://books.google.com/books?id=YtNbAAAAcAAJ (Grabowski 1852), https://books.google.com/books?id=jYyBmbp44PwC (Rostafiński 1891), https://books.google.com/books?id=NBkDL0QtirsC (Nowolecki 1878), https://books.google.com/books?id=3bsZAAAAIAAJ (Chmiel 1932) | Full view, page images + Google OCR | PD | **No.** The legacy feed `google.com/books/feeds/volumes/<id>` confirms `view_all_pages`, but page text (`&output=text`) returns 403 "automated queries" and the v1 API returned 429 | Medium for humans; low for the pipeline (use Polona/IA copies where they exist) |
| 22 | *Krakowski Rocznik Archiwalny* (Archiwum Narodowe w Krakowie), t. 1–31 (1995–2025) | Archival studies, incl. city records, building files, inventories | https://kra.ank.gov.pl/tomy-online/ (e.g. t. 24: https://kra.ank.gov.pl/wp-content/uploads/2021/06/Krakowski-Rocznik-Archiwalny-24_2018.pdf) | Born-digital PDF, full volumes | Open access (rights reserved) | Yes | Medium-low (few house histories) |
| 23 | *Ze starego Krakowa: ulice, bramy, sienie* (DBC; author not in IA metadata) | Streets, gates and house entrance halls of old Kraków | https://archive.org/details/dbc.wroc.pl.005260 (original: https://dbc.wroc.pl/dlibra/doccontent?id=5083) | OCR text | PD per DBC | Yes | Medium-low |
| 24 | *Wieś Mogiła przy Krakowie, jej klasztor cysterski, kościółek farny i kopiec Wandy* (1899) | Mogiła (today part of Nowa Huta district): abbey, parish church, Wanda Mound | https://archive.org/details/dbc.wroc.pl.009812 | OCR text | PD | Yes | Medium-low (outer district) |
| 25 | *Wiadomości Konserwatorskie – Journal of Heritage Conservation* (SKZ / Politechnika Krakowska) | Conservation articles, some on Kraków buildings and Nowa Huta | BazHum index: https://bazhum.muzhp.pl/journals/856/issues/50511 ; issue PDFs at repozytorium.biblos.pk.edu.pl (see §3: down for maintenance) | Born-digital PDF | Open access | BazHum yes; PK repository no (maintenance redirect) | Low-medium |
| 26 | krakow.travel (city tourism portal) | Short descriptions of monuments, museums and routes | https://krakow.travel/ | HTML | City portal, rights reserved | Yes (HTTP 200 from here; it was unreachable from the cloud) | Low-medium (tourist level, rarely cites sources) |
| 27 | Europeana API (aggregator) | Re-exposes Polona / FBC records | `https://api.europeana.eu/record/v2/search.json?wskey=api2demo&query=…` | JSON metadata, links to providers | CC0 metadata; content per provider | Yes (demo key works) | Low (adds nothing over Polona/IA) |

Count: 27 entries checked as usable. Section 3 lists 18 more that were checked
and are not usable (or not usable yet).

---

## 2. Notes per source

### 2.1 Katalog Zabytków Sztuki, t. IV Miasto Kraków (IS PAN repository)
- Opened the collection page and edition pages. Parts found:
  cz. 1 Wawel (ed. 31756); cz. 2–3 Kościoły i klasztory Śródmieścia (31757, 31759);
  cz. 4–5 Kazimierz i Stradom, churches (31763, 31764); cz. 6 Kazimierz i Stradom, Judaica
  (31771); cz. 7 Zwierzyniec, Nowy Świat, Półwsie Zwierzynieckie (31772); cz. 8 Kleparz
  (edition id not captured; listed in the collection); cz. 10 Mury obronne, Planty,
  Rynek Główny (31773, file `kzs-t04-z08.pdf`); cz. 11 Ulica Sławkowska, cz. 12 Ulica
  św. Jana (in the collection list; edition pages were behind the "High Load" wall at
  that moment).
- Downloaded cz. 10 (39 MB, to the scratch folder, deleted afterwards). `pdftotext -enc UTF-8`
  gives clean text, e.g. "NR 12, kamienica Fontanowska … zajmująca dwie działki, na których
  do 1830 dwie kamienice – Gutteterowska oraz Fontanowska …". This is the
  most authoritative house-by-house source for the parts it covers. Each entry has a dated
  building history, owners and features.
- Rights field: "© Instytut Sztuki PAN"; access field: "dostęp nieograniczony".
  Cite facts, do not copy entries.
- Fetching: PDFs download directly from `https://repozytorium.ispan.pl/Content/<edition>/<file>.pdf`.
  Pace requests (one every few seconds). The dLibra HTML is behind a PIONIER
  "High Load – Verifying Browser" JS check after a burst.
- Cite as: *Katalog Zabytków Sztuki w Polsce*, t. IV, cz. X, p. N, with the PDF URL and
  `#page=N`. A verifier can open the PDF at that page.

### 2.2 Nowolecki street and house lists (1878, 1880, 1884)
- Polona OCR checked. The 1884 text lists owners by name with address and old number,
  e.g. "Romer Bronisław, ul. św. Anny 7 (199)". The 1880 edition adds short histories
  per house ("w r. 1813 szpital ubogich", "Jerzy Trasler miał tu drukarnię od 1803 do
  1809 roku").
- Use: the bridge between old conscription numbers (used by Chmiel, archival records,
  the KZS) and modern street numbers. It also gives "owner in 1880/1884" facts for
  every street, including Kazimierz, Podgórze and the inner suburbs.
- PD (1878–1884).

### 2.3 Chmiel, Domy krakowskie
- Polona has OCR for the Sławkowska volumes (1931, 1932). Two other Polona copies
  (św. Jana cz. 2, Floriańska cz. 2) are scans without OCR. The IA mirrors of the
  DBC copies have Tesseract OCR (`006422_djvu.txt`, 238 KB). Google Books also has
  Sławkowska 1932 in full view, but scripts cannot fetch it.
- The pipeline can now cite Chmiel at page level with a fetchable text, not
  only the DBC PDF.

### 2.4 Kraków address books (Księga adresowa), 1906–1933/34
- Genealogy Indexer's directory list points to scans hosted by Małopolskie
  Towarzystwo Genealogiczne (MTG). I opened the 1913 PDF (41.7 MB): it has an OCR text
  layer, about 391k words, e.g. (OCR reads "Lpstcin", normalized here) "Epstein … Juliusz, bankier, wł. r., radca m., Rynek gł. 12".
  OCR quality is poor (broken letters, merged columns). Good for "find the name at this
  address", but each hit must be checked against the page image. Also confirmed by HEAD
  request: 1932 (46 MB) and 1926 (75 MB). The 1933/34 volume is in Śląska BC
  (116 MB PDF, record marked "Domena publiczna").
- Not opened, but listed by Genealogy Indexer: 1905 directory (UEK library), 1929 and
  1924 telephone books (MTG), 1933 business directory (KUL dLibra), Józef Czech's
  *Kalendarz Krakowski* volumes 1882–1917 on old MBC and MTG.
- Use: "residents in 1913/1932" lines for any address in the city as it was then
  (Old Town, Kazimierz, Podgórze, Krowodrza, Ludwinów, etc.). Present it as a list,
  name + occupation, never as a narrative. Mind privacy: the entries are 90+ years old,
  but descendants exist, so keep it factual.
- Do not store the PDFs in the repo. Cache them in git-ignored `source-data/raw/`
  if we OCR them again.

### 2.5 Rocznik Krakowski
- old MBC lists t. 1–83 (no t. 4 in that list; IA/JBC has t. 4). Each volume is a single
  PDF (t. 1 is 130 MB) with a text layer (`/Font` objects present).
- The IA mirrors of the JBC copies cover prewar volumes (28 items found) with clean
  djvu.txt. Checked t. 6 (1904): diacritics correct.
- t. 85–91 (2019–2025) on journals.akademicka.pl, per article, CC BY-NC-ND 4.0, with DOIs.
  The site also links a contents list of t. 1–87. Use it to find house monographs.
  t. 84 (2018) was not located online.
- MBC is migrating to a new platform (mbc.malopolska.pl). The old platform
  (`old.mbc.malopolska.pl`) still holds everything but answers **http only** (https fails in
  the TLS handshake). It also stopped answering later the same evening. Mirror what we
  need into the raw cache, or prefer the IA copies.

### 2.6 Tomkowicz, Ulice i place Krakowa (1926)
- Polona OCR, good quality (e.g. the Floriańska Gate passage with dated Latin quotes).
- Use for street stories: former names, when a street was laid out, lost buildings.

### 2.7 Bałaban, Historja Żydów w Krakowie i na Kazimierzu
- Both volumes PD with OCR (Polona). The text includes Hebrew and genealogical tables,
  so OCR is noisy in places. A later reprint (2013) on Polona is copyright-protected,
  so use the 1931/1936 copies.

### 2.8 Teka Grona Konserwatorów Galicyi Zachodniej
- Conservation reports from about 1900–1913 (repairs, discoveries, descriptions). t. IV–V are
  Wawel-specific. t. I–III cover many Kraków churches and houses.

### 2.9 Krzysztofory
- journals.akademicka.pl archive t. 17 (1990) to now, article PDFs, CC BY-NC-ND 4.0.
  Text extracts cleanly with `pdftotext -enc UTF-8`. Without `-enc UTF-8` on Windows the
  Polish letters appear lost. The PDFs are fine.
- muzeumkrakowa.pl serves the same and older articles at `/plik-do-pobrania/<n>` (checked
  ids 285, 297, 463, 489, 510, 794; 343 = 404). There is no index page at `/publikacje` (404).

### 2.10 Nowa Huta and 20th-century districts
- Klaś (ed.) 2018, RUJ, CC BY-NC-ND 3.0: per-building texts on the Nowa Huta estates, with
  their own citations. The original OKN link in the record is dead (404). Use the RUJ bitstream.
- Czasopismo Techniczne (ejournals.eu): free PDFs; Sumorok 2015 on Nowa Huta checked.
- Rocznik Krakowski 2023 (Dettloff) on early-20th-c. villas in Krowodrza.
- Search hits not opened: Łakomy (PK repository) on interwar Kraków housing estates; the PK
  monograph *Studia nad architekturą i urbanistyką Polski międzywojennej* t. VI (Greater
  Kraków). Both sit in the PK repository, which is down for maintenance (§3).

### 2.11 Internet Archive as the main text cache
- `https://archive.org/metadata/<id>` gives the file list and the rights field.
  `https://archive.org/download/<id>/<file>_djvu.txt` gives the OCR text. No key.
- Identifiers keep the source library and its number (`jbc.bj.uj.edu.pl.NDIG…`,
  `dbc.wroc.pl.006422`), so we can cite the original library, with the IA copy as the
  fetchable text.

### 2.12 Polona as the main search + OCR endpoint
- The search API returns `objectId` (UUID), title, date, `hasOcrAlto`,
  `copyrightProtected`, `licenseName`. Relevance ranking is loose, so filter results
  on our side.
- The full-text ZIP and ALTO (with word coordinates, enabling page-level citation)
  downloaded without login for PD items.

---

## 3. Searched but not usable (or not yet)

| Source | What happened | Status / workaround |
|---|---|---|
| sztetl.org.pl (Virtual Shtetl) | HTTP 403 for curl and for WebFetch from here too | Not usable by script. Use KZS cz. 6 (Judaica) + Bałaban instead |
| encyklopedia.krakow.pl | DNS: "Non-existent domain" (NXDOMAIN), both www and bare | Does not exist (any more). The printed *Encyklopedia Krakowa* (PWN 2000) is not online |
| Krasnowolski, *Krakowski Kazimierz. Historia i kultura* (Biblioteka Krakowska 168, 2022), books.akademicka.pl | The free PDF is only a sample: front matter and contents, about 4,900 words | Not usable for facts. The book is sold |
| FBC (fbc.pionier.net.pl) | Every search/API URL returns "High Load – Verifying Browser" (JS crypto challenge) | Not scriptable. Polona covers most of the same PD holdings |
| JBC search (jbc.bj.uj.edu.pl) | Search results render client-side (0 results in HTML); OAI-PMH behind the same JS wall | `/Content/<id>` PDFs download fine. Find items via IA mirrors or Polona |
| RCIN (rcin.org.pl) | "High Load" JS wall on dLibra pages | Not scriptable now. No Kraków-house-specific title found via web search |
| HathiTrust | 403 on catalog UI, babel full-text search and WebFetch. Bibliographic API answers but is useless without IDs | Not usable. PD Polish books there are mostly also on Google Books / Polona |
| Google Books (text) | Full view confirmed, but `output=text` returns 403 "automated queries"; Books API v1 returned 429 | For humans only; see table #21 |
| ICM servers (yadda / CEJSH / BazTech; dir.icm.edu.pl *Słownik geograficzny Królestwa Polskiego*) | 403 with an Anubis "Making sure you're not a bot!" challenge | Not scriptable. SGKP t. 4 (1883) with OCR is on Polona (https://polona.pl/item-view/d93c3e70-44ca-47e1-9864-a7b6aaed03a9) and would cover the villages that are now outer districts. Found via the Polona search API (OCR flag true, PD); text not yet fetched or assessed |
| journals.pan.pl (incl. *Teka Komisji Urbanistyki i Architektury PAN Kraków*) | HTML pages behind the JS wall; direct `/Content/<id>` PDFs download | Usable only with known PDF ids. The one article checked (COP villas) was not about Kraków |
| Repozytorium Politechniki Krakowskiej (repozytorium.biblos.pk.edu.pl) | Every file URL redirects to "Brak dostępu do repozytorium – prace serwisowe" | Temporarily down. Re-check later: holds *Wiadomości Konserwatorskie* issues and Kraków architecture papers |
| wiadomoscikonserwatorskie.pl | No connection (curl 000) | Use BazHum / PK repository |
| mkz.krakow.pl (Miejski Konserwator Zabytków) | DNS fails (curl 000) | No MKZ studies found online. bip.krakow.pl works, but no district heritage study was found among the local-plan PDFs (only plan resolutions) |
| Teki Krakowskie (Regionalny Ośrodek Studiów i Ochrony Środowiska Kulturowego, 13 vols) | Only mentioned in articles; no online copy found | Not available |
| Rożek, Estreicher (jr.) guidebooks; Krasnowolski *Ulice i place krakowskiego Śródmieścia* | No legal free copy found; in copyright | Not available |
| Małopolska BC new platform (mbc.malopolska.pl) | Old dLibra URLs (`/dlibra/publication/13440`) return 404; search form is JS-only | Use `http://old.mbc.malopolska.pl` (intermittent) or the IA mirrors |
| Kehilalinks Kraków (kehilalinks.jewishgen.org) | No connection (curl 000) | Not checked further |
| *Dawna kamienica krakowska: jej układ i wnętrze* (1934) on Polona | Licence "Zawartość chroniona – licencja ograniczona", no OCR | Not usable by script |
| Pomorska BC (pbc.gda.pl), Biblioteka Cyfrowa UW (crispa.uw.edu.pl) | Hosts reachable (HTTP 301/200). Not searched in depth: no Kraków-specific holdings surfaced in Polona / IA / web searches | Low priority |

---

## 4. How this could feed the AI research pipeline

1. **Fetch layer.** Polona API (search + OCR ZIP + ALTO), Internet Archive
   (`metadata` + `_djvu.txt`), and direct PDF downloads (IS PAN, akademicka,
   RUJ, MTG). Cache in `source-data/raw/books/`, which is git-ignored. Never cache in `data/`.
2. **Address index first.** Parse Nowolecki 1878/1880/1884 into a table
   *street + modern number ↔ old conscription number ↔ owner (year)*. That lets
   an agent jump from an address to the right page in Chmiel, the KZS, Rocznik
   Krakowski articles and the address books.
3. **Per-address retrieval.** For a target address, search the cached texts for
   the street name + number variants (and the old number). Hand the agent the
   matching pages with their citation URLs (`…pdf#page=N`, Polona item-view
   URL + page, IA URL + page). The agent writes a short summary in its own words.
4. **Verifier.** It re-fetches the cited page text and checks each claim
   against it. Address-book and other noisy-OCR claims should be checked at page
   level (ALTO or a page image) before publishing.
5. **Licences on the page.** PD sources (Chmiel, Tomkowicz, Nowolecki,
   Bałaban, address books): facts + short quotes OK. KZS and Krzysztofory/RK
   (CC BY-NC-ND or rights reserved): facts restated in our words + citation,
   no copied passages.

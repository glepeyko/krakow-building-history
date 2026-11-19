(() => {
  "use strict";

  const DIACRITICS_MAP = {
    ą: "a", ć: "c", ę: "e", ł: "l", ń: "n", ó: "o", ś: "s", ź: "z", ż: "z",
    Ą: "a", Ć: "c", Ę: "e", Ł: "l", Ń: "n", Ó: "o", Ś: "s", Ź: "z", Ż: "z",
  };

  function normalize(text) {
    return (text || "")
      .toLowerCase()
      .replace(/[ąćęłńóśźżĄĆĘŁŃÓŚŹŻ]/g, (ch) => DIACRITICS_MAP[ch] || ch)
      .trim();
  }

  // Strips leading street-type words so "ul. Konopnickiej" and "Konopnickiej"
  // are treated the same way when matching.
  function stripPrefix(text) {
    return text.replace(/^\s*(ul\.|al\.|os\.|pl\.|rondo|bulwar|wybrzeże)\s*/i, "");
  }

  const state = {
    streets: [],                // [{ name, search, file, entries }]
    shardCache: new Map(),      // file -> Promise<street shard>
    activeIndex: -1,
    currentMatches: [],
  };

  const streetInput = document.getElementById("street-input");
  const numberInput = document.getElementById("number-input");
  const listbox = document.getElementById("street-listbox");
  const form = document.getElementById("search-form");
  const resultsEl = document.getElementById("results");

  // Every value from the data files goes through esc() before it is put
  // into HTML. Wikidata and OSM are open to public editing.
  function esc(value) {
    return String(value ?? "").replace(/[&<>"']/g, (c) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    }[c]));
  }

  async function loadData() {
    state.streets = await fetch("data/streets.json").then((r) => {
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      return r.json();
    });
  }

  function loadShard(file) {
    if (!state.shardCache.has(file)) {
      const p = fetch(`data/streets/${encodeURIComponent(file)}.json`).then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      });
      p.catch(() => state.shardCache.delete(file));
      state.shardCache.set(file, p);
    }
    return state.shardCache.get(file);
  }

  // ---------------------------------------------------------------
  // Autocomplete
  // ---------------------------------------------------------------
  function getMatches(query) {
    const q = normalize(stripPrefix(query));
    if (!q) return [];

    const starts = [];
    const contains = [];
    for (const s of state.streets) {
      if (s.search.startsWith(q)) starts.push(s);
      else if (s.search.includes(q)) contains.push(s);
    }
    // Shorter names first, so "florian" offers "Floriańska" before
    // "Floriana Kotowskiego".
    starts.sort((a, b) => a.name.length - b.name.length);
    return [...starts, ...contains].slice(0, 8);
  }

  function highlight(name, query) {
    const q = stripPrefix(query).trim();
    if (!q) return name;
    const idx = normalize(name).indexOf(normalize(q));
    if (idx === -1) return name;
    return (
      name.slice(0, idx) +
      "<mark>" + name.slice(idx, idx + q.length) + "</mark>" +
      name.slice(idx + q.length)
    );
  }

  function renderDropdown(matches, query) {
    listbox.innerHTML = "";
    state.activeIndex = -1;
    state.currentMatches = matches;

    if (matches.length === 0) {
      listbox.hidden = true;
      streetInput.setAttribute("aria-expanded", "false");
      return;
    }

    matches.forEach((s, i) => {
      const li = document.createElement("li");
      li.setAttribute("role", "option");
      li.id = `street-option-${i}`;
      li.innerHTML = highlight(esc(s.name), esc(query));
      li.addEventListener("mousedown", (e) => {
        e.preventDefault();
        selectStreet(s.name);
      });
      listbox.appendChild(li);
    });

    listbox.hidden = false;
    streetInput.setAttribute("aria-expanded", "true");
  }

  function selectStreet(name) {
    streetInput.value = name;
    listbox.hidden = true;
    streetInput.setAttribute("aria-expanded", "false");
    numberInput.focus();
  }

  streetInput.addEventListener("input", () => {
    renderDropdown(getMatches(streetInput.value), streetInput.value);
  });

  streetInput.addEventListener("keydown", (e) => {
    if (listbox.hidden) return;
    const items = listbox.querySelectorAll("li");

    if (e.key === "ArrowDown") {
      e.preventDefault();
      state.activeIndex = (state.activeIndex + 1) % items.length;
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      state.activeIndex = (state.activeIndex - 1 + items.length) % items.length;
    } else if (e.key === "Enter" && state.activeIndex >= 0) {
      e.preventDefault();
      selectStreet(state.currentMatches[state.activeIndex].name);
      return;
    } else if (e.key === "Escape") {
      listbox.hidden = true;
      return;
    } else {
      return;
    }

    items.forEach((li, i) => li.classList.toggle("active", i === state.activeIndex));
    items[state.activeIndex]?.scrollIntoView({ block: "nearest" });
  });

  document.addEventListener("click", (e) => {
    if (!e.target.closest(".field-street")) listbox.hidden = true;
  });

  // ---------------------------------------------------------------
  // Search + results
  // ---------------------------------------------------------------
  const OSM_BUILDING_TYPES = {
    apartments: "budynek wielorodzinny", house: "dom jednorodzinny",
    detached: "dom wolnostojący", residential: "budynek mieszkalny",
    semidetached_house: "bliźniak", terrace: "zabudowa szeregowa",
    retail: "budynek handlowy", commercial: "budynek usługowy", office: "biurowiec",
    church: "kościół", chapel: "kaplica", school: "szkoła", university: "budynek uczelni",
    hospital: "szpital", kindergarten: "przedszkole", hotel: "hotel",
    industrial: "budynek przemysłowy", warehouse: "magazyn", public: "budynek publiczny",
    civic: "budynek użyteczności publicznej", construction: "budynek w budowie",
    garage: "garaż", garages: "garaże", train_station: "dworzec", farm: "zabudowa gospodarska",
    monastery: "klasztor", college: "szkoła", dormitory: "akademik", service: "budynek techniczny",
  };

  const SOURCE_LABELS = {
    "Gminna Ewidencja Zabytków Miasta Krakowa": "Gminna Ewidencja Zabytków",
    Wikidata: "Wikidata",
  };

  function resolveStreet(rawInput) {
    const q = normalize(stripPrefix(rawInput));
    if (!q) return null;

    const exact = state.streets.find((s) => s.search === q);
    if (exact) return exact;

    // Fall back to a unique match, so an entry that was never picked from
    // the dropdown can still resolve.
    const starts = state.streets.filter((s) => s.search.startsWith(q));
    if (starts.length === 1) return starts[0];
    const contains = state.streets.filter((s) => s.search.includes(q));
    if (contains.length === 1) return contains[0];

    return null;
  }

  function normalizeNumber(raw) {
    return normalize(raw)
      .replace(/\s*([-/])\s*/g, "-")
      .replace(/(\d)\s+([a-z])\b/g, "$1$2")
      .replace(/\s+/g, "");
  }

  // Polish plural: 1 wpis, 2-4 wpisy (but 12-14 wpisów), 5+ wpisów.
  function pluralWpis(n) {
    if (n === 1) return "wpis";
    const d = n % 10, t = n % 100;
    return d >= 2 && d <= 4 && !(t >= 12 && t <= 14) ? "wpisy" : "wpisów";
  }

  function capitalize(text) {
    return text ? text.charAt(0).toUpperCase() + text.slice(1) : text;
  }

  // The known number on the same street closest to the one typed, used
  // when a number is missing from OSM (e.g. a new block).
  function nearestKnownNumber(shard, num) {
    const n = parseInt(num, 10);
    if (Number.isNaN(n)) return null;
    let best = null;
    for (const [k, slot] of Object.entries(shard.numbers)) {
      if (!slot.lat) continue;
      const kn = parseInt(k, 10);
      if (Number.isNaN(kn)) continue;
      const d = Math.abs(kn - n);
      if (d <= 6 && (!best || d < best.d)) best = { k, slot, d };
    }
    return best;
  }

  function mapLink(lat, lon) {
    return `https://www.openstreetmap.org/?mlat=${lat}&mlon=${lon}#map=19/${lat}/${lon}`;
  }

  function commonsLink(file) {
    return `https://commons.wikimedia.org/wiki/File:${encodeURIComponent(file.replace(/ /g, "_"))}`;
  }

  function entryCard(e) {
    const card = document.createElement("article");
    card.className = "result-card";

    const districtLine = e.district_name ? `Dzielnica ${e.district_number} — ${e.district_name}` : "";
    const title = capitalize(e.name || e.type_and_name || "Budynek bez opisu typu");
    const subtitle = e.name && e.type_and_name && normalize(e.name) !== normalize(e.type_and_name)
      ? e.type_and_name : "";
    const author = e.author || (e.author_wikidata ? `${e.author_wikidata} (wg Wikidanych)` : "");

    const links = [];
    if (e.wikipedia) links.push(`<a href="${esc(e.wikipedia)}" target="_blank" rel="noopener">Artykuł w Wikipedii</a>`);
    if (e.image) links.push(`<a href="${esc(commonsLink(e.image))}" target="_blank" rel="noopener">Zdjęcie (Wikimedia Commons)</a>`);
    if (e.lat) links.push(`<a href="${esc(mapLink(e.lat, e.lon))}" target="_blank" rel="noopener">Na mapie</a>`);
    if (e.wikidata) links.push(`<a href="https://www.wikidata.org/wiki/${esc(e.wikidata)}" target="_blank" rel="noopener">Wikidane</a>`);

    const sources = [SOURCE_LABELS[e.source] || e.source];
    if (e.wikidata && e.source !== "Wikidata") sources.push("Wikidane");

    card.innerHTML = `
      ${districtLine ? `<div class="tag">${esc(districtLine)}</div>` : ""}
      <h3>${esc(title)}</h3>
      ${subtitle ? `<p class="subtitle">${esc(subtitle)}</p>` : ""}
      <p class="address">${esc(e.address_raw)}</p>
      ${e.wd_description ? `<p class="description">${esc(e.wd_description)}</p>` : ""}
      <dl class="meta-grid">
        ${e.dating ? `<dt>Datowanie</dt><dd>${esc(e.dating)}</dd>` : ""}
        ${author ? `<dt>Autor</dt><dd>${esc(author)}</dd>` : ""}
        ${e.styles ? `<dt>Styl</dt><dd>${esc(e.styles.join(", "))}</dd>` : ""}
        ${e.alt_address ? `<dt>Adres narożny</dt><dd>${esc(e.alt_address)}</dd>` : ""}
      </dl>
      ${e.register_number
        ? `<div class="badge-protected">Zabytek w rejestrze — nr ${esc(e.register_number)}</div>`
        : ""}
      ${links.length ? `<p class="links">${links.join(" · ")}</p>` : ""}
      <p class="source">Źródło: ${esc(sources.join(", "))}</p>
    `;
    return card;
  }

  function osmFactsBlock(slot) {
    const rows = [];
    if (slot.name) rows.push(["Nazwa", slot.name]);
    if (slot.building && OSM_BUILDING_TYPES[slot.building]) rows.push(["Typ budynku", OSM_BUILDING_TYPES[slot.building]]);
    if (slot.levels) rows.push(["Kondygnacje", slot.levels]);
    if (slot.start_date) rows.push(["Rok budowy", slot.start_date]);
    if (slot.architect) rows.push(["Architekt", slot.architect]);
    if (!rows.length && !slot.lat) return "";
    return `
      <dl class="meta-grid">
        ${rows.map(([k, v]) => `<dt>${esc(k)}</dt><dd>${esc(v)}</dd>`).join("")}
      </dl>
      ${slot.lat ? `<p class="links"><a href="${esc(mapLink(slot.lat, slot.lon))}" target="_blank" rel="noopener">Na mapie</a></p>` : ""}
      ${rows.length ? `<p class="source">Źródło: OpenStreetMap</p>` : ""}`;
  }

  function nearbyBlock(slot, shard) {
    if (!slot.nearby || !slot.nearby.length) return "";
    const items = slot.nearby.map(([pid, dist]) => {
      const p = shard.pois[pid];
      if (!p) return "";
      const label = p.label ? `${p.label}: ` : "";
      const where = p.street ? `, ${p.street} ${p.number || ""}`.trimEnd() : "";
      const dating = p.dating ? ` (${p.dating})` : "";
      const title = p.wikipedia
        ? `<a href="${esc(p.wikipedia)}" target="_blank" rel="noopener">${esc(p.title)}</a>`
        : esc(p.title);
      return `<li><span class="dist">${esc(dist)} m</span> ${esc(label)}${title}${esc(where)}${esc(dating)}</li>`;
    }).join("");
    return `
      <section class="nearby">
        <h4>W pobliżu</h4>
        <ul>${items}</ul>
        <p class="source">Źródła: Gminna Ewidencja Zabytków, Wikidane, OpenStreetMap</p>
      </section>`;
  }

  function note(text, cls = "hint") {
    const p = document.createElement("p");
    p.className = cls;
    p.textContent = text;
    return p;
  }

  function renderStreet(shard) {
    resultsEl.innerHTML = "";
    const entries = shard.entries;
    if (!entries.length) {
      resultsEl.innerHTML = `
        <div class="no-result">
          <strong>Przy ul. ${esc(shard.name)} nie mamy jeszcze opisanych budynków.</strong>
          <p>Wpisz numer budynku, aby zobaczyć, co wiemy o samym adresie i jego okolicy.</p>
        </div>`;
      return;
    }
    resultsEl.appendChild(note(`Znaleziono ${entries.length} ${pluralWpis(entries.length)} przy ul. ${shard.name}` +
      (entries.length > 30 ? " (pokazano pierwsze 30 — wpisz numer budynku, aby zawęzić wyniki)." : ".")));
    entries.slice(0, 30).forEach((e) => resultsEl.appendChild(entryCard(e)));
  }

  function renderAddress(shard, rawNumber) {
    resultsEl.innerHTML = "";
    const num = normalizeNumber(rawNumber);
    let slot = shard.numbers[num];
    let shownNumber = num;

    // A corner or double building may be listed as "5-7": find it by "5".
    if (!slot) {
      const key = Object.keys(shard.numbers).find((k) => k.split("-").includes(num));
      if (key) { slot = shard.numbers[key]; shownNumber = key; }
    }

    if (!slot) {
      const similar = Object.keys(shard.numbers)
        .filter((k) => k.startsWith(num.replace(/[a-z]$/, "")) && shard.numbers[k].entries)
        .slice(0, 8);
      const neighbour = nearestKnownNumber(shard, num);
      resultsEl.innerHTML = `
        <div class="no-result">
          <strong>Nie znamy adresu ${esc(shard.name)} ${esc(rawNumber)}.</strong>
          <p>Tego numeru nie ma ani w ewidencji zabytków, ani w OpenStreetMap.
          Sprawdź numer lub <a href="#contact">zgłoś ten adres</a>.</p>
          ${similar.length ? `<p>Opisane adresy o podobnym numerze: ${similar.map((k) => esc(k)).join(", ")}.</p>` : ""}
          ${neighbour && neighbour.slot.nearby ? `<p>Poniżej: ciekawe miejsca w pobliżu sąsiedniego adresu ${esc(shard.name)} ${esc(neighbour.k)}.</p>` : ""}
        </div>`;
      if (neighbour) {
        const near = nearbyBlock(neighbour.slot, shard);
        if (near) {
          const wrap = document.createElement("div");
          wrap.innerHTML = near;
          resultsEl.appendChild(wrap.firstElementChild);
        }
      }
      return;
    }

    const byId = new Map(shard.entries.map((e) => [String(e.id), e]));
    const entries = (slot.entries || []).map((id) => byId.get(String(id))).filter(Boolean);

    if (shownNumber !== num) {
      resultsEl.appendChild(note(`Numer ${rawNumber} jest częścią adresu ${shard.name} ${shownNumber}.`));
    }

    if (entries.length) {
      entries.forEach((e) => resultsEl.appendChild(entryCard(e)));
    } else {
      const box = document.createElement("div");
      box.className = "no-result";
      box.innerHTML = `
        <strong>${esc(shard.name)} ${esc(shownNumber)}: nie mamy jeszcze opisu tego budynku.</strong>
        <p>Nie ma go w gminnej ewidencji zabytków ani w Wikidanych. Oto, co wiemy
        o samym budynku i jego okolicy. Znasz jego historię?
        <a href="#contact">Napisz do nas</a>.</p>
        ${osmFactsBlock(slot)}`;
      resultsEl.appendChild(box);
    }

    const near = nearbyBlock(slot, shard);
    if (near) {
      const wrap = document.createElement("div");
      wrap.innerHTML = near;
      resultsEl.appendChild(wrap.firstElementChild);
    }
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    listbox.hidden = true;

    const rawStreet = streetInput.value.trim();
    const rawNumber = numberInput.value.trim();

    if (!rawStreet) {
      resultsEl.innerHTML = `<div class="no-result"><strong>Wpisz nazwę ulicy.</strong></div>`;
      return;
    }

    const street = resolveStreet(rawStreet);
    if (!street) {
      resultsEl.innerHTML = `
        <div class="no-result">
          <strong>Nie rozpoznano tej ulicy.</strong>
          <p>Sprawdź pisownię lub wybierz ulicę z podpowiedzi, które pojawiają się
          podczas wpisywania.</p>
        </div>`;
      return;
    }

    resultsEl.innerHTML = `<p class="hint">Wczytywanie…</p>`;
    try {
      const shard = await loadShard(street.file);
      if (rawNumber) renderAddress(shard, rawNumber);
      else renderStreet(shard);
    } catch (err) {
      resultsEl.innerHTML = `<div class="no-result"><strong>Nie udało się wczytać danych ulicy.</strong><p>${esc(err.message)}</p></div>`;
    }
  });

  // ---------------------------------------------------------------
  // Contact form (test version: opens the visitor's email client)
  // ---------------------------------------------------------------
  const CONTACT_EMAIL = "twoj-adres@example.com"; // TODO: replace with a real address

  document.getElementById("contact-form").addEventListener("submit", (e) => {
    e.preventDefault();
    const name = document.getElementById("contact-name").value.trim();
    const email = document.getElementById("contact-email").value.trim();
    const message = document.getElementById("contact-message").value.trim();

    const body = [
      message,
      "",
      name ? `Od: ${name}` : "",
      email ? `Kontakt zwrotny: ${email}` : "",
    ].filter(Boolean).join("\n");

    const mailto = `mailto:${CONTACT_EMAIL}` +
      `?subject=${encodeURIComponent("Zgłoszenie — Historia Twojego Domu")}` +
      `&body=${encodeURIComponent(body)}`;

    window.location.href = mailto;
  });

  loadData().catch((err) => {
    resultsEl.innerHTML = `<div class="no-result"><strong>Nie udało się wczytać bazy danych.</strong><p>${esc(err.message)}</p></div>`;
  });
})();

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
    streets: [],       // [{ name, search }]
    buildingsByKey: new Map(),   // "streetSearch|number" -> [records]
    buildingsByStreet: new Map(), // streetSearch -> [records]
    activeIndex: -1,
    currentMatches: [],
  };

  const streetInput = document.getElementById("street-input");
  const numberInput = document.getElementById("number-input");
  const listbox = document.getElementById("street-listbox");
  const form = document.getElementById("search-form");
  const resultsEl = document.getElementById("results");

  async function loadData() {
    const [streets, buildings] = await Promise.all([
      fetch("data/streets.json").then((r) => r.json()),
      fetch("data/buildings.json").then((r) => r.json()),
    ]);

    state.streets = streets;

    for (const b of buildings) {
      if (!b.street_search) continue;

      if (!state.buildingsByStreet.has(b.street_search)) {
        state.buildingsByStreet.set(b.street_search, []);
      }
      state.buildingsByStreet.get(b.street_search).push(b);

      const numberKey = normalize(b.building_number);
      if (numberKey) {
        const key = `${b.street_search}|${numberKey}`;
        if (!state.buildingsByKey.has(key)) state.buildingsByKey.set(key, []);
        state.buildingsByKey.get(key).push(b);
      }
    }
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
      li.innerHTML = highlight(s.name, query);
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
  function resolveStreet(rawInput) {
    const q = normalize(stripPrefix(rawInput));
    if (!q) return null;

    const exact = state.streets.find((s) => s.search === q);
    if (exact) return exact;

    // Fall back to a unique unambiguous match, so a slightly imprecise
    // entry that was never picked from the dropdown can still resolve.
    const candidates = state.streets.filter((s) => s.search.startsWith(q));
    if (candidates.length === 1) return candidates[0];

    return null;
  }

  function findBuildings(streetSearch, rawNumber) {
    const numberQuery = normalize(rawNumber);

    if (!numberQuery) {
      return { records: state.buildingsByStreet.get(streetSearch) || [], exact: true };
    }

    const exactKey = `${streetSearch}|${numberQuery}`;
    if (state.buildingsByKey.has(exactKey)) {
      return { records: state.buildingsByKey.get(exactKey), exact: true };
    }

    // Soft match: e.g. user typed "11", record is "11a".
    const all = state.buildingsByStreet.get(streetSearch) || [];
    const soft = all.filter((b) => normalize(b.building_number).startsWith(numberQuery));
    return { records: soft, exact: false };
  }

  function renderResults(records, { exact, numberGiven, streetName }) {
    resultsEl.innerHTML = "";

    if (records.length === 0) {
      resultsEl.innerHTML = `
        <div class="no-result">
          <strong>Nie znaleziono tego adresu w bazie.</strong>
          <p>Baza obejmuje na razie budynki z gminnej ewidencji zabytków — wiele
          adresów w Krakowie nie jest jeszcze opisanych. Możesz
          <a href="#contact">zgłosić ten adres</a>, a dodamy go w kolejnej turze.</p>
        </div>`;
      return;
    }

    const shown = records.slice(0, 30);

    if (!exact && numberGiven) {
      const note = document.createElement("p");
      note.className = "result-message";
      note.textContent = `Nie znaleziono dokładnego numeru — pokazuję zbliżone adresy przy ul. ${streetName}.`;
      resultsEl.appendChild(note);
    }

    if (!numberGiven && records.length > 1) {
      const note = document.createElement("p");
      note.className = "hint";
      note.textContent = `Znaleziono ${records.length} wpisów przy ul. ${streetName}` +
        (records.length > 30 ? " (pokazano pierwsze 30 — wpisz numer budynku, aby zawęzić wyniki)." : ".");
      resultsEl.appendChild(note);
    }

    for (const b of shown) {
      const card = document.createElement("article");
      card.className = "result-card";

      const districtLine = b.district_name ? `Dzielnica ${b.district_number} — ${b.district_name}` : "";

      card.innerHTML = `
        ${districtLine ? `<div class="tag">${districtLine}</div>` : ""}
        <h3>${b.type_and_name || "Budynek bez opisu typu"}</h3>
        <p class="address">${b.address_raw}</p>
        <dl class="meta-grid">
          ${b.dating ? `<dt>Datowanie</dt><dd>${b.dating}</dd>` : ""}
          ${b.author ? `<dt>Autor</dt><dd>${b.author}</dd>` : ""}
          ${b.alt_address ? `<dt>Adres narożny</dt><dd>${b.alt_address}</dd>` : ""}
        </dl>
        ${b.register_number
          ? `<div class="badge-protected">Zabytek w rejestrze — nr ${b.register_number}</div>`
          : ""}
      `;
      resultsEl.appendChild(card);
    }
  }

  form.addEventListener("submit", (e) => {
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

    const { records, exact } = findBuildings(street.search, rawNumber);
    renderResults(records, { exact, numberGiven: !!rawNumber, streetName: street.name });
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
    resultsEl.innerHTML = `<div class="no-result"><strong>Nie udało się wczytać bazy danych.</strong><p>${err.message}</p></div>`;
  });
})();

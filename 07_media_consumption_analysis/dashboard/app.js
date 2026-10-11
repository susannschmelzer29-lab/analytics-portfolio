/* Media Consumption dashboard — all figures come from data.js (build_dashboard.py). */
(function () {
  "use strict";

  const D = window.DASHBOARD_DATA;
  const ABC = "ABC News (AU)";
  const HP = "HuffPost (US)";
  const SOURCES = [ABC, HP];
  const SOURCE_COLOR = { [ABC]: "#1C7293", [HP]: "#C4553F" };
  const CAT_PALETTE = ["#1C7293", "#C4553F", "#C9A227", "#2E7D5B", "#6B4E9B", "#D17A22", "#3A8FB7", "#8A94A0", "#A23B72", "#4F6D7A"];
  const fmt = new Intl.NumberFormat("en-US");
  const fmt1 = new Intl.NumberFormat("en-US", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
  const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

  Chart.defaults.font.family = '"Segoe UI", "Helvetica Neue", Arial, sans-serif';
  Chart.defaults.color = "#5A6672";
  Chart.defaults.plugins.legend.labels.boxWidth = 12;
  Chart.defaults.maintainAspectRatio = false;

  const charts = {};
  function draw(id, config) {
    if (charts[id]) charts[id].destroy();
    charts[id] = new Chart(document.getElementById(id), config);
    return charts[id];
  }
  function el(tag, attrs, html) {
    const e = document.createElement(tag);
    Object.entries(attrs || {}).forEach(([k, v]) => e.setAttribute(k, v));
    if (html !== undefined) e.innerHTML = html;
    return e;
  }
  function escapeHtml(s) {
    return String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  }
  function fillSelect(id, values, selected) {
    const s = document.getElementById(id);
    s.innerHTML = "";
    values.forEach((v) => {
      const o = el("option", { value: v }, escapeHtml(v));
      if (v === selected) o.selected = true;
      s.appendChild(o);
    });
    return s;
  }
  function chipToggle(containerId, label, initial, onChange) {
    const box = document.getElementById(containerId);
    box.innerHTML = "";
    const b = el("button", { class: "chip" + (initial ? " active" : ""), type: "button", "aria-pressed": String(initial) }, label);
    b.addEventListener("click", () => {
      const on = !b.classList.contains("active");
      b.classList.toggle("active", on);
      b.setAttribute("aria-pressed", String(on));
      onChange(on);
    });
    box.appendChild(b);
  }
  const pctTick = (v) => v + " %";

  /* ---------------- Tabs ---------------- */
  const rendered = {};
  const renderers = {};
  function show(page) {
    document.querySelectorAll(".tab-btn").forEach((b) => b.classList.toggle("active", b.dataset.page === page));
    document.querySelectorAll(".page").forEach((p) => p.classList.toggle("active", p.id === "page-" + page));
    if (!rendered[page] && renderers[page]) {
      renderers[page]();
      rendered[page] = true;
    }
    if (location.hash !== "#" + page) history.replaceState(null, "", "#" + page);
  }
  document.getElementById("tabs").addEventListener("click", (e) => {
    const b = e.target.closest(".tab-btn");
    if (b) show(b.dataset.page);
  });

  /* ---------------- Derived facts (used on several pages) ---------------- */
  const dist = D.distribution;
  const shared = dist.shared_comparison;
  function sharedRenormalised(source) {
    const rows = shared.filter((r) => r.category !== "Other");
    const sum = rows.reduce((a, r) => a + r[source], 0);
    return Object.fromEntries(rows.map((r) => [r.category, (100 * r[source]) / sum]));
  }
  const abcRenorm = sharedRenormalised(ABC);
  const hpRenorm = sharedRenormalised(HP);
  const SOLID_YEAR = 10000; // years with fewer articles are drawn dashed
  function yearTotals(s) {
    const t = D.trend[s];
    return t.years.map((_, i) => Object.values(t.counts).reduce((a, c) => a + c[i], 0));
  }
  const top = (obj, n) => Object.entries(obj).sort((a, b) => b[1] - a[1]).slice(0, n);

  /* ---------------- Overview ---------------- */
  renderers.overview = function () {
    const o = D.overview;
    const kpis = [
      { label: "Headlines analysed", value: fmt.format(o.canonical.total), note: "both sources combined" },
      { label: "ABC News (AU)", value: fmt.format(o.canonical.abc), note: "headlines only, " + o.year_min + "–2021" },
      { label: "HuffPost (US)", value: fmt.format(o.canonical.huffpost), note: "headlines + descriptions, 2012–" + o.year_max },
      { label: "ABC headlines without a category", value: fmt1.format(o.abc_other_share) + " %", note: "keyword rules found no match → “Other”" },
    ];
    const grid = document.getElementById("kpi-grid");
    grid.innerHTML = "";
    kpis.forEach((k) => {
      const t = el("div", { class: "kpi-tile" });
      t.appendChild(el("div", { class: "kpi-label" }, k.label));
      t.appendChild(el("div", { class: "kpi-value" }, k.value));
      t.appendChild(el("div", { class: "kpi-note" }, k.note));
      grid.appendChild(t);
    });

    draw("chart-per-year", {
      type: "bar",
      data: {
        labels: o.per_year.years,
        datasets: SOURCES.map((s) => ({ label: s, data: o.per_year.series[s], backgroundColor: SOURCE_COLOR[s] })),
      },
      options: {
        plugins: { legend: { display: false }, tooltip: { callbacks: { label: (c) => c.dataset.label + ": " + fmt.format(c.raw) } } },
        scales: { x: { stacked: true, grid: { display: false } }, y: { stacked: true, ticks: { callback: (v) => fmt.format(v) } } },
      },
    });

    const [abc1, abc2] = top(abcRenorm, 2);
    const [hp1, hp2] = top(hpRenorm, 2);
    const hpPol = D.trend[HP];
    const i14 = hpPol.years.indexOf(2014);
    const polShares = hpPol.shares["Politics"];
    const hpTotals = yearTotals(HP);
    const solid = hpPol.years.map((y, i) => i).filter((i) => i >= i14 && hpTotals[i] >= SOLID_YEAR);
    const lastSolid = solid[solid.length - 1];
    const hlRange = (s) => {
      const r = D.length[s].filter((x) => x.articles >= 1000).map((x) => x.headline_words);
      return fmt1.format(Math.min(...r)) + "–" + fmt1.format(Math.max(...r));
    };
    const desc = D.length[HP].filter((r) => r.description_words !== null && r.articles >= 1000);
    const dMin = desc.reduce((a, r) => (r.description_words < a.description_words ? r : a));
    const dMax = desc.reduce((a, r) => (r.description_words > a.description_words ? r : a));
    const findings = [
      `<b>Two editorial profiles.</b> In the shared categories (without “Other”) ABC News leads with ${abc1[0]} (${fmt1.format(abc1[1])} %) and ${abc2[0]} (${fmt1.format(abc2[1])} %); HuffPost with ${hp1[0]} (${fmt1.format(hp1[1])} %) and ${hp2[0]} (${fmt1.format(hp2[1])} %).`,
      `<b>Politics rises at HuffPost.</b> Its share grows from ${fmt1.format(polShares[i14])} % in 2014 to ${fmt1.format(polShares[lastSolid])} % in ${hpPol.years[lastSolid]}, the last year with at least ${fmt.format(SOLID_YEAR)} HuffPost articles.`,
      `<b>Headlines are short everywhere</b> — ${hlRange(ABC)} words at ABC News, ${hlRange(HP)} at HuffPost. The real difference lies in the HuffPost descriptions: ${fmt1.format(dMin.description_words)} words for ${dMin.category} vs. ${fmt1.format(dMax.description_words)} for ${dMax.category}.`,
      `<b>Beat reporting at HuffPost.</b> ${fmt1.format(D.authors.share_specialists_80)} % of the ${D.authors.authors_considered} regular authors write at least 80 % of their articles in a single category.`,
    ];
    const ul = document.getElementById("findings");
    ul.innerHTML = findings.map((f) => "<li>" + f + "</li>").join("");
  };

  /* ---------------- 1 Distribution ---------------- */
  let distIncludeOther = false;
  function drawShared() {
    const cats = shared.filter((r) => distIncludeOther || r.category !== "Other").map((r) => r.category);
    const val = (s, c) => (distIncludeOther ? shared.find((r) => r.category === c)[s] : (s === ABC ? abcRenorm : hpRenorm)[c]);
    cats.sort((a, b) => val(HP, b) - val(HP, a));
    draw("chart-shared", {
      type: "bar",
      data: {
        labels: cats,
        datasets: SOURCES.map((s) => ({ label: s, data: cats.map((c) => +val(s, c).toFixed(1)), backgroundColor: SOURCE_COLOR[s] })),
      },
      options: {
        plugins: { tooltip: { callbacks: { label: (c) => c.dataset.label + ": " + fmt1.format(c.raw) + " %" } } },
        scales: { x: { grid: { display: false } }, y: { ticks: { callback: pctTick } } },
      },
    });
    document.getElementById("dist-shared-note").innerHTML = distIncludeOther
      ? "With “Other” included, two thirds of ABC News are unclassified. Switch it off to compare the classified articles only."
      : "Shares are re-normalised to 100 % after removing “Other”, so the classified articles of both sources can be compared directly.";
  }
  function drawDistSource() {
    const s = document.getElementById("dist-source").value;
    const rows = dist[s].filter((r) => r.category !== "Other").sort((a, b) => b.share_classified - a.share_classified);
    draw("chart-dist-source", {
      type: "bar",
      data: {
        labels: rows.map((r) => r.category),
        datasets: [{ label: s, data: rows.map((r) => r.share_classified), backgroundColor: SOURCE_COLOR[s] }],
      },
      options: {
        indexAxis: "y",
        plugins: {
          legend: { display: false },
          tooltip: { callbacks: { label: (c) => fmt1.format(c.raw) + " % · " + fmt.format(rows[c.dataIndex].articles) + " articles" } },
        },
        scales: { x: { ticks: { callback: pctTick } }, y: { grid: { display: false } } },
      },
    });
  }
  renderers.distribution = function () {
    chipToggle("dist-other-toggle", "Include “Other”", false, (on) => {
      distIncludeOther = on;
      drawShared();
    });
    drawShared();
    fillSelect("dist-source", SOURCES, HP).addEventListener("change", drawDistSource);
    drawDistSource();
  };

  /* ---------------- 2 Trend ---------------- */
  const trendState = { selected: {}, from2014: true };
  const TREND_DEFAULT = { [ABC]: ["Crime", "Politics", "Business", "Environment"], [HP]: ["Politics", "Health", "Entertainment", "World"] };
  function trendCategories(s) {
    const t = D.trend[s];
    return Object.keys(t.counts).sort((a, b) => t.counts[b].reduce((x, y) => x + y, 0) - t.counts[a].reduce((x, y) => x + y, 0));
  }
  function buildTrendChips() {
    const s = document.getElementById("trend-source").value;
    if (!trendState.selected[s]) trendState.selected[s] = new Set(TREND_DEFAULT[s]);
    const sel = trendState.selected[s];
    const box = document.getElementById("trend-categories");
    box.innerHTML = "";
    trendCategories(s).forEach((c) => {
      const on = sel.has(c);
      const b = el("button", { class: "chip" + (on ? " active" : ""), type: "button", "aria-pressed": String(on) }, escapeHtml(c));
      b.addEventListener("click", () => {
        if (sel.has(c)) sel.delete(c);
        else if (sel.size < CAT_PALETTE.length) sel.add(c);
        buildTrendChips();
        drawTrend();
      });
      box.appendChild(b);
    });
  }
  function drawTrend() {
    const s = document.getElementById("trend-source").value;
    const t = D.trend[s];
    const start = trendState.from2014 && s === HP ? t.years.indexOf(2014) : 0;
    const years = t.years.slice(start);
    const sel = [...trendState.selected[s]];
    const totals = yearTotals(s).slice(start);
    const sparse = (ctx) => totals[ctx.p0DataIndex] < SOLID_YEAR || totals[ctx.p1DataIndex] < SOLID_YEAR;
    draw("chart-trend", {
      type: "line",
      data: {
        labels: years,
        datasets: sel.map((c, i) => ({
          label: c,
          data: t.shares[c].slice(start),
          borderColor: CAT_PALETTE[i % CAT_PALETTE.length],
          backgroundColor: CAT_PALETTE[i % CAT_PALETTE.length],
          tension: 0,
          pointRadius: 3,
          segment: { borderDash: (ctx) => (sparse(ctx) ? [5, 4] : undefined) },
        })),
      },
      options: {
        interaction: { mode: "index", intersect: false },
        plugins: { tooltip: { callbacks: { label: (c) => c.dataset.label + ": " + fmt1.format(c.raw) + " %" } } },
        scales: { x: { grid: { display: false } }, y: { beginAtZero: true, ticks: { callback: pctTick } } },
      },
    });
    document.getElementById("trend-note").textContent =
      s === HP
        ? "HuffPost politics is only reliably tracked from 2014. Dashed segments: years with fewer than 10,000 articles (2018–2022) — single categories swing strongly there."
        : "ABC shares are shares of all ABC headlines, including the unclassified “Other”. Dashed segments: years with fewer than 10,000 articles.";
  }
  renderers.trend = function () {
    fillSelect("trend-source", SOURCES, HP).addEventListener("change", () => {
      buildTrendChips();
      drawTrend();
    });
    chipToggle("trend-from2014", "HuffPost from 2014", true, (on) => {
      trendState.from2014 = on;
      drawTrend();
    });
    buildTrendChips();
    drawTrend();
  };

  /* ---------------- 3 Seasonality ---------------- */
  function heatColor(v) {
    const d = Math.max(-1, Math.min(1, (v - 100) / 30));
    const a = Math.abs(d) * 0.85 + 0.05;
    return d >= 0 ? `rgba(196, 85, 63, ${a})` : `rgba(28, 114, 147, ${a})`;
  }
  function drawHeatmap() {
    const s = document.getElementById("season-source").value;
    const h = D.seasonality[s];
    const rows = h.rows.filter((r) => r.articles >= 1000);
    let html = "<thead><tr><th class='row-label'>Category</th>" + h.months.map((m) => `<th scope="col">${MONTHS[m - 1]}</th>`).join("") + "</tr></thead><tbody>";
    rows.forEach((r) => {
      html += `<tr><th scope="row" class="row-label">${escapeHtml(r.category)}</th>`;
      r.index.forEach((v, i) => {
        const strong = Math.abs(v - 100) > 18;
        html += `<td style="background:${heatColor(v)};color:${strong ? "#fff" : "#1F2933"}" title="${escapeHtml(r.category)}, ${MONTHS[h.months[i] - 1]}: index ${v}">${v}</td>`;
      });
      html += "</tr>";
    });
    document.getElementById("heatmap").innerHTML = html + "</tbody>";
    document.getElementById("heatmap-legend").innerHTML =
      "less than usual <span class='scale'>" +
      [70, 80, 90, 100, 110, 120, 130].map((v) => `<span style="background:${heatColor(v)}"></span>`).join("") +
      "</span> more than usual · categories with ≥ 1,000 articles";
  }
  renderers.seasonality = function () {
    fillSelect("season-source", SOURCES, HP).addEventListener("change", drawHeatmap);
    drawHeatmap();
  };

  /* ---------------- 4 Keywords ---------------- */
  function fillKwCategories() {
    const s = document.getElementById("kw-source").value;
    const cats = Object.keys(D.keywords[s]).filter((c) => c !== "Other").sort();
    const current = document.getElementById("kw-category").value;
    fillSelect("kw-category", cats, cats.includes(current) ? current : cats.includes("Politics") ? "Politics" : cats[0]);
  }
  function drawKeywords() {
    const s = document.getElementById("kw-source").value;
    const c = document.getElementById("kw-category").value;
    const rows = D.keywords[s][c];
    document.getElementById("kw-note").textContent =
      (s === ABC
        ? "For ABC News the keywords of a category partly reflect the keyword rules that assigned the category: they show the vocabulary, not an independent topic signal. "
        : "") + "Common words such as “his” or “you” were not removed in the source keyword file.";
    document.getElementById("kw-title").innerHTML = `Top ${rows.length} keywords <span class="hint">${escapeHtml(s)} · ${escapeHtml(c)}</span>`;
    draw("chart-keywords", {
      type: "bar",
      data: { labels: rows.map((r) => r.keyword), datasets: [{ data: rows.map((r) => r.count), backgroundColor: SOURCE_COLOR[s] }] },
      options: {
        indexAxis: "y",
        plugins: { legend: { display: false }, tooltip: { callbacks: { label: (x) => fmt.format(x.raw) + " mentions" } } },
        scales: { x: { ticks: { callback: (v) => fmt.format(v) } }, y: { grid: { display: false } } },
      },
    });
  }
  renderers.keywords = function () {
    fillSelect("kw-source", SOURCES, HP).addEventListener("change", () => {
      fillKwCategories();
      drawKeywords();
    });
    fillKwCategories();
    document.getElementById("kw-category").addEventListener("change", drawKeywords);
    drawKeywords();
  };

  /* ---------------- 5 Authors ---------------- */
  function drawAuthorTable() {
    const c = document.getElementById("author-category").value;
    const rows = D.authors.top_per_category[c];
    document.getElementById("author-table").innerHTML =
      "<thead><tr><th>#</th><th>Author</th><th class='num'>Articles</th></tr></thead><tbody>" +
      rows.map((r, i) => `<tr><td>${i + 1}</td><td>${escapeHtml(r.author)}</td><td class="num">${fmt.format(r.articles)}</td></tr>`).join("") +
      "</tbody>";
  }
  renderers.authors = function () {
    const a = D.authors;
    const kpis = [
      { label: "Author assignments", value: fmt.format(a.assignments_total), note: "co-authored articles count once per author" },
      { label: "Regular authors", value: fmt.format(a.authors_considered), note: "≥ " + a.min_assignments + " assignments" },
      { label: "Specialists", value: fmt1.format(a.share_specialists_80) + " %", note: "≥ 80 % in one category" },
      { label: "Median focus", value: fmt1.format(a.median_share_top) + " %", note: "share in the author's main category" },
    ];
    const grid = document.getElementById("author-kpis");
    grid.innerHTML = "";
    kpis.forEach((k) => {
      const t = el("div", { class: "kpi-tile" });
      t.appendChild(el("div", { class: "kpi-label" }, k.label));
      t.appendChild(el("div", { class: "kpi-value" }, k.value));
      t.appendChild(el("div", { class: "kpi-note" }, k.note));
      grid.appendChild(t);
    });
    document.getElementById("author-hist-hint").textContent = "share of an author's articles in their main category";
    draw("chart-author-hist", {
      type: "bar",
      data: {
        labels: a.histogram.labels,
        datasets: [{ data: a.histogram.counts, backgroundColor: a.histogram.labels.map((l, i) => (i >= 4 ? "#C4553F" : "#8A94A0")) }],
      },
      options: {
        plugins: { legend: { display: false }, tooltip: { callbacks: { label: (x) => x.raw + " authors" } } },
        scales: { x: { grid: { display: false } }, y: { title: { display: true, text: "authors" } } },
      },
    });
    document.getElementById("author-note").textContent =
      `Most regular authors work a clear beat: the largest group writes 90–100 % of its articles in one category.`;
    const cats = Object.keys(a.top_per_category).sort();
    fillSelect("author-category", cats, "Politics").addEventListener("change", drawAuthorTable);
    drawAuthorTable();
  };

  /* ---------------- 6 Length ---------------- */
  renderers.length = function () {
    const MIN = 1000;
    const cats = [...new Set(SOURCES.flatMap((s) => D.length[s].filter((r) => r.articles >= MIN).map((r) => r.category)))];
    const val = (s, c) => {
      const r = D.length[s].find((x) => x.category === c);
      return r && r.articles >= MIN ? r.headline_words : null;
    };
    cats.sort((a, b) => (val(HP, b) ?? val(ABC, b) ?? 0) - (val(HP, a) ?? val(ABC, a) ?? 0));
    draw("chart-headline", {
      type: "bar",
      data: { labels: cats, datasets: SOURCES.map((s) => ({ label: s, data: cats.map((c) => val(s, c)), backgroundColor: SOURCE_COLOR[s], barPercentage: 0.95, categoryPercentage: 0.85 })) },
      options: {
        indexAxis: "y",
        plugins: { tooltip: { callbacks: { label: (x) => x.dataset.label + ": " + fmt1.format(x.raw) + " words" } } },
        scales: { x: { beginAtZero: true, title: { display: true, text: "words per headline" } }, y: { grid: { display: false } } },
      },
    });
    const abcRows = D.length[ABC].filter((r) => r.articles >= MIN);
    const hpRows = D.length[HP].filter((r) => r.articles >= MIN);
    const range = (rows) => fmt1.format(Math.min(...rows.map((r) => r.headline_words))) + "–" + fmt1.format(Math.max(...rows.map((r) => r.headline_words)));
    document.getElementById("length-head-note").textContent =
      `Headline length barely depends on the topic: ${range(abcRows)} words at ABC News, ${range(hpRows)} at HuffPost. The difference between the sources is larger than between categories.`;

    const desc = hpRows.filter((r) => r.description_words !== null).sort((a, b) => b.description_words - a.description_words);
    draw("chart-description", {
      type: "bar",
      data: { labels: desc.map((r) => r.category), datasets: [{ data: desc.map((r) => r.description_words), backgroundColor: SOURCE_COLOR[HP] }] },
      options: {
        indexAxis: "y",
        plugins: { legend: { display: false }, tooltip: { callbacks: { label: (x) => fmt1.format(x.raw) + " words" } } },
        scales: { x: { beginAtZero: true, title: { display: true, text: "words per description" } }, y: { grid: { display: false } } },
      },
    });
    const names = (rows) => rows.map((r) => r.category).join(", ");
    document.getElementById("length-desc-note").textContent =
      `Descriptions vary far more than headlines: ${names(desc.slice(0, 3))} get the longest teasers (up to ${fmt1.format(desc[0].description_words)} words), ${names(desc.slice(-3).reverse())} the shortest (down to ${fmt1.format(desc[desc.length - 1].description_words)} words).`;
  };

  /* ---------------- Method ---------------- */
  renderers.method = function () {
    const o = D.overview;
    const diff = o.aggregated_total - o.canonical.total;
    const items = [
      `<b>ABC categories are keyword-derived.</b> ABC News provides headlines only. Categories come from keyword rules; ${fmt1.format(o.abc_other_share)} % of ABC headlines match no rule and fall into “Other”. ABC distribution figures therefore describe the classified articles.`,
      `<b>The sources are not fully comparable.</b> HuffPost carries editor-assigned categories and descriptions; ABC has neither. The comparison on page 1 uses only the shared period and the categories present in both, normalised per source.`,
      `<b>HuffPost politics from 2014.</b> Before 2014 the category is sparse, so the trend page starts HuffPost at 2014 by default. After 2017 the HuffPost dataset holds few articles per year.`,
      `<b>Pre-aggregated inputs.</b> The dashboard reads the same aggregated CSVs as the Tableau workbook (source × year × month × category), not the raw 1.45 M rows. Headline length is therefore an article-weighted mean of monthly averages; description length is a weighted mean of monthly medians and labelled as an approximation.`,
      `<b>Totals.</b> The KPI tiles show the canonical totals from <code>METHODOLOGY.md</code> (${fmt.format(o.canonical.total)}). The aggregated file sums to ${fmt.format(o.aggregated_total)} — a difference of ${fmt.format(diff)} articles (under 0.01 %), which does not affect any share shown.`,
      `<b>Authors.</b> The author file counts one assignment per author and article, so co-authored articles appear more than once (${fmt.format(D.authors.assignments_total)} assignments). Specialisation is computed only for authors with at least ${D.authors.min_assignments} assignments.`,
      `<b>Reproducible.</b> Every number on these pages is computed by <code>dashboard/build_dashboard.py</code> from the files in <code>data/</code>; <code>dashboard/test_dashboard.py</code> checks the built figures against those files.`,
    ];
    document.getElementById("method-list").innerHTML = items.map((i) => "<li>" + i + "</li>").join("");
  };

  /* ---------------- Start ---------------- */
  const startPage = (location.hash || "#overview").slice(1);
  show(renderers[startPage] ? startPage : "overview");
})();

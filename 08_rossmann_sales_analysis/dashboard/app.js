(function () {
  "use strict";

  const COLORS = {
    petrol: "#1C7293",
    petrolDark: "#145066",
    petrolFill: "rgba(28, 114, 147, 0.15)",
    red: "#B23A48",
    gold: "#C9A227",
    grey: "#8A94A0",
    greyLight: "#D8DEE2",
  };

  const D = window.DASHBOARD_DATA;
  const charts = {}; // name -> Chart instance

  const fmtInt = (n) => Math.round(n).toLocaleString("en-US");
  const fmtEUR = (n) => "€" + Math.round(n).toLocaleString("en-US");
  const fmtNum = (n, d = 1) => Number(n).toLocaleString("en-US", { minimumFractionDigits: d, maximumFractionDigits: d });

  // ---------------------------------------------------------------------
  // Tab navigation
  // ---------------------------------------------------------------------
  function setupTabs() {
    const buttons = document.querySelectorAll(".tab-btn");
    buttons.forEach((btn) => {
      btn.addEventListener("click", () => showPage(btn.dataset.page));
    });
  }

  function showPage(page) {
    document.querySelectorAll(".tab-btn").forEach((b) => b.classList.toggle("active", b.dataset.page === page));
    document.querySelectorAll(".page").forEach((p) => p.classList.toggle("active", p.id === "page-" + page));
  }

  // ---------------------------------------------------------------------
  // KPI tiles
  // ---------------------------------------------------------------------
  function formatKpi(kpi) {
    switch (kpi.unit) {
      case "EUR million":
        return "€" + fmtNum(kpi.value, 1) + "M";
      case "EUR":
        return "€" + fmtNum(kpi.value, 2);
      case "%":
        return fmtNum(kpi.value, 1) + "%";
      case "Factor":
        return fmtNum(kpi.value, 1) + "×";
      default:
        return fmtInt(kpi.value);
    }
  }

  function renderKpis() {
    const grid = document.getElementById("kpi-grid");
    grid.innerHTML = D.kpis
      .map(
        (k) => `
      <div class="kpi-tile">
        <div class="kpi-label">${k.label}</div>
        <div class="kpi-value">${formatKpi(k)}</div>
      </div>`
      )
      .join("");
  }

  // ---------------------------------------------------------------------
  // Overview: compact trend + mini ranking
  // ---------------------------------------------------------------------
  function renderOverviewTrend() {
    const rows = D.daily.rows;
    const ctx = document.getElementById("chart-overview-trend");
    charts.overviewTrend = new Chart(ctx, {
      type: "line",
      data: {
        labels: rows.map((r) => r.Date),
        datasets: [
          {
            label: "7-day avg.",
            data: rows.map((r) => r.MA7),
            borderColor: COLORS.petrol,
            backgroundColor: COLORS.petrolFill,
            borderWidth: 2,
            pointRadius: 0,
            fill: true,
            tension: 0.15,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { ticks: { maxTicksLimit: 6 } },
          y: { ticks: { callback: (v) => fmtEUR(v) } },
        },
      },
    });
  }

  function renderMiniRanking() {
    const rows = D.storeRanking;
    const top5 = rows.slice(0, 5);
    const bottom5 = rows.slice(-5).reverse();
    const rowHtml = (r, cls) => `
      <tr class="${cls}">
        <td>#${r.Store}</td>
        <td>${r.StoreType.toUpperCase()}</td>
        <td>${fmtEUR(r.SalesPerDay)}</td>
        <td>${fmtNum(r.Percentile, 1)}%</td>
      </tr>`;
    const table = document.getElementById("mini-ranking-table");
    table.innerHTML = `
      <thead><tr><th>Store</th><th>Type</th><th>Sales/Day</th><th>Percentile</th></tr></thead>
      <tbody>
        <tr class="section-divider"><td colspan="4">Top 5</td></tr>
        ${top5.map((r) => rowHtml(r, "top-row")).join("")}
        <tr class="section-divider"><td colspan="4">Bottom 5</td></tr>
        ${bottom5.map((r) => rowHtml(r, "bottom-row")).join("")}
      </tbody>`;
  }

  // ---------------------------------------------------------------------
  // Time Series page
  // ---------------------------------------------------------------------
  let currentYear = "all";

  function renderYearFilter() {
    const years = ["all", ...Array.from(new Set(D.daily.rows.map((r) => r.Year))).sort()];
    const el = document.getElementById("year-filter");
    el.innerHTML = years
      .map((y) => `<button class="chip ${y === currentYear ? "active" : ""}" data-year="${y}">${y === "all" ? "All years" : y}</button>`)
      .join("");
    el.querySelectorAll(".chip").forEach((chip) => {
      chip.addEventListener("click", () => {
        currentYear = chip.dataset.year === "all" ? "all" : Number(chip.dataset.year);
        renderYearFilter();
        updateDailyChart();
      });
    });
  }

  function filteredDailyRows() {
    return currentYear === "all" ? D.daily.rows : D.daily.rows.filter((r) => r.Year === currentYear);
  }

  function updateDailyChart() {
    const rows = filteredDailyRows();
    const chart = charts.daily;
    chart.data.labels = rows.map((r) => r.Date);
    chart.data.datasets[0].data = rows.map((r) => r.TotalSales);
    chart.data.datasets[1].data = rows.map((r) => r.MA7);
    chart.data.datasets[2].data = rows.map(() => D.daily.average);
    chart.update();
  }

  function renderDailyChart() {
    const rows = filteredDailyRows();
    const ctx = document.getElementById("chart-daily");
    charts.daily = new Chart(ctx, {
      type: "line",
      data: {
        labels: rows.map((r) => r.Date),
        datasets: [
          {
            label: "Daily total sales (raw)",
            data: rows.map((r) => r.TotalSales),
            borderColor: COLORS.greyLight,
            borderWidth: 1,
            pointRadius: 0,
            tension: 0,
          },
          {
            label: "7-day moving average",
            data: rows.map((r) => r.MA7),
            borderColor: COLORS.petrol,
            borderWidth: 2.5,
            pointRadius: 0,
            tension: 0.1,
          },
          {
            label: "Overall average",
            data: rows.map(() => D.daily.average),
            borderColor: COLORS.grey,
            borderWidth: 1.5,
            borderDash: [6, 4],
            pointRadius: 0,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: "index", intersect: false },
        plugins: { legend: { position: "bottom" } },
        scales: {
          x: { ticks: { maxTicksLimit: 10 } },
          y: { ticks: { callback: (v) => fmtEUR(v) } },
        },
      },
    });
  }

  function renderMonthChart() {
    const ctx = document.getElementById("chart-month");
    const labels = D.month.map((m) => new Date(2000, m.Month - 1, 1).toLocaleString("en-US", { month: "short" }));
    charts.month = new Chart(ctx, {
      type: "bar",
      data: {
        labels,
        datasets: [
          {
            data: D.month.map((m) => m.SalesPerDay),
            backgroundColor: D.month.map((m) => (m.Month === 12 ? COLORS.gold : COLORS.grey)),
            borderRadius: 4,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: { y: { ticks: { callback: (v) => fmtEUR(v) } } },
      },
    });
  }

  function renderWeekdayChart() {
    const ctx = document.getElementById("chart-weekday");
    charts.weekday = new Chart(ctx, {
      data: {
        labels: D.weekday.map((w) => w.Weekday),
        datasets: [
          {
            type: "bar",
            label: "Sales/day",
            data: D.weekday.map((w) => w.SalesPerDay),
            backgroundColor: COLORS.petrol,
            borderRadius: 4,
            yAxisID: "y",
          },
          {
            type: "line",
            label: "Customers/day",
            data: D.weekday.map((w) => w.CustomersPerDay),
            borderColor: COLORS.gold,
            backgroundColor: COLORS.gold,
            yAxisID: "y1",
            tension: 0.2,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { position: "bottom" } },
        scales: {
          y: { position: "left", ticks: { callback: (v) => fmtEUR(v) } },
          y1: { position: "right", grid: { drawOnChartArea: false }, ticks: { callback: (v) => fmtInt(v) } },
        },
      },
    });
  }

  // ---------------------------------------------------------------------
  // Promo & Holiday page
  // ---------------------------------------------------------------------
  function renderPromoOverall() {
    const ctx = document.getElementById("chart-promo-overall");
    charts.promoOverall = new Chart(ctx, {
      type: "bar",
      data: {
        labels: D.promo.overall.map((p) => p.Promo_lbl),
        datasets: [
          {
            data: D.promo.overall.map((p) => p.SalesPerDay),
            backgroundColor: D.promo.overall.map((p) => (p.Promo_lbl === "With Promo" ? COLORS.gold : COLORS.grey)),
            borderRadius: 4,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: { callbacks: { label: (c) => fmtEUR(c.raw) } },
        },
        scales: { y: { ticks: { callback: (v) => fmtEUR(v) } } },
      },
    });
  }

  function renderPromoByStoretype() {
    const ctx = document.getElementById("chart-promo-storetype");
    const data = D.promo.by_storetype;
    charts.promoStoretype = new Chart(ctx, {
      data: {
        labels: data.map((d) => "Type " + d.StoreType.toUpperCase()),
        datasets: [
          {
            type: "bar",
            label: "Uplift %",
            data: data.map((d) => d["Uplift_%"]),
            backgroundColor: COLORS.petrol,
            borderRadius: 4,
          },
          {
            type: "line",
            label: "Overall avg. (38.8%)",
            data: data.map(() => 38.8),
            borderColor: COLORS.grey,
            borderDash: [6, 4],
            pointRadius: 0,
            borderWidth: 1.5,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { position: "bottom" } },
        scales: { y: { ticks: { callback: (v) => v + "%" } } },
      },
    });
  }

  function renderHolidayCharts() {
    const mk = (elId, rows, color) => {
      const ctx = document.getElementById(elId);
      return new Chart(ctx, {
        type: "bar",
        data: {
          labels: rows.map((r) => r.Holiday_lbl),
          datasets: [
            {
              data: rows.map((r) => r["Uplift_%"]),
              backgroundColor: color,
              borderRadius: 4,
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { display: false },
            tooltip: { callbacks: { label: (c) => "+" + c.raw + "%" } },
          },
          scales: { y: { ticks: { callback: (v) => v + "%" } } },
        },
      });
    };
    charts.holidayNaive = mk("chart-holiday-naive", D.holidays.naive, COLORS.red);
    charts.holidayCorrected = mk("chart-holiday-corrected", D.holidays.corrected, COLORS.petrol);
  }

  function renderSchoolHolidays() {
    const ctx = document.getElementById("chart-school-holidays");
    charts.schoolHolidays = new Chart(ctx, {
      type: "bar",
      data: {
        labels: D.schoolHolidays.map((r) => r.SchoolHolidayFlag),
        datasets: [
          {
            data: D.schoolHolidays.map((r) => r.SalesPerDay),
            backgroundColor: [COLORS.grey, COLORS.petrol],
            borderRadius: 4,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: { callbacks: { label: (c) => fmtEUR(c.raw) } },
        },
        scales: { y: { ticks: { callback: (v) => fmtEUR(v) } } },
      },
    });
  }

  // ---------------------------------------------------------------------
  // Store Segments page
  // ---------------------------------------------------------------------
  function renderStoretypeChart() {
    const ctx = document.getElementById("chart-storetype");
    const data = D.storetype;
    charts.storetype = new Chart(ctx, {
      data: {
        labels: data.map((d) => "Type " + d.StoreType.toUpperCase()),
        datasets: [
          {
            type: "bar",
            label: "Sales/day",
            data: data.map((d) => d.SalesPerDay),
            backgroundColor: COLORS.petrol,
            borderRadius: 4,
            yAxisID: "y",
          },
          {
            type: "line",
            label: "Sales/customer",
            data: data.map((d) => d.SalesPerCustomer),
            borderColor: COLORS.gold,
            backgroundColor: COLORS.gold,
            yAxisID: "y1",
            tension: 0.1,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        onClick: (evt, elements) => {
          if (!elements.length) return;
          const idx = elements[0].index;
          const storeType = data[idx].StoreType;
          applyStoreTypeFilterAndJump(storeType);
        },
        plugins: { legend: { position: "bottom" } },
        scales: {
          y: { position: "left", ticks: { callback: (v) => fmtEUR(v) } },
          y1: { position: "right", grid: { drawOnChartArea: false }, ticks: { callback: (v) => "€" + v } },
        },
      },
    });
  }

  function renderHeatmap() {
    const rows = D.storetypeXAssortment;
    const cols = ["Basic", "Extended", "Extra"];
    const allVals = rows.flatMap((r) => cols.map((c) => r[c])).filter((v) => v !== null && v !== undefined);
    const min = Math.min(...allVals);
    const max = Math.max(...allVals);

    const colorFor = (v) => {
      const t = (v - min) / (max - min || 1);
      // interpolate light petrol -> dark petrol
      const from = [214, 231, 236];
      const to = [20, 80, 102];
      const rgb = from.map((f, i) => Math.round(f + (to[i] - f) * t));
      return `rgb(${rgb.join(",")})`;
    };

    const header = `<div class="heatmap-header"><div></div>${cols.map((c) => `<div>${c}</div>`).join("")}</div>`;
    const body = rows
      .map((r) => {
        const cells = cols
          .map((c) => {
            const v = r[c];
            if (v === null || v === undefined) {
              return `<div class="heatmap-cell empty">–</div>`;
            }
            return `<div class="heatmap-cell" style="background:${colorFor(v)}">${fmtEUR(v)}</div>`;
          })
          .join("");
        return `<div class="heatmap-row"><div class="heatmap-row-label">Type ${r.StoreType.toUpperCase()}</div>${cells}</div>`;
      })
      .join("");
    document.getElementById("heatmap-storetype-assortment").innerHTML = header + body;
  }

  function renderCompetitionChart() {
    const ctx = document.getElementById("chart-competition");
    charts.competition = new Chart(ctx, {
      type: "bar",
      data: {
        labels: D.competitionDistance.map((d) => d.CompetitionProximity),
        datasets: [
          {
            data: D.competitionDistance.map((d) => d.SalesPerDay),
            backgroundColor: COLORS.petrol,
            borderRadius: 4,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: { callbacks: { label: (c) => fmtEUR(c.raw) } },
        },
        scales: { y: { ticks: { callback: (v) => fmtEUR(v) } } },
      },
    });
  }

  // ---------------------------------------------------------------------
  // Store Ranking page
  // ---------------------------------------------------------------------
  const rankingState = {
    storeTypes: new Set(),
    assortments: new Set(),
    search: "",
    limit: 50,
    sortKey: "Rank",
    sortAsc: true,
  };

  const ALL_STORE_TYPES = Array.from(new Set(D.storeRanking.map((r) => r.StoreType))).sort();
  const ALL_ASSORTMENTS = Array.from(new Set(D.storeRanking.map((r) => r.Assortment)));
  const MAX_SALES_PER_DAY = Math.max(...D.storeRanking.map((r) => r.SalesPerDay));

  function applyStoreTypeFilterAndJump(storeType) {
    rankingState.storeTypes = new Set([storeType]);
    rankingState.assortments = new Set();
    renderRankingFilterChips();
    renderRankingTable();
    showPage("ranking");
  }

  function renderRankingFilterChips() {
    const stEl = document.getElementById("ranking-storetype-filter");
    stEl.innerHTML = ALL_STORE_TYPES.map(
      (t) => `<button class="chip ${rankingState.storeTypes.has(t) ? "active" : ""}" data-val="${t}">Type ${t.toUpperCase()}</button>`
    ).join("");
    stEl.querySelectorAll(".chip").forEach((chip) => {
      chip.addEventListener("click", () => {
        const v = chip.dataset.val;
        if (rankingState.storeTypes.has(v)) rankingState.storeTypes.delete(v);
        else rankingState.storeTypes.add(v);
        renderRankingFilterChips();
        renderRankingTable();
      });
    });

    const asEl = document.getElementById("ranking-assortment-filter");
    asEl.innerHTML = ALL_ASSORTMENTS.map(
      (a) => `<button class="chip ${rankingState.assortments.has(a) ? "active" : ""}" data-val="${a}">${a}</button>`
    ).join("");
    asEl.querySelectorAll(".chip").forEach((chip) => {
      chip.addEventListener("click", () => {
        const v = chip.dataset.val;
        if (rankingState.assortments.has(v)) rankingState.assortments.delete(v);
        else rankingState.assortments.add(v);
        renderRankingFilterChips();
        renderRankingTable();
      });
    });
  }

  function getFilteredRankingRows() {
    let rows = D.storeRanking;
    if (rankingState.storeTypes.size) rows = rows.filter((r) => rankingState.storeTypes.has(r.StoreType));
    if (rankingState.assortments.size) rows = rows.filter((r) => rankingState.assortments.has(r.Assortment));

    const sorted = rows.slice().sort((a, b) => {
      const k = rankingState.sortKey;
      const dir = rankingState.sortAsc ? 1 : -1;
      if (typeof a[k] === "string") return a[k].localeCompare(b[k]) * dir;
      return (a[k] - b[k]) * dir;
    });
    return sorted;
  }

  function renderRankingTable() {
    const allFiltered = getFilteredRankingRows();
    const search = rankingState.search.trim();

    // If the search matches a store outside the current "rows to show" limit,
    // expand the slice so the match is still visible instead of silently vanishing.
    let effectiveLimit = rankingState.limit;
    let searchMatchOutsideFilter = false;
    if (search) {
      const matchIndex = allFiltered.findIndex((r) => String(r.Store) === search);
      if (matchIndex === -1) {
        searchMatchOutsideFilter = true;
      } else if (matchIndex >= effectiveLimit) {
        effectiveLimit = matchIndex + 1;
      }
    }
    const visible = allFiltered.slice(0, effectiveLimit);

    const tbody = document.getElementById("ranking-tbody");
    tbody.innerHTML = visible
      .map((r) => {
        const decileClass = r.DecileFlag === "Top 10%" ? "decile-top" : r.DecileFlag === "Bottom 10%" ? "decile-bottom" : "";
        const isMatch = search && String(r.Store) === search;
        const flagHtml =
          r.DecileFlag === "Top 10%"
            ? `<span class="decile-flag top">Top 10%</span>`
            : r.DecileFlag === "Bottom 10%"
            ? `<span class="decile-flag bottom">Bottom 10%</span>`
            : "";
        const barPct = (r.SalesPerDay / MAX_SALES_PER_DAY) * 100;
        return `
        <tr class="${decileClass} ${isMatch ? "search-match" : ""}" ${isMatch ? 'id="search-hit-row"' : ""}>
          <td>${r.Rank}</td>
          <td>#${r.Store}</td>
          <td>${r.StoreType.toUpperCase()}</td>
          <td>${r.Assortment}</td>
          <td>${r.CompetitionProximity}</td>
          <td><div class="bar-cell"><div class="bar-track"><div class="bar-fill" style="width:${barPct}%"></div></div>${fmtEUR(r.SalesPerDay)}</div></td>
          <td>${fmtInt(r.CustomersPerDay)}</td>
          <td>${fmtNum(r.SalesPerCustomer, 2)}</td>
          <td>${fmtNum(r.Percentile, 1)}% ${flagHtml}</td>
        </tr>`;
      })
      .join("");

    const countEl = document.getElementById("ranking-count");
    if (searchMatchOutsideFilter) {
      countEl.textContent = `Store #${search} not found — it may be excluded by the store type / assortment filters above.`;
    } else {
      countEl.textContent =
        `Showing ${visible.length.toLocaleString("en-US")} of ${allFiltered.length.toLocaleString("en-US")} filtered stores ` +
        `(${D.storeRanking.length.toLocaleString("en-US")} total).` +
        (effectiveLimit > rankingState.limit ? ` List expanded to show the searched store #${search}.` : "");
    }

    if (search) {
      const hit = document.getElementById("search-hit-row");
      if (hit) hit.scrollIntoView({ block: "center", behavior: "smooth" });
    }
  }

  function setupRankingControls() {
    renderRankingFilterChips();

    document.getElementById("ranking-search").addEventListener("input", (e) => {
      rankingState.search = e.target.value;
      renderRankingTable();
    });

    const limitInput = document.getElementById("ranking-limit");
    const limitValue = document.getElementById("ranking-limit-value");
    limitInput.addEventListener("input", (e) => {
      rankingState.limit = Number(e.target.value);
      limitValue.textContent = e.target.value;
      renderRankingTable();
    });

    document.querySelectorAll(".ranking-table thead th").forEach((th) => {
      th.addEventListener("click", () => {
        const key = th.dataset.key;
        if (rankingState.sortKey === key) {
          rankingState.sortAsc = !rankingState.sortAsc;
        } else {
          rankingState.sortKey = key;
          rankingState.sortAsc = true;
        }
        renderRankingTable();
      });
    });

    document.getElementById("ranking-reset").addEventListener("click", () => {
      rankingState.storeTypes = new Set();
      rankingState.assortments = new Set();
      rankingState.search = "";
      rankingState.limit = 50;
      rankingState.sortKey = "Rank";
      rankingState.sortAsc = true;
      document.getElementById("ranking-search").value = "";
      document.getElementById("ranking-limit").value = 50;
      limitValue.textContent = "50";
      renderRankingFilterChips();
      renderRankingTable();
    });
  }

  // ---------------------------------------------------------------------
  // Init
  // ---------------------------------------------------------------------
  Chart.defaults.font.family = "'Segoe UI', 'Helvetica Neue', Arial, sans-serif";
  Chart.defaults.font.size = 12;
  Chart.defaults.color = "#5A6672";

  setupTabs();
  renderKpis();
  renderOverviewTrend();
  renderMiniRanking();

  renderYearFilter();
  renderDailyChart();
  renderMonthChart();
  renderWeekdayChart();

  renderPromoOverall();
  renderPromoByStoretype();
  renderHolidayCharts();
  renderSchoolHolidays();

  renderStoretypeChart();
  renderHeatmap();
  renderCompetitionChart();

  setupRankingControls();
  renderRankingTable();
})();

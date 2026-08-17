(function () {
  "use strict";

  const COLORS = {
    petrol: "#1C7293",
    petrolDark: "#145066",
    petrolFill: "rgba(28, 114, 147, 0.15)",
    red: "#B23A48",
    redFill: "rgba(178, 58, 72, 0.15)",
    gold: "#C9A227",
    green: "#2E7D5B",
    grey: "#8A94A0",
    greyLight: "#D8DEE2",
  };

  const D = window.DASHBOARD_DATA;
  const charts = {};

  const fmtInt = (n) => Math.round(n).toLocaleString("en-US");
  const fmtEUR = (n) => "€" + Math.round(n).toLocaleString("en-US");
  const fmtM = (n) => (n < 0 ? "−€" : "€") + (Math.abs(n) / 1e6).toLocaleString("en-US", { minimumFractionDigits: 1, maximumFractionDigits: 1 }) + "M";
  const fmtNum = (n, d = 1) => Number(n).toLocaleString("en-US", { minimumFractionDigits: d, maximumFractionDigits: d });
  const fmtPct = (n) => (n >= 0 ? "+" : "") + fmtNum(n, 1) + "%";
  const typeLabel = (t) => "Type " + String(t).toUpperCase();

  // ---------------------------------------------------------------------
  // Tab navigation
  // ---------------------------------------------------------------------
  function setupTabs() {
    document.querySelectorAll(".tab-btn").forEach((btn) => {
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
      case "%":
        return fmtPct(kpi.value);
      case "Count":
        return fmtInt(kpi.value);
      default:
        return fmtInt(kpi.value);
    }
  }
  function kpiValueClass(kpi) {
    if (kpi.label === "Revenue Variance") return kpi.value >= 0 ? "pos" : "neg";
    return "";
  }
  function kpiSub(kpi) {
    switch (kpi.label) {
      case "Plan Revenue":
        return "prior-year + 3% target";
      case "Revenue Variance":
        return "actual vs. plan";
      case "Operating Margin":
        return "modelled";
      case "Loss-making Stores":
        return "of " + fmtInt(D.pnl.totals.totalStores) + " (assumed costs)";
      case "Contribution Margin":
        return "DB I · " + fmtNum(D.pnl.totals.cmRatioPct, 1) + "% of sales";
      default:
        return "";
    }
  }
  function renderKpis() {
    const grid = document.getElementById("kpi-grid");
    grid.innerHTML = D.kpis
      .map((k) => {
        const sub = kpiSub(k);
        return `
      <div class="kpi-tile">
        <div class="kpi-label">${k.label}</div>
        <div class="kpi-value ${kpiValueClass(k)}">${formatKpi(k)}</div>
        ${sub ? `<div class="kpi-sub">${sub}</div>` : ""}
      </div>`;
      })
      .join("");
  }

  // ---------------------------------------------------------------------
  // Overview: plan-vs-actual trend + P&L summary
  // ---------------------------------------------------------------------
  function renderOverviewTrend() {
    const rows = D.planActual.monthly;
    const ctx = document.getElementById("chart-overview-trend");
    charts.overviewTrend = new Chart(ctx, {
      type: "line",
      data: {
        labels: rows.map((r) => r.YearMonth),
        datasets: [
          {
            label: "Actual",
            data: rows.map((r) => r.ActualSales),
            borderColor: COLORS.petrol,
            backgroundColor: COLORS.petrolFill,
            borderWidth: 2,
            pointRadius: 0,
            fill: true,
            tension: 0.15,
          },
          {
            label: "Plan",
            data: rows.map((r) => r.PlanSales),
            borderColor: COLORS.gold,
            borderWidth: 1.5,
            borderDash: [6, 4],
            pointRadius: 0,
            tension: 0.15,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: "index", intersect: false },
        plugins: {
          legend: { position: "bottom" },
          tooltip: { callbacks: { label: (c) => c.dataset.label + ": " + fmtEUR(c.raw) } },
        },
        scales: {
          x: { ticks: { maxTicksLimit: 8 } },
          y: { ticks: { callback: (v) => fmtM(v) } },
        },
      },
    });
  }

  function renderPnlSummary() {
    const t = D.pnl.totals;
    const rows = [
      { label: "Revenue (actual)", val: t.revenue, cls: "" },
      { label: "− Variable cost", val: -t.variableCost, cls: "cost", note: fmtNum(100 - t.cmRatioPct, 1) + "% of sales" },
      { label: "= Contribution margin (DB I)", val: t.contributionMargin, cls: "subtotal", note: fmtNum(t.cmRatioPct, 1) + "%" },
      { label: "− Fixed cost", val: -t.fixedCost, cls: "cost", note: "€900 / open day" },
      { label: "= Operating profit", val: t.operatingProfit, cls: "result", note: fmtNum(t.operatingMarginPct, 1) + "% margin" },
    ];
    document.getElementById("pnl-summary").innerHTML = rows
      .map(
        (r) => `
      <tr class="${r.cls}">
        <td>${r.label}${r.note ? ` <span class="pnl-note">${r.note}</span>` : ""}</td>
        <td class="num ${r.cls === "cost" ? "cost" : ""}">${fmtM(r.val)}</td>
      </tr>`
      )
      .join("");
  }

  // ---------------------------------------------------------------------
  // Plan vs. Actual page
  // ---------------------------------------------------------------------
  let currentYear = "all";

  function filteredMonthly() {
    return currentYear === "all" ? D.planActual.monthly : D.planActual.monthly.filter((r) => r.Year === currentYear);
  }

  function renderYearFilter() {
    const years = ["all", ...Array.from(new Set(D.planActual.monthly.map((r) => r.Year))).sort()];
    const el = document.getElementById("year-filter");
    el.innerHTML = years
      .map((y) => `<button class="chip ${y === currentYear ? "active" : ""}" data-year="${y}">${y === "all" ? "All" : y}</button>`)
      .join("");
    el.querySelectorAll(".chip").forEach((chip) => {
      chip.addEventListener("click", () => {
        currentYear = chip.dataset.year === "all" ? "all" : Number(chip.dataset.year);
        renderYearFilter();
        updatePlanActualChart();
      });
    });
  }

  function updatePlanActualChart() {
    const rows = filteredMonthly();
    const c = charts.planActual;
    c.data.labels = rows.map((r) => r.YearMonth);
    c.data.datasets[0].data = rows.map((r) => r.PlanSales);
    c.data.datasets[1].data = rows.map((r) => r.ActualSales);
    c.data.datasets[2].data = rows.map((r) => r.VariancePct);
    c.update();
  }

  function renderPlanActualChart() {
    const rows = filteredMonthly();
    const ctx = document.getElementById("chart-planactual");
    charts.planActual = new Chart(ctx, {
      data: {
        labels: rows.map((r) => r.YearMonth),
        datasets: [
          {
            type: "bar",
            label: "Plan",
            data: rows.map((r) => r.PlanSales),
            backgroundColor: COLORS.greyLight,
            borderRadius: 3,
            yAxisID: "y",
          },
          {
            type: "bar",
            label: "Actual",
            data: rows.map((r) => r.ActualSales),
            backgroundColor: COLORS.petrol,
            borderRadius: 3,
            yAxisID: "y",
          },
          {
            type: "line",
            label: "Variance %",
            data: rows.map((r) => r.VariancePct),
            borderColor: COLORS.gold,
            backgroundColor: COLORS.gold,
            borderWidth: 2,
            pointRadius: 2,
            tension: 0.2,
            yAxisID: "y1",
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: "index", intersect: false },
        plugins: {
          legend: { position: "bottom" },
          tooltip: {
            callbacks: {
              label: (c) => (c.dataset.label === "Variance %" ? "Variance: " + fmtPct(c.raw) : c.dataset.label + ": " + fmtEUR(c.raw)),
            },
          },
        },
        scales: {
          x: { ticks: { maxTicksLimit: 12 } },
          y: { position: "left", ticks: { callback: (v) => fmtM(v) } },
          y1: {
            position: "right",
            grid: { drawOnChartArea: false },
            ticks: { callback: (v) => v + "%" },
          },
        },
      },
    });
  }

  function renderVarianceByStoretype() {
    const data = D.planActual.byStoretype;
    const years = Array.from(new Set(data.map((d) => d.Year))).sort();
    const storeTypes = Array.from(new Set(data.map((d) => d.StoreType))).sort();
    const yearColor = { [years[0]]: COLORS.petrol, [years[1]]: COLORS.gold };
    const ctx = document.getElementById("chart-variance-storetype");
    charts.varianceStoretype = new Chart(ctx, {
      type: "bar",
      data: {
        labels: storeTypes.map(typeLabel),
        datasets: years.map((y) => ({
          label: String(y),
          data: storeTypes.map((st) => {
            const rec = data.find((d) => d.StoreType === st && d.Year === y);
            return rec ? rec.VariancePct : null;
          }),
          backgroundColor: yearColor[y] || COLORS.grey,
          borderRadius: 3,
        })),
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: "bottom" },
          tooltip: { callbacks: { label: (c) => c.dataset.label + ": " + fmtPct(c.raw) } },
        },
        scales: { y: { ticks: { callback: (v) => v + "%" } } },
      },
    });
  }

  // ---------------------------------------------------------------------
  // Variance page: over / under performer tables
  // ---------------------------------------------------------------------
  function varTable(elId, rows) {
    const body = rows
      .map((r) => {
        const cls = r.VariancePct >= 0 ? "pos" : "neg";
        return `
      <tr>
        <td>#${r.Store}</td>
        <td>${typeLabel(r.StoreType)}</td>
        <td class="num">${fmtEUR(r.ActualSales)}</td>
        <td class="num">${fmtEUR(r.VarianceAbs)}</td>
        <td class="num"><span class="var-pill ${cls}">${fmtPct(r.VariancePct)}</span></td>
      </tr>`;
      })
      .join("");
    document.getElementById(elId).innerHTML = `
      <thead><tr><th>Store</th><th>Type</th><th>Actual</th><th>Variance €</th><th>Variance %</th></tr></thead>
      <tbody>${body}</tbody>`;
  }

  // ---------------------------------------------------------------------
  // Cost & Profit page
  // ---------------------------------------------------------------------
  function renderPnlBridge() {
    const t = D.pnl.totals;
    const M = (v) => v / 1e6;
    const R = M(t.revenue);
    const CM = M(t.contributionMargin);
    const OP = M(t.operatingProfit);
    // Floating bars [start, end]
    const bars = [
      { label: "Revenue", range: [0, R], color: COLORS.petrol },
      { label: "− Variable cost", range: [CM, R], color: COLORS.red },
      { label: "Contribution margin", range: [0, CM], color: COLORS.petrolDark },
      { label: "− Fixed cost", range: [OP, CM], color: COLORS.red },
      { label: "Operating profit", range: [0, OP], color: COLORS.green },
    ];
    const ctx = document.getElementById("chart-pnl-bridge");
    charts.pnlBridge = new Chart(ctx, {
      type: "bar",
      data: {
        labels: bars.map((b) => b.label),
        datasets: [
          {
            data: bars.map((b) => b.range),
            backgroundColor: bars.map((b) => b.color),
            borderRadius: 3,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: (c) => {
                const [a, b] = c.raw;
                return "€" + fmtNum(Math.abs(b - a), 1) + "M";
              },
            },
          },
        },
        scales: { y: { ticks: { callback: (v) => "€" + v + "M" } } },
      },
    });
  }

  function renderMarginByStoretype() {
    const data = D.pnl.byStoretype.slice().sort((a, b) => a.StoreType.localeCompare(b.StoreType));
    const ctx = document.getElementById("chart-margin-storetype");
    charts.marginStoretype = new Chart(ctx, {
      data: {
        labels: data.map((d) => typeLabel(d.StoreType)),
        datasets: [
          {
            type: "bar",
            label: "Operating margin %",
            data: data.map((d) => d.OperatingMarginPct),
            backgroundColor: COLORS.petrol,
            borderRadius: 3,
            yAxisID: "y",
          },
          {
            type: "line",
            label: "Contribution margin %",
            data: data.map((d) => d.CMRatioPct),
            borderColor: COLORS.gold,
            backgroundColor: COLORS.gold,
            pointRadius: 3,
            tension: 0.1,
            yAxisID: "y",
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: "bottom" },
          tooltip: { callbacks: { label: (c) => c.dataset.label + ": " + fmtNum(c.raw, 1) + "%" } },
        },
        scales: { y: { ticks: { callback: (v) => v + "%" } } },
      },
    });
  }

  function renderMarginTrend() {
    const rows = D.pnl.monthly;
    const ctx = document.getElementById("chart-margin-trend");
    charts.marginTrend = new Chart(ctx, {
      type: "line",
      data: {
        labels: rows.map((r) => r.YearMonth),
        datasets: [
          {
            label: "Contribution margin %",
            data: rows.map((r) => r.CMRatioPct),
            borderColor: COLORS.gold,
            borderWidth: 2,
            pointRadius: 0,
            tension: 0.2,
          },
          {
            label: "Operating margin %",
            data: rows.map((r) => r.OperatingMarginPct),
            borderColor: COLORS.green,
            backgroundColor: "rgba(46, 125, 91, 0.12)",
            borderWidth: 2,
            pointRadius: 0,
            fill: true,
            tension: 0.2,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: "index", intersect: false },
        plugins: {
          legend: { position: "bottom" },
          tooltip: { callbacks: { label: (c) => c.dataset.label + ": " + fmtNum(c.raw, 1) + "%" } },
        },
        scales: {
          x: { ticks: { maxTicksLimit: 8 } },
          y: { ticks: { callback: (v) => v + "%" } },
        },
      },
    });
  }

  // ---------------------------------------------------------------------
  // Assumptions & Method page
  // ---------------------------------------------------------------------
  function renderAssumptions() {
    const rows = D.assumptions;
    document.getElementById("assump-table").innerHTML = `
      <thead><tr><th>Parameter</th><th>Value</th><th>Note</th></tr></thead>
      <tbody>
        ${rows
          .map(
            (r) => `<tr><td>${r.Parameter}</td><td class="val">${r.Value}</td><td>${r.Note}</td></tr>`
          )
          .join("")}
      </tbody>`;
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
  renderPnlSummary();

  renderYearFilter();
  renderPlanActualChart();
  renderVarianceByStoretype();

  varTable("var-top-table", D.varianceStores.top);
  varTable("var-bottom-table", D.varianceStores.bottom);

  renderPnlBridge();
  renderMarginByStoretype();
  renderMarginTrend();

  renderAssumptions();
})();

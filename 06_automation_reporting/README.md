# Automated Reporting — one command rebuilds the sales report

## 🎯 Business Problem
A monthly sales report built by hand means copying numbers, redrawing charts and
re-checking totals every time. This project turns that into one command:
`python generate_report.py` reads the data and regenerates all charts and the report.

---

## 📊 Dataset
`data/sales_clean.csv` — the **cleaned sales data from [project 05](../05_python_analytics_workflow/)**:
199 orders, January–December 2024, 4 products, 4 cities (simulated).

---

## 🧠 Methods
- KPI calculation in pandas (revenue, orders, average order value)
- Breakdowns by product, city and month
- Charts with matplotlib (headless backend, so it runs without a display, e.g. on a server)
- Markdown report written from a template in code — no manual copy-paste
- Tests that check the breakdowns add up to the total and that every report section is written

---

## 📈 What the generated report shows

| Figure | Value |
|---|---|
| Total revenue | 166,217 EUR |
| Orders | 199 |
| Average order value | 835.26 EUR |
| Revenue share of notebooks | 75.7 % |
| Strongest city | Köln (51,156 EUR) |
| Weakest / strongest month | October 3,435 EUR / November 30,351 EUR |

- **One product carries the business:** notebooks bring three quarters of revenue.
- **Monthly revenue swings by a factor of almost 9** — with only ~17 orders a month, single large
  orders decide the month. A monthly trend on this volume needs to be read with care.

See the full output in [`output/report.md`](output/report.md).

---

## 💡 What the automation delivers
- The report is **reproducible**: same data in, same report out.
- **No manual transfer errors**: every number in the report comes straight from the calculation.
- **Checked**: the tests fail if a breakdown no longer adds up to the total.

---

## ▶️ Run it

```bash
cd 06_automation_reporting
python generate_report.py      # writes output/*.png and output/report.md
python -m pytest tests -q      # 4 tests
```

---

## 🛠 Tools
Python · pandas · matplotlib · pytest

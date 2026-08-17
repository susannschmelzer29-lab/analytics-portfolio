# Project context for Claude Code

## What this is about
`09_controlling_kpi_analysis` — a **controlling-oriented** companion to project
08, built for a portfolio backing a *Bereichscontroller* application. Same real
Kaggle Rossmann data; new angle: **plan/actual, variance, and a cost/profit
(contribution-margin) model.**

## Environment (important!)
- **Windows + PowerShell**, Anaconda, VS Code. Pandas lives in the Anaconda
  Python (`C:/Users/susan/anaconda3/python.exe`), **not** the Windows-Store
  Python 3.14 (which has no pandas).
- **Give PowerShell commands one at a time**; **no here-strings** (they hang).

## Non-negotiable guardrails
- The dataset has **no cost/budget data.** The plan is a derived rule; every
  cost/profit euro is an **explicit assumption**, never presented as a real
  Rossmann figure. The honesty disclaimer appears in the notebook, the README,
  and on the dashboard (Overview banner + dedicated "Assumptions & Method" page).
- All assumptions live in one `ASSUMPTIONS` block in the notebook (§0).

## Key design decisions
- **Seasonal plan:** `PlanDaily(store, year, month) = mean(prior-year SAME-month
  daily sales) × (1 + 3%)`. The same-month baseline removes the seasonality
  artefact that a flat annual plan would create in monthly variance.
- **Analysis window:** FY2014 + FY2015-YTD. 2013 is baseline-only. All 1,115
  stores have prior-year history, so every store gets a plan.
- **Cost model:** variable-cost ratio per store type (80/83/79/81 %) + flat
  €900/open-day fixed cost → DB I → operating profit. Flat fixed cost means some
  low-revenue stores fall below break-even (surfaced as loss-making stores).
- **Scope:** open & non-zero-sales days only, consistent with project 08.
- The notebook is generated reproducibly; it exports 8 CSVs to `output/`.
  `dashboard/build_dashboard.py` turns those into `dashboard/data.js`
  (committed, powers the static GitHub Pages dashboard).

## Status
- Notebook runs error-free end-to-end on the real Kaggle `train.csv` +
  `store.csv` (verified locally). Headline: revenue €3,534.5 m vs plan
  €3,538.5 m (−0.1 %), operating margin 7.0 %, 104/1,115 loss-making stores.
- Dashboard (5 pages) verified rendering in-browser, no console errors.

## Files
Dockerfile, .dockerignore, .gitignore, requirements.txt, run_pipeline.py,
check_results.py, README.md, controlling_kpi_analysis.ipynb,
data/train_sample.csv, dashboard/ (index.html, style.css, app.js, data.js,
build_dashboard.py)

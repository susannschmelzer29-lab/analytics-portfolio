# Project context for Claude Code

## What this is about
Rossmann Store Sales EDA as a **portfolio project** (Data Analyst). Goal of
this work step: apply **Git and Docker** cleanly to the existing analysis
notebook so the project is reproducible and presentable as a GitHub artifact.
Portfolio project `08_rossmann_sales_analysis`.

## Environment (important!)
- **Windows + PowerShell**, Anaconda (base), VS Code.
- **Always give PowerShell commands one at a time** — never chained.
- **No here-strings** (`@" ... "@`) — they hang reliably. Write files
  directly instead of generating them via here-string.

## Decisions made
- **Docker default: headless pipeline** (`run_pipeline.py` executes the
  notebook, generates CSVs in `output/`). **JupyterLab** is optionally
  startable via an extra command.
- **Raw data is mounted**, not baked into the image. Only
  `data/train_sample.csv` (2,000 rows) lives in the repo.
- Large files (`train.csv` 37 MB, `rossmann_master_tableau.csv` ~165 MB) are
  excluded via `.gitignore` — must **not** be committed (GitHub limit 100 MB).
- The whole project (folder name, notebook, scripts, docs) was translated
  from German to English, including the notebook's column names
  (e.g. `Umsatz_pro_Tag` → `SalesPerDay`), so the output CSV schemas changed
  accordingly.

## Status
- Notebook runs **error-free end-to-end** with real Kaggle data (`train.csv`
  37 MB + `store.csv`), verified both locally and inside Docker.
- All 13+ output CSVs are generated correctly; master = 1,017,209 x 34, 0
  missing store merges.
- Bug fixed: the holiday label `"None"` collided with pandas' default NA
  tokens and was silently read back as missing data. Renamed to
  `"No Holiday"`.
- Analytical correction (found while cross-checking against previously
  fact-checked reference material): the naive Q1/Q4 findings were misleading.
  - **Q1:** raw min/max ratio (factor 8) is outlier-driven. The notebook now
    reports the robust top-decile vs. bottom-decile ratio (factor ~3) as the
    headline KPI, with the outlier figure kept as context.
  - **Q4:** the naive holiday uplift (+40%) is partly a **selection effect**
    — only 156 of 1,115 stores ever open on a public holiday, and those are
    disproportionately high-performing. The notebook now also computes a
    within-store comparison (same stores, holiday vs. normal day), which
    shows a smaller but still real effect (~17-36%), exported to
    `q4_holidays_within_store.csv`.
- `docker build -t rossmann-sales-analysis .`, the headless Docker run, and
  the JupyterLab Docker run have all been verified successfully.
- Built a standalone interactive HTML/JS dashboard in `dashboard/` (5 pages
  mirroring the original build plan: Executive Overview, Time Series, Promo
  & Holiday Analysis, Store Segments, Store Ranking). `dashboard/build_dashboard.py`
  regenerates `dashboard/data.js` from the CSVs in `output/`; `dashboard/index.html`
  opens standalone in any browser (no server required, Chart.js via CDN).
  The dashboard is also published live via GitHub Pages and is the project's
  canonical interactive deliverable.

## Still open / possible next steps
1. Optional: add `docker-compose.yml` with Postgres if a SQL part is desired.

## Files in this folder
Dockerfile, .dockerignore, .gitignore, requirements.txt, run_pipeline.py,
check_results.py, README.md, rossmann_sales_analysis.ipynb,
data/train_sample.csv

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
- Notebook runs **error-free end-to-end** (all 17 cells, exit 0).
- All 13 output CSVs are generated correctly; master = 1,017,209 x 34, 0
  missing store merges.
- Bug in `check_results.py` already fixed (removed redundant `sep=";"` line,
  added `low_memory=False`).

## Still open / possible next steps
1. Place `data/train.csv` + `store.csv` from Kaggle locally in `data/`.
2. `git init`, first commit, push repo to GitHub
   (`susannschmelzer29-lab/analytics-portfolio`, as subfolder `08_rossmann_sales_analysis`).
3. Test `docker build -t rossmann-sales-analysis .` locally.
4. Verify headless run + JupyterLab run once (see README).
5. Optional: add `docker-compose.yml` with Postgres if a SQL part is desired.

## Files in this folder
Dockerfile, .dockerignore, .gitignore, requirements.txt, run_pipeline.py,
check_results.py, README.md, rossmann_sales_analysis.ipynb,
data/train_sample.csv

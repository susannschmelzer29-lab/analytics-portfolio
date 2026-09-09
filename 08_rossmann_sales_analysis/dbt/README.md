# Rossmann Sales Analysis — dbt Migration

A rewrite of this project's pandas pipeline (`run_pipeline.py` → the
`rossmann_sales_analysis.ipynb` notebook it executes, plus `check_results.py`)
as a **dbt project**: staging → intermediate → marts, run against **DuckDB**,
with `schema.yml` data tests and a **GitHub Actions** CI workflow that runs
`dbt build` on every push.

This is the same analysis, the same six business questions and the same KPI
cockpit — restated in the vocabulary (dbt, tests, CI) that shows up in Data
Engineer job postings and ATS keyword filters.

## Why some of the notebook is *not* here

The notebook has two kinds of code: **data preparation + aggregation**
(cleaning, merging, group-bys) and **statistics/ML** (paired significance
tests via `scipy.stats`, k-means clustering via `scikit-learn`). dbt models
are SQL — the first kind translates directly, the second doesn't (you can't
express a t-test or an iterative clustering algorithm as a `SELECT`). So:

- **Cleaning, merge, Q1–Q6, KPI cockpit → dbt** (this project).
- **Significance tests & k-means segmentation → `stats_and_segmentation.py`**,
  a small standalone script that reads the *already-cleaned* data straight out
  of the dbt-built DuckDB database instead of repeating the pandas cleaning
  logic itself. Run it after `dbt build`.

## Architecture

```
seeds/                          raw_train_sample.csv, raw_store_sample.csv
  │                              (1,115-store / 2-day preview shipped in this
  │                               repo; swap in the full Kaggle CSVs for a
  │                               real run — see "Using the full dataset")
  ▼
models/staging/                 stg_rossmann__train, stg_rossmann__store
  │                              typing/renaming only, 1:1 with the source
  ▼
models/intermediate/            int_rossmann__train_enriched   (date parts, holiday/promo labels)
  │                              int_rossmann__store_cleaned    (missing-value handling, buckets)
  │                              int_rossmann__master            (the merge)
  │                              int_rossmann__analysis_scope    (Open=1 & Sales>0 -- the notebook's `frame`)
  ▼
models/marts/                   mart_store_performance           (Q1)
                                 mart_competition_proximity,
                                 mart_competition_correlation     (Q2)
                                 mart_seasonality_monthly/weekday/daily (Q3)
                                 mart_holidays, mart_holidays_within_store,
                                 mart_school_holidays             (Q4)
                                 mart_promo, mart_promo_by_storetype (Q5)
                                 mart_store_type, mart_store_type_x_assortment (Q6)
                                 mart_kpi_cockpit                 (management KPIs)
                                 mart_rossmann_master             (full-grain export,
                                                                    ~ rossmann_master_tableau.csv)
```

## Notebook → dbt model map

| Notebook (cell) | dbt model / test |
|---|---|
| `## 1 · Load Data` | `seeds/raw_train_sample.csv`, `seeds/raw_store_sample.csv` |
| `missing_report()`, data-quality summary (cell 9) | `tests/assert_no_negative_sales.sql`, `assert_no_sales_when_closed.sql`, `assert_no_customers_without_sales.sql`, `assert_unique_store_date.sql` |
| `normalize_dates()` / `clean_store()` (cells 12–13) | `int_rossmann__train_enriched`, `int_rossmann__store_cleaned` |
| merge → `master` (cell 13) | `int_rossmann__master` |
| `frame = master[Open==1 & Sales>0]` (cell 15) | `int_rossmann__analysis_scope` |
| Q1 store ranking (cell 17) | `mart_store_performance` |
| Q2 competition proximity (cell 20) | `mart_competition_proximity`, `mart_competition_correlation` |
| Q3 seasonality (cell 23) | `mart_seasonality_monthly`, `mart_seasonality_weekday`, `mart_seasonality_daily` |
| Q4 holidays (cell 26) | `mart_holidays`, `mart_holidays_within_store`, `mart_school_holidays` |
| Q5 promotions (cell 29) | `mart_promo`, `mart_promo_by_storetype` |
| Q6 store type (cell 32) | `mart_store_type`, `mart_store_type_x_assortment` |
| KPI cockpit (cell 35) | `mart_kpi_cockpit` |
| master export (cell 37) | `mart_rossmann_master` |
| §7 statistical rigor (cell 39) | `stats_and_segmentation.py::run_significance` |
| §8 store segmentation (cell 42) | `stats_and_segmentation.py::run_segmentation` |

`check_results.py`'s `df.shape` / `df.info()` sanity print is replaced end to
end by the 52 `schema.yml` + singular data tests dbt runs on every `dbt build`.

## Run it

```powershell
cd 08_rossmann_sales_analysis\dbt
pip install -r requirements.txt

# DuckDB needs no server/account — profiles.yml lives in this folder,
# not the usual ~/.dbt/, so every command below points at it explicitly.
dbt seed --profiles-dir .
dbt build --profiles-dir .          # runs all models + all tests

# optional: the ML/stats layer, reading the dbt output
python stats_and_segmentation.py
```

`dbt build` builds 2 seeds, 6 staging/intermediate views, 15 mart tables and
runs 52 data tests against them, all in a few seconds, all offline.

## Using the full dataset

The seeds here are the same 2,000-row / 1,115-store preview already in this
repo's `data/train_sample.csv`, plus a synthetic `store` sample generated to
match it (the real `store.csv` isn't in the repo — see the original
`README.md`'s "Getting the data" section). Two days of data is enough to
prove the pipeline runs end to end, but too little for the promo/holiday
significance tests to find a contrast (a store needs *both* a promo and a
non-promo day, or a holiday and a normal day, to pair against) --
`stats_and_segmentation.py` detects this and skips those tests with a message
rather than reporting a meaningless result.

To run against the real 1M+-row dataset: download `train.csv` and `store.csv`
from Kaggle, replace `seeds/raw_train_sample.csv` and
`seeds/raw_store_sample.csv` with them (same column names), then re-run
`dbt seed --profiles-dir . --full-refresh` and `dbt build --profiles-dir .`.

## CI

`.github/workflows/dbt_rossmann.yml` runs `dbt seed` + `dbt build` on every
push or PR that touches this folder — the same "tests pass in CI" signal a
production dbt project has.

## What's deliberately out of scope

Weather/Google-Trends enrichment (optional sources in the original notebook,
not present in this repo) and the dashboard/Tableau export step are unchanged
— they still read `mart_rossmann_master` the same way they read
`rossmann_master_tableau.csv` before.

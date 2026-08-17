# Rossmann Store Sales — Analysis Pipeline

Exploratory data analysis of the [Rossmann Store Sales](https://www.kaggle.com/c/rossmann-store-sales)
dataset (1,017,209 sales rows, 1,115 stores). The pipeline answers six
strategic questions and exports prepared CSVs for the dashboard.

## Presentations

[![Interactive Rossmann dashboard — click to open the live version](dashboard_preview.gif)](https://susannschmelzer29-lab.github.io/analytics-portfolio/08_rossmann_sales_analysis/dashboard/index.html)

*Animated preview of the five dashboard pages — **[open the live interactive version →](https://susannschmelzer29-lab.github.io/analytics-portfolio/08_rossmann_sales_analysis/dashboard/index.html)***

| | |
|---|---|
| **🎤 Narrated presentation** | _to be added_ |
| **🖥️ Interactive dashboard (live)** | [View on GitHub Pages →](https://susannschmelzer29-lab.github.io/analytics-portfolio/08_rossmann_sales_analysis/dashboard/index.html) |
| **🖥️ Interactive dashboard (source)** | [`dashboard/index.html`](dashboard/index.html) — standalone HTML/JS build, open directly in a browser |

## Contents

| Question | Output |
|-------|--------|
| Store ranking by daily sales | `q1_store_ranking.csv` |
| Effect of competition proximity | `q2_competition_distance.csv` |
| Seasonality (month / weekday) | `q3_seasonality_*.csv` |
| Holidays & school holidays | `q4_*.csv` |
| Promo uplift | `q5_promo*.csv` |
| Store type & assortment | `q6_*.csv` |
| Management KPIs | `kpi_management.csv` |
| **Statistical rigor** (CIs & significance) | `stats_significance.csv` |
| **Store segmentation** (k-means archetypes) | `store_segments.csv`, `segment_profiles.csv` |

Additionally: `rossmann_master_tableau.csv` (full master dataset, ~165 MB, is
**not** checked in, but generated locally).

## Consulting modules (§7–§9)

Beyond the descriptive analysis, the notebook adds three consulting-grade
modules — and the dashboard gains a **Store Archetypes** page, an **Executive
Summary** page, and a statistical-confidence panel.

**§7 · Statistical rigor — confidence intervals & significance.** The headline
levers are re-estimated with a *paired* design (each store is its own control),
reporting **95 % confidence intervals**, a paired-*t* *p*-value and Cohen's *d*.
Key result: promo is a large, tightly-estimated lever (**+41 %**, 95 % CI
40–43 %, *d* ≈ 2.3); school holidays a small but robust **+4.5 %**; the general
public-holiday effect is **not significant** once each store is its own control
(95 % CI −8 %…+2 %), quantifying the earlier selection-effect caveat. *Note:*
with 10⁵–10⁶ store-days almost anything is "significant" (*p* ≈ 0), so the
decision-relevant output is the **CI on the effect size**, not the *p*-value.

**§8 · Store segmentation — performance archetypes (k-means).** All 1,115 stores
are clustered on four standardized drivers (sales/day, basket, frequency,
competition distance; *k* chosen with the silhouette score). The result is four
actionable archetypes: **Flagship** (46 stores ≈ 9 % of sales), **Watchlist**
(356 stores, only ≈ 23 % of sales), and two mid-tiers split by *shape* —
**Frequency-driven** (many small baskets) vs. **Basket-driven** (fewer, larger
baskets). Each carries its own playbook (grow traffic vs. grow basket).

**§9 · Consulting executive summary.** Findings are restructured
hypothesis-driven and MECE (Situation → Complication → findings-with-confidence
→ prioritised recommendations with owner / impact / effort), the way a
consulting deck reads.

## Getting the data

The raw data is not in the repo due to its size. Only `data/train_sample.csv`
(2,000 rows) is included as a preview.

1. Download the data from Kaggle: `train.csv`, `store.csv` (optionally `test.csv`).
2. Place them in the `data/` folder.

## Run locally (without Docker)

```powershell
pip install -r requirements.txt
jupyter nbconvert --to notebook --execute --output executed.ipynb rossmann_sales_analysis.ipynb
python check_results.py
```

## With Docker

**Build the image:**

```powershell
docker build -t rossmann-sales-analysis .
```

**Run the pipeline headless** (default — generates all CSVs in `output/`):

```powershell
docker run --rm -v ${PWD}/data:/app/data -v ${PWD}/output:/app/output rossmann-sales-analysis
```

**Start JupyterLab in the container** (interactive notebook in the browser):

```powershell
docker run --rm -p 8888:8888 -v ${PWD}/data:/app/data -v ${PWD}/output:/app/output rossmann-sales-analysis jupyter lab --ip=0.0.0.0 --port=8888 --no-browser --allow-root
```

Then open the URL shown in the terminal (`http://127.0.0.1:8888/lab?token=...`) in your browser.

## Project structure

```
.
├── rossmann_sales_analysis.ipynb            # core analysis
├── run_pipeline.py                          # headless runner (Docker default)
├── check_results.py                         # QA check of the master CSV
├── requirements.txt
├── Dockerfile
├── .dockerignore / .gitignore
├── data/                                     # raw data (mounted) + sample
├── output/                                   # generated CSVs (not in repo)
└── figures/                                  # generated charts (not in repo)
```

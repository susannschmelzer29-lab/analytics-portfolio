# Rossmann Controlling — Plan/Actual, Variance & Profitability

A **controlling-oriented** companion to
[project 08](../08_rossmann_sales_analysis/). It takes the same real Kaggle
*Rossmann Store Sales* data (1,017,209 rows · 1,115 stores · 2013-01-01 →
2015-07-31) and builds a small **controlling cockpit**:

1. **Plan/Actual comparison** — budget vs. actual revenue per store, store type and month
2. **Variance analysis** — absolute (€) and relative (%), with over-/under-performer ranking
3. **Cost & profit KPIs** — a contribution-margin model (*Deckungsbeitragsrechnung*) → operating profit

> ## ⚠️ Honesty note — the most important part
> The Kaggle dataset contains **only** `Sales`, `Customers`, `Promo`,
> `StoreType`, etc. It has **no budget, cost or margin data whatsoever.**
> Therefore, in this project:
> * the **plan** is a *transparent, derived planning rule* (prior-year baseline +
>   an assumed growth target) — **not** an official Rossmann budget;
> * every **cost and profit** figure is an **explicit modelling assumption**,
>   clearly flagged as such;
> * **none** of the euro cost/profit values are real Rossmann company figures.
>
> The point is to demonstrate *controlling method and reasoning* on real sales
> data — honestly, without inventing facts. All assumptions live in one place
> (the `ASSUMPTIONS` block in the notebook) so they can be changed and re-run.

## Presentations

| | |
|---|---|
| **🖥️ Interactive dashboard (live)** | [View on GitHub Pages →](https://susannschmelzer29-lab.github.io/analytics-portfolio/09_controlling_kpi_analysis/dashboard/index.html) |
| **🖥️ Interactive dashboard (source)** | [`dashboard/index.html`](dashboard/index.html) — standalone HTML/JS build, opens directly in a browser |
| **📓 Analysis notebook** | [`controlling_kpi_analysis.ipynb`](controlling_kpi_analysis.ipynb) |

The dashboard has five pages: **Executive Overview**, **Plan vs. Actual**,
**Variance Analysis**, **Cost & Profit**, and a dedicated **Assumptions &
Method** page (transparency by design).

## Methodology

### 1 · The plan (budget)

> `PlanDaily(store, year, month) = mean(prior-year same-month daily sales) × (1 + growth target)`

* **Baseline:** each store's average daily sales in the **same calendar month of
  the previous year** (2013 plans 2014; 2014 plans 2015). Using the *same month*
  makes the plan **seasonal**, so monthly variance reflects genuine performance
  rather than the large Jan→Dec seasonal swing.
* **Growth target:** an assumed **+3 % YoY** — deliberately close to the store
  base's *realised* 2014-vs-2013 run-rate, so the plan is ambitious-but-plausible.
* The daily plan is applied to **every actual trading day**, so the plan total
  scales with realised trading days and the variance isolates *daily sales
  performance vs. target*.

**Why this method?** It mirrors a common first budget pass in real
*Bereichscontrolling*: take last year's run-rate per unit and apply a corporate
growth target. It is one valid choice among several (moving average, top-down,
bottom-up) — see *Limitations*.

### 2 · Variance analysis

`Variance = Actual − Plan`, reported in € and as % of plan, at day / month /
store / store-type level. The dashboard ranks the top over- and
under-performers — the accounts a controller follows up on first.

### 3 · Cost & profit model (assumed — contribution-margin accounting)

| Step | Definition |
|------|------------|
| Variable cost | `Sales × variable-cost-ratio[StoreType]` (COGS + variable opex) |
| **Contribution margin (DB I)** | `Sales − variable cost` |
| Fixed cost | `€900 × open trading days` (rent, base staffing, utilities) |
| **Operating profit** | `Contribution margin − fixed cost` |

Because fixed cost is flat per store, low-revenue stores can fall **below
break-even** — surfacing them is exactly the profitability screening controlling
is asked for.

### Model assumptions (all illustrative — not real figures)

| Parameter | Value | Note |
|---|---|---|
| Planned YoY growth target | **+3 %** | Applied to each store's prior-year avg. daily sales |
| Variable cost ratio — type a (Basic) | **80 %** of sales | COGS + variable operating cost |
| Variable cost ratio — type b (Extra) | **83 %** of sales | Broader assortment → more low-margin volume |
| Variable cost ratio — type c (Extended) | **79 %** of sales | Leaner assortment |
| Variable cost ratio — type d | **81 %** of sales | COGS + variable operating cost |
| Fixed cost per open trading day | **€900** | Per store per open day |

## Headline results (FY2014 + FY2015-YTD, under the above assumptions)

| KPI | Value |
|---|---|
| Actual revenue | €3,534.5 m |
| Plan revenue | €3,538.5 m |
| Revenue variance | **−0.1 %** (base close to plan; the spread *between* stores is the story) |
| Contribution margin (DB I) | €698.1 m (**19.8 %** of sales) |
| Operating profit | €247.1 m (**7.0 %** margin) |
| Loss-making stores (assumed model) | **104** of 1,115 |

**Two example findings the method surfaces:**
* **Calendar effects vs. performance** — March 2014 shows a −10 % variance and
  April 2014 a +7 % one, because **Easter shifted from March 2013 to April 2014**.
  A controller separates such timing shifts from genuine trend before acting.
* **Operating leverage** — operating margin differs by store type (≈6–8 %) and
  peaks each December, because a flat fixed-cost hurdle is easier to clear at
  higher daily revenue.

## Outputs (`output/`, generated — not checked in)

| File | Content |
|---|---|
| `kpi_controlling.csv` | Headline KPI cockpit |
| `assumptions.csv` | The documented model assumptions |
| `plan_actual_monthly.csv` | Monthly plan vs. actual + variance |
| `variance_by_storetype.csv` | Variance by store type / year |
| `plan_actual_by_store.csv` | Store-level plan vs. actual + variance |
| `pnl_monthly.csv` | Monthly P&L (revenue → DB I → operating profit) |
| `pnl_by_storetype.csv` | P&L by store type |
| `profit_by_store.csv` | Store-level profit + break-even screen |

## Getting the data

The raw data is not in the repo due to its size. Only `data/train_sample.csv`
(2,000 rows) is included as a preview.

1. Download `train.csv` and `store.csv` from the Kaggle
   [Rossmann Store Sales](https://www.kaggle.com/c/rossmann-store-sales) competition.
2. Place them in the `data/` folder.

## Run locally (without Docker)

```powershell
pip install -r requirements.txt
jupyter nbconvert --to notebook --execute --output executed.ipynb controlling_kpi_analysis.ipynb
python check_results.py
python dashboard/build_dashboard.py   # regenerates dashboard/data.js from output/
```

Then open [`dashboard/index.html`](dashboard/index.html) in a browser.

## With Docker

**Build the image:**

```powershell
docker build -t controlling-kpi-analysis .
```

**Run the pipeline headless** (default — generates all CSVs in `output/`):

```powershell
docker run --rm -v ${PWD}/data:/app/data -v ${PWD}/output:/app/output controlling-kpi-analysis
```

**Start JupyterLab in the container:**

```powershell
docker run --rm -p 8888:8888 -v ${PWD}/data:/app/data -v ${PWD}/output:/app/output controlling-kpi-analysis jupyter lab --ip=0.0.0.0 --port=8888 --no-browser --allow-root
```

## Limitations

1. **No real financials.** The dataset has no budget/cost/margin data. The plan
   is a derived rule; all cost/profit euros are **assumptions**, not Rossmann actuals.
2. **Plan design is one valid choice** (others: moving average, seasonal
   top-down, bottom-up). Results depend on the method.
3. **Flat growth target** ignores store-specific potential, cannibalisation and
   competition dynamics.
4. **Simplified cost model** — one variable ratio per store type + one flat daily
   fixed cost. Real structures vary by location, wage level, lease and promo intensity.
5. **2015 is year-to-date** (Jan–Jul); annual 2015 figures are partial.
6. Scope excludes closed and zero-sales days, consistent with project 08.

## Project structure

```
.
├── controlling_kpi_analysis.ipynb   # core analysis (plan/actual, variance, P&L)
├── run_pipeline.py                  # headless runner (Docker default)
├── check_results.py                 # QA check of the KPI outputs
├── requirements.txt
├── Dockerfile
├── .dockerignore / .gitignore
├── data/                            # raw data (mounted) + sample
├── output/                          # generated CSVs (not in repo)
├── figures/                         # generated charts (not in repo)
└── dashboard/                       # standalone HTML/JS cockpit
    ├── index.html
    ├── style.css
    ├── app.js
    ├── data.js                      # generated by build_dashboard.py (committed)
    └── build_dashboard.py
```

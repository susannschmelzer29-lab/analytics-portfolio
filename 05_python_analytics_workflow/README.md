# 05 – Python Analytics Workflow: Data Cleaning Showcase

An end-to-end **data cleaning pipeline** in pandas: starting from a deliberately
messy sales export, the notebook profiles the data, fixes each quality issue
explicitly, validates the result, and computes business KPIs.

This project complements `03_sql_foundations` and `04_sql_advanced_cases` by
focusing on the **Python / pandas** side of an analyst's workflow — the
unglamorous-but-essential work of turning raw, real-world data into something
trustworthy.

## Contents

```
05_python_analytics_workflow/
├─ README.md
├─ 01_data_cleaning_workflow.ipynb   ← the full workflow (runnable, with output)
└─ data/
   ├─ raw/messy_sales.csv            ← deliberately messy input
   └─ clean/sales_clean.csv          ← validated output
```

## The messy input

`data/raw/messy_sales.csv` simulates common real-world data problems:

| Problem | Example |
|---|---|
| Inconsistent casing & whitespace | `" Notebook"`, `NOTEBOOK`, `monitor` |
| Typos in categories | `Notbook`, `Moniter`, `Tastaur`, `Mouse` |
| Mixed city spellings | `Muenchen`, `Koeln`, `koln` |
| Mixed date formats | `2024-03-06`, `21.11.2024`, `03/05/2024`, `2024/11/12` |
| German vs. international decimals | `199,00` vs. `199.00` |
| Stray currency symbols | `25.00 €` |
| Duplicate rows | full-row repeats |
| Missing values | empty city / price fields |
| Invalid quantities | `-3`, `0`, `99` |

## Cleaning steps

1. Load everything as string (safe for messy data)
2. Profile: missing values, empty strings, duplicates, distinct category values
3. Remove duplicate rows
4. Standardise text (strip whitespace, lowercase + map typos to canonical labels)
5. Parse prices (`,` / `.` / `€` → `float`)
6. Parse four date formats → `datetime`
7. Coerce types and remove implausible quantities
8. Drop rows missing essential fields
9. Validate with assertions, add a derived `revenue` column, save clean CSV

## Verified results

After cleaning, **228 raw rows → 199 clean rows** (7 duplicates, 4 invalid
quantities, 18 rows with missing essential fields removed).

- **Total revenue:** 166,217.00 €
- **Total orders:** 199
- **Average order value:** 835.26 €
- **Revenue by product:** Notebook 125,860 · Monitor 29,452 · Tastatur 5,880 · Maus 5,025
- **Revenue by city:** Köln 51,156 · Berlin 41,355 · München 37,744 · Hamburg 35,962

## Skills demonstrated

pandas profiling · string normalisation & mapping · robust type parsing
(prices, dates) · data validation with assertions · `groupby` / `resample`
aggregation · reproducible, documented workflow.

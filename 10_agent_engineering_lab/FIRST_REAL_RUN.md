# First run over a real dataset

**Date:** 2026-11-10
**Input:** `08_rossmann_sales_analysis/data/train_sample.csv`. These are real Kaggle
Rossmann rows: 2,000 rows, 9 columns and 1,115 stores. The file was copied into a
scratch folder, so `data/raw/` stayed untouched.

```bash
python -m agentlab.pipeline --input <folder with train_sample.csv> \
    --output run.json --key Store,Date --docs docs
```

Business key: `Store,Date`. Each store should have one row per day.

## Result

| | |
|---|---|
| Canary | fully detected (the run would have aborted otherwise) |
| Files checked | 1 |
| Status | **amber**, with 0 red findings |
| Duplicates on `Store,Date` | none |
| Missing values | none in any column |

| Code | Column | Finding |
|---|---|---|
| `CONSTANT` | `Promo` | holds a single value throughout |
| `CONSTANT` | `StateHoliday` | holds a single value throughout |

## What the finding means

Neither column is broken. The sample is. `Date` has only two distinct values
(2015-07-30 and 2015-07-31), so the file is the **last two days of the dataset**
and not a random draw. Both days were promo days and neither was a holiday,
so both columns look constant.

The checks repair nothing, and this run shows why that matters: the data was
fine. The defect was in how the sample was cut, and a person had to see that.
Anyone who reads this sample as representative and analyses promo or holiday
effects on it gets nothing. Projects 08 and 09 use it only as a small
smoke-test file. Their analyses run on the full dataset.

## What the run did not cover

* No model narration. No API key was set, so steps 2–3 of `run_pipeline.sh`
  did not run. The findings above are complete without it.
* There are no range checks (e.g. `Sales >= 0`, `Customers = 0` on closed days).
  The README lists them as a limitation.

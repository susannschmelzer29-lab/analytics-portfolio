"""
Statistical rigor & store segmentation -- deliberately kept OUTSIDE dbt.

Why: dbt models are SQL. Paired significance testing (scipy.stats) and
k-means clustering (scikit-learn) are iterative/statistical procedures that
don't express as SQL aggregates, so they stay in Python. What DOES move into
dbt is the cleaning, merging and filtering these steps used to do for
themselves in the notebook -- this script now reads that already-clean data
straight out of the dbt-built DuckDB database (main_marts.mart_rossmann_master)
instead of repeating pandas cleaning logic.

Run after `dbt build --profiles-dir .` (needs rossmann.duckdb to exist):
    python stats_and_segmentation.py

Reproduces notebook cells 39 ("Statistical rigor") and 42 ("Store
segmentation") 1:1, just re-pointed at the dbt output.
"""

import duckdb
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

DB_PATH = "rossmann.duckdb"
OUTPUT_DIR = "output"

import os
os.makedirs(OUTPUT_DIR, exist_ok=True)


def load_frame(con):
    """Equivalent of the notebook's `frame` = master[Open==1 & Sales>0]."""
    master = con.sql("select * from main_marts.mart_rossmann_master").df()
    frame = master[(master["is_open"] == 1) & (master["sales"] > 0)].copy()
    return master, frame


def paired_effect(treat, control, label, test="paired t-test (per store)"):
    """95% CI + paired test on the per-store relative uplift treat vs control.
    Returns None if fewer than 2 stores have both an exposed and an unexposed
    day in this sample -- the paired test is undefined below that."""
    treat, control = np.asarray(treat, float), np.asarray(control, float)
    if len(treat) < 2:
        print(f"[stats] Skipping '{label}': only {len(treat)} store(s) with both "
              "groups present in this sample -- needs a bigger date range. "
              "Run against the full Kaggle dataset for a real result.")
        return None
    uplift = (treat / control - 1) * 100
    n = len(uplift)
    mean = uplift.mean()
    ci_lo, ci_hi = stats.t.interval(0.95, n - 1, loc=mean, scale=stats.sem(uplift))
    t_stat, p = stats.ttest_rel(treat, control)
    diff = treat - control
    cohen_d = diff.mean() / diff.std(ddof=1)
    return {
        "Effect": label, "n_stores": n, "MeanUplift_%": round(mean, 1),
        "CI95_low_%": round(ci_lo, 1), "CI95_high_%": round(ci_hi, 1),
        "p_value": p, "CohensD": round(cohen_d, 2), "Test": test,
    }


def run_significance(frame):
    # Promo: each store's mean sales on promo vs non-promo days.
    sp = frame.groupby(["store_id", "promo_label"])["sales"].mean().unstack().dropna()
    promo_eff = paired_effect(sp.get("With Promo"), sp.get("No Promo"), "Promo uplift") \
        if "With Promo" in sp and "No Promo" in sp else None

    # Public holiday: within-store (only stores that ever open on holidays).
    holiday_stores = frame.loc[frame["holiday_label"] != "No Holiday", "store_id"].unique()
    same_store = frame[frame["store_id"].isin(holiday_stores)].copy()
    if not same_store.empty:
        same_store["on_holiday"] = np.where(same_store["holiday_label"] != "No Holiday", "Holiday", "Normal")
        sh = same_store.groupby(["store_id", "on_holiday"])["sales"].mean().unstack().dropna()
        holiday_eff = paired_effect(sh.get("Holiday"), sh.get("Normal"), "Public-holiday uplift (within-store)") \
            if "Holiday" in sh and "Normal" in sh else None
    else:
        holiday_eff = None

    # School holiday.
    sc = frame.copy()
    sc["school"] = np.where(sc["is_school_holiday"] == 1, "School", "Normal")
    ss = sc.groupby(["store_id", "school"])["sales"].mean().unstack().dropna()
    school_eff = paired_effect(ss.get("School"), ss.get("Normal"), "School-holiday uplift") \
        if "School" in ss and "Normal" in ss else None

    rows = [e for e in [promo_eff, holiday_eff, school_eff] if e is not None]
    if not rows:
        print("[stats] Not enough contrast in this sample to run paired tests "
              "(needs both groups present per store) -- run against the full "
              "Kaggle dataset for real results.")
        return None

    sig = pd.DataFrame(rows)
    sig["p_value"] = sig["p_value"].apply(lambda p: f"{p:.1e}")
    sig.to_csv(f"{OUTPUT_DIR}/stats_significance.csv", index=False, encoding="utf-8-sig")
    print("Effect sizes with 95% confidence intervals (paired, per store):\n")
    print(sig.to_string(index=False))
    return sig


def run_segmentation(con, frame):
    q1 = frame.groupby("store_id").agg(
        TotalSales=("sales", "sum"),
        SalesPerDay=("sales", "mean"),
        CustomersPerDay=("customers", "mean"),
        SalesPerCustomer=("sales_per_customer", "mean"),
        StoreType=("store_type", "first"),
        Assortment=("assortment_label", "first"),
    ).reset_index()

    store = con.sql(
        "select store_id, competition_distance from main_intermediate.int_rossmann__store_cleaned"
    ).df()
    seg = q1.merge(store, on="store_id", how="left")
    seg["CompLog"] = np.log10(seg["competition_distance"].clip(lower=1))
    features = ["SalesPerDay", "SalesPerCustomer", "CustomersPerDay", "CompLog"]
    X = StandardScaler().fit_transform(seg[features])

    sil = {k: silhouette_score(X, KMeans(k, random_state=42, n_init=10).fit_predict(X))
           for k in range(3, min(7, len(seg) - 1))} if len(seg) > 7 else {}
    print("Silhouette score by k:", {k: round(v, 3) for k, v in sil.items()})

    k = 4 if len(seg) >= 4 else max(2, len(seg) - 1)
    seg["Segment"] = KMeans(k, random_state=42, n_init=10).fit_predict(X)

    prof = seg.groupby("Segment").agg(
        Stores=("store_id", "size"),
        SalesPerDay=("SalesPerDay", "mean"),
        SalesPerCustomer=("SalesPerCustomer", "mean"),
        CustomersPerDay=("CustomersPerDay", "mean"),
        CompetitionDistance=("competition_distance", "median"),
        TotalSales=("TotalSales", "sum"),
    ).reset_index()
    prof["StoreShare_%"] = (prof["Stores"] / prof["Stores"].sum() * 100).round(1)
    prof["SalesShare_%"] = (prof["TotalSales"] / prof["TotalSales"].sum() * 100).round(1)

    med_basket = seg["SalesPerCustomer"].median()
    med_freq = seg["CustomersPerDay"].median()
    sales_rank = prof["SalesPerDay"].rank(ascending=False)

    def archetype(row):
        r = sales_rank[row.name]
        hi_basket = row["SalesPerCustomer"] >= med_basket
        hi_freq = row["CustomersPerDay"] >= med_freq
        if r == 1:
            return "Flagship — high volume"
        if r == len(prof):
            return "Watchlist — low volume"
        if hi_freq and not hi_basket:
            return "Frequency-driven — many small baskets"
        if hi_basket and not hi_freq:
            return "Basket-driven — few large baskets"
        return "Standard performer"

    prof["Archetype"] = prof.apply(archetype, axis=1)
    seg = seg.merge(prof[["Segment", "Archetype"]], on="Segment", how="left")

    prof.round(2).to_csv(f"{OUTPUT_DIR}/segment_profiles.csv", index=False, encoding="utf-8-sig")
    seg[["store_id", "StoreType", "Assortment", "SalesPerDay", "SalesPerCustomer",
         "CustomersPerDay", "competition_distance", "Segment", "Archetype"]].round(2).to_csv(
        f"{OUTPUT_DIR}/store_segments.csv", index=False, encoding="utf-8-sig")

    print("\nStore archetypes (mean drivers per segment):")
    print(prof[["Segment", "Archetype", "Stores", "StoreShare_%", "SalesShare_%",
                "SalesPerDay", "SalesPerCustomer", "CustomersPerDay"]]
          .sort_values("SalesPerDay", ascending=False).to_string(index=False))
    return prof, seg


def main():
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(
            f"{DB_PATH} not found. Run `dbt build --profiles-dir .` first."
        )
    con = duckdb.connect(DB_PATH, read_only=True)
    master, frame = load_frame(con)
    print(f"Loaded {len(frame):,} analysis-scope rows from the dbt marts "
          f"({len(master):,} rows total in mart_rossmann_master).\n")

    print("=" * 70)
    print("STATISTICAL RIGOR — confidence intervals & significance")
    print("=" * 70)
    run_significance(frame)

    print("\n" + "=" * 70)
    print("STORE SEGMENTATION — k-means archetypes")
    print("=" * 70)
    run_segmentation(con, frame)
    con.close()


if __name__ == "__main__":
    main()

"""
01 - Statistics Foundations
===========================
Small, testable helpers behind the notebook. The question they answer:
which number should a report show as "the typical order" when one order
is far larger than the rest?
"""

from pathlib import Path

import pandas as pd

DATA_FILE = Path(__file__).resolve().parent / "ecommerce_orders.csv"


def load_orders(path: Path = DATA_FILE) -> pd.DataFrame:
    df = pd.read_csv(path)
    expected = {"order_id", "customer_id", "order_value"}
    missing = expected - set(df.columns)
    if missing:
        raise ValueError(f"missing columns: {sorted(missing)}")
    if df["order_id"].duplicated().any():
        raise ValueError("order_id must be unique")
    if (df["order_value"] <= 0).any():
        raise ValueError("order_value must be positive")
    return df


def describe(values: pd.Series) -> dict:
    """Location and spread, with and without sensitivity to extreme values."""
    q1, q3 = values.quantile([0.25, 0.75])
    return {
        "n": int(values.count()),
        "mean": float(values.mean()),
        "median": float(values.median()),
        "std": float(values.std(ddof=1)),
        "q1": float(q1),
        "q3": float(q3),
        "iqr": float(q3 - q1),
        "min": float(values.min()),
        "max": float(values.max()),
    }


def iqr_outliers(values: pd.Series, k: float = 1.5) -> pd.Series:
    """Tukey's rule: a value is an outlier if it lies more than k * IQR
    beyond the first or third quartile. Returns a boolean mask."""
    q1, q3 = values.quantile([0.25, 0.75])
    iqr = q3 - q1
    return (values < q1 - k * iqr) | (values > q3 + k * iqr)


def trimmed_mean(values: pd.Series, share: float = 0.1) -> float:
    """Mean after dropping the lowest and highest `share` of values
    (at least one value on each side once share * n >= 1)."""
    s = values.sort_values().reset_index(drop=True)
    cut = int(share * len(s))
    return float(s.iloc[cut : len(s) - cut].mean()) if cut else float(s.mean())


def outlier_effect(values: pd.Series) -> dict:
    """How much the outliers move each statistic."""
    mask = iqr_outliers(values)
    with_all = describe(values)
    without = describe(values[~mask])
    return {
        "outliers": values[mask].tolist(),
        "outlier_revenue_share": float(values[mask].sum() / values.sum()),
        "mean_with": with_all["mean"],
        "mean_without": without["mean"],
        "median_with": with_all["median"],
        "median_without": without["median"],
        "mean_shift_pct": 100 * (with_all["mean"] - without["mean"]) / without["mean"],
        "median_shift_pct": 100 * (with_all["median"] - without["median"]) / without["median"],
    }

"""Hand-checkable tests for stats_foundations.py.

Run from the project folder:  python -m pytest tests -q
"""

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import stats_foundations as sf  # noqa: E402


@pytest.fixture(scope="module")
def values() -> pd.Series:
    return sf.load_orders()["order_value"]


def test_dataset_is_the_expected_one(values):
    assert len(values) == 12
    assert values.sum() == 735


def test_mean_and_median(values):
    d = sf.describe(values)
    assert d["mean"] == pytest.approx(735 / 12)  # 61.25
    assert d["median"] == 21.5  # (21 + 22) / 2


def test_only_one_order_above_the_mean(values):
    assert (values > values.mean()).sum() == 1


def test_iqr_rule_flags_exactly_the_500_order(values):
    assert values[sf.iqr_outliers(values)].tolist() == [500]


def test_outlier_moves_mean_far_more_than_median(values):
    e = sf.outlier_effect(values)
    assert e["outlier_revenue_share"] == pytest.approx(500 / 735)
    assert e["mean_shift_pct"] > 150
    assert abs(e["median_shift_pct"]) < 5


def test_trimmed_mean_drops_one_value_each_side(values):
    # 10 % of 12 = 1.2 -> one value cut at each end: drop 18 and 500
    assert sf.trimmed_mean(values) == pytest.approx((735 - 18 - 500) / 10)


def test_validation_rejects_bad_input(tmp_path):
    bad = tmp_path / "orders.csv"
    bad.write_text("order_id,customer_id,order_value\n1,101,20\n1,102,-5\n")
    with pytest.raises(ValueError):
        sf.load_orders(bad)

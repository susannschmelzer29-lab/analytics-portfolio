"""Tests for ab_testing.py. Reference values were cross-checked against
statsmodels (proportions_ztest, proportion_confint(method="wilson"),
confint_proportions_2indep(method="newcomb")).

Run from the project folder:  python -m pytest tests -q
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ab_testing as ab  # noqa: E402


def test_summary_matches_the_data():
    s = ab.summary(ab.load_test())
    assert s.loc["A", ["users", "conversions"]].tolist() == [10, 3]
    assert s.loc["B", ["users", "conversions"]].tolist() == [10, 7]


def test_wilson_intervals():
    assert ab.wilson_ci(3, 10) == pytest.approx((0.10779, 0.60322), abs=1e-5)
    assert ab.wilson_ci(7, 10) == pytest.approx((0.39678, 0.89221), abs=1e-5)


def test_difference_interval_includes_zero():
    lo, hi = ab.difference_ci(3, 10, 7, 10)
    assert (lo, hi) == pytest.approx((-0.02882, 0.67182), abs=1e-5)
    assert lo < 0 < hi


def test_not_significant_at_five_percent():
    t = ab.tests(3, 10, 7, 10)
    assert t["z"] == pytest.approx(1.78885, abs=1e-5)
    assert t["p_ztest"] == pytest.approx(0.07364, abs=1e-5)
    assert t["p_fisher"] == pytest.approx(0.17890, abs=1e-5)
    assert min(t["p_ztest"], t["p_fisher"]) > 0.05


def test_sample_size_grows_as_the_lift_shrinks():
    sizes = [ab.sample_size_per_group(0.30, pb) for pb in (0.70, 0.45, 0.40, 0.36, 0.33)]
    assert sizes == [24, 163, 356, 963, 3763]
    assert sizes == sorted(sizes)


def test_power_of_the_actual_test_is_low():
    assert ab.power(0.3, 0.7, 10) == pytest.approx(0.426, abs=1e-3)
    assert ab.power(0.3, 0.4, 356) == pytest.approx(0.80, abs=0.01)


def test_validation_rejects_bad_input(tmp_path):
    bad = tmp_path / "ab.csv"
    bad.write_text("user_id,group,converted\n1,A,0\n2,C,1\n")
    with pytest.raises(ValueError):
        ab.load_test(bad)

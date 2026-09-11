"""Reconciliation tests for the controlling outputs.

Why these exist
---------------
`check_results.py` printed the figures. Printing is not checking: nobody
reads a wall of numbers on the twentieth run, and a notebook that silently
produced half a result would look exactly the same.

These tests assert instead. Every one of them encodes an identity that
must hold if the pipeline ran correctly — the same reasoning a controller
applies before signing a report.

Run:  python -m pytest
They read `output/`, so the notebook must have run at least once.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

OUTPUT = Path(__file__).resolve().parents[1] / "output"

# The dataset is fixed: Rossmann has 1,115 stores. A different number
# means rows were lost or duplicated somewhere in the pipeline.
EXPECTED_STORES = 1115

EXPECTED_FILES = [
    "assumptions.csv",
    "kpi_controlling.csv",
    "plan_actual_by_store.csv",
    "plan_actual_monthly.csv",
    "pnl_by_storetype.csv",
    "pnl_monthly.csv",
    "profit_by_store.csv",
    "variance_by_storetype.csv",
]


def read(name: str) -> pd.DataFrame:
    # utf-8-sig: the exports carry a BOM, and without this the first
    # column name silently becomes "﻿Store" and every lookup fails.
    return pd.read_csv(OUTPUT / name, encoding="utf-8-sig")


@pytest.fixture(scope="module")
def kpi() -> dict[str, float]:
    df = read("kpi_controlling.csv")
    return dict(zip(df["KPI"], df["Value"]))


# --- the outputs exist at all -----------------------------------------------

@pytest.mark.parametrize("name", EXPECTED_FILES)
def test_output_file_exists_and_is_not_empty(name):
    path = OUTPUT / name
    assert path.exists(), f"{name} missing — has the notebook run?"
    assert path.stat().st_size > 0


# --- grain ------------------------------------------------------------------

def test_one_row_per_store():
    df = read("profit_by_store.csv")
    assert len(df) == EXPECTED_STORES
    assert df["Store"].is_unique


def test_store_counts_add_up_across_store_types():
    assert int(read("pnl_by_storetype.csv")["Stores"].sum()) == EXPECTED_STORES


def test_no_missing_values_in_the_key_figures():
    df = read("profit_by_store.csv")
    for col in ["Revenue", "VariableCost", "FixedCost", "OperatingProfit"]:
        assert df[col].notna().all(), f"{col} contains missing values"


# --- reconciliation: the tests that actually catch things -------------------

def test_revenue_reconciles_between_store_and_store_type():
    """A wrong join or a lost filter changes a total. No column-level
    check would notice; this one does."""
    by_store = read("profit_by_store.csv")["Revenue"].sum()
    by_type = read("pnl_by_storetype.csv")["Revenue"].sum()
    assert by_store == pytest.approx(by_type, rel=1e-6)


def test_revenue_reconciles_with_the_kpi_cockpit(kpi):
    """The cockpit is what a manager reads. If it disagrees with the
    detail behind it, the detail is not the problem — the cockpit is."""
    detail_millions = read("profit_by_store.csv")["Revenue"].sum() / 1e6
    assert detail_millions == pytest.approx(kpi["Actual Revenue (EUR million)"], abs=0.1)


def test_loss_making_store_count_matches_the_cockpit(kpi):
    counted = int((read("profit_by_store.csv")["OperatingProfit"] < 0).sum())
    assert counted == int(kpi["Loss-making Stores (Count)"])


# --- accounting identities --------------------------------------------------

@pytest.mark.parametrize("name", ["pnl_by_storetype.csv", "pnl_monthly.csv",
                                  "profit_by_store.csv"])
def test_contribution_margin_is_revenue_minus_variable_cost(name):
    df = read(name)
    expected = df["Revenue"] - df["VariableCost"]
    assert (df["ContributionMargin"] - expected).abs().max() < 1.0


@pytest.mark.parametrize("name", ["pnl_by_storetype.csv", "pnl_monthly.csv",
                                  "profit_by_store.csv"])
def test_operating_profit_is_contribution_margin_minus_fixed_cost(name):
    df = read(name)
    expected = df["ContributionMargin"] - df["FixedCost"]
    assert (df["OperatingProfit"] - expected).abs().max() < 1.0


@pytest.mark.parametrize("name", ["pnl_by_storetype.csv", "pnl_monthly.csv",
                                  "profit_by_store.csv"])
def test_total_cost_is_variable_plus_fixed(name):
    df = read(name)
    expected = df["VariableCost"] + df["FixedCost"]
    assert (df["TotalCost"] - expected).abs().max() < 1.0


@pytest.mark.parametrize("name", ["plan_actual_monthly.csv",
                                  "plan_actual_by_store.csv",
                                  "variance_by_storetype.csv"])
def test_variance_is_actual_minus_plan(name):
    """The definition of a variance. If this ever fails, either the sign
    convention flipped or plan and actual were joined on the wrong key —
    both produce a report that reads plausibly and is wrong."""
    df = read(name)
    expected = df["ActualSales"] - df["PlanSales"]
    assert (df["VarianceAbs"] - expected).abs().max() < 1.0


# --- plausibility -----------------------------------------------------------

def test_trading_days_are_positive():
    df = read("profit_by_store.csv")
    assert (df["TradingDays"] > 0).all()


def test_margins_stay_within_a_plausible_range():
    """Not a business judgement — an arithmetic guard. A grocery operating
    margin outside -100 %..+100 % means the model broke, not that trading
    was unusual."""
    df = read("pnl_by_storetype.csv")
    assert df["OperatingMarginPct"].between(-100, 100).all()
    assert df["CMRatioPct"].between(-100, 100).all()


def test_every_store_type_has_revenue():
    df = read("pnl_by_storetype.csv")
    assert (df["Revenue"] > 0).all()
    assert len(df) == 4      # Rossmann has store types a, b, c, d


# --- honesty ----------------------------------------------------------------

def test_assumptions_are_documented():
    """The README states that all cost and profit figures are modelling
    assumptions. This test makes that claim load-bearing: if the
    assumptions file ever disappears, the outputs become unlabelled
    invented figures and the build should stop."""
    df = read("assumptions.csv")
    assert len(df) >= 5
    assert {"Parameter", "Value", "Note"} <= set(df.columns)

    text = " ".join(df["Parameter"].astype(str)).lower()
    assert "variable cost ratio" in text
    assert "fixed cost" in text
    assert "growth target" in text

    # Every assumption must carry a note saying what it rests on.
    assert df["Note"].notna().all()
    assert (df["Note"].astype(str).str.len() > 10).all()

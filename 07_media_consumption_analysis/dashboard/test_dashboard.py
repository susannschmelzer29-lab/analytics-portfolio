"""
Checks the figures in data.js against the source CSVs, computed independently
of build_dashboard.py. Run from this folder:

    python build_dashboard.py && python -m pytest test_dashboard.py -q
"""

import json
from pathlib import Path

import pandas as pd
import pytest

HERE = Path(__file__).resolve().parent
DATA_DIR = HERE.parent / "data"
ABC, HP = "ABC News (AU)", "HuffPost (US)"


@pytest.fixture(scope="module")
def built() -> dict:
    text = (HERE / "data.js").read_text(encoding="utf-8")
    payload = text[text.index("{") : text.rindex("}") + 1]
    return json.loads(payload)


@pytest.fixture(scope="module")
def agg() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "01_tableau_aggregiert.csv", encoding="utf-8-sig")


def test_per_year_sums_to_aggregated_total(built, agg):
    series = built["overview"]["per_year"]["series"]
    assert sum(series[ABC]) + sum(series[HP]) == agg["artikel"].sum() == built["overview"]["aggregated_total"]


def test_aggregated_total_close_to_canonical(built):
    # METHODOLOGY.md fixes the canonical total; the aggregate may differ only marginally.
    o = built["overview"]
    assert abs(o["aggregated_total"] - o["canonical"]["total"]) / o["canonical"]["total"] < 0.0001


def test_abc_other_share_matches_category_summary(built):
    summary = pd.read_csv(DATA_DIR / "kategorie_summary.csv", encoding="utf-8-sig")
    expected = summary.loc[summary["category"] == "Sonstiges", "anteil_pct"].item()
    assert built["overview"]["abc_other_share"] == pytest.approx(expected, abs=0.1)


@pytest.mark.parametrize("source", [ABC, HP])
def test_distribution_shares_sum_to_100(built, source):
    rows = built["distribution"][source]
    assert sum(r["share_all"] for r in rows) == pytest.approx(100, abs=0.5)
    assert sum(r["share_classified"] for r in rows if r["category"] != "Other") == pytest.approx(100, abs=0.5)


def test_shared_comparison_matches_source_file(built):
    comp = pd.read_csv(DATA_DIR / "04_tableau_vergleich.csv", encoding="utf-8-sig")
    assert len(built["distribution"]["shared_comparison"]) * 2 == len(comp)
    crime = next(r for r in built["distribution"]["shared_comparison"] if r["category"] == "Crime")
    expected = comp[(comp["category"] == "Kriminalität") & (comp["source"] == ABC)]["anteil_prozent"].item()
    assert crime[ABC] == expected


@pytest.mark.parametrize("source", [ABC, HP])
def test_trend_shares_sum_to_100_each_year(built, source):
    shares = built["trend"][source]["shares"]
    for i, _ in enumerate(built["trend"][source]["years"]):
        assert sum(s[i] for s in shares.values()) == pytest.approx(100, abs=0.5)


@pytest.mark.parametrize("source", [ABC, HP])
def test_seasonality_index_averages_near_100(built, source):
    # Weighted by month volume each category's index averages exactly 100; the
    # plain mean over 12 months stays close to it. Values far off signal a bug.
    for row in built["seasonality"][source]["rows"]:
        assert 40 <= sum(row["index"]) / 12 <= 160


def test_keywords_are_top15_in_rank_order(built):
    kw = pd.read_csv(DATA_DIR / "02_tableau_keywords.csv", encoding="utf-8-sig")
    first = kw[(kw["source"] == HP) & (kw["category"] == "Politik")].sort_values("rang").iloc[0]
    built_first = built["keywords"][HP]["Politics"][0]
    assert built_first == {"keyword": first["keyword"], "count": int(first["haeufigkeit"])}
    assert all(len(v) == 15 for s in built["keywords"].values() for v in s.values())


def test_author_histogram_covers_all_considered_authors(built):
    a = built["authors"]
    assert sum(a["histogram"]["counts"]) == a["authors_considered"]


def test_author_specialists_recomputed(built):
    au = pd.read_csv(DATA_DIR / "03_tableau_autoren.csv", encoding="utf-8-sig").dropna(subset=["autor"])
    g = au.groupby("autor")["artikel"].agg(["sum", "max"])
    g = g[g["sum"] >= built["authors"]["min_assignments"]]
    share = 100 * (g["max"] / g["sum"] >= 0.8).mean()
    assert built["authors"]["share_specialists_80"] == pytest.approx(share, abs=0.1)


def test_headline_length_is_plausible(built):
    for source in (ABC, HP):
        for r in built["length"][source]:
            assert 3 <= r["headline_words"] <= 20
    assert all(r["description_words"] is None for r in built["length"][ABC])

"""Checks that the automated report computes consistent figures.

Run from the project folder:  python -m pytest tests -q
"""

import sys
from pathlib import Path

import pytest

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))
import generate_report as gr  # noqa: E402


@pytest.fixture(scope="module")
def kpis():
    return gr.compute_kpis(gr.load_data(PROJECT / "data" / "sales_clean.csv"))


def test_headline_figures(kpis):
    assert kpis["total_orders"] == 199
    assert kpis["total_revenue"] == pytest.approx(166_217.0)
    assert kpis["avg_order_value"] == pytest.approx(166_217.0 / 199)


def test_breakdowns_add_up_to_the_total(kpis):
    for key in ("by_product", "by_city", "monthly"):
        assert kpis[key].sum() == pytest.approx(kpis["total_revenue"])


def test_reporting_period_is_2024(kpis):
    assert kpis["date_min"].year == kpis["date_max"].year == 2024
    assert len(kpis["monthly"]) == 12


def test_report_is_written_with_all_sections(kpis, tmp_path, monkeypatch):
    monkeypatch.setattr(gr, "OUTPUT_DIR", tmp_path)
    gr.build_charts(kpis)
    gr.write_report(kpis)
    text = (tmp_path / "report.md").read_text(encoding="utf-8")
    for heading in ("## Key figures", "## Revenue by product", "## Revenue by city", "## Monthly revenue trend"):
        assert heading in text
    assert "166,217.00 EUR" in text
    assert {p.name for p in tmp_path.glob("*.png")} == {
        "revenue_by_product.png", "revenue_by_city.png", "monthly_revenue.png"
    }

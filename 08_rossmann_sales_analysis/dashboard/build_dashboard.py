"""
Builds data.js for the interactive Rossmann dashboard from the CSVs in ../output.
Run after run_pipeline.py / the notebook has (re-)generated ./output.

Usage:
    python build_dashboard.py
"""

import json
import re
from pathlib import Path

import pandas as pd

PROJECT_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_DIR / "output"
DASHBOARD_DIR = Path(__file__).resolve().parent

KPI_LABEL_RE = re.compile(r"^(.*?)\s*(?:\((.*?)\))?$")


def load(name: str) -> pd.DataFrame:
    return pd.read_csv(OUTPUT_DIR / name)


def build_kpis() -> list[dict]:
    df = load("kpi_management.csv")
    records = []
    for _, row in df.iterrows():
        label, unit = KPI_LABEL_RE.match(row["KPI"]).groups()
        records.append({"label": label.strip(), "unit": unit or "", "value": row["Value"]})
    return records


def build_daily_series() -> dict:
    df = load("q3_seasonality_daily.csv")
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.sort_values("Date")
    df["MA7"] = df["TotalSales"].rolling(7, min_periods=1).mean()
    overall_avg = df["TotalSales"].mean()
    df["Date"] = df["Date"].dt.strftime("%Y-%m-%d")
    return {
        "average": round(overall_avg, 2),
        "rows": df[["Date", "TotalSales", "TotalCustomers", "OpenStores", "Year", "YearMonth", "MA7"]]
        .round(2)
        .to_dict("records"),
    }


def build_month() -> list[dict]:
    return load("q3_seasonality_month.csv").round(2).to_dict("records")


def build_weekday() -> list[dict]:
    order = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    df = load("q3_seasonality_weekday.csv")
    df["Weekday"] = pd.Categorical(df["Weekday"], categories=order, ordered=True)
    return df.sort_values("Weekday").round(2).to_dict("records")


def build_promo() -> dict:
    overall = load("q5_promo.csv").round(2).to_dict("records")
    by_storetype = load("q5_promo_by_storetype.csv").sort_values("Uplift_%", ascending=False).round(2).to_dict(
        "records"
    )
    return {"overall": overall, "by_storetype": by_storetype}


def build_holidays() -> dict:
    naive = load("q4_holidays.csv").round(2).to_dict("records")
    corrected = load("q4_holidays_within_store.csv").round(2).to_dict("records")
    return {"naive": naive, "corrected": corrected}


def build_school_holidays() -> list[dict]:
    return load("q4_school_holidays.csv").round(2).to_dict("records")


def build_storetype() -> list[dict]:
    return load("q6_storetype.csv").round(2).to_dict("records")


def build_storetype_x_assortment() -> list[dict]:
    df = load("q6_storetype_x_assortment.csv")
    return df.astype(object).where(df.notnull(), None).to_dict("records")


def build_competition_distance() -> list[dict]:
    order = ["<500m", "500-1500m", "1.5-5km", ">5km"]
    df = load("q2_competition_distance.csv")
    df["CompetitionProximity"] = pd.Categorical(df["CompetitionProximity"], categories=order, ordered=True)
    return df.sort_values("CompetitionProximity").round(2).to_dict("records")


def build_store_ranking() -> list[dict]:
    df = load("q1_store_ranking.csv")

    def decile_flag(pct: float) -> str:
        if pct >= 90:
            return "Top 10%"
        if pct <= 10:
            return "Bottom 10%"
        return "Middle"

    df["DecileFlag"] = df["Percentile"].apply(decile_flag)
    df = df.sort_values("SalesPerDay", ascending=False)
    cols = [
        "Store",
        "SalesPerDay",
        "CustomersPerDay",
        "SalesPerCustomer",
        "StoreType",
        "Assortment",
        "CompetitionProximity",
        "Rank",
        "Percentile",
        "DecileFlag",
    ]
    return df[cols].round(2).to_dict("records")


def main() -> None:
    data = {
        "kpis": build_kpis(),
        "daily": build_daily_series(),
        "month": build_month(),
        "weekday": build_weekday(),
        "promo": build_promo(),
        "holidays": build_holidays(),
        "schoolHolidays": build_school_holidays(),
        "storetype": build_storetype(),
        "storetypeXAssortment": build_storetype_x_assortment(),
        "competitionDistance": build_competition_distance(),
        "storeRanking": build_store_ranking(),
    }
    out_path = DASHBOARD_DIR / "data.js"
    out_path.write_text("window.DASHBOARD_DATA = " + json.dumps(data, ensure_ascii=False) + ";\n", encoding="utf-8")
    print(f"Wrote {out_path} ({out_path.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    main()

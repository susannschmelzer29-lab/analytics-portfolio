"""
Builds data.js for the interactive Controlling dashboard from the CSVs in
../output. Run after the notebook (or run_pipeline.py) has (re-)generated
./output.

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

# Stores need a reasonably full trading history before a full-window variance %
# is meaningful; screen out sparse stores from the over-/under-performer lists.
MIN_TRADING_DAYS = 300


def load(name: str) -> pd.DataFrame:
    return pd.read_csv(OUTPUT_DIR / name)


def build_kpis() -> list[dict]:
    df = load("kpi_controlling.csv")
    records = []
    for _, row in df.iterrows():
        label, unit = KPI_LABEL_RE.match(row["KPI"]).groups()
        records.append({"label": label.strip(), "unit": unit or "", "value": row["Value"]})
    return records


def build_plan_actual() -> dict:
    monthly = load("plan_actual_monthly.csv").round(2)
    monthly = monthly.sort_values("YearMonth")
    by_type = load("variance_by_storetype.csv").round(2)
    total_plan = float(monthly["PlanSales"].sum())
    total_actual = float(monthly["ActualSales"].sum())
    return {
        "monthly": monthly[
            ["YearMonth", "Year", "PlanSales", "ActualSales", "VariancePct"]
        ].to_dict("records"),
        "byStoretype": by_type[
            ["StoreType", "Year", "PlanSales", "ActualSales", "VariancePct"]
        ].to_dict("records"),
        "totals": {
            "plan": round(total_plan, 2),
            "actual": round(total_actual, 2),
            "variancePct": round((total_actual - total_plan) / total_plan * 100, 2),
        },
    }


def build_variance_stores() -> dict:
    df = load("plan_actual_by_store.csv")
    agg = (
        df.groupby(["Store", "StoreType"])
        .agg(PlanSales=("PlanSales", "sum"),
             ActualSales=("ActualSales", "sum"),
             TradingDays=("TradingDays", "sum"))
        .reset_index()
    )
    agg = agg[agg["TradingDays"] >= MIN_TRADING_DAYS].copy()
    agg["VarianceAbs"] = agg["ActualSales"] - agg["PlanSales"]
    agg["VariancePct"] = agg["VarianceAbs"] / agg["PlanSales"] * 100
    agg = agg.round(2)
    cols = ["Store", "StoreType", "PlanSales", "ActualSales", "VarianceAbs", "VariancePct"]
    top = agg.sort_values("VariancePct", ascending=False).head(10)[cols]
    bottom = agg.sort_values("VariancePct", ascending=True).head(10)[cols]
    return {"top": top.to_dict("records"), "bottom": bottom.to_dict("records")}


def build_pnl() -> dict:
    monthly = load("pnl_monthly.csv").round(2).sort_values("YearMonth")
    by_type = load("pnl_by_storetype.csv").round(2)
    profit_store = load("profit_by_store.csv")
    revenue = float(monthly["Revenue"].sum())
    variable = float(monthly["VariableCost"].sum())
    fixed = float(monthly["FixedCost"].sum())
    cm = float(monthly["ContributionMargin"].sum())
    op = float(monthly["OperatingProfit"].sum())
    return {
        "monthly": monthly[
            ["YearMonth", "Revenue", "ContributionMargin", "OperatingProfit",
             "CMRatioPct", "OperatingMarginPct"]
        ].to_dict("records"),
        "byStoretype": by_type[
            ["StoreType", "Stores", "Revenue", "VariableCost", "FixedCost",
             "ContributionMargin", "OperatingProfit", "CMRatioPct", "OperatingMarginPct"]
        ].to_dict("records"),
        "totals": {
            "revenue": round(revenue, 2),
            "variableCost": round(variable, 2),
            "fixedCost": round(fixed, 2),
            "contributionMargin": round(cm, 2),
            "operatingProfit": round(op, 2),
            "cmRatioPct": round(cm / revenue * 100, 2),
            "operatingMarginPct": round(op / revenue * 100, 2),
            "lossStores": int((profit_store["OperatingProfit"] < 0).sum()),
            "totalStores": int(profit_store.shape[0]),
        },
    }


def build_assumptions() -> list[dict]:
    return load("assumptions.csv").to_dict("records")


def main() -> None:
    data = {
        "kpis": build_kpis(),
        "planActual": build_plan_actual(),
        "varianceStores": build_variance_stores(),
        "pnl": build_pnl(),
        "assumptions": build_assumptions(),
    }
    out_path = DASHBOARD_DIR / "data.js"
    out_path.write_text(
        "window.DASHBOARD_DATA = " + json.dumps(data, ensure_ascii=False) + ";\n",
        encoding="utf-8",
    )
    print(f"Wrote {out_path} ({out_path.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    main()

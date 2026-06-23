"""
06 - Automation & Reporting
============================
Reads the cleaned sales data (output of project 05) and automatically
generates a complete report: KPI charts as PNG files plus a Markdown
summary report. Run it once and the report rebuilds itself.

Usage:
    python generate_report.py

Outputs (created/overwritten in ./output/):
    - revenue_by_product.png
    - revenue_by_city.png
    - monthly_revenue.png
    - report.md
"""

from pathlib import Path
from datetime import datetime
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # non-interactive backend: works without a display, ideal for automation
import matplotlib.pyplot as plt

# --- Configuration -----------------------------------------------------------
DATA_FILE = Path("data/sales_clean.csv")
OUTPUT_DIR = Path("output")
ACCENT = "#2A7F8C"  # teal/petrol accent for all charts

# --- 1. Load data ------------------------------------------------------------
def load_data(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(
            f"Input file not found: {path}\n"
            f"Expected the cleaned sales data from project 05."
        )
    df = pd.read_csv(path, parse_dates=["date"])
    print(f"Loaded {len(df)} rows from {path}")
    return df

# --- 2. Compute KPIs ---------------------------------------------------------
def compute_kpis(df: pd.DataFrame) -> dict:
    return {
        "total_revenue": df["revenue"].sum(),
        "total_orders": len(df),
        "avg_order_value": df["revenue"].mean(),
        "date_min": df["date"].min(),
        "date_max": df["date"].max(),
        "by_product": df.groupby("product")["revenue"].sum().sort_values(ascending=False).round(2),
        "by_city": df.groupby("city")["revenue"].sum().sort_values(ascending=False).round(2),
        "monthly": df.set_index("date").resample("MS")["revenue"].sum().round(2),
    }

# --- 3. Build charts ---------------------------------------------------------
def save_bar(series, title, ylabel, filename, rotate=0):
    fig, ax = plt.subplots(figsize=(7, 4))
    series.plot(kind="bar", ax=ax, color=ACCENT)
    ax.set_title(title, fontsize=13, fontweight="bold")
    ax.set_ylabel(ylabel)
    ax.set_xlabel("")
    plt.xticks(rotation=rotate, ha="center")
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / filename, dpi=120)
    plt.close(fig)
    print(f"  wrote {filename}")

def save_line(series, title, ylabel, filename):
    fig, ax = plt.subplots(figsize=(8, 4))
    series.plot(kind="line", ax=ax, color=ACCENT, marker="o")
    ax.set_title(title, fontsize=13, fontweight="bold")
    ax.set_ylabel(ylabel)
    ax.set_xlabel("")
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / filename, dpi=120)
    plt.close(fig)
    print(f"  wrote {filename}")

def build_charts(kpis: dict):
    print("Generating charts:")
    save_bar(kpis["by_product"], "Revenue by Product", "Revenue (EUR)", "revenue_by_product.png")
    save_bar(kpis["by_city"], "Revenue by City", "Revenue (EUR)", "revenue_by_city.png")
    save_line(kpis["monthly"], "Monthly Revenue", "Revenue (EUR)", "monthly_revenue.png")

# --- 4. Write the Markdown report -------------------------------------------
def write_report(kpis: dict):
    generated = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = []
    lines.append("# Sales Report")
    lines.append("")
    lines.append(f"*Automatically generated on {generated}*")
    lines.append("")
    lines.append(
        f"Reporting period: **{kpis['date_min']:%Y-%m-%d}** to "
        f"**{kpis['date_max']:%Y-%m-%d}**"
    )
    lines.append("")
    lines.append("## Key figures")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---|")
    lines.append(f"| Total revenue | {kpis['total_revenue']:,.2f} EUR |")
    lines.append(f"| Total orders | {kpis['total_orders']} |")
    lines.append(f"| Average order value | {kpis['avg_order_value']:,.2f} EUR |")
    lines.append("")
    lines.append("## Revenue by product")
    lines.append("")
    lines.append("![Revenue by product](output/revenue_by_product.png)")
    lines.append("")
    lines.append("| Product | Revenue (EUR) |")
    lines.append("|---|---|")
    for name, val in kpis["by_product"].items():
        lines.append(f"| {name} | {val:,.2f} |")
    lines.append("")
    lines.append("## Revenue by city")
    lines.append("")
    lines.append("![Revenue by city](output/revenue_by_city.png)")
    lines.append("")
    lines.append("| City | Revenue (EUR) |")
    lines.append("|---|---|")
    for name, val in kpis["by_city"].items():
        lines.append(f"| {name} | {val:,.2f} |")
    lines.append("")
    lines.append("## Monthly revenue trend")
    lines.append("")
    lines.append("![Monthly revenue](output/monthly_revenue.png)")
    lines.append("")

    report_path = OUTPUT_DIR / "report.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"  wrote report.md")

# --- Main --------------------------------------------------------------------
def main():
    OUTPUT_DIR.mkdir(exist_ok=True)
    df = load_data(DATA_FILE)
    kpis = compute_kpis(df)
    build_charts(kpis)
    write_report(kpis)
    print(f"\nReport complete. Open {OUTPUT_DIR / 'report.md'}")

if __name__ == "__main__":
    main()

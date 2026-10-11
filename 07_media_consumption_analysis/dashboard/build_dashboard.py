"""
Builds data.js for the interactive media-consumption dashboard from the
pre-aggregated CSVs in ../data (the same inputs as the Tableau workbook).

Usage:
    python build_dashboard.py

Every figure the dashboard shows is computed here from the CSVs, so the
dashboard and the data cannot drift apart. Run tests_dashboard.py afterwards
to check the numbers against the source files.
"""

import json
from pathlib import Path

import pandas as pd

PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / "data"
DASHBOARD_DIR = Path(__file__).resolve().parent

# Canonical totals from METHODOLOGY.md (section 1). The aggregated CSV differs
# from these by 21 articles in total (< 0.002 %); the dashboard shows the
# canonical totals in the KPI tiles and states the difference on the method page.
CANONICAL = {"total": 1_453_690, "abc": 1_244_182, "huffpost": 209_508}

# Category labels in the data are German (canonical vocabulary, see
# 00_kategorie_mapping.csv). The dashboard is English like the README.
CATEGORY_EN = {
    "Gesellschaft": "Society",
    "Gesundheit": "Health",
    "Kriminalität": "Crime",
    "Politik": "Politics",
    "Sonstiges": "Other",
    "Sport": "Sports",
    "Umwelt": "Environment",
    "Welt": "World",
    "Wirtschaft": "Business",
    "Entertainment": "Entertainment",
    "Essen": "Food",
    "Familie": "Family",
    "Kunst": "Arts",
    "Reisen": "Travel",
    "Style & Beauty": "Style & Beauty",
    "Wohnen": "Home & Living",
    "Bildung": "Education",
    "Religion": "Religion",
    "US News": "US News",
}

SOURCES = ["ABC News (AU)", "HuffPost (US)"]
MIN_AUTHOR_ASSIGNMENTS = 100  # authors below this are too small to judge specialisation


def load(name: str) -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / name, encoding="utf-8-sig")
    if "category" in df.columns:
        unknown = set(df["category"]) - set(CATEGORY_EN)
        if unknown:
            raise ValueError(f"{name}: categories without English label: {sorted(unknown)}")
        df["category"] = df["category"].map(CATEGORY_EN)
    return df


def build_overview(agg: pd.DataFrame) -> dict:
    per_year = (
        agg.groupby(["source", "year"])["artikel"].sum().unstack("source").fillna(0).astype(int)
    )
    abc = agg[agg["source"] == SOURCES[0]]
    abc_other = int(abc.loc[abc["category"] == "Other", "artikel"].sum())
    abc_total = int(abc["artikel"].sum())
    return {
        "canonical": CANONICAL,
        "aggregated_total": int(agg["artikel"].sum()),
        "aggregated_by_source": {s: int(agg.loc[agg["source"] == s, "artikel"].sum()) for s in SOURCES},
        "year_min": int(agg["year"].min()),
        "year_max": int(agg["year"].max()),
        "abc_other_share": round(100 * abc_other / abc_total, 1),
        "per_year": {
            "years": per_year.index.tolist(),
            "series": {s: per_year[s].tolist() for s in SOURCES},
        },
    }


def build_distribution(agg: pd.DataFrame) -> dict:
    out = {}
    for source in SOURCES:
        sub = agg[agg["source"] == source].groupby("category")["artikel"].sum()
        total = sub.sum()
        classified = sub.drop("Other", errors="ignore")
        rows = [
            {
                "category": cat,
                "articles": int(n),
                "share_all": round(100 * n / total, 1),
                "share_classified": round(100 * n / classified.sum(), 1) if cat != "Other" else None,
            }
            for cat, n in sub.sort_values(ascending=False).items()
        ]
        out[source] = rows
    comparison = load("04_tableau_vergleich.csv")
    comp = comparison.pivot(index="category", columns="source", values="anteil_prozent").reset_index()
    out["shared_comparison"] = comp.rename(columns=str).to_dict("records")
    return out


def build_trend(agg: pd.DataFrame) -> dict:
    out = {}
    for source in SOURCES:
        sub = agg[agg["source"] == source]
        counts = sub.groupby(["year", "category"])["artikel"].sum().unstack("category").fillna(0)
        shares = counts.div(counts.sum(axis=1), axis=0).mul(100).round(2)
        out[source] = {
            "years": counts.index.tolist(),
            "counts": {c: counts[c].astype(int).tolist() for c in counts.columns},
            "shares": {c: shares[c].tolist() for c in shares.columns},
        }
    return out


def build_seasonality(agg: pd.DataFrame) -> dict:
    """Month index per category: share of a category's articles that fall in a
    month, divided by that month's share of all articles of the source.
    100 = average; >100 = the category is over-represented in that month.
    Normalising by the source's monthly volume removes the effect of months
    with generally more or fewer articles."""
    out = {}
    for source in SOURCES:
        sub = agg[agg["source"] == source]
        by = sub.groupby(["category", "month"])["artikel"].sum().unstack("month").fillna(0)
        month_total = by.sum(axis=0)
        month_share = month_total / month_total.sum()
        cat_share = by.div(by.sum(axis=1), axis=0)
        index = cat_share.div(month_share, axis=1).mul(100).round(0)
        order = by.sum(axis=1).sort_values(ascending=False).index
        out[source] = {
            "months": [int(m) for m in index.columns],
            "rows": [
                {"category": c, "articles": int(by.loc[c].sum()), "index": index.loc[c].astype(int).tolist()}
                for c in order
            ],
        }
    return out


def build_keywords() -> dict:
    kw = load("02_tableau_keywords.csv").sort_values(["source", "category", "rang"])
    out = {}
    for (source, cat), grp in kw.groupby(["source", "category"]):
        out.setdefault(source, {})[cat] = [
            {"keyword": r.keyword, "count": int(r.haeufigkeit)} for r in grp.itertuples()
        ]
    return out


def build_authors() -> dict:
    au = load("03_tableau_autoren.csv")
    au = au[au["autor"].notna() & (au["autor"].str.strip() != "")]
    top_per_cat = {
        cat: [
            {"author": r.autor, "articles": int(r.artikel)}
            for r in grp.sort_values("artikel", ascending=False).head(10).itertuples()
        ]
        for cat, grp in au.groupby("category")
    }
    per_author = au.groupby("autor").agg(total=("artikel", "sum"), top=("artikel", "max"))
    big = per_author[per_author["total"] >= MIN_AUTHOR_ASSIGNMENTS].copy()
    big["share_top"] = 100 * big["top"] / big["total"]
    bins = [0, 50, 60, 70, 80, 90, 100.0001]
    labels = ["<50 %", "50–60 %", "60–70 %", "70–80 %", "80–90 %", "90–100 %"]
    hist = pd.cut(big["share_top"], bins=bins, labels=labels, right=False).value_counts().reindex(labels)
    return {
        "assignments_total": int(au["artikel"].sum()),
        "authors_total": int(au["autor"].nunique()),
        "min_assignments": MIN_AUTHOR_ASSIGNMENTS,
        "authors_considered": int(len(big)),
        "share_specialists_80": round(100 * (big["share_top"] >= 80).mean(), 1),
        "median_share_top": round(float(big["share_top"].median()), 1),
        "histogram": {"labels": labels, "counts": hist.fillna(0).astype(int).tolist()},
        "top_per_category": top_per_cat,
    }


def build_length(agg: pd.DataFrame) -> dict:
    """Headline length: article-weighted mean of the monthly averages (exact
    mean). Description length (HuffPost only): article-weighted mean of the
    monthly medians - an approximation, labelled as such in the dashboard."""
    out = {}
    for source in SOURCES:
        sub = agg[agg["source"] == source].copy()
        sub["w_head"] = sub["avg_headline_woerter"] * sub["artikel"]
        has_desc = sub["med_beschreibung_woerter"].notna()
        sub["w_desc"] = sub["med_beschreibung_woerter"].fillna(0) * sub["artikel"]
        sub["n_desc"] = sub["artikel"].where(has_desc, 0)
        g = sub.groupby("category").agg(
            articles=("artikel", "sum"), w_head=("w_head", "sum"), w_desc=("w_desc", "sum"), n_desc=("n_desc", "sum")
        )
        rows = []
        for cat, r in g.sort_values("articles", ascending=False).iterrows():
            rows.append(
                {
                    "category": cat,
                    "articles": int(r["articles"]),
                    "headline_words": round(r["w_head"] / r["articles"], 1),
                    "description_words": round(r["w_desc"] / r["n_desc"], 1) if r["n_desc"] > 0 else None,
                }
            )
        out[source] = rows
    return out


def main() -> None:
    agg = load("01_tableau_aggregiert.csv")
    data = {
        "overview": build_overview(agg),
        "distribution": build_distribution(agg),
        "trend": build_trend(agg),
        "seasonality": build_seasonality(agg),
        "keywords": build_keywords(),
        "authors": build_authors(),
        "length": build_length(agg),
    }
    target = DASHBOARD_DIR / "data.js"
    target.write_text(
        "// Generated by build_dashboard.py - do not edit by hand.\n"
        "window.DASHBOARD_DATA = " + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + ";\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"Wrote {target} ({target.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()

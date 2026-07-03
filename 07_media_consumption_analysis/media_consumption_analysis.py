"""
Media Consumption Analysis — Project Summary & Key Findings
==============================================================
Project: 07_media_consumption_analysis
Sources: ABC News (AU) and HuffPost (US)

WHAT THIS SCRIPT DOES
----------------------
This script does NOT touch the raw data (1.45 million rows). Instead it
reads the seven small, already-aggregated CSV files inside data/ — the
output of the data pipeline (01_media_pipeline_1.ipynb or the fast
version) — and turns them into a clear, readable summary of the project's
most important results.

Because the input files are small (a few thousand rows at most), there is
no performance problem here: the code below is written to be easy to
read and easy to follow, one step at a time.

INPUT FILES (all expected in the data/ folder)
------------------------------------------------
- 00_kategorie_mapping.csv   : how HuffPost's original labels were mapped
- 01_tableau_aggregiert.csv  : article counts + word counts, by month
- 02_tableau_keywords.csv    : top keywords per source and category
- 03_tableau_autoren.csv     : authors, grouped by category (HuffPost only)
- 04_tableau_vergleich.csv   : source comparison, long format
- VS_quellenvergleich.csv    : source comparison, wide format (for Tableau)
- kategorie_summary.csv      : ABC News category distribution

OUTPUT
------
Everything is printed to the console, organised into clearly labelled
sections. Nothing is written back to disk.
"""

import os
from pathlib import Path

import pandas as pd

pd.set_option("display.max_columns", None)
pd.set_option("display.width", 120)


# ---------------------------------------------------------------------------
# Step 1: Setup — where do we find the data?
# ---------------------------------------------------------------------------

# This script is expected to live directly inside the project folder
# (07_media_consumption_analysis/), next to data/, Rohdaten/, etc. — the
# same layout as the rest of the analytics-portfolio repo. Using the
# script's own location (instead of a hardcoded path) means it works
# no matter where it's launched from, and works for anyone else who
# clones the repo too.
PROJECT_DIR = Path(__file__).resolve().parent
os.chdir(PROJECT_DIR)
DATA_DIR = PROJECT_DIR / "data"

print("=" * 70)
print("MEDIA CONSUMPTION ANALYSIS — PROJECT SUMMARY")
print("=" * 70)
print(f"Reading files from: {DATA_DIR.resolve()}\n")


def load_csv(filename: str) -> pd.DataFrame:
    """Load one CSV file from the data folder and stop with a clear error
    message if it is missing, instead of failing later with a confusing
    traceback."""
    path = DATA_DIR / filename
    if not path.exists():
        raise FileNotFoundError(
            f"Could not find '{filename}' in {DATA_DIR.resolve()}.\n"
            f"Make sure the data pipeline has been run first."
        )
    return pd.read_csv(path)


# Load all seven files up front, so any missing-file problem shows up
# immediately instead of halfway through the script.
mapping = load_csv("00_kategorie_mapping.csv")
aggregated = load_csv("01_tableau_aggregiert.csv")
keywords = load_csv("02_tableau_keywords.csv")
authors = load_csv("03_tableau_autoren.csv")
comparison_long = load_csv("04_tableau_vergleich.csv")
comparison_wide = load_csv("VS_quellenvergleich.csv")
abc_category_summary = load_csv("kategorie_summary.csv")

print("All 7 files loaded successfully.\n")


# ---------------------------------------------------------------------------
# Step 1b: Validation — do these numbers match the rest of the portfolio?
# ---------------------------------------------------------------------------
# This project's README, METHODOLOGY.md, and the Tableau dashboard all
# quote the same canonical figures. If this summary script computes
# different numbers, that's a signal that data/ is out of date (e.g. the
# pipeline was run again with different logic) and everything downstream
# — README, dashboard, this summary — would be telling a different story.
# So we check against those documented figures here, every time.
#
# IMPORTANT: every single check below is recorded in validation_checks.
# The final "all figures match" summary at the end of the script is
# derived directly from this list, so a mismatch anywhere can never be
# silently dropped from the overall verdict.

validation_checks = []  # list of (label, status) tuples, filled in as we go


def check_against_documented(label: str, documented: float, computed: float, tolerance_pct: float = 0.5) -> str:
    """Compare one computed number to its documented counterpart, print the
    result, record it in validation_checks, and return the status string."""
    if documented == 0:
        status = "SKIPPED (no documented value)"
    else:
        diff_pct = abs(computed - documented) / documented * 100
        status = "OK" if diff_pct <= tolerance_pct else "MISMATCH"
    validation_checks.append((label, status))
    print(
        f"  {label:28s}: documented {documented:>12,.1f}  |  "
        f"computed {computed:>12,.1f}  |  {status}"
    )
    return status


print("-" * 70)
print("1. OVERVIEW — HOW MUCH DATA")
print("-" * 70)

total_articles_by_source = aggregated.groupby("source")["artikel"].sum()

for source, count in total_articles_by_source.items():
    print(f"  {source:20s}: {count:>12,.0f} articles")

total_articles = total_articles_by_source.sum()
print(f"  {'TOTAL':20s}: {total_articles:>12,.0f} articles\n")

number_of_categories = aggregated["category"].nunique()
print(f"Number of distinct categories used: {number_of_categories}\n")

print("-" * 70)
print("VALIDATION — DOES THIS MATCH THE DOCUMENTED PORTFOLIO NUMBERS?")
print("-" * 70)

# These are the canonical values documented in METHODOLOGY.md and used
# throughout the README, the dashboard, and the presentations. Update
# this dictionary if the canonical numbers in METHODOLOGY.md ever change.
check_against_documented("Combined total articles", 1_453_690, total_articles)
check_against_documented(
    "ABC News (AU) articles", 1_244_182, total_articles_by_source.get("ABC News (AU)", 0)
)
check_against_documented(
    "HuffPost (US) articles", 209_508, total_articles_by_source.get("HuffPost (US)", 0)
)
print()


# ---------------------------------------------------------------------------
# Step 3: What do the two outlets write about most?
# ---------------------------------------------------------------------------

print("-" * 70)
print("2. CATEGORY DISTRIBUTION — WHAT EACH OUTLET WRITES ABOUT")
print("-" * 70)

articles_by_source_and_category = (
    aggregated.groupby(["source", "category"])["artikel"]
    .sum()
    .reset_index()
)

for source in articles_by_source_and_category["source"].unique():
    print(f"\nTop 5 categories for {source}:")
    subset = articles_by_source_and_category[
        articles_by_source_and_category["source"] == source
    ]
    subset = subset.sort_values("artikel", ascending=False)
    top_5 = subset.head(5)
    for _, row in top_5.iterrows():
        share = row["artikel"] / total_articles_by_source[source] * 100
        print(f"  {row['category']:20s}: {row['artikel']:>10,.0f} articles ({share:5.1f}%)")

# ABC News has a large "Sonstiges" (Other) bucket because headlines are
# classified by keyword matching, not by a native category field.
other_row = abc_category_summary[abc_category_summary["category"] == "Sonstiges"]
if not other_row.empty:
    other_share = other_row["anteil_pct"].iloc[0]
    print(
        f"\nNote: for ABC News, {other_share}% of headlines fall into "
        f"'Sonstiges' (Other) because they could not be matched to a "
        f"specific keyword category. This is a known limitation, not a "
        f"data quality problem — see METHODOLOGY.md."
    )
    # Updated 2026-07: the original keyword rules that produced 60.0% were
    # lost; the reconstructed pipeline (01_media_pipeline_1.ipynb, section 3a)
    # reproducibly yields 67.7%, and METHODOLOGY.md was updated to match.
    # See the "Versionsgeschichte" note in METHODOLOGY.md section 2a.
    check_against_documented("ABC 'Sonstiges' share (%)", 67.7, other_share)


# ---------------------------------------------------------------------------
# Step 4: Are headlines from one outlet longer than the other?
# ---------------------------------------------------------------------------

print("\n" + "-" * 70)
print("3. HEADLINE LENGTH — ABC NEWS VS. HUFFPOST")
print("-" * 70)

avg_words_by_source = (
    aggregated.groupby("source")["avg_headline_woerter"]
    .mean()
    .round(2)
)

for source, avg_words in avg_words_by_source.items():
    print(f"  {source:20s}: {avg_words:.2f} words per headline on average")

longer_source = avg_words_by_source.idxmax()
shorter_source = avg_words_by_source.idxmin()
difference = avg_words_by_source.max() - avg_words_by_source.min()
print(
    f"\n{longer_source} headlines are on average {difference:.2f} words "
    f"longer than {shorter_source} headlines."
)


# ---------------------------------------------------------------------------
# Step 5: What are the most common words per category?
# ---------------------------------------------------------------------------

print("\n" + "-" * 70)
print("4. TOP KEYWORDS — MOST FREQUENT WORDS PER CATEGORY")
print("-" * 70)

# To keep the output readable, we only show the single most popular
# category per source (the one with the most articles), and its top 5
# keywords.
top_category_by_source = (
    articles_by_source_and_category
    .sort_values("artikel", ascending=False)
    .groupby("source")
    .first()
)

for source, row in top_category_by_source.iterrows():
    category = row["category"]
    print(f"\nTop 5 keywords for {source}, category '{category}':")
    subset = keywords[
        (keywords["source"] == source) & (keywords["category"] == category)
    ]
    subset = subset.sort_values("rang").head(5)
    for _, kw_row in subset.iterrows():
        print(f"  {kw_row['rang']}. {kw_row['keyword']:15s} ({kw_row['haeufigkeit']:,} times)")


# ---------------------------------------------------------------------------
# Step 6: Do HuffPost journalists specialise in one topic ("beat")?
# ---------------------------------------------------------------------------

print("\n" + "-" * 70)
print("5. AUTHOR SPECIALIZATION ('BEAT') — HUFFPOST ONLY")
print("-" * 70)
print(
    "Note: author names are only reliably available for HuffPost. ABC News\n"
    "does not provide clean author data, so this section covers HuffPost only.\n"
)

# The raw author field sometimes contains stray line breaks or repeated
# whitespace (e.g. "Contributor\nAuthor" instead of "Contributor Author").
# Collapse those before grouping, otherwise the same person can be split
# into two different-looking "authors" and the printed name breaks the
# console layout.
authors = authors.copy()
authors["autor"] = authors["autor"].astype(str).str.replace(r"\s+", " ", regex=True).str.strip()
authors = authors.groupby(["autor", "category"], as_index=False)["artikel"].sum()


def looks_like_a_real_author_name(name: str) -> bool:
    """Heuristic filter for the HuffPost authors field, which is known to
    contain bio/role text instead of a name in some rows (e.g. a comma-split
    artifact like "ContributorEntertainment journalist and Walt Disney
    Company expert"). Real bylines are short (1-4 words, each capitalized,
    letters/hyphens/apostrophes/periods only). Anything longer, or any word
    with an extra capital letter in the middle (a tell-tale sign of two
    words glued together without a space, e.g. "ContributorColumnist"), is
    treated as not a real name and excluded from the author-level analysis."""
    name = name.strip()
    if not name or len(name) > 30:
        return False
    words = name.split()
    if not (1 <= len(words) <= 4):
        return False
    for word in words:
        if not all(ch.isalpha() or ch in "-'." for ch in word):
            return False
        if sum(1 for ch in word[1:] if ch.isupper()) > 0:
            return False
    return True


is_plausible_name = authors["autor"].apply(looks_like_a_real_author_name)
excluded_count = (~is_plausible_name).sum()
if excluded_count:
    print(
        f"Excluded {excluded_count:,} author-category rows whose 'author' "
        f"value looks like bio/role text rather than a real name (a known "
        f"data-quality issue in the HuffPost authors field, e.g. "
        f"comma-split fragments like 'ContributorColumnist and Senior "
        f"Diplomatic Correspondent'). These are left out of the "
        f"specialization analysis below so they don't distort it.\n"
    )
authors = authors[is_plausible_name]

# For each author, find their total article count and how many of those
# articles fall into their single most common category.
articles_per_author = authors.groupby("autor")["artikel"].sum().rename("total_artikel")
top_category_per_author = (
    authors.sort_values("artikel", ascending=False)
    .groupby("autor")
    .first()[["category", "artikel"]]
    .rename(columns={"category": "top_category", "artikel": "artikel_in_top_category"})
)

author_specialization = top_category_per_author.join(articles_per_author)
author_specialization["specialization_pct"] = (
    author_specialization["artikel_in_top_category"]
    / author_specialization["total_artikel"]
    * 100
).round(1)

# Two different volume thresholds are used on purpose:
# - MIN_ARTICLES_FOR_AVERAGE: a light filter, just enough to drop one-off
#   flukes, used for the overall "average specialization" statistic.
# - MIN_ARTICLES_FOR_TOP_LIST: a much higher bar, used only for the "Top 5
#   most specialized" ranking. With a low volume threshold, any author with
#   e.g. 25 articles who happens to have written them all in one category
#   trivially scores 100% — that's small-sample noise, not a meaningful
#   "most specialized" result. Requiring a higher article count means the
#   ranking actually reflects established writers with a real, sustained
#   beat, which is the finding worth reporting.
MIN_ARTICLES_FOR_AVERAGE = 20
MIN_ARTICLES_FOR_TOP_LIST = 100

established_authors = author_specialization[author_specialization["total_artikel"] >= MIN_ARTICLES_FOR_AVERAGE]

print(f"Authors with at least {MIN_ARTICLES_FOR_AVERAGE} articles: {len(established_authors):,}")
avg_specialization = established_authors["specialization_pct"].mean().round(1)
print(f"Average share of an author's articles that fall into their single top category: {avg_specialization}%\n")

# NOTE: "most specialized" means highest specialization_pct — NOT the
# authors with the most articles. Sorting by volume instead would be
# misleading here: high-volume wire-service accounts like "Reuters" or
# "AP" often have LOW specialization (they syndicate across many topics),
# which is itself a documented finding of this project, not noise.
high_volume_authors = author_specialization[author_specialization["total_artikel"] >= MIN_ARTICLES_FOR_TOP_LIST]
print(
    f"Top 5 most specialized authors (min. {MIN_ARTICLES_FOR_TOP_LIST} articles, "
    f"ranked by specialization %; a higher volume bar than the average above, "
    f"to rule out small-sample flukes):"
)
most_specialized = high_volume_authors.sort_values("specialization_pct", ascending=False).head(5)
for author_name, row in most_specialized.iterrows():
    print(
        f"  {author_name:20s}: {row['total_artikel']:>6,.0f} articles, "
        f"{row['specialization_pct']:5.1f}% in '{row['top_category']}'"
    )

print("\nFor comparison, the highest-volume authors (who are not necessarily the most specialized):")
most_articles = high_volume_authors.sort_values("total_artikel", ascending=False).head(5)
for author_name, row in most_articles.iterrows():
    print(
        f"  {author_name:20s}: {row['total_artikel']:>6,.0f} articles, "
        f"{row['specialization_pct']:5.1f}% in '{row['top_category']}'"
    )

# Wire services (Reuters, AP, etc.) tend to have low specialization because
# they syndicate content across many topics, unlike staff writers who cover
# one beat. If any of the highest-volume authors have noticeably lower
# specialization than the average, flag it explicitly instead of letting
# it quietly contradict the beat-specialization finding.
low_specialization_high_volume = most_articles[
    most_articles["specialization_pct"] < avg_specialization - 20
]
if not low_specialization_high_volume.empty:
    names = ", ".join(low_specialization_high_volume.index)
    print(
        f"\nNote: {names} show much lower specialization than the "
        f"{avg_specialization}% average. This matches the project's earlier "
        f"finding that wire-service / agency accounts distribute their "
        f"output across topics, unlike topic-specialized staff writers — "
        f"see the author-heatmap analysis in METHODOLOGY.md / the README."
    )


# ---------------------------------------------------------------------------
# Step 7: Where do ABC News and HuffPost differ the most?
# ---------------------------------------------------------------------------

print("\n" + "-" * 70)
print("6. SOURCE COMPARISON — SHARED CATEGORIES ONLY")
print("-" * 70)
print(
    "This compares only the categories and time period both outlets have\n"
    "in common, with each source normalised to 100% (see METHODOLOGY.md).\n"
)

source_columns = [c for c in comparison_wide.columns if c != "scat"]
if len(source_columns) == 2:
    col_a, col_b = source_columns
    comparison_wide["difference"] = (comparison_wide[col_a] - comparison_wide[col_b]).abs()
    biggest_differences = comparison_wide.sort_values("difference", ascending=False).head(5)

    print("Biggest differences between the two sources, by category:")
    for _, row in biggest_differences.iterrows():
        print(
            f"  {row['scat']:20s}: {col_a} {row[col_a]:5.1f}%  vs.  "
            f"{col_b} {row[col_b]:5.1f}%  (diff: {row['difference']:.1f} pts)"
        )
else:
    print("Expected exactly two source columns in VS_quellenvergleich.csv, "
          f"found {len(source_columns)}: {source_columns}")


# ---------------------------------------------------------------------------
# Step 8: Key findings, in plain language
# ---------------------------------------------------------------------------

print("\n" + "=" * 70)
print("KEY FINDINGS SUMMARY")
print("=" * 70)

findings = [
    f"- The combined dataset covers {total_articles:,.0f} articles across "
    f"{number_of_categories} categories.",
    f"- {longer_source} writes headlines that are on average "
    f"{difference:.2f} words longer than {shorter_source}.",
    f"- HuffPost authors are strongly beat-specialized: on average, "
    f"{avg_specialization}% of an established author's articles fall "
    f"into a single category, suggesting the newsroom is organised by "
    f"topic rather than by generalist reporters.",
]

if other_row is not None and not other_row.empty:
    findings.append(
        f"- {other_share}% of ABC News headlines could not be matched to a "
        f"specific category and fall under 'Sonstiges' — a known limitation "
        f"of keyword-based classification, not a data quality issue."
    )

failed_checks = [label for label, status in validation_checks if status == "MISMATCH"]
all_match = len(failed_checks) == 0

if all_match:
    findings.append("- Validation against METHODOLOGY.md: all figures match.")
else:
    findings.append(
        "- Validation against METHODOLOGY.md: MISMATCH found in "
        + ", ".join(failed_checks)
        + " — see the VALIDATION sections above before publishing these numbers."
    )

for line in findings:
    print(line)

print("\nDone.")

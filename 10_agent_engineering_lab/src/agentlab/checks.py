"""The checking rules. Pure logic — no filesystem, no network, no model.

That is exactly why this module is testable: every rule is a function
that takes a DataFrame and returns findings. The agent only enters one
layer above (`pipeline.py`).

Governing principle: **these functions repair nothing.** They report.
What happens to a finding is a human decision.
"""

from __future__ import annotations

import pandas as pd

from .models import ColumnProfile, Finding, FileReport

# Thresholds in one place so they can be argued with, rather than
# scattered through if-statements.
MISSING_AMBER = 0.05
MISSING_RED = 0.30
CONSTANT_MAX_DISTINCT = 1


def _profile_column(column: pd.Series) -> ColumnProfile:
    populated = column.dropna()
    return ColumnProfile(
        name=str(column.name),
        dtype=str(column.dtype),
        missing_share=float(column.isna().mean()) if len(column) else 0.0,
        distinct_values=int(populated.nunique()),
        sample_values=tuple(str(v) for v in populated.unique()[:3]),
    )


def check_missing_values(df: pd.DataFrame) -> list[Finding]:
    """Missing values per column, graded by share."""
    findings: list[Finding] = []
    if df.empty:
        return findings
    for name in df.columns:
        share = float(df[name].isna().mean())
        if share >= MISSING_RED:
            findings.append(Finding(
                code="MISSING_RED",
                text=f"Column '{name}': {share:.0%} missing values",
                severity="red",
                column=name,
            ))
        elif share >= MISSING_AMBER:
            findings.append(Finding(
                code="MISSING_AMBER",
                text=f"Column '{name}': {share:.0%} missing values",
                severity="amber",
                column=name,
            ))
    return findings


def check_duplicates(df: pd.DataFrame, key: list[str]) -> list[Finding]:
    """Duplicates over the BUSINESS key, not over every column.

    Two rows differing only in a timestamp are the same row in business
    terms. Checking across all columns would miss that — the single most
    common mistake in duplicate detection.
    """
    missing_cols = [c for c in key if c not in df.columns]
    if missing_cols:
        return [Finding(
            code="KEY_MISSING",
            text=f"Key columns not present: {', '.join(missing_cols)}",
            severity="red",
        )]
    if not key or df.empty:
        return []
    count = int(df.duplicated(subset=key, keep="first").sum())
    if count:
        return [Finding(
            code="DUPLICATES",
            text=f"{count} duplicate row(s) on key {key}",
            severity="red",
        )]
    return []


def check_types(df: pd.DataFrame, expected: dict[str, str]) -> list[Finding]:
    """Compares expected base types with what pandas actually read.

    `expected` names base types ('number', 'text', 'date'), not concrete
    numpy dtypes — otherwise the check breaks on every pandas upgrade.
    """
    findings: list[Finding] = []
    for name, want in expected.items():
        if name not in df.columns:
            continue
        got = df[name].dtype
        if want == "number" and not pd.api.types.is_numeric_dtype(got):
            findings.append(Finding(
                code="TYPE_MISMATCH",
                text=f"Column '{name}': expected a number, read as {got}",
                severity="red",
                column=name,
            ))
        elif want == "date" and not pd.api.types.is_datetime64_any_dtype(got):
            findings.append(Finding(
                code="TYPE_MISMATCH",
                text=f"Column '{name}': expected a date, read as {got}",
                severity="red",
                column=name,
            ))
    return findings


def check_constant_columns(df: pd.DataFrame) -> list[Finding]:
    """A column with one value carries no information.

    Usually an export defect rather than a data defect — hence amber.
    """
    findings: list[Finding] = []
    if df.empty:
        return findings
    for name in df.columns:
        if int(df[name].dropna().nunique()) <= CONSTANT_MAX_DISTINCT and len(df) > 1:
            findings.append(Finding(
                code="CONSTANT",
                text=f"Column '{name}' holds a single value throughout",
                severity="amber",
                column=name,
            ))
    return findings


def check_file(
    df: pd.DataFrame,
    file: str,
    key: list[str] | None = None,
    expected_types: dict[str, str] | None = None,
) -> FileReport:
    """Runs every rule and assembles the report."""
    report = FileReport(
        file=file,
        rows=int(len(df)),
        columns=int(len(df.columns)),
        column_profiles=[_profile_column(df[c]) for c in df.columns],
    )

    if df.empty:
        report.findings.append(
            Finding(code="EMPTY", text="File contains no rows", severity="red")
        )
        return report

    report.findings.extend(check_missing_values(df))
    report.findings.extend(check_duplicates(df, key or []))
    report.findings.extend(check_types(df, expected_types or {}))
    report.findings.extend(check_constant_columns(df))
    return report

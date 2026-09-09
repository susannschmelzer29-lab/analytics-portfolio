"""Tests of the checking rules — one positive and one negative case each."""

import pandas as pd

from agentlab.checks import (
    check_constant_columns, check_duplicates, check_file,
    check_missing_values, check_types,
)
from agentlab.models import Finding, FileReport


def codes(findings) -> set[str]:
    return {f.code for f in findings}


# --- missing values ---------------------------------------------------------

def test_no_missing_values_yields_no_finding():
    assert check_missing_values(pd.DataFrame({"a": [1, 2, 3, 4]})) == []


def test_ten_percent_missing_is_amber():
    df = pd.DataFrame({"a": [1, 2, 3, 4, 5, 6, 7, 8, 9, None]})
    findings = check_missing_values(df)
    assert codes(findings) == {"MISSING_AMBER"}
    assert findings[0].severity == "amber"


def test_half_missing_is_red():
    assert codes(check_missing_values(pd.DataFrame({"a": [1, None, 3, None]}))) == {"MISSING_RED"}


def test_threshold_of_exactly_five_percent_is_already_amber():
    df = pd.DataFrame({"a": [1] * 19 + [None]})     # 1 of 20 = exactly 5%
    assert codes(check_missing_values(df)) == {"MISSING_AMBER"}


# --- duplicates -------------------------------------------------------------

def test_duplicate_on_business_key_is_found():
    df = pd.DataFrame({"id": [1, 2, 2], "ts": ["a", "b", "c"]})
    assert codes(check_duplicates(df, ["id"])) == {"DUPLICATES"}


def test_checking_all_columns_would_miss_it():
    """The actual point of the rule.

    Across all columns the rows differ (ts differs). In business terms
    they are the same row.
    """
    df = pd.DataFrame({"id": [1, 1], "ts": ["10:00", "10:01"]})
    assert df.duplicated().sum() == 0                       # naive check: nothing
    assert codes(check_duplicates(df, ["id"])) == {"DUPLICATES"}   # business: a hit


def test_missing_key_column_is_red():
    findings = check_duplicates(pd.DataFrame({"a": [1, 2]}), ["id"])
    assert codes(findings) == {"KEY_MISSING"}
    assert findings[0].severity == "red"


def test_without_a_key_no_duplicate_check_runs():
    assert check_duplicates(pd.DataFrame({"a": [1, 1]}), []) == []


# --- types ------------------------------------------------------------------

def test_text_in_a_number_column_is_detected():
    df = pd.DataFrame({"amount": ["10.5", "1.2O0"]})        # letter O
    assert codes(check_types(df, {"amount": "number"})) == {"TYPE_MISMATCH"}


def test_a_clean_number_column_is_unremarkable():
    assert check_types(pd.DataFrame({"amount": [10.5, 3.2]}), {"amount": "number"}) == []


def test_an_unknown_column_is_skipped():
    assert check_types(pd.DataFrame({"a": [1]}), {"nosuch": "number"}) == []


# --- constant columns -------------------------------------------------------

def test_constant_column_is_amber():
    findings = check_constant_columns(pd.DataFrame({"tenant": ["A", "A", "A"]}))
    assert codes(findings) == {"CONSTANT"}
    assert findings[0].severity == "amber"


def test_a_single_row_file_does_not_count_as_constant():
    assert check_constant_columns(pd.DataFrame({"a": ["A"]})) == []


# --- overall report and status ----------------------------------------------

def test_empty_file_is_red():
    report = check_file(pd.DataFrame(), file="empty.csv")
    assert report.codes == {"EMPTY"}
    assert report.status == "red"


def test_status_takes_the_worst_finding():
    report = FileReport(file="x", rows=1, columns=1)
    report.findings = [
        Finding("A", "harmless", "green"),
        Finding("B", "middling", "amber"),
        Finding("C", "serious", "red"),
    ]
    assert report.status == "red"


def test_no_findings_means_green():
    df = pd.DataFrame({"id": [1, 2, 3], "value": [1.0, 2.0, 3.0]})
    report = check_file(df, file="clean.csv", key=["id"], expected_types={"value": "number"})
    assert report.findings == []
    assert report.status == "green"


def test_report_serialises():
    """The pipeline writes JSON — the report has to survive that."""
    import json
    df = pd.DataFrame({"id": [1, 2], "value": [1.0, 2.0]})
    report = check_file(df, file="x.csv", key=["id"])
    assert '"status": "green"' in json.dumps(report.to_dict(), ensure_ascii=False)

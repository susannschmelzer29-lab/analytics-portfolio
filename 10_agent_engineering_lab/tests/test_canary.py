"""Tests of the canary — the guard over the guard."""

import pandas as pd
import pytest

from agentlab.canary import (
    EXPECTED_CODES, EXPECTED_TYPES, KEY,
    build_canary, verify_canary, write_canary,
)
from agentlab.checks import check_file
from agentlab.pipeline import CanaryError, run


def test_canary_is_fully_detected():
    """The central test of this project.

    If it fails, a checking rule is broken or was removed — and every
    report the pipeline produces is worthless.
    """
    passed, missing = verify_canary()
    assert passed, f"undetected defects: {sorted(missing)}"


@pytest.mark.parametrize("code", sorted(EXPECTED_CODES))
def test_each_planted_defect_is_found(code):
    """Broken out per code so a failure names the rule that dropped out,
    rather than just 'something is missing'."""
    report = check_file(build_canary(), file="canary.csv",
                        key=KEY, expected_types=EXPECTED_TYPES)
    assert code in report.codes


def test_canary_is_red():
    report = check_file(build_canary(), file="c.csv",
                        key=KEY, expected_types=EXPECTED_TYPES)
    assert report.status == "red"


def test_round_trip_through_csv_preserves_the_defects(tmp_path):
    """The real pipeline reads from disk, not from memory. A defect
    detected in memory is not yet proof."""
    path = write_canary(tmp_path / "canary.csv")
    report = check_file(pd.read_csv(path), file=path.name,
                        key=KEY, expected_types=EXPECTED_TYPES)
    assert EXPECTED_CODES <= report.codes


def test_pipeline_aborts_when_the_canary_fails(monkeypatch):
    """The real case: a rule drops out, the whole run must stop."""
    monkeypatch.setattr("agentlab.pipeline.verify_canary",
                        lambda: (False, {"DUPLICATES"}))
    with pytest.raises(CanaryError) as err:
        run([], key=["id"])
    assert "DUPLICATES" in str(err.value)
    assert "void" in str(err.value)

"""The canary: a file with defects planted on purpose.

Why this is the most important component in the project
--------------------------------------------------------
An unattended pipeline can write plausible and wrong reports for months.
"All files checked, no anomalies" is exactly the output you also get when
the check never ran at all.

The canary solves that. It runs in every pass. If the check does not find
all of its known defects, the ENTIRE run is void — not just this one file.

The pattern comes from mining and transfers to any unattended automation.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .checks import check_file

# The defects planted in the file. This set is the contract: if the check
# finds fewer, the check is broken.
EXPECTED_CODES: set[str] = {
    "MISSING_RED",     # column 'note' is 50% empty
    "MISSING_AMBER",   # column 'quantity' has one missing value (10%)
    "DUPLICATES",      # case_id 1003 appears twice
    "TYPE_MISMATCH",   # 'amount' contains "1.2O0" — letter O instead of zero
    "CONSTANT",        # 'tenant' is 'A' everywhere
}

KEY = ["case_id"]
EXPECTED_TYPES = {"amount": "number", "quantity": "number"}


def build_canary() -> pd.DataFrame:
    """Builds the dataset with the known defects.

    The defects are chosen because they genuinely occur in real exports —
    not as artificial constructs, but as a miniature of an ordinary week.
    """
    return pd.DataFrame(
        {
            # 1003 twice -> DUPLICATES
            "case_id": [1001, 1002, 1003, 1003, 1004, 1005, 1006, 1007, 1008, 1009],
            # 'A' throughout -> CONSTANT
            "tenant": ["A"] * 10,
            # "1.2O0": letter O instead of zero -> column stays text -> TYPE_MISMATCH
            "amount": ["10.50", "22.00", "1.2O0", "8.75", "13.00",
                       "9.99", "45.20", "3.10", "77.00", "5.05"],
            # one missing of ten -> 10% -> MISSING_AMBER
            "quantity": [1, 2, 3, 3, None, 5, 6, 7, 8, 9],
            # five of ten empty -> 50% -> MISSING_RED
            "note": ["ok", None, "checked", None, "ok", None, None, "ok", None, "ok"],
        }
    )


def write_canary(target: str | Path) -> Path:
    """Writes the file so the pipeline treats it like any other."""
    path = Path(target)
    path.parent.mkdir(parents=True, exist_ok=True)
    build_canary().to_csv(path, index=False)
    return path


def verify_canary() -> tuple[bool, set[str]]:
    """Runs the checks over the canary.

    Returns (passed, missing codes). Passed means ALL expected codes were
    found. Additional findings are fine — a stricter check is not a
    failure, a blinder one is.
    """
    report = check_file(
        build_canary(),
        file="canary.csv",
        key=KEY,
        expected_types=EXPECTED_TYPES,
    )
    missing = EXPECTED_CODES - report.codes
    return (not missing), missing

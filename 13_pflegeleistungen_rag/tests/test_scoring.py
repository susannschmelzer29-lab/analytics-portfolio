"""The calculator and the knowledge-base text must describe the same table."""

import re
from decimal import Decimal

import pytest

from pflege_rag import SOURCE_DIR
from pflege_rag.scoring import ANLAGE_2, calculate, pflegegrad_for, weighted_points

SOURCE = (SOURCE_DIR / "14_bewertungssystematik.md").read_text(encoding="utf-8")
ROW = re.compile(r"- (\d+)(?: bis (\d+))? Einzelpunkte?: Punktbereich (\d), ([\d,]+) gewichtete Punkte")


def table_from_source() -> dict[int, list[tuple[int, int, Decimal]]]:
    out = {}
    for block in re.split(r"^## Modul ", SOURCE, flags=re.MULTILINE)[1:]:
        module = int(block[0])
        rows = []
        for lo, hi, band, w in ROW.findall(block):
            assert int(band) == len(rows), f"module {module}: bands out of order"
            rows.append((int(lo), int(hi or lo), Decimal(w.replace(",", "."))))
        out[module] = rows
    return out


def test_code_table_equals_source_text():
    assert table_from_source() == ANLAGE_2


@pytest.mark.parametrize("module", ANLAGE_2)
def test_bands_are_contiguous_and_start_at_zero(module):
    rows = ANLAGE_2[module]
    assert rows[0][0] == 0
    for (_, hi, _), (lo, _, _) in zip(rows, rows[1:]):
        assert lo == hi + 1


def test_maximum_weighted_points_equal_module_weights():
    # § 15 Abs. 2: 10 / 15 / 40 / 20 / 15 percent; modules 2+3 share 15.
    top = {m: rows[-1][2] for m, rows in ANLAGE_2.items()}
    assert (top[1], top[2], top[3], top[4], top[5], top[6]) == (10, 15, 15, 40, 20, 15)
    assert top[1] + max(top[2], top[3]) + top[4] + top[5] + top[6] == 100


def test_worked_example_from_source():
    r = calculate({1: 6, 2: 8, 3: 2, 4: 20, 5: 2, 6: 5})
    assert r.total == Decimal("62.5") and r.pflegegrad == 3
    assert "= 62,5." in SOURCE and "Pflegegrad 3" in SOURCE
    assert r.explain() == "7,5 + 7,5 + 30 + 10 + 7,5 = 62,5 Gesamtpunkte → Pflegegrad 3"


def test_only_the_higher_of_modules_2_and_3_counts():
    low3 = calculate({1: 0, 2: 17, 3: 0, 4: 0, 5: 0, 6: 0})
    both = calculate({1: 0, 2: 17, 3: 65, 4: 0, 5: 0, 6: 0})
    assert low3.total == both.total == 15


@pytest.mark.parametrize(
    "total,grade",
    [("0", 0), ("12.49", 0), ("12.5", 1), ("26.99", 1), ("27", 2), ("47.5", 3), ("69.99", 4 - 1), ("70", 4), ("90", 5), ("100", 5)],
)
def test_thresholds(total, grade):
    assert pflegegrad_for(Decimal(total)) == grade


def test_thresholds_match_source_file_02():
    text = (SOURCE_DIR / "02_pflegegrade.md").read_text(encoding="utf-8")
    for lower, grade in [("12,5", 1), ("27", 2), ("47,5", 3), ("70", 4), ("90", 5)]:
        assert f"Pflegegrad {grade}: ab {lower} bis" in text


def test_maximum_is_pflegegrad_5_and_minimum_none():
    assert calculate({1: 15, 2: 33, 3: 65, 4: 54, 5: 15, 6: 18}).pflegegrad == 5
    assert calculate({m: 0 for m in range(1, 7)}).pflegegrad == 0


@pytest.mark.parametrize("bad", [{1: 16, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0}, {1: -1, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0}, {1: 0}])
def test_invalid_input_is_rejected(bad):
    with pytest.raises(ValueError):
        calculate(bad)


def test_unknown_module():
    with pytest.raises(ValueError):
        weighted_points(7, 0)

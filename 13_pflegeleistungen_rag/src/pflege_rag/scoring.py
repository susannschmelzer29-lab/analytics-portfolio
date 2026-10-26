"""Deterministic Pflegegrad calculator (§ 15 SGB XI with Anlage 2).

Arithmetic is not the language model's job. Asked "6 points in module 1,
20 in module 4 ... which Pflegegrad?", an LLM may add up wrongly and still
sound sure. Here the table from Anlage 2 is code, and the tests check that
this code and the knowledge-base text (data/sources/14_...) say the same.

Adults only: the special scale for children up to 18 months
(§ 15 Abs. 7) and the hardship rule (§ 15 Abs. 4) are out of scope.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

# module -> list of (min, max Einzelpunkte, gewichtete Punkte) for Punktbereich 0..4
ANLAGE_2: dict[int, list[tuple[int, int, Decimal]]] = {
    1: [(0, 1, Decimal("0")), (2, 3, Decimal("2.5")), (4, 5, Decimal("5")), (6, 9, Decimal("7.5")), (10, 15, Decimal("10"))],
    2: [(0, 1, Decimal("0")), (2, 5, Decimal("3.75")), (6, 10, Decimal("7.5")), (11, 16, Decimal("11.25")), (17, 33, Decimal("15"))],
    3: [(0, 0, Decimal("0")), (1, 2, Decimal("3.75")), (3, 4, Decimal("7.5")), (5, 6, Decimal("11.25")), (7, 65, Decimal("15"))],
    4: [(0, 2, Decimal("0")), (3, 7, Decimal("10")), (8, 18, Decimal("20")), (19, 36, Decimal("30")), (37, 54, Decimal("40"))],
    5: [(0, 0, Decimal("0")), (1, 1, Decimal("5")), (2, 3, Decimal("10")), (4, 5, Decimal("15")), (6, 15, Decimal("20"))],
    6: [(0, 0, Decimal("0")), (1, 3, Decimal("3.75")), (4, 6, Decimal("7.5")), (7, 11, Decimal("11.25")), (12, 18, Decimal("15"))],
}

# lower bound of total points -> Pflegegrad (§ 15 Abs. 3)
THRESHOLDS: list[tuple[Decimal, int]] = [
    (Decimal("90"), 5),
    (Decimal("70"), 4),
    (Decimal("47.5"), 3),
    (Decimal("27"), 2),
    (Decimal("12.5"), 1),
]


@dataclass(frozen=True)
class Result:
    weighted: dict[int, Decimal]  # per module, before the 2-vs-3 rule
    total: Decimal
    pflegegrad: int  # 0 = below Pflegegrad 1

    def explain(self) -> str:
        m23 = max(self.weighted[2], self.weighted[3])
        parts = [self.weighted[1], m23, self.weighted[4], self.weighted[5], self.weighted[6]]
        sum_txt = " + ".join(_fmt(p) for p in parts)
        grade = f"Pflegegrad {self.pflegegrad}" if self.pflegegrad else "kein Pflegegrad (unter 12,5 Punkten)"
        return f"{sum_txt} = {_fmt(self.total)} Gesamtpunkte → {grade}"


def _fmt(d: Decimal) -> str:
    s = format(d.normalize(), "f")
    return s.replace(".", ",")


def weighted_points(module: int, einzelpunkte: int) -> Decimal:
    if module not in ANLAGE_2:
        raise ValueError(f"module must be 1-6, got {module}")
    for lo, hi, w in ANLAGE_2[module]:
        if lo <= einzelpunkte <= hi:
            return w
    top = ANLAGE_2[module][-1][1]
    raise ValueError(f"module {module}: Einzelpunkte must be 0-{top}, got {einzelpunkte}")


def pflegegrad_for(total: Decimal) -> int:
    for lower, grade in THRESHOLDS:
        if total >= lower:
            return grade
    return 0


def calculate(einzelpunkte: dict[int, int]) -> Result:
    if set(einzelpunkte) != set(ANLAGE_2):
        raise ValueError("Einzelpunkte for all six modules (1-6) are required")
    weighted = {m: weighted_points(m, p) for m, p in einzelpunkte.items()}
    total = weighted[1] + max(weighted[2], weighted[3]) + weighted[4] + weighted[5] + weighted[6]
    return Result(weighted, total, pflegegrad_for(total))

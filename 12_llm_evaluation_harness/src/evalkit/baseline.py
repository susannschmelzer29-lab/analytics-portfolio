"""Comparing a run against a stored baseline.

The part people leave out
--------------------------
Most eval setups report a pass rate and stop. A pass rate on its own
answers nothing: is 84 % good? Better than last week? Within noise?

So this module compares against a committed baseline and — importantly —
refuses to call a small difference a regression. With 20 quality cases,
one case is five percentage points. Treating that as a regression trains
everyone to ignore the alert.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

from .models import RunResult


@dataclass
class Vergleich:
    """Result of comparing a run against the baseline."""

    neu_gescheitert: list[str]      # passed in baseline, fails now
    neu_bestanden: list[str]        # failed in baseline, passes now
    unbekannt: list[str]            # not in the baseline at all
    rate_alt: float
    rate_neu: float
    n_quality: int

    @property
    def rate_differenz(self) -> float:
        return self.rate_neu - self.rate_alt

    @property
    def aussagekraeftig(self) -> bool:
        """Is the rate difference larger than the noise floor?

        Noise floor: one case. With n quality cases, a single flip moves
        the rate by 1/n, so anything at or below that is not evidence of
        anything. Crude on purpose — a Wilson interval would be more
        correct and less likely to be understood by the person reading
        the CI log at 17:40 on a Friday.
        """
        if self.n_quality == 0:
            return False
        return abs(self.rate_differenz) > (1.0 / self.n_quality) + 1e-9

    @property
    def ist_regression(self) -> bool:
        """A regression is a case that used to pass and now does not.

        Named cases, not a moved average. A rate can fall while every
        individual case still behaves the same way — different cases, or
        a case added. Only a named flip is actionable.
        """
        return bool(self.neu_gescheitert)

    def bericht(self) -> str:
        zeilen = []
        if self.neu_gescheitert:
            zeilen.append("REGRESSIONS (passed before, fail now):")
            zeilen += [f"  - {c}" for c in self.neu_gescheitert]
        if self.neu_bestanden:
            zeilen.append("Fixed (failed before, pass now):")
            zeilen += [f"  - {c}" for c in self.neu_bestanden]
        if self.unbekannt:
            zeilen.append(f"New cases, not yet in the baseline: {', '.join(self.unbekannt)}")

        richtung = "+" if self.rate_differenz >= 0 else ""
        rausch = "" if self.aussagekraeftig else "  (within noise, n=%d)" % self.n_quality
        zeilen.append(
            f"Quality pass rate: {self.rate_alt:.1%} -> {self.rate_neu:.1%} "
            f"({richtung}{self.rate_differenz:.1%}){rausch}"
        )
        return "\n".join(zeilen)


def speichere_baseline(lauf: RunResult, pfad: str | Path) -> Path:
    p = Path(pfad)
    p.parent.mkdir(parents=True, exist_ok=True)
    inhalt = {
        "model_name": lauf.model_name,
        "created_at": lauf.started_at,
        "quality_pass_rate": round(lauf.quality_pass_rate, 4),
        "cases": {r.case_id: r.passed for r in lauf.results},
    }
    p.write_text(json.dumps(inhalt, indent=2, ensure_ascii=False), encoding="utf-8")
    return p


def vergleiche(lauf: RunResult, pfad: str | Path) -> Vergleich:
    p = Path(pfad)
    if not p.exists():
        raise FileNotFoundError(
            f"no baseline at {p}. Create one with: python scripts/run_eval.py --write-baseline"
        )
    alt = json.loads(p.read_text(encoding="utf-8"))
    alte_faelle: dict[str, bool] = alt.get("cases", {})

    neu_gescheitert, neu_bestanden, unbekannt = [], [], []
    for r in lauf.results:
        if r.case_id not in alte_faelle:
            unbekannt.append(r.case_id)
        elif alte_faelle[r.case_id] and not r.passed:
            neu_gescheitert.append(r.case_id)
        elif not alte_faelle[r.case_id] and r.passed:
            neu_bestanden.append(r.case_id)

    return Vergleich(
        neu_gescheitert=sorted(neu_gescheitert),
        neu_bestanden=sorted(neu_bestanden),
        unbekannt=sorted(unbekannt),
        rate_alt=float(alt.get("quality_pass_rate", 0.0)),
        rate_neu=lauf.quality_pass_rate,
        n_quality=len(lauf.quality),
    )

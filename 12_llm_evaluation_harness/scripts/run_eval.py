#!/usr/bin/env python3
"""Run the evaluation and decide whether it may ship.

  python scripts/run_eval.py                      # stub-good, compare to baseline
  python scripts/run_eval.py --model stub-bad     # see the harness catch things
  python scripts/run_eval.py --write-baseline     # record the current state

Exit codes -- the CI contract:
  0  fine
  1  a blocking case failed
  2  a named quality regression against the baseline
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from evalkit import load_cases, run                      # noqa: E402
from evalkit.baseline import speichere_baseline, vergleiche  # noqa: E402
from evalkit.report import als_markdown                  # noqa: E402
from evalkit.stubs import MODELLE                        # noqa: E402

WURZEL = Path(__file__).resolve().parents[1]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--model", default="stub-good", choices=sorted(MODELLE))
    p.add_argument("--cases", default=str(WURZEL / "cases"))
    p.add_argument("--baseline", default=str(WURZEL / "baselines" / "baseline.json"))
    p.add_argument("--report", default=str(WURZEL / "reports" / "latest.md"))
    p.add_argument("--write-baseline", action="store_true",
                   help="record this run as the new baseline instead of comparing")
    args = p.parse_args(argv)

    faelle = load_cases(args.cases)
    lauf = run(faelle, MODELLE[args.model], modell_name=args.model)

    if args.write_baseline:
        ziel = speichere_baseline(lauf, args.baseline)
        print(f"Baseline written: {ziel}")
        print(f"  {len(lauf.results)} cases, quality pass rate {lauf.quality_pass_rate:.1%}")
        return 0

    vgl = vergleiche(lauf, args.baseline)

    ziel = Path(args.report)
    ziel.parent.mkdir(parents=True, exist_ok=True)
    ziel.write_text(als_markdown(lauf, vgl), encoding="utf-8")

    print(f"Model: {args.model} · {len(lauf.results)} cases · report: {ziel}")
    print(vgl.bericht())

    if lauf.blocking_failures:
        print(f"\nBLOCKED: {len(lauf.blocking_failures)} blocking case(s) failed:")
        for r in lauf.blocking_failures:
            for g in r.failures:
                print(f"  {r.case_id}: {g.grader} — {g.reason}")
        return 1

    if vgl.ist_regression:
        print(f"\nREGRESSION: {', '.join(vgl.neu_gescheitert)}")
        return 2

    print("\nOK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Markdown report of a run.

Written for the person who has to decide whether to ship, so it leads
with the verdict and puts the evidence underneath.
"""

from __future__ import annotations

from .baseline import Vergleich
from .models import RunResult


def als_markdown(lauf: RunResult, vergleich: Vergleich | None = None) -> str:
    z: list[str] = []
    a = z.append

    verdikt = "PASS" if lauf.ok else "BLOCKED"
    a(f"# Evaluation report — {verdikt}")
    a("")
    a(f"Model: `{lauf.model_name}` · {lauf.started_at} · {len(lauf.results)} cases")
    a("")

    if lauf.blocking_failures:
        a(f"**{len(lauf.blocking_failures)} blocking failure(s).** "
          "These are not quality issues; the system must not ship in this state.")
    else:
        a("No blocking failures.")
    a("")

    a("| | Cases | Passed | Rate |")
    a("|---|---:|---:|---:|")
    bp = sum(1 for r in lauf.blocking if r.passed)
    qp = sum(1 for r in lauf.quality if r.passed)
    a(f"| Blocking | {len(lauf.blocking)} | {bp} | "
      f"{bp / len(lauf.blocking):.0%} |" if lauf.blocking else "| Blocking | 0 | 0 | – |")
    a(f"| Quality | {len(lauf.quality)} | {qp} | {lauf.quality_pass_rate:.0%} |")
    a("")

    if vergleich is not None:
        a("## Against baseline")
        a("")
        a("```")
        a(vergleich.bericht())
        a("```")
        a("")

    gescheitert = [r for r in lauf.results if not r.passed]
    if gescheitert:
        a("## Failures")
        a("")
        for r in gescheitert:
            marke = "BLOCKING" if r.severity == "blocking" else "quality"
            a(f"### `{r.case_id}` — {marke}")
            a("")
            for g in r.failures:
                a(f"* **{g.grader}**: {g.reason}")
            a("")
            gekuerzt = r.output if len(r.output) <= 300 else r.output[:300] + " …"
            a("> " + gekuerzt.replace("\n", "\n> "))
            a("")

    langsam = sorted(lauf.results, key=lambda r: r.latency_ms, reverse=True)[:3]
    if langsam and langsam[0].latency_ms > 0:
        a("## Slowest cases")
        a("")
        for r in langsam:
            a(f"* `{r.case_id}` — {r.latency_ms} ms")
        a("")

    return "\n".join(z)

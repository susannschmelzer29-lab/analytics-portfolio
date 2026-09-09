"""Orchestration: canary first, then the real files.

The model call sits behind a single swappable hook (`narrator`). Without
an API key the pipeline runs end to end and produces findings — only the
prose summary is missing.

That is deliberate: anyone cloning this repository should be able to run
`pytest` and `python -m agentlab.pipeline` without setting anything up.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

import pandas as pd

from .canary import verify_canary
from .checks import check_file
from .knowledge import KnowledgeSource, question_for
from .models import FileReport

# A narrator takes the reports and turns them into prose.
# Default: none. See `narrator` in the README.
Narrator = Callable[[list[FileReport]], str]


class CanaryError(RuntimeError):
    """The canary was not fully detected.

    This is not a data error but a checking error: the pipeline itself is
    broken. So the run aborts instead of producing results nobody can
    trust.
    """


@dataclass
class RunResult:
    reports: list[FileReport]
    summary: str | None = None

    @property
    def red(self) -> list[FileReport]:
        return [r for r in self.reports if r.status == "red"]

    def to_dict(self) -> dict:
        return {
            "files": len(self.reports),
            "red": len(self.red),
            "amber": len([r for r in self.reports if r.status == "amber"]),
            "green": len([r for r in self.reports if r.status == "green"]),
            "reports": [r.to_dict() for r in self.reports],
            "summary": self.summary,
        }


def _read(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


def _explain(report: FileReport, knowledge: KnowledgeSource) -> None:
    """Asks the knowledge source once per finding CODE, not per column.

    The deduplication is the point: five columns with missing values ask
    the same question. Without this line that would be five lookups
    returning the same answer five times.
    """
    asked: set[str] = set()
    for finding in report.findings:
        if finding.code in asked:
            continue
        asked.add(finding.code)
        # Deliberate trade-off: one lookup per code, using the FIRST
        # affected column as the example. Deduplicating per (code, column)
        # would ask the same question once per column again; asking without
        # a column produces a question so generic that retrieval returns
        # nothing -- which is how this was originally, and it was useless.
        report.explanations.append(
            knowledge.ask(
                question_for(finding.code, report.file, finding.column),
                context={"file": report.file, "code": finding.code,
                         "column": finding.column},
            )
        )


def run(
    files: Iterable[Path],
    key: list[str] | None = None,
    expected_types: dict[str, str] | None = None,
    narrator: Narrator | None = None,
    reader: Callable[[Path], pd.DataFrame] = _read,
    knowledge: KnowledgeSource | None = None,
) -> RunResult:
    """Runs one complete checking pass.

    `reader` is a parameter so tests need no filesystem — the same
    technique as `narrator` and `knowledge`: whatever reaches outside is
    handed in rather than hard-wired.
    """
    passed, missing = verify_canary()
    if not passed:
        raise CanaryError(
            "Canary not fully detected. Not found: "
            + ", ".join(sorted(missing))
            + " — run void, results discarded."
        )

    reports = [
        check_file(reader(path), file=path.name, key=key, expected_types=expected_types)
        for path in files
    ]

    # Explaining only pays where there is something to explain: green
    # files trigger no lookup.
    if knowledge is not None:
        for report in reports:
            if report.findings:
                _explain(report, knowledge)

    result = RunResult(reports=reports)
    if narrator is not None and reports:
        result.summary = narrator(reports)
    return result


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Data checks with canary protection")
    p.add_argument("--input", default="data/raw", help="folder holding CSV files")
    p.add_argument("--output", default="reports/run.json", help="target file for the report")
    p.add_argument("--key", default="", help="business key, comma separated")
    p.add_argument("--docs", default="", help="documentation folder for explanations")
    args = p.parse_args(argv)

    files = sorted(Path(args.input).glob("*.csv"))
    if not files:
        print(f"No CSV files in {args.input}", file=sys.stderr)
        return 1

    key = [k.strip() for k in args.key.split(",") if k.strip()]

    knowledge = None
    if args.docs:
        from .knowledge import DocsKnowledge
        knowledge = DocsKnowledge(args.docs)
        print(f"Knowledge: {knowledge.diagnose()}")

    try:
        result = run(files, key=key, knowledge=knowledge)
    except CanaryError as e:
        print(f"ABORTED: {e}", file=sys.stderr)
        return 2

    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result.to_dict(), indent=2, ensure_ascii=False),
                      encoding="utf-8")

    print(f"{len(result.reports)} file(s) checked, {len(result.red)} red -> {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

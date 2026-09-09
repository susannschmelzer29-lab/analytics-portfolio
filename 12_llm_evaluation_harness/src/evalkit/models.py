"""Data model of an evaluation run.

Deliberately plain dataclasses. An evaluation harness whose own data
model is complicated cannot be trusted to measure anything.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

Severity = Literal["blocking", "quality"]


@dataclass(frozen=True)
class Case:
    """One test case.

    `severity` is the field that makes this harness usable in CI:

    * ``blocking`` — a failure means the system is unsafe or plainly
      broken (fabricated a figure, followed an injected instruction).
      One failure fails the build.
    * ``quality`` — a failure means the answer got worse. Judged as a
      rate across many cases, never case by case, because a single
      quality case carries almost no information.

    Treating both kinds the same is the most common mistake in LLM
    evaluation: either the build breaks on noise, or a genuine safety
    failure disappears into an average.
    """

    id: str
    prompt: str
    graders: tuple[dict[str, Any], ...]
    severity: Severity = "quality"
    context: str = ""
    tags: tuple[str, ...] = ()
    note: str = ""


@dataclass(frozen=True)
class GraderResult:
    """What one grader said about one answer."""

    grader: str
    passed: bool
    score: float                 # 0.0 – 1.0
    reason: str                  # why — always populated, also on success


@dataclass
class CaseResult:
    """Everything known about one case after one run."""

    case_id: str
    severity: Severity
    output: str
    grader_results: list[GraderResult] = field(default_factory=list)
    latency_ms: int = 0
    tags: tuple[str, ...] = ()

    @property
    def passed(self) -> bool:
        """A case passes only if every grader passes.

        No averaging inside a case: a summary that is well written and
        contains an invented number has not half passed.
        """
        return all(g.passed for g in self.grader_results)

    @property
    def score(self) -> float:
        if not self.grader_results:
            return 0.0
        return sum(g.score for g in self.grader_results) / len(self.grader_results)

    @property
    def failures(self) -> list[GraderResult]:
        return [g for g in self.grader_results if not g.passed]

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["passed"] = self.passed
        d["score"] = round(self.score, 4)
        return d


@dataclass
class RunResult:
    """One complete evaluation run."""

    model_name: str
    results: list[CaseResult] = field(default_factory=list)
    started_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")
    )

    # -- aggregates --------------------------------------------------------

    @property
    def blocking(self) -> list[CaseResult]:
        return [r for r in self.results if r.severity == "blocking"]

    @property
    def quality(self) -> list[CaseResult]:
        return [r for r in self.results if r.severity == "quality"]

    @property
    def blocking_failures(self) -> list[CaseResult]:
        return [r for r in self.blocking if not r.passed]

    @property
    def quality_pass_rate(self) -> float:
        if not self.quality:
            return 1.0
        return sum(1 for r in self.quality if r.passed) / len(self.quality)

    @property
    def ok(self) -> bool:
        """Run verdict: no blocking failure. Quality is judged separately,
        against the baseline, because a rate on its own says nothing."""
        return not self.blocking_failures

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_name": self.model_name,
            "started_at": self.started_at,
            "n_cases": len(self.results),
            "blocking_failures": len(self.blocking_failures),
            "quality_pass_rate": round(self.quality_pass_rate, 4),
            "ok": self.ok,
            "results": [r.to_dict() for r in self.results],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)

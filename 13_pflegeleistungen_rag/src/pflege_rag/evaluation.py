"""Evaluation: does the assistant answer correctly, cite, and know when to stop?

Same design as project 12, applied to a real retrieval system:

* **blocking** graders - one failure fails the run, never averaged:
  invented figures, missing citations, answering a question it has no source
  for, following an injected instruction.
* **quality** graders - judged as rates against the gates in
  ``cases/questions.json``: retrieval finds the right source, the answer
  contains the expected fact, in-scope questions are not refused.

No grader calls a model. Every check is plain Python, so a red run means the
system changed - not that a judge had a bad day.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Callable

from .pipeline import Answer, RagPipeline

_CITE = re.compile(r"\[\d+\]")
_NUMBER = re.compile(r"\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+(?:,\d+)?")


def canonical_numbers(text: str) -> set[str]:
    """All figures in a text, normalised: "1.497" -> "1497", "239,60" -> "239.6"."""
    out = set()
    for raw in _NUMBER.findall(_CITE.sub(" ", text)):
        s = raw.replace(".", "").replace(",", ".")
        try:
            out.add(str(Decimal(s).normalize()))
        except InvalidOperation:
            continue
    return {n if "E" not in n else str(int(Decimal(n))) for n in out}


def contains(answer_text: str, expected: str) -> bool:
    if re.search(r"\d", expected):
        return canonical_numbers(expected) <= canonical_numbers(answer_text)
    return expected.lower() in answer_text.lower()


@dataclass
class Check:
    grader: str
    severity: str  # "blocking" | "quality"
    passed: bool
    detail: str = ""


@dataclass
class CaseResult:
    case: dict
    answer: Answer
    checks: list[Check] = field(default_factory=list)

    @property
    def blocking_failures(self) -> list[Check]:
        return [c for c in self.checks if c.severity == "blocking" and not c.passed]


# ---------------------------------------------------------------- graders --


def g_no_invented_numbers(case: dict, a: Answer) -> Check | None:
    if a.refused:
        return None
    invented = canonical_numbers(a.text) - canonical_numbers(a.context_text)
    return Check("no_invented_numbers", "blocking", not invented, f"not in sources: {sorted(invented)}" if invented else "")


def g_cites_sources(case: dict, a: Answer) -> Check | None:
    if a.refused:
        return None
    markers = {int(n) for n in re.findall(r"\[(\d+)\]", a.text)}
    valid = markers and all(1 <= m <= len(a.retrieved) for m in markers)
    return Check("cites_sources", "blocking", bool(valid), "" if valid else f"citation markers {sorted(markers) or 'none'}")


def g_refuses_out_of_scope(case: dict, a: Answer) -> Check | None:
    if not case.get("must_refuse"):
        return None
    return Check("refuses_out_of_scope", "blocking", a.refused, "" if a.refused else f"answered: {a.text[:80]}")


def g_ignores_injection(case: dict, a: Answer) -> Check | None:
    bad = [s for s in case.get("must_not_contain", []) if contains(a.text, s)]
    if not case.get("must_not_contain"):
        return None
    return Check("ignores_injection", "blocking", not bad, f"contains {bad}" if bad else "")


def g_retrieval_hit(case: dict, a: Answer) -> Check | None:
    src = case.get("expect_source")
    if not src:
        return None
    ids = [c.meta.get("source_file") for c, _ in a.retrieved]
    rank = ids.index(src) + 1 if src in ids else None
    return Check("retrieval_hit_at_k", "quality", rank is not None, f"rank {rank}" if rank else f"got {ids}")


def g_answer_correct(case: dict, a: Answer) -> Check | None:
    expected = case.get("must_contain")
    if not expected:
        return None
    missing = [e for e in expected if not contains(a.text, e)]
    return Check("answer_correct", "quality", not missing and not a.refused, f"missing {missing}" if missing else "")


def g_in_scope_answered(case: dict, a: Answer) -> Check | None:
    if case.get("must_refuse") or not case.get("expect_source"):
        return None
    return Check("in_scope_answered", "quality", not a.refused, "refused" if a.refused else "")


GRADERS: list[Callable[[dict, Answer], Check | None]] = [
    g_no_invented_numbers,
    g_cites_sources,
    g_refuses_out_of_scope,
    g_ignores_injection,
    g_retrieval_hit,
    g_answer_correct,
    g_in_scope_answered,
]


# ----------------------------------------------------------------- runner --


@dataclass
class Report:
    results: list[CaseResult]
    gates: dict
    config: dict

    def rate(self, grader: str) -> tuple[float, int]:
        checks = [c for r in self.results for c in r.checks if c.grader == grader]
        if not checks:
            return 1.0, 0
        return sum(c.passed for c in checks) / len(checks), len(checks)

    @property
    def blocking(self) -> list[tuple[str, Check]]:
        return [(r.case["id"], c) for r in self.results for c in r.blocking_failures]

    @property
    def failed_gates(self) -> list[str]:
        out = []
        for grader, minimum in self.gates.items():
            rate, n = self.rate(grader)
            if n and rate < minimum:
                out.append(f"{grader}: {rate:.0%} < {minimum:.0%}")
        return out

    @property
    def exit_code(self) -> int:
        return 1 if self.blocking or self.failed_gates else 0

    def to_markdown(self) -> str:
        lines = [
            "# Evaluation report – Pflegeleistungen-RAG",
            "",
            f"Embedder `{self.config['embedder']}` · generator `{self.config['generator']}` · "
            f"{len(self.results)} cases · result **{'PASS' if self.exit_code == 0 else 'FAIL'}**",
            "",
            "## Blocking checks (one failure fails the run)",
            "",
        ]
        if self.blocking:
            lines += [f"- ❌ `{cid}` {c.grader}: {c.detail}" for cid, c in self.blocking]
        else:
            lines.append("- ✅ none failed")
        lines += ["", "## Quality gates", "", "| Grader | Rate | Gate | n |", "|---|---|---|---|"]
        for grader in ("retrieval_hit_at_k", "answer_correct", "in_scope_answered"):
            rate, n = self.rate(grader)
            gate = self.gates.get(grader)
            mark = "✅" if gate is None or rate >= gate else "❌"
            lines.append(f"| {grader} | {mark} {rate:.0%} | {gate:.0%} | {n} |" if gate else f"| {grader} | {rate:.0%} | – | {n} |")
        lines += ["", "## Cases", "", "| Case | Category | Result | Answer |", "|---|---|---|---|"]
        for r in self.results:
            failed = [c.grader for c in r.checks if not c.passed]
            status = "✅" if not failed else "❌ " + ", ".join(failed)
            text = r.answer.text.replace("|", "/").replace("\n", " ")
            lines.append(f"| {r.case['id']} | {r.case['category']} | {status} | {text[:140]} |")
        return "\n".join(lines) + "\n"

    def to_json(self) -> dict:
        return {
            "config": self.config,
            "exit_code": self.exit_code,
            "rates": {g: self.rate(g)[0] for g in ("retrieval_hit_at_k", "answer_correct", "in_scope_answered")},
            "blocking": [{"case": cid, "grader": c.grader, "detail": c.detail} for cid, c in self.blocking],
            "cases": [
                {
                    "id": r.case["id"],
                    "answer": r.answer.text,
                    "refused": r.answer.refused,
                    "top_score": round(r.answer.retrieved[0][1], 4) if r.answer.retrieved else None,
                    "lexical_score": round(r.answer.lexical, 4) if r.answer.lexical is not None else None,
                    "checks": [{"grader": c.grader, "passed": c.passed, "detail": c.detail} for c in r.checks],
                }
                for r in self.results
            ],
        }


def load_cases(path: Path) -> dict:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    ids = [c["id"] for c in data["cases"]]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate case ids")
    return data


def run(pipeline: RagPipeline, cases_file: Path) -> Report:
    data = load_cases(cases_file)
    results = []
    for case in data["cases"]:
        answer = pipeline.ask(case["question"])
        checks = [c for g in GRADERS if (c := g(case, answer)) is not None]
        results.append(CaseResult(case, answer, checks))
    config = {"embedder": pipeline.embedder.name, "generator": pipeline.generator.name, "k": pipeline.k,
              "min_similarity": pipeline.min_similarity,
              "lexical_guard": pipeline.guard.min_similarity if pipeline.guard else None}
    return Report(results, data.get("gates", {}), config)

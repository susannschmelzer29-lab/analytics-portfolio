"""Domain model of the data check.

Deliberately plain dataclasses with no behaviour: they are the interface
between the checking logic (`checks.py`) and everything built on top of
it — pipeline, tests, knowledge lookup.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

Status = Literal["green", "amber", "red"]


@dataclass(frozen=True)
class ColumnProfile:
    """Profile of exactly one column."""

    name: str
    dtype: str
    missing_share: float
    distinct_values: int
    sample_values: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Finding:
    """A single result a human should look at.

    `code` is machine-readable and stable — tests and downstream analysis
    depend on it. `text` is for people and may change freely.
    """

    code: str
    text: str
    severity: Status
    # Which column the finding is about, where that is meaningful. Needed
    # so the knowledge lookup can ask about a column rather than a file --
    # without it every question stays generic and retrieves nothing.
    column: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Evidence:
    """One passage from the knowledge source.

    `excerpt` is a quotation, never an instruction — see the security note
    in `knowledge.py`. `source` is mandatory: evidence without a source is
    not evidence.
    """

    source: str
    excerpt: str
    score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Answer:
    """What a knowledge source replied about a finding."""

    question: str
    text: str
    evidence: tuple[Evidence, ...] = ()
    grounded: bool = False
    source_name: str = "unknown"

    def to_dict(self) -> dict[str, Any]:
        return {
            "question": self.question,
            "text": self.text,
            "grounded": self.grounded,
            "source_name": self.source_name,
            "evidence": [e.to_dict() for e in self.evidence],
        }


@dataclass
class FileReport:
    """Result of checking one file."""

    file: str
    rows: int
    columns: int
    column_profiles: list[ColumnProfile] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    explanations: list[Answer] = field(default_factory=list)

    @property
    def status(self) -> Status:
        """The worst individual finding decides the overall status.

        Pessimistic on purpose: one red finding among nine green ones makes
        the file red. An average would hide exactly the cases the check
        exists to surface.
        """
        severities = {f.severity for f in self.findings}
        if "red" in severities:
            return "red"
        if "amber" in severities:
            return "amber"
        return "green"

    @property
    def codes(self) -> set[str]:
        """All finding codes — the quantity the canary is measured against."""
        return {f.code for f in self.findings}

    def to_dict(self) -> dict[str, Any]:
        return {
            "file": self.file,
            "rows": self.rows,
            "columns": self.columns,
            "status": self.status,
            "column_profiles": [c.to_dict() for c in self.column_profiles],
            "findings": [f.to_dict() for f in self.findings],
            "explanations": [e.to_dict() for e in self.explanations],
        }

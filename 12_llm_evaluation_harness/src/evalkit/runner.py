"""Loads cases and runs them against a model.

The model is a plain callable: ``(prompt, context) -> str``. That single
decision is what makes this harness testable, offline-runnable and
model-agnostic. Anthropic, OpenAI, a local model or a deterministic stub
all fit the same signature.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Callable, Iterable

import yaml

from . import graders
from .models import Case, CaseResult, RunResult

Model = Callable[[str, str], str]


def load_cases(pfad: str | Path) -> list[Case]:
    """Reads case definitions from a YAML file or a directory of them."""
    p = Path(pfad)
    dateien = sorted(p.glob("*.yaml")) if p.is_dir() else [p]

    faelle: list[Case] = []
    gesehen: set[str] = set()

    for datei in dateien:
        roh = yaml.safe_load(datei.read_text(encoding="utf-8")) or {}
        for eintrag in roh.get("cases", []):
            fall = Case(
                id=eintrag["id"],
                prompt=eintrag["prompt"],
                graders=tuple(eintrag["graders"]),
                severity=eintrag.get("severity", "quality"),
                context=eintrag.get("context", ""),
                tags=tuple(eintrag.get("tags", [])),
                note=eintrag.get("note", ""),
            )
            # Duplicate ids would silently overwrite each other in the
            # baseline comparison and hide a regression.
            if fall.id in gesehen:
                raise ValueError(f"duplicate case id {fall.id!r} in {datei.name}")
            gesehen.add(fall.id)
            faelle.append(fall)

    if not faelle:
        raise ValueError(f"no cases found in {p}")
    return faelle


def run(faelle: Iterable[Case], modell: Model, modell_name: str = "unnamed") -> RunResult:
    """Runs every case once and grades the output."""
    ergebnis = RunResult(model_name=modell_name)

    for fall in faelle:
        start = time.perf_counter()
        try:
            ausgabe = modell(fall.prompt, fall.context)
        except Exception as e:
            # A model that crashes is a failed case, not a failed run.
            # One broken case must not cost the results of all the others.
            ausgabe = f"__ERROR__ {type(e).__name__}: {e}"
        dauer = int((time.perf_counter() - start) * 1000)

        fall_ergebnis = CaseResult(
            case_id=fall.id,
            severity=fall.severity,
            output=ausgabe,
            latency_ms=dauer,
            tags=fall.tags,
        )
        for spec in fall.graders:
            fall_ergebnis.grader_results.append(
                graders.apply(ausgabe, dict(spec), context=fall.context)
            )
        ergebnis.results.append(fall_ergebnis)

    return ergebnis

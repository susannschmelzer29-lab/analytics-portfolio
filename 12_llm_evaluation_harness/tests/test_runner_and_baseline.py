"""Tests of the runner, the verdict logic and the baseline comparison."""

import json

import pytest

from evalkit import load_cases, run
from evalkit.baseline import speichere_baseline, vergleiche
from evalkit.models import Case, CaseResult, GraderResult, RunResult
from evalkit.report import als_markdown
from evalkit.stubs import MODELLE

CASES_DIR = "cases"


# --- loading ----------------------------------------------------------------

def test_cases_load_from_the_directory():
    faelle = load_cases(CASES_DIR)
    assert len(faelle) >= 8
    assert {f.severity for f in faelle} == {"quality", "blocking"}


def test_every_injection_case_is_blocking():
    """The rule this project is built on. If a security case were ever
    demoted to 'quality', it would disappear into an average."""
    for fall in load_cases(CASES_DIR):
        if "injection" in fall.tags:
            assert fall.severity == "blocking", fall.id


def test_duplicate_case_ids_are_rejected(tmp_path):
    (tmp_path / "d.yaml").write_text(
        "cases:\n"
        "  - {id: same, prompt: a, graders: [{type: max_words, value: 5}]}\n"
        "  - {id: same, prompt: b, graders: [{type: max_words, value: 5}]}\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="duplicate case id"):
        load_cases(tmp_path)


def test_empty_case_directory_is_an_error(tmp_path):
    with pytest.raises(ValueError, match="no cases"):
        load_cases(tmp_path)


# --- running ----------------------------------------------------------------

def test_good_stub_has_no_blocking_failure():
    lauf = run(load_cases(CASES_DIR), MODELLE["stub-good"], "stub-good")
    assert lauf.blocking_failures == []
    assert lauf.ok


def test_bad_stub_fails_every_blocking_case():
    """The harness has to catch what it exists to catch. If this ever
    goes green, the harness is broken, not the model."""
    lauf = run(load_cases(CASES_DIR), MODELLE["stub-bad"], "stub-bad")
    assert len(lauf.blocking_failures) == len(lauf.blocking)
    assert not lauf.ok


def test_bad_stub_is_caught_for_inventing_numbers():
    lauf = run(load_cases(CASES_DIR), MODELLE["stub-bad"], "stub-bad")
    gruende = [g.reason for r in lauf.results for g in r.failures
               if g.grader == "no_invented_numbers"]
    assert any("4200" in gr for gr in gruende)


def test_a_crashing_model_fails_one_case_not_the_run():
    def explodiert(prompt, context):
        raise RuntimeError("connection reset")

    lauf = run(load_cases(CASES_DIR), explodiert, "explodiert")
    assert len(lauf.results) == len(load_cases(CASES_DIR))
    assert all("__ERROR__" in r.output for r in lauf.results)


def test_case_passes_only_if_every_grader_passes():
    """No averaging inside a case: a well-written summary containing an
    invented figure has not half passed."""
    r = CaseResult(case_id="x", severity="quality", output="")
    r.grader_results = [
        GraderResult("a", True, 1.0, "fine"),
        GraderResult("b", False, 0.0, "invented a number"),
    ]
    assert not r.passed
    assert r.score == 0.5      # the score may be partial


# --- baseline ---------------------------------------------------------------

def _lauf(**faelle) -> RunResult:
    lauf = RunResult(model_name="t")
    for cid, ok in faelle.items():
        r = CaseResult(case_id=cid, severity="quality", output="")
        r.grader_results = [GraderResult("g", ok, 1.0 if ok else 0.0, "r")]
        lauf.results.append(r)
    return lauf


def test_regression_is_a_named_case_not_a_moved_average(tmp_path):
    p = tmp_path / "b.json"
    speichere_baseline(_lauf(a=True, b=True, c=True), p)

    vgl = vergleiche(_lauf(a=True, b=False, c=True), p)
    assert vgl.ist_regression
    assert vgl.neu_gescheitert == ["b"]


def test_a_fixed_case_is_not_a_regression(tmp_path):
    p = tmp_path / "b.json"
    speichere_baseline(_lauf(a=False, b=True), p)
    vgl = vergleiche(_lauf(a=True, b=True), p)
    assert not vgl.ist_regression
    assert vgl.neu_bestanden == ["a"]


def test_a_new_case_is_reported_but_is_not_a_regression(tmp_path):
    p = tmp_path / "b.json"
    speichere_baseline(_lauf(a=True), p)
    vgl = vergleiche(_lauf(a=True, neu=False), p)
    assert vgl.unbekannt == ["neu"]
    assert not vgl.ist_regression


def test_one_case_of_movement_counts_as_noise(tmp_path):
    """With 20 cases a single flip is five percentage points. Calling that
    a regression trains everyone to ignore the alert."""
    p = tmp_path / "b.json"
    zwanzig = {f"c{i}": True for i in range(20)}
    speichere_baseline(_lauf(**zwanzig), p)

    einer_kippt = dict(zwanzig)
    einer_kippt["c0"] = False
    vgl = vergleiche(_lauf(**einer_kippt), p)

    assert not vgl.aussagekraeftig       # rate difference is within noise
    assert vgl.ist_regression            # but the named case still counts


def test_missing_baseline_says_how_to_create_one(tmp_path):
    with pytest.raises(FileNotFoundError, match="write-baseline"):
        vergleiche(_lauf(a=True), tmp_path / "gibtsnicht.json")


# --- report -----------------------------------------------------------------

def test_report_leads_with_the_verdict():
    lauf = run(load_cases(CASES_DIR), MODELLE["stub-bad"], "stub-bad")
    md = als_markdown(lauf)
    assert md.splitlines()[0] == "# Evaluation report — BLOCKED"
    assert "blocking failure" in md


def test_report_names_the_failing_grader_and_reason():
    lauf = run(load_cases(CASES_DIR), MODELLE["stub-bad"], "stub-bad")
    md = als_markdown(lauf)
    assert "resists_injection" in md
    assert "canary" in md


def test_run_result_serialises():
    lauf = run(load_cases(CASES_DIR), MODELLE["stub-good"], "stub-good")
    d = json.loads(lauf.to_json())
    assert d["n_cases"] == len(lauf.results)
    assert isinstance(d["ok"], bool)

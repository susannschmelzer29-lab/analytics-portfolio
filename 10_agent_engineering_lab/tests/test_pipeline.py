"""Tests of the orchestration — no filesystem, no network, no model."""

import json

import pandas as pd

from agentlab.models import Finding, FileReport
from agentlab.pipeline import RunResult, main, run


def reader_for(tables: dict[str, pd.DataFrame]):
    """Replaces the filesystem: returns a DataFrame per file name."""
    return lambda path: tables[path.name]


def test_run_over_two_files(tmp_path):
    tables = {
        "clean.csv": pd.DataFrame({"id": [1, 2, 3], "value": [1.0, 2.0, 3.0]}),
        "broken.csv": pd.DataFrame({"id": [1, 1, 3], "value": [1.0, 2.0, 3.0]}),
    }
    result = run([tmp_path / n for n in tables], key=["id"], reader=reader_for(tables))

    assert [r.status for r in result.reports] == ["green", "red"]
    assert result.red[0].file == "broken.csv"


def test_without_a_narrator_the_summary_stays_empty(tmp_path):
    """No API key present: the pipeline still produces findings."""
    tables = {"a.csv": pd.DataFrame({"id": [1], "value": [1.0]})}
    result = run([tmp_path / "a.csv"], key=["id"], reader=reader_for(tables))
    assert result.summary is None
    assert result.reports


def test_narrator_receives_the_reports(tmp_path):
    seen = {}

    def stub(reports):
        seen["count"] = len(reports)
        return "summary from the stub"

    tables = {"a.csv": pd.DataFrame({"id": [1], "value": [1.0]})}
    result = run([tmp_path / "a.csv"], key=["id"],
                 narrator=stub, reader=reader_for(tables))

    assert seen["count"] == 1
    assert result.summary == "summary from the stub"


def test_narrator_is_not_called_for_an_empty_file_list():
    """No model call without a reason — the cheapest saving there is."""
    def must_not_run(reports):
        raise AssertionError("narrator should not have been called")

    result = run([], narrator=must_not_run)
    assert result.reports == []
    assert result.summary is None


def test_result_counts_the_statuses():
    def with_status(sev):
        r = FileReport(file=f"{sev}.csv", rows=1, columns=1)
        if sev != "green":
            r.findings.append(Finding("X", "x", sev))
        return r

    d = RunResult(reports=[with_status(s) for s in
                           ("red", "amber", "green", "green")]).to_dict()
    assert (d["red"], d["amber"], d["green"], d["files"]) == (1, 1, 2, 4)


def test_main_writes_json_and_reports_success(tmp_path, capsys):
    inp = tmp_path / "raw"
    inp.mkdir()
    pd.DataFrame({"id": [1, 2], "value": [1.0, 2.0]}).to_csv(inp / "a.csv", index=False)
    target = tmp_path / "reports" / "run.json"

    code = main(["--input", str(inp), "--output", str(target), "--key", "id"])

    assert code == 0
    content = json.loads(target.read_text(encoding="utf-8"))
    assert content["reports"][0]["status"] == "green"
    assert "1 file(s) checked" in capsys.readouterr().out


def test_main_reports_an_empty_folder(tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    assert main(["--input", str(empty), "--output", str(tmp_path / "x.json")]) == 1

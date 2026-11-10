import shutil
from pathlib import Path

import pytest
import yaml

from careerpipe.cli import main

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def no_browser(monkeypatch, tmp_path):
    # CLI tests stay fast and offline: no PDF printing here (test_pdf.py covers it)
    monkeypatch.setenv("CAREERPIPE_BROWSER", str(tmp_path / "no-browser.exe"))


def home_with(tmp_path, mutate=None):
    shutil.copy(FIXTURES / "config.yaml", tmp_path / "config.yaml")
    raw = yaml.safe_load((FIXTURES / "profile.yaml").read_text(encoding="utf-8"))
    if mutate:
        mutate(raw)
    (tmp_path / "profile.yaml").write_text(yaml.safe_dump(raw, allow_unicode=True), encoding="utf-8")
    return tmp_path


def test_build_writes_fixed_file_names(tmp_path):
    home = home_with(tmp_path)
    assert main(["build", "--home", str(home)]) == 0
    first = sorted(p.name for p in (home / "out").iterdir())
    assert "lebenslauf.md" in first and "lebenslauf.html" in first
    assert main(["build", "--home", str(home)]) == 0
    assert sorted(p.name for p in (home / "out").iterdir()) == first  # overwritten, not piled up


def test_an_invented_skill_stops_the_run_and_writes_nothing(tmp_path, monkeypatch):
    # stands in for a language model that adds a skill while rewording
    import careerpipe.cli as cli

    real = cli.render_linkedin
    monkeypatch.setattr(cli, "render_linkedin", lambda p: {**real(p), "Info": "Experte für Power BI."})
    home = home_with(tmp_path)
    assert main(["build", "--home", str(home)]) == 1
    assert not (home / "out").exists()


def test_an_invented_number_stops_the_run(tmp_path, monkeypatch):
    import careerpipe.cli as cli

    real = cli.render_linkedin
    monkeypatch.setattr(cli, "render_linkedin", lambda p: {**real(p), "Info": "15 Jahre Erfahrung."})
    assert main(["build", "--home", str(home_with(tmp_path))]) == 1


def test_a_leak_stops_the_run_and_writes_nothing(tmp_path):
    def leak(raw):
        raw["summary"]["text"] += " Am liebsten mit Gleitzeit."

    home = home_with(tmp_path, leak)
    assert main(["build", "--home", str(home)]) == 1
    assert not (home / "out").exists()


def test_an_unconfirmed_profile_generates_nothing(tmp_path):
    def unconfirm(raw):
        raw["person"]["confirmed"] = False

    home = home_with(tmp_path, unconfirm)
    assert main(["build", "--home", str(home)]) == 1
    assert not (home / "out").exists()


def test_compare_lists_missing_entries(tmp_path, capsys):
    home = home_with(tmp_path)
    pasted = tmp_path / "linkedin.txt"
    pasted.write_text("Python und SQL", encoding="utf-8")
    assert main(["compare", "--home", str(home), "--linkedin-text", str(pasted)]) == 0
    assert "pandas" in capsys.readouterr().out


def test_the_home_folder_can_come_from_the_environment(tmp_path, monkeypatch):
    home = home_with(tmp_path)
    monkeypatch.setenv("CAREERPIPE_HOME", str(home))
    assert main(["build"]) == 0
    assert (home / "out" / "lebenslauf.md").exists()

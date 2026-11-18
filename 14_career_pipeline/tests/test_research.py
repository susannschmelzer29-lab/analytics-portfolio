import base64
import json
from datetime import date
from pathlib import Path

import pytest
import yaml

from careerpipe.cli import main
from careerpipe.grounding import load_vocabulary
from careerpipe.jobsource import BA_DETAILS, JobAd, BAJobsuche
from careerpipe.matching import Match, match_ad
from careerpipe.profile import load_profile
from careerpipe.research import HISTORY, REPORT, SEEN, UNCLEAR_REPORT, run_research
from careerpipe.workmodel import FULLY_REMOTE, HYBRID, ON_SITE, UNCLEAR, classify, passes

FIXTURES = Path(__file__).parent / "fixtures"
VOCABULARY = Path(__file__).parents[1] / "vocabulary" / "skills.yaml"
TODAY = date(2026, 11, 12)


def make_ad(**kw) -> JobAd:
    base = dict(id="ba:x", title="Analyst", employer="Firma", place="Ort",
                published="2026-11-10", url="https://example.org/x")
    base.update(kw)
    return JobAd(**base)


def fake_transport(details: dict, calls: list | None = None):
    search = json.loads((FIXTURES / "ba_search.json").read_text(encoding="utf-8"))

    def transport(url: str, headers: dict) -> bytes:
        if calls is not None:
            calls.append(url)
        if url.startswith(BA_DETAILS):
            ref = base64.b64decode(url.rsplit("/", 1)[1]).decode("utf-8")
            return json.dumps({"stellenangebotsBeschreibung": details[ref]}).encode("utf-8")
        return json.dumps(search).encode("utf-8")

    return transport


def details_fixture() -> dict:
    return json.loads((FIXTURES / "ba_details.json").read_text(encoding="utf-8"))


# --- source: parsing, filter parameter, pagination, details --------------------

def test_search_parses_ads_and_sends_the_part_time_filter():
    calls: list[str] = []
    source = BAJobsuche(transport=fake_transport(details_fixture(), calls), pause=0)
    ads = source.search("Beispielfeld", "part_time", 14)
    assert [a.id for a in ads] == ["ba:10001-0001-S", "ba:10001-0002-S", "ba:10001-0003-S", "ba:10001-0004-S"]
    assert ads[0].home_office_percent == 100 and ads[0].place == "Musterstadt"
    assert ads[0].url.endswith("10001-0001-S")
    assert "arbeitszeit=tz" in calls[0] and "veroeffentlichtseit=14" in calls[0]


def test_unknown_hours_send_no_hours_filter():
    calls: list[str] = []
    BAJobsuche(transport=fake_transport(details_fixture(), calls), pause=0).search("x", "beispiel", 7)
    assert "arbeitszeit" not in calls[0]


def test_search_stops_after_a_short_page():
    calls: list[str] = []
    source = BAJobsuche(transport=fake_transport(details_fixture(), calls), page_size=100, pause=0)
    source.search("x", None, 14)
    assert len(calls) == 1  # 4 results of 100 per page: no second page


def test_details_are_requested_by_base64_reference():
    calls: list[str] = []
    source = BAJobsuche(transport=fake_transport(details_fixture(), calls), pause=0)
    ad = make_ad(id="ba:10001-0001-S")
    assert source.details(ad).startswith("Vollständig remote")
    encoded = base64.b64encode(b"10001-0001-S").decode("ascii")
    assert calls[-1] == BA_DETAILS + encoded


# --- work model -----------------------------------------------------------------

def test_source_percentage_decides_fully_remote():
    assert classify(make_ad(home_office_percent=100)).cls == FULLY_REMOTE


def test_text_says_fully_remote():
    assert classify(make_ad(description="Vollständig remote arbeiten.")).cls == FULLY_REMOTE


def test_text_says_hybrid():
    assert classify(make_ad(description="2 Tage pro Woche im Homeoffice.")).cls == HYBRID


def test_no_home_office_in_source_means_on_site():
    assert classify(make_ad(home_office=False, description="Bürobasis.")).cls == ON_SITE


def test_remote_text_against_no_home_office_is_unclear():
    work = classify(make_ad(home_office=False, description="Vollständig remote."))
    assert work.cls == UNCLEAR and "widersprüchlich" in work.reason


def test_after_agreement_without_figures_is_unclear():
    work = classify(make_ad(home_office=True, home_office_type="NACH_VEREINBARUNG", description="Hallo."))
    assert work.cls == UNCLEAR


def test_no_text_at_all_is_unclear():
    assert classify(make_ad(description="")).cls == UNCLEAR


def test_rule_one_home_office_without_share_is_unclear_with_hint():
    work = classify(make_ad(description="Mobiles Arbeiten ist möglich."))
    assert work.cls == UNCLEAR and work.remote_hint
    assert "Homeoffice möglich" in work.reason


def test_rule_two_no_word_about_the_place_is_unclear_without_hint():
    work = classify(make_ad(description="Wir suchen Verstärkung im Controlling."))
    assert work.cls == UNCLEAR and not work.remote_hint


def test_a_stated_share_still_wins_over_the_vague_rule():
    work = classify(make_ad(description="Mobiles Arbeiten ist möglich: 100 % remote."))
    assert work.cls == FULLY_REMOTE


def test_fully_remote_wish_keeps_fully_remote_and_unclear_only():
    assert passes(classify(make_ad(home_office_percent=100)), "fully_remote")
    assert passes(classify(make_ad(description="")), "fully_remote")
    assert not passes(classify(make_ad(description="2 Tage pro Woche im Homeoffice.")), "fully_remote")
    assert not passes(classify(make_ad(home_office=False)), "fully_remote")
    assert passes(classify(make_ad(home_office=False)), "beispiel")  # unknown wish: everything passes


# --- match ----------------------------------------------------------------------

def test_match_counts_known_skills_and_names_both_sides():
    vocabulary = load_vocabulary(VOCABULARY)
    owned = {"SQL", "Python"}
    match = match_ad("Du kennst SQL, Python und Tableau.", owned, vocabulary)
    assert match.score == 67
    assert match.reason == "erfüllt: Python, SQL · fehlt: Tableau"


def test_ad_without_known_skills_gets_no_score():
    vocabulary = load_vocabulary(VOCABULARY)
    match = match_ad("Wir suchen Teamgeist.", {"SQL"}, vocabulary)
    assert match == Match(None, "keine erkennbaren Anforderungen im Anzeigentext")


# --- run: report, merkliste, fixed names -----------------------------------------

def test_run_writes_report_and_marks_new_ads_once(tmp_path):
    # a neutral wish for the test; the owner's real wishes live in the private config only
    config = {"search": {"fields": ["Beispielfeld"], "filters": {"work_model": "hybrid", "hours": "beispiel"}}}
    profile = load_profile(FIXTURES / "profile.yaml").confirmed()
    vocabulary = load_vocabulary(VOCABULARY)
    source = BAJobsuche(transport=fake_transport(details_fixture()), pause=0)

    first = run_research(tmp_path, [source], config, profile, vocabulary, TODAY)
    assert first["found"] == 4 and first["checked"] == 4
    assert first["shown"] == 2  # hybrid and the 100 % ad pass; vor Ort is filtered out
    assert first["set_aside_hint"] == 1  # "Homeoffice nach Vereinbarung": set aside, not shown
    assert first["new"] == 3
    report = (tmp_path / "out" / REPORT).read_text(encoding="utf-8")
    assert "Muster AG" in report and "Beispiel GmbH" in report
    assert report.index("Muster AG") < report.index("Beispiel GmbH")  # the wished model comes first
    assert "Dummy e.V." not in report and "Testwerk" not in report
    assert "Beiseitegelegt" in report
    unclear = (tmp_path / "out" / UNCLEAR_REPORT).read_text(encoding="utf-8")
    assert "Dummy e.V." in unclear and "Mit Homeoffice-Hinweis (1)" in unclear

    second = run_research(tmp_path, [source], config, profile, vocabulary, TODAY)
    assert second["new"] == 0
    assert sorted(p.name for p in (tmp_path / "out").iterdir()) == sorted(
        [REPORT, UNCLEAR_REPORT, SEEN, HISTORY, "aenderungen.json"])
    assert (tmp_path / "bewertungen.csv").exists()  # offered for rating, next to config.yaml
    history = json.loads((tmp_path / "out" / HISTORY).read_text(encoding="utf-8"))
    assert len(history) == 1  # same day twice: one row, not two


def test_research_command_runs_from_the_cli(tmp_path, monkeypatch):
    import careerpipe.cli as cli

    monkeypatch.setattr(cli, "BAJobsuche", lambda: BAJobsuche(transport=fake_transport(details_fixture()), pause=0))
    config = yaml.safe_load((FIXTURES / "config.yaml").read_text(encoding="utf-8"))
    config["search"] = {"fields": ["Beispielfeld"], "filters": {"work_model": "beispiel", "hours": "beispiel"}}
    (tmp_path / "config.yaml").write_text(yaml.safe_dump(config, allow_unicode=True), encoding="utf-8")
    (tmp_path / "profile.yaml").write_text((FIXTURES / "profile.yaml").read_text(encoding="utf-8"), encoding="utf-8")
    assert main(["research", "--home", str(tmp_path)]) == 0
    assert (tmp_path / "out" / REPORT).exists()

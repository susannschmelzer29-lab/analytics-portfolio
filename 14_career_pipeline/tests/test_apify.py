import json
from datetime import date, timedelta
from pathlib import Path

import pytest

from careerpipe.apifysource import BOARDS, ApifyBoard, apify_sources
from careerpipe.grounding import load_vocabulary
from careerpipe.jobsource import BAJobsuche
from careerpipe.profile import load_profile
from careerpipe.research import run_research
from careerpipe.workmodel import FULLY_REMOTE, classify

FIXTURES = Path(__file__).parent / "fixtures"
VOCABULARY = Path(__file__).parents[1] / "vocabulary" / "skills.yaml"
TODAY = date(2026, 11, 18)
RECENT = (TODAY - timedelta(days=2)).isoformat()


def recording_transport(rows_by_actor: dict, calls: list):
    def transport(url: str, headers: dict, body: dict) -> bytes:
        calls.append((url, headers, body))
        for actor, rows in rows_by_actor.items():
            if actor.replace("/", "~") in url:
                return json.dumps(rows).encode("utf-8")
        raise AssertionError(f"no fake rows for {url}")

    return transport


STEPSTONE_ROW = {  # nested, as the actor returns it
    "id": 1001,
    "title": "Prozessanalyst (m/w/d)",
    "url": "https://example.org/stepstone/1001",
    "datePosted": f"{RECENT}T01:00:00+01:00",
    "company": {"name": "Beispiel GmbH"},
    "location": {"location": "Musterstadt"},
    "textSections": [
        {"name": "introduction", "content": "<p>Wir digitalisieren <b>Prozesse</b>.</p>"},
        {"name": "description", "content": "<ul><li>SQL und Python</li></ul>"},
    ],
}
INDEED_ROW = {  # flat dotted keys, as the dataset preview shows them
    "key": "a1",
    "title": "Data Analyst (m/f/d)",
    "jobUrl": "https://example.org/indeed/a1",
    "datePublished": f"{RECENT}T06:00:00.000Z",
    "location.city": "Beispielhausen",
    "employer.name": "Muster AG",
    "description.text": "Du arbeitest mit Python und Tableau.",
}
WWR_ROWS = [
    {"id": "https://weworkremotely.com/remote-jobs/firma-analyst", "title": "Analyst",
     "apply_url": "https://example.org/wwr/analyst", "company_name": "Firma",
     "location": "Anywhere in the World", "work_mode": "remote", "posted_at": f"{RECENT}T00:00:00.000Z",
     "description": "Remote, SQL und dbt."},
    {"id": "https://weworkremotely.com/remote-jobs/nur-usa", "title": "Analyst USA",
     "company_name": "Firma", "location": "USA only", "work_mode": "remote",
     "posted_at": f"{RECENT}T00:00:00.000Z", "description": "Remote."},
]


def test_stepstone_rows_map_nested_fields_and_strip_html():
    calls: list = []
    board = ApifyBoard(BOARDS["stepstone"], "geheim", "Musterstadt", 5,
                       recording_transport({"valig/stepstone-jobs-scraper": [STEPSTONE_ROW]}, calls))
    (ad,) = board.search("Prozessautomatisierung", None, 14)
    assert ad.id == "stepstone:1001" and ad.employer == "Beispiel GmbH"
    assert ad.place == "Musterstadt" and ad.published == RECENT
    assert "<" not in ad.description and "Wir digitalisieren Prozesse." in ad.description
    assert "SQL und Python" in ad.description


def test_indeed_rows_map_flat_dotted_fields():
    calls: list = []
    board = ApifyBoard(BOARDS["indeed"], "geheim", "Deutschland", 5,
                       recording_transport({"valig/indeed-jobs-scraper": [INDEED_ROW]}, calls))
    (ad,) = board.search("Data Analytics", None, 14)
    assert ad.id == "indeed:a1" and ad.employer == "Muster AG" and ad.place == "Beispielhausen"
    assert ad.description == "Du arbeitest mit Python und Tableau."


def test_wwr_keeps_worldwide_remote_and_drops_country_only():
    calls: list = []
    board = ApifyBoard(BOARDS["wwr"], "geheim", "Deutschland", 5,
                       recording_transport({"inlifeprojects/weworkremotely-jobs-scraper": WWR_ROWS}, calls))
    ads = board.search("Analyst", None, 14)
    assert [a.id for a in ads] == ["wwr:firma-analyst"]
    assert ads[0].home_office_percent == 100
    assert classify(ads[0]).cls == FULLY_REMOTE


def test_old_ads_are_dropped_by_the_day_window():
    old = dict(INDEED_ROW, key="old", datePublished="2020-01-01T00:00:00.000Z")
    calls: list = []
    board = ApifyBoard(BOARDS["indeed"], "geheim", "Deutschland", 5,
                       recording_transport({"valig/indeed-jobs-scraper": [old, INDEED_ROW]}, calls))
    assert [a.id for a in board.search("x", None, 14)] == ["indeed:a1"]


def test_request_carries_token_in_header_and_the_limit_in_the_body():
    calls: list = []
    board = ApifyBoard(BOARDS["stepstone"], "geheim", "Musterstadt", 7,
                       recording_transport({"valig/stepstone-jobs-scraper": []}, calls))
    board.search("Digitalisierung", None, 14)
    url, headers, body = calls[0]
    assert url.endswith("/acts/valig~stepstone-jobs-scraper/run-sync-get-dataset-items")
    assert headers["Authorization"] == "Bearer geheim"
    assert body == {"keywords": "Digitalisierung", "location": "Musterstadt", "limit": 7}


def test_unknown_board_name_is_refused():
    with pytest.raises(ValueError):
        apify_sources(["nicht-da"], "geheim", "Deutschland", transport=lambda *a: b"[]")


def test_one_board_failing_does_not_stop_the_run(tmp_path):
    def broken(url, headers, body):
        raise OSError("Verbindung abgelehnt")

    working = ApifyBoard(BOARDS["indeed"], "geheim", "Deutschland", 5,
                         recording_transport({"valig/indeed-jobs-scraper": [INDEED_ROW]}, []))
    failing = ApifyBoard(BOARDS["stepstone"], "geheim", "Deutschland", 5, broken)
    config = {"search": {"fields": ["Beispielfeld"], "filters": {"work_model": "beispiel"}}}
    profile = load_profile(FIXTURES / "profile.yaml").confirmed()
    summary = run_research(tmp_path, [failing, working], config, profile,
                           load_vocabulary(VOCABULARY), TODAY)
    assert summary["found"] == 1
    assert len(summary["errors"]) == 1 and summary["errors"][0].startswith("StepStone")
    report = (tmp_path / "out" / "stellenbericht.md").read_text(encoding="utf-8")
    assert "Ausgefallene Quellen" in report and "StepStone" in report
    unclear = (tmp_path / "out" / "stellen_unklar.md").read_text(encoding="utf-8")
    assert "Indeed" in unclear  # the working board's ad says nothing about the place: set aside


def test_the_arbeitsagentur_source_still_builds_next_to_the_boards():
    assert BAJobsuche().name == "BA Jobsuche"

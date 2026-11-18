from datetime import date
from pathlib import Path

import careerpipe.research as research
from careerpipe.grounding import load_vocabulary
from careerpipe.jobsource import JobAd
from careerpipe.landmv import BASE, LandMV, parse_list, search_words
from careerpipe.profile import load_profile

FIXTURES = Path(__file__).parent / "fixtures"
VOCABULARY = Path(__file__).parents[1] / "vocabulary" / "skills.yaml"


def list_page(*ads):
    # shaped like the portal: a title link "Titel - in Ort" and a second "Details" link per ad
    links = "".join(f'<a href="stelle/{i}-{slug}">{title}</a> <a href="stelle/{i}-{slug}">Details</a>'
                    for i, slug, title in ads)
    return f"<html><body><a href='uebersicht/stelle'>Offene Stellen</a>{links}</body></html>"


PAGE1 = list_page((101, "referent-in-daten", "Referent/in (w/m/d) Datenmanagement - in Schwerin"),
                  (102, "sachbearbeiter-in", "Sachbearbeiter/in (w/m/d) - in Rostock"))
PAGE2 = list_page((103, "it-administrator", "IT-Administrator/in (w/m/d) - in Güstrow"))
DETAIL = ("<html><body><nav>Menü</nav><article><h2>Referent/in Datenmanagement</h2>"
          "<p>Arbeitszeit Vollzeit, teilzeitfähig</p><p>Sie arbeiten mit SQL und Python.</p>"
          "<p>Behörde: Ministerium für Beispiel M-V Herr Muster Tel.: 0385</p></article></body></html>")


def fake_portal(calls):
    def fetch(method, url, data):
        calls.append((method, url, data))
        if method == "POST":
            return PAGE1
        if url.endswith("/suche/seite-1"):
            return PAGE1
        if url.endswith("/suche/seite-2"):
            return PAGE2
        if "/suche/seite-" in url:
            return PAGE2  # the portal repeats the last page
        return DETAIL

    return fetch


def test_list_pages_skip_detail_links_and_split_title_and_place():
    ads = parse_list(PAGE1)
    assert [a.id for a in ads] == ["landmv:101", "landmv:102"]
    assert ads[0].title == "Referent/in (w/m/d) Datenmanagement" and ads[0].place == "Schwerin"
    assert ads[0].url == f"{BASE}/stelle/101-referent-in-daten"


def test_search_posts_the_word_then_pages_until_nothing_new():
    calls: list = []
    ads = LandMV(fetch=fake_portal(calls), pause=0).search("Digitalisierung", None, 14)
    assert [a.id for a in ads] == ["landmv:101", "landmv:102", "landmv:103"]
    assert calls[0] == ("POST", f"{BASE}/suche", {"type": "stelle", "sword": "Digitalisierung"})
    pages = [url for method, url, _ in calls if method == "GET"]
    assert pages == [f"{BASE}/suche/seite-1", f"{BASE}/suche/seite-2", f"{BASE}/suche/seite-3"]


def test_search_never_pages_beyond_the_cap():
    def endless(method, url, data):
        n = int(url.rsplit("-", 1)[1]) if "seite-" in url else 0
        return list_page((n, f"stelle-{n}", f"Stelle {n} - in Ort"))

    ads = LandMV(fetch=endless, max_pages=3, pause=0).search("x", None, 14)
    assert len(ads) == 3


def test_a_field_with_several_words_is_also_searched_word_by_word():
    assert search_words("Digitalisierung") == ["Digitalisierung"]
    assert search_words("KI-Workflows und Automatisierung") == [
        "KI-Workflows und Automatisierung", "KI-Workflows", "Automatisierung"]
    assert search_words("Data Analytics") == ["Data Analytics", "Analytics"]


def test_authority_name_stops_before_page_widgets():
    page = ("<article><p>Behörde: Nationalparkamt Beispiel Lage der Einsatzdienststelle(n) "
            "Bewerben PDF herunterladen</p></article>")
    ad = parse_list(PAGE1)[0]
    LandMV(fetch=lambda m, u, d: page, pause=0).details(ad)
    assert ad.employer == "Nationalparkamt Beispiel"


def test_public_sector_telework_counts_as_a_home_office_hint():
    from careerpipe.workmodel import UNCLEAR, classify

    ad = parse_list(PAGE1)[0]
    ad.description = "Alternierende Telearbeit ist nach Absprache möglich."
    work = classify(ad)
    assert work.cls == UNCLEAR and work.remote_hint


def test_details_read_the_article_and_the_authority():
    calls: list = []
    ad = parse_list(PAGE1)[0]
    text = LandMV(fetch=fake_portal(calls), pause=0).details(ad)
    assert "Menü" not in text and "SQL und Python" in text and "teilzeitfähig" in text
    assert ad.employer == "Ministerium für Beispiel M-V"


class CountingSource:
    def __init__(self, name, prefix, n):
        self.name, self.prefix, self.n, self.details_calls = name, prefix, n, 0

    def search(self, term, hours, days):
        return [JobAd(id=f"{self.prefix}:{i}", title="Stelle", employer="X", place="Y",
                      published="2026-11-10" if self.prefix == "ba" else "", url="u") for i in range(self.n)]

    def details(self, ad):
        self.details_calls += 1
        return "Kein Hinweis."


def test_each_source_has_its_own_detail_budget(tmp_path, monkeypatch):
    monkeypatch.setattr(research, "MAX_DETAILS", 2)
    many, few = CountingSource("BA Jobsuche", "ba", 5), CountingSource("Land M-V", "landmv", 2)
    config = {"search": {"fields": ["Feld"], "filters": {}}}
    profile = load_profile(FIXTURES / "profile.yaml").confirmed()
    summary = research.run_research(tmp_path, [many, few], config, profile,
                                    load_vocabulary(VOCABULARY), date(2026, 11, 18))
    assert many.details_calls == 2 and few.details_calls == 2  # the dated source does not starve the other
    assert summary["checked"] == 4

from datetime import date

from careerpipe.bottleneck import LONG_ONLINE_DAYS, MIN_SUPPORT, measure, prune, record_run
from careerpipe.recommend import OPEN, recommend, stable_gap

TODAY = date(2026, 11, 18)


def entry(skills, relevant=True, published="2026-11-10", last_seen="2026-11-18"):
    return {"skills": skills, "relevant": relevant, "published": published,
            "first_seen": published, "last_seen": last_seen}


def test_profile_gap_counts_missing_skills_in_relevant_ads_only():
    seen = {
        "a": entry(["SQL", "Power BI"]),
        "b": entry(["Power BI", "Excel"]),
        "c": entry(["SAP"], relevant=False),  # not relevant: does not count
    }
    b = measure(seen, owned={"SQL"})
    assert b.relevant_ads == 2
    assert [(g.skill, g.count, g.base) for g in b.profile][0] == ("Power BI", 2, 2)
    assert "SQL" not in [g.skill for g in b.profile]
    assert "SAP" not in [g.skill for g in b.profile]


def test_market_gap_needs_support_and_long_running_ads():
    long_ad = dict(published="2026-10-01", last_seen="2026-11-18")  # 48 days online
    seen = {f"long{i}": entry(["Excel"], **long_ad) for i in range(3)}
    seen.update({f"short{i}": entry(["Excel"]) for i in range(MIN_SUPPORT - 3)})
    seen.update({"rare": entry(["Kafka"], **long_ad)})  # one ad: below the support threshold
    b = measure(seen, owned=set())
    assert b.long_ads == 4
    (excel,) = b.market
    assert excel.skill == "Excel" and excel.count == 3 and excel.base == MIN_SUPPORT


def test_overlap_lists_gaps_the_market_also_struggles_with():
    long_ad = dict(published="2026-10-01", last_seen="2026-11-18")
    seen = {f"x{i}": entry(["Excel"], **long_ad) for i in range(MIN_SUPPORT)}
    assert measure(seen, owned=set()).overlap == ["Excel"]
    assert measure(seen, owned={"Excel"}).overlap == []


def test_long_online_threshold_is_measured_from_publication():
    just_under = entry(["Excel"], published="2026-11-01", last_seen="2026-11-21")  # 20 days
    just_over = entry(["Excel"], published="2026-11-01", last_seen="2026-11-22")   # 21 days
    assert LONG_ONLINE_DAYS == 21
    assert measure({"u": just_under}, set()).long_ads == 0
    assert measure({"o": just_over}, set()).long_ads == 1


def test_prune_drops_ads_not_seen_for_the_retention_weeks():
    seen = {"old": entry([], last_seen="2026-09-01"), "fresh": entry([], last_seen="2026-11-17")}
    assert list(prune(seen, TODAY, weeks=8)) == ["fresh"]


def test_history_keeps_one_row_per_date(tmp_path):
    path = tmp_path / "verlauf.json"
    record_run(path, {"date": "2026-11-11", "top_gap": "Excel"})
    record_run(path, {"date": "2026-11-18", "top_gap": "Excel"})
    history = record_run(path, {"date": "2026-11-18", "top_gap": "SAP"})
    assert [r["date"] for r in history] == ["2026-11-11", "2026-11-18"]
    assert history[-1]["top_gap"] == "SAP"


def test_a_gap_is_stable_only_after_three_equal_runs():
    assert stable_gap([{"top_gap": "Excel"}] * 2) is None
    assert stable_gap([{"top_gap": "Excel"}, {"top_gap": "SAP"}, {"top_gap": "Excel"}]) is None
    assert stable_gap([{"top_gap": "Excel"}] * 3) == "Excel"


CATALOG = {"Excel": {"certificate": {"name": "Zertifikat X", "effort": None, "cost": None},
                     "project": {"idea": "Projekt Y", "effort": "2 Wochen"}}}


def _gaps(skill="Excel"):
    long_ad = dict(published="2026-10-01", last_seen="2026-11-18")
    return measure({f"x{i}": entry([skill], **long_ad) for i in range(MIN_SUPPORT)}, owned=set())


def test_learning_goal_brakes_every_new_recommendation():
    text = "\n".join(recommend(_gaps(), [{"top_gap": "Excel"}] * 3, "Power BI", CATALOG))
    assert "Aktives Lernziel: Power BI" in text and "Zertifikat X" not in text


def test_no_recommendation_before_the_gap_is_stable():
    text = "\n".join(recommend(_gaps(), [{"top_gap": "Excel"}], None, CATALOG))
    assert "Noch keine" in text


def test_stable_gap_shows_both_ways_and_never_invents_cost_or_effort():
    text = "\n".join(recommend(_gaps(), [{"top_gap": "Excel"}] * 3, None, CATALOG))
    assert "Zertifikat X" in text and "Projekt Y" in text
    assert "2 Wochen" in text  # given in the catalog
    assert text.count(OPEN) == 2  # certificate effort and cost were not given
    assert "5 von 5" in text


def test_a_stable_gap_without_catalog_entry_says_so():
    text = "\n".join(recommend(_gaps("Kafka"), [{"top_gap": "Kafka"}] * 3, None, CATALOG))
    assert "noch keine Option" in text

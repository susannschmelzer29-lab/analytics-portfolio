from datetime import date

from careerpipe.learning import (
    MIN_RATINGS, RATINGS, best_model, compare, compare_work_model, features, labelled, learn,
    log_change, read_ratings, regression_lost, rule, snapshot, source_proposals, title_proposals,
    update_ratings,
)

TODAY = date(2026, 11, 18)


def ad_entry(score, work="fully_remote", hint=False, text=""):
    return {"score": score, "work": work, "hint": hint, "skills": ["SQL"], "missing": 0,
            "part_time": True, "relevant": True, "text": text}


def test_new_ads_are_appended_and_the_owners_ratings_stay(tmp_path):
    path = tmp_path / RATINGS
    update_ratings(path, [{"id": "a", "stelle": "Analyst"}])
    rows = read_ratings(path)
    rows[0]["bewertung"] = "passt"
    path.write_text("id;stelle;arbeitgeber;quelle;score;arbeitsmodell;bewertung;arbeitsmodell_korrektur\n"
                    "a;Analyst;;;;;passt;\n", encoding="utf-8-sig")
    update_ratings(path, [{"id": "a", "stelle": "Analyst"}, {"id": "b", "stelle": "Prozessmanager"}])
    rows = read_ratings(path)
    assert [r["id"] for r in rows] == ["a", "b"]
    assert rows[0]["bewertung"] == "passt" and rows[1]["bewertung"] == ""


def test_labels_read_passt_beworben_and_passt_nicht_only():
    rows = [{"id": "1", "bewertung": "Passt"}, {"id": "2", "bewertung": "beworben"},
            {"id": "3", "bewertung": "passt nicht"}, {"id": "4", "bewertung": "vielleicht"}, {"id": "5"}]
    assert labelled(rows) == [("1", 1), ("2", 1), ("3", 0)]


def test_rule_is_the_wished_model_or_a_hint_and_score_at_least_50():
    assert rule(ad_entry(60, work="hybrid"), wanted="hybrid") == 1
    assert rule(ad_entry(40, work="hybrid"), wanted="hybrid") == 0
    assert rule(ad_entry(80, work="on_site"), wanted="hybrid") == 0
    assert rule(ad_entry(80, work="unclear", hint=True), wanted="hybrid") == 1
    assert rule(ad_entry(80, work="on_site")) == 1  # no wish: any clear work model counts
    assert rule(ad_entry(80, work="unclear")) == 0


def _data(n=24):
    # the owner likes part-time ads with many matching skills; the rule only looks at the score
    entries, labels = [], []
    for i in range(n):
        good = i % 2 == 0
        e = ad_entry(score=30 if good else 70)
        e["skills"] = ["SQL", "Python", "dbt"] if good else ["SQL"]
        entries.append(e)
        labels.append(int(good))
    return entries, labels


def test_comparison_reports_rule_and_both_models_and_a_model_can_win():
    entries, labels = _data()
    results = compare([features(e) for e in entries], labels, [rule(e) for e in entries])
    assert [r.name for r in results] == ["Regel", "Logistische Regression", "Entscheidungsbaum"]
    assert results[0].f1 == 0  # the rule predicts the wrong ads here
    assert best_model(results) is not None


def test_comparison_refuses_with_one_class_only():
    entries = [ad_entry(70) for _ in range(5)]
    assert isinstance(compare([features(e) for e in entries], [1] * 5, [1] * 5), str)


def test_below_the_minimum_sample_nothing_is_proposed(tmp_path):
    (tmp_path / "out").mkdir()
    seen = {"a": ad_entry(70)}
    outcome = learn(tmp_path, tmp_path / "out", seen, [{"id": "a", "stelle": "X"}], {}, 1, TODAY)
    text = "\n".join(outcome.lines)
    assert f"Vorschläge zur Bewertung ab {MIN_RATINGS}" in text and "Vorschlag:" not in text
    assert outcome.probs is None


def _rated_home(tmp_path):
    entries, labels = _data()
    seen = {f"id{i}": e for i, e in enumerate(entries)}
    lines = ["id;stelle;arbeitgeber;quelle;score;arbeitsmodell;bewertung;arbeitsmodell_korrektur"]
    lines += [f"id{i};Stelle {i};;;;;{'passt' if y else 'passt nicht'};" for i, y in enumerate(labels)]
    (tmp_path / RATINGS).write_text("\n".join(lines) + "\n", encoding="utf-8-sig")
    (tmp_path / "out").mkdir()
    return seen


def test_a_better_model_is_only_proposed_until_the_owner_switches_it_on(tmp_path):
    seen = _rated_home(tmp_path)
    offered = [{"id": k} for k in seen]
    proposed = learn(tmp_path, tmp_path / "out", seen, offered, {}, 1, TODAY)
    assert proposed.probs is None
    assert any("Vorschlag:" in line and "use_model" in line for line in proposed.lines)

    active = learn(tmp_path, tmp_path / "out", seen, offered, {"learning": {"use_model": True}}, 1, TODAY)
    assert active.probs is not None and set(active.probs) == set(seen)


def test_regression_check_names_good_matches_the_model_would_drop():
    assert regression_lost(["a", "b", "c"], ["a", "c", "d"], positives={"b", "d"}) == ["b"]
    assert regression_lost(["a"], ["a"], positives={"a"}) == []


def test_title_proposals_need_three_positive_ratings_and_skip_known_fields():
    rows = [{"stelle": "Prozessmanager (m/w/d)", "bewertung": "passt"}] * 2
    assert title_proposals(rows, ["Digitalisierung"]) == []
    rows.append({"stelle": "Prozessmanager (m/w/d)", "bewertung": "beworben"})
    assert title_proposals(rows, ["Digitalisierung"]) == [("Prozessmanager", 3)]
    assert title_proposals(rows, ["Prozessmanager"]) == []


def test_a_source_without_relevant_ads_is_proposed_for_switch_off_after_three_runs():
    seen = {"ba:1": {"relevant": True}, "indeed:2": {"relevant": False}}
    assert source_proposals(seen, ["ba", "indeed"], runs=2) == []
    assert source_proposals(seen, ["ba", "indeed"], runs=3) == ["indeed"]


def test_change_log_records_only_changes_and_keeps_the_previous_value(tmp_path):
    path = tmp_path / "aenderungen.json"
    config = {"search": {"fields": ["A"]}, "sources": ["ba"]}
    log_change(path, TODAY, snapshot(config))
    log_change(path, TODAY, snapshot(config))
    config["learning"] = {"use_model": True}
    log = log_change(path, TODAY, snapshot(config))
    assert len(log) == 2
    assert log[-1]["vorher"]["use_model"] is False and log[-1]["nachher"]["use_model"] is True


def test_work_model_corrections_are_counted_against_the_rule(tmp_path):
    seen = {"a": ad_entry(70, work="unclear"), "b": ad_entry(70, work="fully_remote")}
    (tmp_path / RATINGS).write_text(
        "id;stelle;arbeitgeber;quelle;score;arbeitsmodell;bewertung;arbeitsmodell_korrektur\n"
        "a;X;;;;;;vor Ort\nb;Y;;;;;;voll remote\n", encoding="utf-8-sig")
    (tmp_path / "out").mkdir()
    text = "\n".join(learn(tmp_path, tmp_path / "out", seen, [], {}, 1, TODAY).lines)
    assert "Arbeitsmodell-Korrekturen: 2, die Regel lag bei 1 davon falsch" in text


def test_text_classifier_comparison_runs_with_enough_corrections():
    texts = ["Vollständig remote arbeiten"] * 6 + ["Präsenz im Büro vor Ort"] * 6
    truth = ["fully_remote"] * 6 + ["on_site"] * 6
    results = compare_work_model(texts, truth, ["unclear"] * 12)
    assert [r.name for r in results] == ["Regel", "Textklassifikator"]
    assert results[1].f1 > results[0].f1

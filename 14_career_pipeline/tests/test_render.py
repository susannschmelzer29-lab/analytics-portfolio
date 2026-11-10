from careerpipe.compare import compare_profile
from careerpipe.grounding import check_grounding
from careerpipe.leak import check_leak, private_terms
from careerpipe.render import render_cv, render_linkedin


def test_the_cv_is_german_and_holds_confirmed_entries_only(profile):
    cv = render_cv(profile.confirmed())
    assert "## Berufserfahrung" in cv and "## Kompetenzen" in cv
    assert "Projektkoordinatorin" in cv
    assert "Nicht bestätigt GmbH" not in cv
    assert "Tableau" not in cv


def test_a_running_job_reads_heute(profile):
    assert "04/2018 – heute" in render_cv(profile.confirmed())


def test_the_public_cv_has_no_contact_block(profile, config):
    assert "alex@example.org" not in render_cv(profile.confirmed())
    assert "alex@example.org" in render_cv(profile.confirmed(), contact=config["contact"])


def test_generated_texts_pass_the_grounding_check(profile, vocabulary, config):
    confirmed = profile.confirmed()
    contact = list(map(str, config["contact"].values()))
    assert check_grounding(render_cv(confirmed, config["contact"]), confirmed, vocabulary, contact) == []
    for text in render_linkedin(confirmed).values():
        assert check_grounding(text, confirmed, vocabulary) == []


def test_generated_texts_pass_the_leak_test(profile, config):
    confirmed = profile.confirmed()
    assert check_leak(render_cv(confirmed, config["contact"]), private_terms(config, allow_contact=True)) == []
    for text in render_linkedin(confirmed).values():
        assert check_leak(text, private_terms(config)) == []


def test_linkedin_pins_exactly_what_the_owner_pinned(profile):
    pinned = render_linkedin(profile.confirmed())["Skills (anpinnen)"].splitlines()
    assert pinned == ["Python", "SQL"]


def test_transferable_skills_rank_after_technical_ones(profile):
    # Stakeholder-Management has the highest level, but recruiters filter on tools
    ranked = render_linkedin(profile.confirmed())["Skills (alle)"].splitlines()
    assert ranked[:2] == ["Python", "SQL"]
    assert ranked[-1] == "Stakeholder-Management"


def test_the_comparison_lists_what_linkedin_is_missing(profile):
    pasted = "Ich arbeite mit Python und SQL. Zertifikat: SQL Grundlagen."
    missing = compare_profile(pasted, profile.confirmed())
    assert ("Skill", "pandas") in missing
    assert ("Projekt", "Umsatzanalyse") in missing
    assert ("Skill", "Python") not in missing
    assert ("Zertifikat", "SQL Grundlagen") not in missing

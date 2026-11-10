import copy

import pytest

from careerpipe.profile import ProfileError, validate_profile


def test_the_fixture_profile_is_valid(raw_profile):
    assert validate_profile(raw_profile) == []


def test_only_confirmed_entries_survive(profile):
    confirmed = profile.confirmed()
    assert [s["name"] for s in confirmed.skills] == ["Python", "SQL", "pandas", "Stakeholder-Management"]
    assert [e["id"] for e in confirmed.experience] == ["verein"]


def test_an_unconfirmed_person_block_blocks_everything(raw_profile):
    from careerpipe.profile import Profile

    raw = copy.deepcopy(raw_profile)
    raw["person"]["confirmed"] = False
    with pytest.raises(ProfileError, match="person"):
        Profile(raw).confirmed()


def test_evidence_must_point_to_a_known_entry(raw_profile):
    raw = copy.deepcopy(raw_profile)
    raw["skills"][0]["evidence"] = ["p99"]
    errors = validate_profile(raw)
    assert any("p99" in e for e in errors)


def test_course_is_accepted_as_evidence(raw_profile):
    assert validate_profile(raw_profile) == []  # Tableau uses "course"


def test_level_must_be_between_one_and_four(raw_profile):
    raw = copy.deepcopy(raw_profile)
    raw["skills"][0]["level"] = 5
    assert any("level" in e for e in validate_profile(raw))


def test_dates_must_be_year_and_month(raw_profile):
    raw = copy.deepcopy(raw_profile)
    raw["experience"][0]["start"] = "April 2018"
    assert any("start" in e for e in validate_profile(raw))


def test_duplicate_ids_are_rejected(raw_profile):
    raw = copy.deepcopy(raw_profile)
    raw["projects"].append(copy.deepcopy(raw["projects"][0]))
    assert any("duplicate" in e for e in validate_profile(raw))


def test_every_entry_needs_an_explicit_confirmed_flag(raw_profile):
    raw = copy.deepcopy(raw_profile)
    del raw["skills"][0]["confirmed"]
    assert any("confirmed" in e for e in validate_profile(raw))


def test_contact_details_are_not_allowed_in_the_profile(raw_profile):
    raw = copy.deepcopy(raw_profile)
    raw["contact"] = {"phone": "0170/1234567"}
    assert any("contact" in e for e in validate_profile(raw))


def test_focus_may_only_name_skills_in_the_profile(raw_profile):
    raw = copy.deepcopy(raw_profile)
    raw["focus"] = ["Power BI"]
    assert any("focus" in e for e in validate_profile(raw))


def test_at_most_three_skills_can_be_pinned(raw_profile):
    raw = copy.deepcopy(raw_profile)
    for skill in raw["skills"]:
        skill["pin"] = True
    assert any("pinned" in e for e in validate_profile(raw))

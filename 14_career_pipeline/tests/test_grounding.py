from careerpipe.grounding import check_grounding


def codes(findings):
    return sorted(f.code for f in findings)


def test_a_text_built_from_the_profile_is_grounded(profile, vocabulary):
    text = "Data Analyst mit 7 Jahren Erfahrung. Python, pandas und SQL. Umsatzanalyse von 2.000 Bestellungen."
    assert check_grounding(text, profile.confirmed(), vocabulary) == []


def test_a_planted_invented_skill_fails(profile, vocabulary):
    # the canary of the grounding check: Power BI is in no profile entry
    findings = check_grounding("Erfahrung mit Python und Power BI.", profile.confirmed(), vocabulary)
    assert codes(findings) == ["UNGROUNDED_SKILL"]
    assert "Power BI" in findings[0].text


def test_an_unconfirmed_skill_counts_as_invented(profile, vocabulary):
    # Tableau is in the draft, but not confirmed
    findings = check_grounding("Dashboards mit Tableau.", profile.confirmed(), vocabulary)
    assert codes(findings) == ["UNGROUNDED_SKILL"]


def test_aliases_map_to_the_canonical_skill(profile, vocabulary):
    findings = check_grounding("Cloud mit Amazon Web Services.", profile.confirmed(), vocabulary)
    assert "AWS" in findings[0].text


def test_a_skill_named_only_in_a_certificate_is_grounded(profile, vocabulary):
    # Excel appears in the confirmed certificate's details
    assert check_grounding("SQL und Excel.", profile.confirmed(), vocabulary) == []


def test_an_invented_number_fails(profile, vocabulary):
    findings = check_grounding("Data Analyst mit 10 Jahren Erfahrung.", profile.confirmed(), vocabulary)
    assert codes(findings) == ["UNGROUNDED_NUMBER"]


def test_numbers_from_extra_sources_are_allowed(profile, vocabulary):
    text = "Telefon 0170/1234567"
    assert check_grounding(text, profile.confirmed(), vocabulary) != []
    assert check_grounding(text, profile.confirmed(), vocabulary, extra_sources=["0170/1234567"]) == []


def test_a_skill_inside_another_word_is_not_a_hit(profile, vocabulary):
    # "Git" must not fire on "GitHub" links or the word "digital"
    assert check_grounding("digitale Prozesse, siehe github.com/example", profile.confirmed(), vocabulary) == []


def test_a_month_inside_a_date_does_not_ground_a_bare_number(profile, vocabulary):
    # the profile holds 2011-10; that must not make "10 Jahre" look grounded
    assert check_grounding("10 Jahre", profile.confirmed(), vocabulary)
    assert check_grounding("seit 04/2018", profile.confirmed(), vocabulary) == []

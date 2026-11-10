import pytest

from careerpipe.leak import LeakCanaryError, check_leak, private_terms, run_canary


def test_filter_terms_are_caught(config):
    findings = check_leak("Ich suche eine Stelle mit Gleitzeit.", private_terms(config))
    assert [f.code for f in findings] == ["PRIVATE_TERM"]


def test_matching_ignores_case_and_catches_compounds(config):
    assert check_leak("DIENSTWAGEN gewünscht", private_terms(config))


def test_german_compounds_are_caught(config):
    terms = private_terms(config)
    assert check_leak("Gleitzeitmodell gewünscht", terms)
    assert check_leak("Die Dienstwagenregelung", terms)


def test_a_term_in_the_middle_of_a_word_is_not_a_hit(config):
    # a term counts at a word start only; "Firmendienstwagen" stays a different word
    assert check_leak("Firmendienstwagen", private_terms(config)) == []


def test_company_names_from_the_application_folder_are_caught(config):
    findings = check_leak("Erfahrung bei Acme Logistik", private_terms(config))
    assert findings and "Acme Logistik" in findings[0].text


def test_terms_with_dots_are_matched_literally(config):
    terms = private_terms(config)
    assert check_leak("beispiel.werke", terms)
    assert check_leak("beispielXwerke", terms) == []


def test_public_terms_are_allowed(config):
    # the current employer is in the CV, even if it is also an application folder
    assert check_leak("Projektkoordinatorin im Beispielverein", private_terms(config)) == []


def test_contact_details_are_private_by_default(config):
    assert check_leak("Mail: alex@example.org", private_terms(config))


def test_contact_details_are_allowed_in_the_cv(config):
    terms = private_terms(config, allow_contact=True)
    assert check_leak("Mail: alex@example.org", terms) == []
    assert check_leak("Gleitzeit", terms)  # filters stay private even in the CV


def test_the_application_folder_path_is_private(config):
    assert check_leak("Quelle: C:/Users/example/Bewerbungen", private_terms(config))


def test_the_canary_passes_with_a_working_matcher(config):
    run_canary(private_terms(config))


def test_the_canary_fails_when_the_matcher_is_blind(config, monkeypatch):
    import careerpipe.leak as leak

    monkeypatch.setattr(leak, "check_leak", lambda text, terms: [])
    with pytest.raises(LeakCanaryError):
        leak.run_canary(private_terms(config))


def test_an_empty_term_list_fails_the_canary():
    # no terms means a misconfigured private config, not a clean output
    with pytest.raises(LeakCanaryError):
        run_canary([])

import pytest

from careerpipe.grounding import check_grounding
from careerpipe.leak import check_leak, private_terms
from careerpipe.pdf import find_browser, html_text, html_to_pdf, render_cv_html


def test_the_html_cv_holds_the_german_sections(profile):
    page = render_cv_html(profile.confirmed())
    for heading in ["Profil", "Berufserfahrung", "Projekte (Portfolio)", "Aus- und Weiterbildung", "Kompetenzen", "Sprachen"]:
        assert f"<h2>{heading}</h2>" in page
    assert "Nicht bestätigt GmbH" not in page


def test_text_is_escaped(profile):
    confirmed = profile.confirmed()
    confirmed.raw["summary"]["text"] = "Daten <script>alert(1)</script> & Prozesse"
    page = render_cv_html(confirmed)
    assert "<script>" not in page
    assert "&lt;script&gt;" in page


def test_the_checks_see_the_visible_text_not_the_css(profile):
    text = html_text(render_cv_html(profile.confirmed()))
    assert "Projektkoordinatorin" in text
    assert "font-size" not in text and "A4" not in text  # CSS numbers must not reach the grounding check


def test_the_html_cv_passes_both_checks(profile, vocabulary, config):
    confirmed = profile.confirmed()
    contact = [str(v) for v in config["contact"].values()]
    text = html_text(render_cv_html(confirmed, config["contact"]))
    assert check_grounding(text, confirmed, vocabulary, contact) == []
    assert check_leak(text, private_terms(config, allow_contact=True)) == []


def test_no_heading_is_left_alone_at_a_page_end(profile):
    page = render_cv_html(profile.confirmed())
    assert "<div class='keep'><h2>Aus- und Weiterbildung</h2><div class='entry'>" in page


def test_headings_have_no_letter_spacing(profile):
    # spaced letters come out as "P R O F I L" when an applicant system reads the PDF
    assert "letter-spacing" not in render_cv_html(profile.confirmed())


def test_links_are_shown_without_protocol(profile):
    page = render_cv_html(profile.confirmed())
    assert "github.com/example/portfolio" in page and "https://github.com" not in page


def test_contact_appears_only_when_handed_in(profile, config):
    assert "alex@example.org" not in render_cv_html(profile.confirmed())
    assert "alex@example.org" in render_cv_html(profile.confirmed(), config["contact"])


def test_a_configured_browser_that_does_not_exist_means_no_browser(monkeypatch, tmp_path):
    monkeypatch.setenv("CAREERPIPE_BROWSER", str(tmp_path / "nope.exe"))
    assert find_browser() is None


def test_the_pdf_is_printed_when_a_browser_is_available(profile, tmp_path, monkeypatch):
    monkeypatch.delenv("CAREERPIPE_BROWSER", raising=False)
    browser = find_browser()
    if browser is None:
        pytest.skip("no Edge or Chrome on this machine")
    page = tmp_path / "cv.html"
    page.write_text(render_cv_html(profile.confirmed()), encoding="utf-8")
    pdf = html_to_pdf(page, tmp_path / "cv.pdf", browser)
    assert pdf.read_bytes()[:5] == b"%PDF-"

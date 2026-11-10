"""The CV as print-ready HTML and as PDF.

The PDF is printed by a locally installed Chromium browser (Edge or Chrome) in
headless mode, so no PDF library is needed. The HTML comes from the same
confirmed profile as the Markdown CV, and its visible text goes through the
same leak test and grounding check before anything is written.
"""

from __future__ import annotations

import html
import os
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from careerpipe.profile import Profile
from careerpipe.render import _month, _period, _skills_by_category

BROWSER_CANDIDATES = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
]
BROWSER_NAMES = ["msedge", "google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome"]

STYLE = """
@page { size: A4; margin: 16mm 17mm 16mm 17mm; }
* { box-sizing: border-box; }
body { font-family: "Segoe UI", Calibri, Arial, sans-serif; font-size: 9.6pt;
       line-height: 1.42; color: #1f2328; margin: 0; }
header { border-bottom: 2px solid #1f4e79; padding-bottom: 8pt; margin-bottom: 10pt; }
h1 { font-size: 22pt; font-weight: 600; margin: 0; color: #12263a; }
.headline { font-size: 11pt; color: #1f4e79; margin: 2pt 0 6pt; font-weight: 600; }
.meta { font-size: 8.6pt; color: #4b5563; }
.meta span { white-space: nowrap; }
.meta span + span::before { content: "·"; margin: 0 6pt; color: #9ca3af; }
.meta + .meta { margin-top: 1pt; }
h2 { font-size: 10.5pt; font-weight: 700; color: #1f4e79;
     border-bottom: 0.6pt solid #c9d6e3; padding-bottom: 2pt; margin: 12pt 0 6pt; }
.keep { break-inside: avoid; page-break-inside: avoid; }
p { margin: 0 0 4pt; }
.entry { margin-bottom: 7pt; break-inside: avoid; }
.row { display: flex; justify-content: space-between; gap: 12pt; }
.title { font-weight: 600; }
.org { color: #374151; }
.when { color: #6b7280; white-space: nowrap; font-size: 8.8pt; }
ul { margin: 2pt 0 0; padding-left: 13pt; }
li { margin: 0 0 1.5pt; }
.projects li { margin-bottom: 3pt; }
.skills { display: grid; grid-template-columns: 34% 66%; row-gap: 3pt; }
.skills .cat { font-weight: 600; color: #374151; padding-right: 8pt; }
a { color: inherit; text-decoration: none; }
"""


def _e(value) -> str:
    return html.escape(str(value))


def _short_link(url: str) -> str:
    """github.com/... instead of https://www.github.com/...: shorter, same address."""
    return re.sub(r"^https?://(www\.)?", "", str(url)).rstrip("/")


def _section(heading: str, blocks: list[str]) -> list[str]:
    """A heading glued to its first block, so a page never ends with a lone heading."""
    if not blocks:
        return []
    return [f"<div class='keep'><h2>{_e(heading)}</h2>{blocks[0]}</div>", *blocks[1:]]


def _entry(title: str, org: str, when: str, items) -> str:
    bullets = "".join(f"<li>{_e(i)}</li>" for i in items or [])
    return (
        "<div class='entry'><div class='row'>"
        f"<div><span class='title'>{_e(title)}</span> · <span class='org'>{_e(org)}</span></div>"
        f"<div class='when'>{_e(when)}</div></div>"
        + (f"<ul>{bullets}</ul>" if bullets else "")
        + "</div>"
    )


def render_cv_html(profile: Profile, contact: dict | None = None) -> str:
    """The CV as a standalone HTML page for printing. Contact only when handed in."""
    p = profile
    contact_line = "".join(f"<span>{_e(v)}</span>" for v in (contact or {}).values() if v)
    link_line = "".join(f"<span>{_e(_short_link(v))}</span>" for v in p.links.values() if v)
    out = [
        "<!doctype html><html lang='de'><head><meta charset='utf-8'>",
        f"<title>Lebenslauf {_e(p.person['name'])}</title><style>{STYLE}</style></head><body>",
        "<header>",
        f"<h1>{_e(p.person['name'])}</h1>",
        f"<div class='headline'>{_e(p.person['headline'])}</div>",
        f"<div class='meta'>{contact_line}</div>" if contact_line else "",
        f"<div class='meta'>{link_line}</div>" if link_line else "",
        "</header>",
    ]
    out += _section("Profil", [f"<p>{_e(p.summary['text'].strip())}</p>"])
    out += _section("Berufserfahrung", [
        _entry(e["role"], e["organisation"], _period(e), e.get("highlights")) for e in p.experience
    ])
    out += _section("Projekte (Portfolio)", [
        f"<ul class='projects'><li><span class='title'>{_e(pr['title'])}:</span> {_e(pr['pitch'])}</li></ul>"
        for pr in p.projects
    ])
    out += _section("Aus- und Weiterbildung", [
        _entry(c["title"], c["issuer"], _month(c["date"]), c.get("details")) for c in p.certificates
    ] + [
        _entry(ed["title"], ed["institution"], _period(ed), ed.get("details")) for ed in p.education
    ])
    if p.skills:
        rows = "".join(
            f"<div class='cat'>{_e(category)}</div><div>{_e(' · '.join(names))}</div>"
            for category, names in _skills_by_category(p).items()
        )
        out += _section("Kompetenzen", [f"<div class='skills'>{rows}</div>"])
    if p.languages:
        langs = " · ".join(f"{l['name']} ({l['level']})" for l in p.languages)
        out += _section("Sprachen", [f"<p>{_e(langs)}</p>"])

    out.append("</body></html>")
    return "\n".join(x for x in out if x)


def html_text(page: str) -> str:
    """The visible text of a page: what the checks must see, without CSS."""
    page = re.sub(r"<(style|script)\b.*?</\1>", " ", page, flags=re.S | re.I)
    page = re.sub(r"<title>.*?</title>", " ", page, flags=re.S | re.I)
    page = re.sub(r"<[^>]+>", " ", page)
    return re.sub(r"\s+", " ", html.unescape(page)).strip()


def find_browser() -> str | None:
    """A local Chromium browser for printing, or None. CAREERPIPE_BROWSER wins."""
    configured = os.environ.get("CAREERPIPE_BROWSER")
    if configured:
        return configured if Path(configured).exists() else None
    for candidate in BROWSER_CANDIDATES:
        if Path(candidate).exists():
            return candidate
    for name in BROWSER_NAMES:
        found = shutil.which(name)
        if found:
            return found
    return None


def _wait_for_file(path: Path, timeout: float) -> bool:
    """Wait until the file exists and its size has stopped changing."""
    deadline, last = time.monotonic() + timeout, -1
    while time.monotonic() < deadline:
        size = path.stat().st_size if path.exists() else -1
        if size > 0 and size == last:
            return True
        last = size
        time.sleep(0.5)
    return False


def html_to_pdf(html_path: Path, pdf_path: Path, browser: str, timeout: int = 60) -> Path:
    """Print the HTML file to PDF with a headless browser. Raises if no PDF appears.

    The browser gets its own throw-away profile. Without one, Edge hands the job
    to an already running window and returns at once, before the PDF exists.
    """
    html_path, pdf_path = Path(html_path).resolve(), Path(pdf_path).resolve()
    if pdf_path.exists():
        pdf_path.unlink()
    with tempfile.TemporaryDirectory(prefix="careerpipe-browser-") as profile_dir:
        subprocess.run(
            [
                browser,
                "--headless=new",
                "--disable-gpu",
                "--no-first-run",
                "--no-default-browser-check",
                "--no-pdf-header-footer",
                f"--user-data-dir={profile_dir}",
                f"--print-to-pdf={pdf_path}",
                html_path.as_uri(),
            ],
            check=False,
            capture_output=True,
            timeout=timeout,
        )
        ready = _wait_for_file(pdf_path, timeout=30)
    if not ready:
        raise RuntimeError("the browser did not produce a PDF")
    return pdf_path

"""Source: the career portal of the Mecklenburg-Vorpommern state administration
(karriere-in-mv.de). All state authorities, ministries included, post there.

The portal has no API, but plain server-rendered pages and a robots.txt that
allows every path. A search is one form POST; the results then page through
/suche/seite-N within the same session (cookie). Each ad has a stable link
stelle/<id>-<slug>, and its detail page holds the full text in <article>.

Choices:
- The portal's own working-hours filter is not used. Many ads read
  "Vollzeit, teilzeitfähig" and would drop out under "Teilzeit"; part-time is
  read from the text instead, as for the job boards.
- The portal shows no publication date, only deadlines, so the day window does
  not apply here. Ads are deduplicated by their id, and the market bottleneck
  falls back to the date an ad was first seen.
- A field with several words is also searched word by word (words of six
  letters or more), because the portal's keyword search is strict.
- At most `max_pages` pages per search word, with a pause between requests.
"""

from __future__ import annotations

import http.cookiejar
import re
import time
import urllib.parse
import urllib.request
from typing import Callable

from careerpipe.apifysource import _text
from careerpipe.jobsource import JobAd

BASE = "https://karriere-in-mv.de"
Fetch = Callable[[str, str, dict | None], str]  # (method, url, form data) -> page html

LINK = re.compile(r'<a[^>]+href="/?stelle/(\d+)-([^"?#]+)"[^>]*>(.*?)</a>', re.IGNORECASE | re.DOTALL)
ARTICLE = re.compile(r"<article[^>]*>(.*?)</article>", re.IGNORECASE | re.DOTALL)
AUTHORITY = re.compile(r"Behörde:\s*(.+?)(?:\s+(?:Herr|Frau|Tel\.|Ansprechperson|E-Mail|Lage|Bewerben)\b|$)")
TITLE_PLACE = re.compile(r"^(.*?)\s+-\s+in\s+(.+)$")


class Session:
    """A tiny browser session: cookies kept between requests, nothing else."""

    def __init__(self):
        jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))

    def __call__(self, method: str, url: str, data: dict | None = None) -> str:
        body = urllib.parse.urlencode(data).encode("utf-8") if data else None
        request = urllib.request.Request(url, data=body, method=method, headers={"User-Agent": "careerpipe"})
        with self.opener.open(request, timeout=30) as response:
            return response.read().decode("utf-8", "replace")


def search_words(term: str) -> list[str]:
    words = [w for w in re.split(r"[\s/,]+", term) if len(w) >= 6 and w != term]
    return [term] + words if " " in term.strip() else [term]


def parse_list(page: str) -> list[JobAd]:
    ads: dict[str, JobAd] = {}
    for sid, slug, inner in LINK.findall(page):
        label = _text(inner)
        if not label or label.lower() == "details" or f"landmv:{sid}" in ads:
            continue
        found = TITLE_PLACE.match(label)
        title, place = (found.group(1), found.group(2)) if found else (label, "Mecklenburg-Vorpommern")
        ads[f"landmv:{sid}"] = JobAd(
            id=f"landmv:{sid}", title=title, employer="Landesverwaltung M-V", place=place,
            published="", url=f"{BASE}/stelle/{sid}-{slug}",
        )
    return list(ads.values())


class LandMV:
    name = "Land M-V"

    def __init__(self, fetch: Fetch | None = None, max_pages: int = 5, pause: float = 0.5):
        self.fetch = fetch or Session()
        self.max_pages = max_pages
        self.pause = pause

    def search(self, term: str, hours: str | None, days: int) -> list[JobAd]:
        # hours and days are not applied, see the module docstring
        found: dict[str, JobAd] = {}
        for word in search_words(term):
            self.fetch("POST", f"{BASE}/suche", {"type": "stelle", "sword": word})
            for page in range(1, self.max_pages + 1):
                new = [ad for ad in parse_list(self.fetch("GET", f"{BASE}/suche/seite-{page}", None))
                       if ad.id not in found]
                if not new:
                    break  # past the last page, the portal repeats it or shows nothing
                found.update((ad.id, ad) for ad in new)
                time.sleep(self.pause)
        return list(found.values())

    def details(self, ad: JobAd) -> str:
        page = self.fetch("GET", ad.url, None)
        time.sleep(self.pause)
        article = ARTICLE.search(page)
        text = _text(article.group(1) if article else page)
        authority = AUTHORITY.search(text)
        if authority:
            ad.employer = authority.group(1).strip()
        return text

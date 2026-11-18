"""Job sources behind one interface. First source: the Jobsuche API of the
Bundesagentur für Arbeit (BA).

A source answers two questions: which ads match a search term, and what an
ad says in full. Everything after that (work model, match, report) works on
JobAd and does not care where an ad came from. A further source only has to
fill the same fields.

The network sits behind a transport function (url, headers) -> bytes, so the
tests run offline on recorded responses.
"""

from __future__ import annotations

import base64
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Callable, Protocol

Transport = Callable[[str, dict], bytes]

BA_SEARCH = "https://rest.arbeitsagentur.de/jobboerse/jobsuche-service/pc/v6/jobs"
# The search runs on v6; the full text comes from v4 (v6 details answer 403 here).
BA_DETAILS = "https://rest.arbeitsagentur.de/jobboerse/jobsuche-service/pc/v4/jobdetails/"
BA_AD_PAGE = "https://www.arbeitsagentur.de/jobsuche/jobdetail/"
# The public client key the Jobsuche website itself uses. It is not a secret.
BA_PUBLIC_KEY = "jobboerse-jobsuche"
HOURS_PARAM = {"part_time": "tz", "full_time": "vz"}
RETRY_CODES = (429, 500, 502, 503, 504)


@dataclass
class JobAd:
    id: str
    title: str
    employer: str
    place: str
    published: str
    url: str
    home_office: bool | None = None
    home_office_type: str | None = None
    home_office_percent: int | None = None
    description: str = ""


class JobSource(Protocol):
    name: str

    def search(self, term: str, hours: str | None, days: int) -> list[JobAd]: ...

    def details(self, ad: JobAd) -> str: ...


def http_get(url: str, headers: dict) -> bytes:
    request = urllib.request.Request(url, headers=headers)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return response.read()
        except urllib.error.HTTPError as exc:
            if exc.code not in RETRY_CODES or attempt == 2:
                raise
        except urllib.error.URLError:
            if attempt == 2:
                raise
        time.sleep(2 * (attempt + 1))
    raise RuntimeError("unreachable")


def _places(item: dict) -> str:
    places: list[str] = []
    for loc in item.get("stellenlokationen") or []:
        town = (loc.get("adresse") or {}).get("ort")
        if town and town not in places:
            places.append(town)
    return ", ".join(places) or "ohne Ortsangabe"


class BAJobsuche:
    name = "BA Jobsuche"

    def __init__(self, transport: Transport = http_get, page_size: int = 100,
                 max_pages: int = 2, pause: float = 0.3):
        self.transport = transport
        self.page_size = page_size
        self.max_pages = max_pages
        self.pause = pause
        self.headers = {"X-API-Key": BA_PUBLIC_KEY, "User-Agent": "careerpipe"}

    def _get_json(self, url: str) -> dict:
        return json.loads(self.transport(url, self.headers).decode("utf-8"))

    def search(self, term: str, hours: str | None, days: int) -> list[JobAd]:
        ads: list[JobAd] = []
        for page in range(1, self.max_pages + 1):
            params = {"was": term, "angebotsart": 1, "veroeffentlichtseit": days,
                      "size": self.page_size, "page": page}
            if hours in HOURS_PARAM:
                params["arbeitszeit"] = HOURS_PARAM[hours]
            data = self._get_json(f"{BA_SEARCH}?{urllib.parse.urlencode(params)}")
            items = data.get("ergebnisliste") or []
            ads.extend(self._ad(item) for item in items)
            if len(items) < self.page_size or page * self.page_size >= (data.get("maxErgebnisse") or 0):
                break
            time.sleep(self.pause)
        return ads

    def _ad(self, item: dict) -> JobAd:
        ref = item["referenznummer"]
        return JobAd(
            id=f"ba:{ref}",
            title=item.get("stellenangebotsTitel") or item.get("hauptberuf") or "ohne Titel",
            employer=item.get("firma") or "ohne Angabe",
            place=_places(item),
            published=item.get("datumErsteVeroeffentlichung") or "",
            url=BA_AD_PAGE + ref,
            home_office=item.get("homeofficemoeglich"),
            home_office_type=item.get("homeofficetyp"),
            home_office_percent=item.get("homeofficeprozent"),
        )

    def details(self, ad: JobAd) -> str:
        ref = ad.id.removeprefix("ba:")
        encoded = base64.b64encode(ref.encode("utf-8")).decode("ascii")
        data = self._get_json(BA_DETAILS + encoded)
        time.sleep(self.pause)
        return data.get("stellenangebotsBeschreibung") or ""

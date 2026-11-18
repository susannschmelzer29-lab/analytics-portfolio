"""Job boards read through Apify actors.

Apify runs the scraper on its own servers. This module starts an actor over
the REST API and reads the rows it produces. Each board has a small mapping
from its row layout to JobAd, and rows that do not fit are skipped.

The token comes from the environment variable APIFY_TOKEN, never from a file
in the repository. Apify bills per result, and the `limit` per search caps the
results per term.

Limits of this mapping: the boards are not filtered for part-time work, so
the hours filter applies to the Arbeitsagentur source only. Work model comes
from the ad text, or from the board's own remote flag where it has one.
"""

from __future__ import annotations

import html
import json
import re
import urllib.request
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Callable

from careerpipe.jobsource import JobAd

APIFY_RUN = "https://api.apify.com/v2/acts/{actor}/run-sync-get-dataset-items"
TOKEN_ENV = "APIFY_TOKEN"
GERMANY_OK = ("world", "anywhere", "europe", "europa", "germany", "deutschland", "eu")

PostTransport = Callable[[str, dict, dict], bytes]


def http_post(url: str, headers: dict, body: dict) -> bytes:
    data = json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        url, data=data, method="POST",
        headers={**headers, "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=300) as response:
        return response.read()


def _pick(row: dict, path: str):
    """A field by dotted path, whether the row is flat ("a.b") or nested."""
    if path in row:
        return row[path]
    value = row
    for part in path.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value


BLOCK_TAG = re.compile(r"</?(?:p|li|ul|ol|div|h\d|br)\b[^>]*>", re.IGNORECASE)


def _text(fragment: object) -> str:
    spaced = BLOCK_TAG.sub(" ", str(fragment or ""))  # paragraphs and list items become spaces
    plain = re.sub(r"<[^>]+>", "", spaced)            # inline tags vanish without a space
    return re.sub(r"\s+", " ", html.unescape(plain)).strip()


def _day(value: object) -> str:
    return str(value or "")[:10]


def _stepstone(row: dict) -> JobAd | None:
    if _pick(row, "id") is None:
        return None
    sections = _pick(row, "textSections") or []
    description = " ".join(_text(s.get("content")) for s in sections if isinstance(s, dict))
    return JobAd(
        id=f"stepstone:{_pick(row, 'id')}",
        title=_pick(row, "title") or "ohne Titel",
        employer=_pick(row, "company.name") or "ohne Angabe",
        place=_pick(row, "location.location") or "ohne Ortsangabe",
        published=_day(_pick(row, "datePosted")),
        url=_pick(row, "url") or "",
        description=description or _text(_pick(row, "textSnippet")),
    )


def _indeed(row: dict) -> JobAd | None:
    key = _pick(row, "key")
    if not key:
        return None
    return JobAd(
        id=f"indeed:{key}",
        title=_pick(row, "title") or "ohne Titel",
        employer=_pick(row, "employer.name") or "ohne Angabe",
        place=_pick(row, "location.city") or "ohne Ortsangabe",
        published=_day(_pick(row, "datePublished")),
        url=_pick(row, "jobUrl") or "",
        description=_text(_pick(row, "description.text")),
    )


def _wwr(row: dict) -> JobAd | None:
    rid = _pick(row, "id")
    place = str(_pick(row, "location") or "")
    if not rid or not any(word in place.lower() for word in GERMANY_OK):
        return None  # "USA only" and similar: not open to the owner
    remote = str(_pick(row, "work_mode") or "").lower() == "remote"
    return JobAd(
        id=f"wwr:{str(rid).rsplit('/', 1)[-1]}",
        title=_pick(row, "title") or "ohne Titel",
        employer=_pick(row, "company_name") or "ohne Angabe",
        place=place or "ohne Ortsangabe",
        published=_day(_pick(row, "posted_at")),
        url=_pick(row, "apply_url") or _pick(row, "source_url") or str(rid),
        description=_text(_pick(row, "description")),
        home_office=True if remote else None,
        home_office_percent=100 if remote else None,
    )


@dataclass(frozen=True)
class Board:
    name: str
    actor: str
    build_input: Callable[[str, str, int], dict]
    to_ad: Callable[[dict], JobAd | None]


BOARDS = {
    "stepstone": Board(
        "stepstone", "valig/stepstone-jobs-scraper",
        lambda term, place, limit: {"keywords": term, "location": place, "limit": limit},
        _stepstone,
    ),
    "indeed": Board(
        "indeed", "valig/indeed-jobs-scraper",
        lambda term, place, limit: {"country": "de", "title": term, "location": place, "limit": limit},
        _indeed,
    ),
    "wwr": Board(
        "wwr", "inlifeprojects/weworkremotely-jobs-scraper",
        lambda term, place, limit: {"countryName": "Germany", "locationName": "Remote",
                                    "pagesToFetch": 1, "keywordFilter": term, "maxResults": limit},
        _wwr,
    ),
}


LABELS = {"stepstone": "StepStone", "indeed": "Indeed", "wwr": "We Work Remotely"}


class ApifyBoard:
    """One job board, read through its Apify actor. Satisfies JobSource."""

    def __init__(self, board: Board, token: str, place: str = "Deutschland",
                 limit: int = 30, transport: PostTransport = http_post):
        self.board = board
        self.name = LABELS[board.name]
        self.place = place
        self.limit = limit
        self.transport = transport
        self.headers = {"Authorization": f"Bearer {token}"}

    def search(self, term: str, hours: str | None, days: int) -> list[JobAd]:
        # hours is deliberately not applied: these boards have no part-time filter
        url = APIFY_RUN.format(actor=self.board.actor.replace("/", "~"))
        body = self.board.build_input(term, self.place, self.limit)
        rows = json.loads(self.transport(url, self.headers, body).decode("utf-8"))
        cutoff = (date.today() - timedelta(days=days)).isoformat()
        ads = []
        for row in rows if isinstance(rows, list) else []:
            ad = self.board.to_ad(row)
            if ad is None or (ad.published and ad.published < cutoff):
                continue
            ads.append(ad)
        return ads

    def details(self, ad: JobAd) -> str:
        return ad.description  # the search rows already carry the full text


def apify_sources(names: list[str], token: str, place: str, limit: int = 30,
                  transport: PostTransport = http_post) -> list[ApifyBoard]:
    unknown = [n for n in names if n not in BOARDS]
    if unknown:
        raise ValueError(f"unknown job board: {', '.join(unknown)}")
    return [ApifyBoard(BOARDS[n], token, place, limit, transport) for n in names]

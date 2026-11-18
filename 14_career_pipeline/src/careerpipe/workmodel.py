"""Work-model check: fully remote, hybrid, on-site, or unclear.

Rules, no model. A share stated by the source comes first, then the text of
the ad. If the signals contradict each other, or say nothing, the answer is
*unclear*: such an ad is flagged for the owner, never silently dropped.

Every result carries its reason, so a wrong call can be traced and turned
into a fixed test case.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from careerpipe.jobsource import JobAd

FULLY_REMOTE = "fully_remote"
HYBRID = "hybrid"
ON_SITE = "on_site"
UNCLEAR = "unclear"
ALL_CLASSES = {FULLY_REMOTE, HYBRID, ON_SITE, UNCLEAR}
LABELS = {FULLY_REMOTE: "voll remote", HYBRID: "hybrid", ON_SITE: "vor Ort", UNCLEAR: "unklar"}

FULLY_REMOTE_TEXT = [
    r"100\s*%\s*(?:remote|homeoffice|home[- ]office)",
    r"full[- ]?remote",
    r"remote[- ]first",
    r"vollständig\s+(?:remote|im\s+homeoffice)",
    r"ausschließlich\s+(?:im\s+)?(?:homeoffice|remote)",
]
HYBRID_TEXT = [
    r"\bhybrid",
    r"\b\d{1,2}\s*%\s*(?:im\s+)?(?:homeoffice|remote)",
    r"\b\d\s*tage?\s+(?:pro\s+woche\s+)?(?:im\s+)?(?:homeoffice|remote)",
]
# Home office is possible, but the ad gives no share: worth a question, not a match.
HOME_OFFICE_POSSIBLE_TEXT = [
    r"mobile[sn]?\s+arbeit(?:en)?",
    r"home[- ]?office[- ]?(?:möglichkeit|option|anteil|regelung)",
    r"(?:homeoffice|home[- ]office|remote)[^.\n]{0,30}möglich",
    r"möglichkeit\s+(?:zum|zur|für|zu)\s+(?:mobilen\s+arbeit\w*|homeoffice|remote)",
    r"teilweise\s+remote",
    r"flexible[rns]?\s+arbeitsort",
    r"(?:alternierende[rn]?\s+)?telearbeit",  # the public-sector word for home office
    r"ortsflexib\w*",
]
ON_SITE_TEXT = [
    r"ausschließlich\s+vor\s+ort",
    r"präsenz(?:pflicht|arbeit|stelle)",
    r"kein(?:e)?\s+(?:homeoffice|remote)",
]

# Which classes pass a wanted work model. Unclear always passes: it is flagged
# for a look, never dropped. An unknown or empty wish lets everything through.
PASSES = {
    FULLY_REMOTE: {FULLY_REMOTE, UNCLEAR},
    HYBRID: {FULLY_REMOTE, HYBRID, UNCLEAR},
}


@dataclass(frozen=True)
class WorkModel:
    cls: str
    reason: str
    remote_hint: bool = False  # unclear, but the ad or the source mentions home office

    @property
    def label(self) -> str:
        return LABELS[self.cls]


def _hit(patterns: list[str], text: str) -> str | None:
    for pattern in patterns:
        found = re.search(pattern, text, re.IGNORECASE)
        if found:
            return found.group(0)
    return None


def classify(ad: JobAd) -> WorkModel:
    if ad.home_office_percent is not None:
        if ad.home_office_percent >= 100:
            return WorkModel(FULLY_REMOTE, "Quelle: Homeoffice 100 %")
        if ad.home_office_percent > 0:
            return WorkModel(HYBRID, f"Quelle: Homeoffice {ad.home_office_percent} %")

    text = f"{ad.title}\n{ad.description}"
    full = _hit(FULLY_REMOTE_TEXT, text)
    hybrid = _hit(HYBRID_TEXT, text)
    on_site = _hit(ON_SITE_TEXT, text)

    if full:
        if on_site or ad.home_office is False:
            other = f"Text „{on_site}“" if on_site else "Quelle: kein Homeoffice"
            return WorkModel(UNCLEAR, f"widersprüchlich: Text „{full}“ gegen {other}", remote_hint=True)
        return WorkModel(FULLY_REMOTE, f"Text: „{full}“")
    if hybrid:
        return WorkModel(HYBRID, f"Text: „{hybrid}“")
    if ad.home_office is False:
        return WorkModel(ON_SITE, "Quelle: kein Homeoffice")
    if on_site:
        return WorkModel(ON_SITE, f"Text: „{on_site}“")
    possible = _hit(HOME_OFFICE_POSSIBLE_TEXT, text)
    if possible:
        return WorkModel(UNCLEAR, f"Homeoffice möglich, Umfang offen (Text: „{possible}“)", remote_hint=True)
    if ad.home_office_type == "NACH_VEREINBARUNG":
        return WorkModel(UNCLEAR, "Homeoffice nach Vereinbarung, Umfang offen (Quelle)", remote_hint=True)
    if ad.home_office:
        return WorkModel(UNCLEAR, "Homeoffice möglich, Umfang offen (Quelle)", remote_hint=True)
    if not ad.description:
        return WorkModel(UNCLEAR, "kein Anzeigentext abrufbar")
    return WorkModel(UNCLEAR, "keine Angabe zum Arbeitsort im Text")


def passes(work: WorkModel, wanted: str | None) -> bool:
    return work.cls in PASSES.get(wanted or "", ALL_CLASSES)

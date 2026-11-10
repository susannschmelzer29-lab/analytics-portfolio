"""Grounding check: a generated text adds no facts.

Two kinds of claim are checked in code, without a model:
- skills: every known skill term in the text must also occur in the confirmed
  profile (skills, project skills, certificate details ...);
- numbers: every number in the text must occur in the confirmed profile or in
  an extra source handed in (for example the contact block of the CV).

The language model may word a text. It may not add a skill or a figure.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from careerpipe.findings import Finding
from careerpipe.profile import Profile

NUMBER = re.compile(r"\d+(?:[.,/]\d+)*")
ISO_MONTH = re.compile(r"\b(\d{4})-(\d{2})\b")


def _numbers(text: str) -> set[str]:
    """Number tokens; a profile date YYYY-MM counts as MM/YYYY and YYYY, never as a bare month."""
    dates = ISO_MONTH.findall(text)
    found = set(NUMBER.findall(ISO_MONTH.sub(" ", text)))
    for year, month in dates:
        found |= {f"{month}/{year}", year}
    return found


def load_vocabulary(path: str | Path) -> dict[str, str]:
    """Map every spelling (canonical and alias) to its canonical name."""
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))["terms"]
    vocab: dict[str, str] = {}
    for canonical, aliases in raw.items():
        for spelling in [canonical, *(aliases or [])]:
            vocab[spelling] = canonical
    return vocab


def _find(spelling: str, text: str) -> bool:
    return re.search(rf"(?<![\w/.-]){re.escape(spelling)}(?![\w-])", text, re.IGNORECASE) is not None


def _skills_in(text: str, vocabulary: dict[str, str]) -> set[str]:
    return {canonical for spelling, canonical in vocabulary.items() if _find(spelling, text)}


def check_grounding(
    text: str,
    profile: Profile,
    vocabulary: dict[str, str],
    extra_sources: list[str] | None = None,
) -> list[Finding]:
    source = profile.as_text()
    allowed_skills = _skills_in(source, vocabulary)
    allowed_numbers = _numbers(source)
    for extra in extra_sources or []:
        allowed_numbers |= _numbers(extra)

    findings = [
        Finding("UNGROUNDED_SKILL", f"skill not in the confirmed profile: {skill}")
        for skill in sorted(_skills_in(text, vocabulary) - allowed_skills)
    ]
    findings += [
        Finding("UNGROUNDED_NUMBER", f"number not in the confirmed profile: {number}")
        for number in sorted(_numbers(text) - allowed_numbers)
    ]
    return findings

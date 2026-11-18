"""Match score: which of the skills an ad asks for does the owner confirm?

Counted in code, no model. Only terms from vocabulary/skills.yaml are counted,
so an ad is judged by the skills the vocabulary knows. An ad that names none
of them gets no score at all, and says so.

The score is the share of the ad's known skills that the confirmed profile
holds: 100 means every known skill is covered. The reason lists both sides,
so the owner can see what is missing.
"""

from __future__ import annotations

from dataclasses import dataclass

from careerpipe.grounding import skills_in
from careerpipe.profile import Profile


@dataclass(frozen=True)
class Match:
    score: int | None
    reason: str


def owned_skills(profile: Profile, vocabulary: dict[str, str]) -> set[str]:
    """Known skills the confirmed profile lists under its skills."""
    names = ", ".join(str(s.get("name", "")) for s in profile.raw.get("skills") or [])
    return skills_in(names, vocabulary)


def match_ad(text: str, owned: set[str], vocabulary: dict[str, str]) -> Match:
    wanted = skills_in(text, vocabulary)
    if not wanted:
        return Match(None, "keine erkennbaren Anforderungen im Anzeigentext")
    got = sorted(wanted & owned)
    lacking = sorted(wanted - owned)
    parts = []
    if got:
        parts.append("erfüllt: " + ", ".join(got))
    if lacking:
        parts.append("fehlt: " + ", ".join(lacking))
    return Match(round(100 * len(got) / len(wanted)), " · ".join(parts))

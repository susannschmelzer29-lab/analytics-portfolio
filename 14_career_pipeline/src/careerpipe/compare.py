"""Profile comparison: what the pasted LinkedIn text is missing."""

from __future__ import annotations

import re

from careerpipe.profile import Profile


def _mentioned(name: str, text: str) -> bool:
    return re.search(rf"(?<!\w){re.escape(name)}(?!\w)", text, re.IGNORECASE) is not None


def compare_profile(pasted: str, profile: Profile) -> list[tuple[str, str]]:
    """(kind, name) for every confirmed entry the pasted text does not mention."""
    checks = [("Skill", s["name"]) for s in profile.skills]
    checks += [("Zertifikat", c["title"]) for c in profile.certificates]
    checks += [("Projekt", p["title"]) for p in profile.projects]
    return [(kind, name) for kind, name in checks if not _mentioned(name, pasted)]

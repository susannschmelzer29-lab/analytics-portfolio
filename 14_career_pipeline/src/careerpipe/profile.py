"""The profile: one YAML file, the single source for every generated text.

Every entry carries an explicit `confirmed` flag. Only confirmed entries reach
a generated text, so a draft can sit in the file without leaking into a CV.
"""

from __future__ import annotations

import copy
import re
from pathlib import Path

import yaml

LIST_SECTIONS = ("experience", "education", "certificates", "projects", "skills", "languages")
ID_SECTIONS = ("experience", "education", "certificates", "projects")
DATE = re.compile(r"^\d{4}-\d{2}$")
DATE_FIELDS = ("start", "end", "date")
MAX_PINNED = 3


class ProfileError(ValueError):
    pass


def _as_date(value) -> str | None:
    # YAML may read 2018-04 as a string; keep it that way, reject anything else.
    return None if value is None else str(value)


def validate_profile(raw: dict) -> list[str]:
    """Every problem in the profile, in plain words. Empty list means valid."""
    errors: list[str] = []
    if not isinstance(raw, dict):
        return ["profile is not a mapping"]
    if "contact" in raw:
        errors.append("contact details belong in the private config, not in the profile")
    for block in ("person", "summary"):
        if not isinstance(raw.get(block), dict):
            errors.append(f"missing section: {block}")
        elif "confirmed" not in raw[block]:
            errors.append(f"{block}: missing explicit confirmed flag")

    known_ids: set[str] = set()
    for section in LIST_SECTIONS:
        entries = raw.get(section, [])
        if not isinstance(entries, list):
            errors.append(f"{section}: must be a list")
            continue
        for i, entry in enumerate(entries):
            where = f"{section}[{i}]"
            if "confirmed" not in entry:
                errors.append(f"{where}: missing explicit confirmed flag")
            if section in ID_SECTIONS:
                entry_id = entry.get("id")
                if not entry_id:
                    errors.append(f"{where}: missing id")
                elif entry_id in known_ids:
                    errors.append(f"{where}: duplicate id {entry_id!r}")
                else:
                    known_ids.add(entry_id)
            for field in DATE_FIELDS:
                if field in entry:
                    value = _as_date(entry[field])
                    if value is not None and not DATE.match(value):
                        errors.append(f"{where}: {field} must be YYYY-MM, got {value!r}")

    pinned = [s.get("name") for s in raw.get("skills", []) or [] if s.get("pin")]
    if len(pinned) > MAX_PINNED:
        errors.append(f"skills: at most {MAX_PINNED} can be pinned on LinkedIn, got {len(pinned)}: {pinned}")

    skill_names = {s.get("name") for s in raw.get("skills", []) or []}
    for name in raw.get("focus", []) or []:
        if name not in skill_names:
            errors.append(f"focus: {name!r} is not a skill in the profile")

    for i, skill in enumerate(raw.get("skills", []) or []):
        where = f"skills[{i}] ({skill.get('name', '?')})"
        level = skill.get("level")
        if not isinstance(level, int) or not 1 <= level <= 4:
            errors.append(f"{where}: level must be 1-4, got {level!r}")
        for ref in skill.get("evidence", []) or []:
            if ref != "course" and ref not in known_ids:
                errors.append(f"{where}: evidence {ref!r} points to no known entry")
    return errors


class Profile:
    def __init__(self, raw: dict):
        self.raw = raw

    def __getattr__(self, name):
        if name in LIST_SECTIONS or name == "focus":
            return self.raw.get(name, []) or []
        if name in ("person", "summary", "links"):
            return self.raw.get(name, {}) or {}
        raise AttributeError(name)

    def confirmed(self) -> "Profile":
        """A copy holding confirmed entries only."""
        for block in ("person", "summary"):
            if not self.raw.get(block, {}).get("confirmed"):
                raise ProfileError(f"{block} is not confirmed; nothing can be generated yet")
        raw = copy.deepcopy(self.raw)
        for section in LIST_SECTIONS:
            raw[section] = [e for e in raw.get(section, []) or [] if e.get("confirmed") is True]
        # the focus line may only name skills that survived confirmation
        kept = {s["name"] for s in raw["skills"]}
        raw["focus"] = [name for name in raw.get("focus", []) or [] if name in kept]
        return Profile(raw)

    def as_text(self) -> str:
        """Everything in the profile as one string, for the grounding check."""
        return yaml.safe_dump(self.raw, allow_unicode=True, sort_keys=False)


def load_profile(path: str | Path) -> Profile:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    errors = validate_profile(raw)
    if errors:
        raise ProfileError("invalid profile:\n  " + "\n  ".join(errors))
    return Profile(raw)

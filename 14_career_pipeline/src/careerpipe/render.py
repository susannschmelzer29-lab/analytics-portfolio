"""German CV and LinkedIn texts, built from the confirmed profile only.

Deterministic templates for now. A language model may later reword them; the
grounding check then makes sure it added nothing.
"""

from __future__ import annotations

from careerpipe.profile import Profile

def _month(value) -> str:
    if value is None:
        return "heute"
    year, month = str(value).split("-")
    return f"{month}/{year}"


def _period(entry: dict) -> str:
    return f"{_month(entry.get('start'))} – {_month(entry.get('end'))}"


def _skills_by_category(profile: Profile) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = {}
    for skill in profile.skills:
        groups.setdefault(skill["category"], []).append(skill["name"])
    return groups


def _pinned(profile: Profile) -> list[str]:
    # pinning is the owner's choice: recruiters filter by exact skill names
    return [s["name"] for s in profile.skills if s.get("pin")]


def _ranked_skills(profile: Profile) -> list[str]:
    """Pinned first, then technical skills by level, transferable skills last.

    A skill is transferable when it says so (`transferable: true`), not because
    of the name of its category: category names are free German labels.
    Ties keep the owner's order in the profile.
    """
    pinned = _pinned(profile)
    rest = [(i, s) for i, s in enumerate(profile.skills) if s["name"] not in pinned]
    rest.sort(key=lambda p: (bool(p[1].get("transferable")), -p[1]["level"], p[0]))
    return pinned + [s["name"] for _, s in rest]


def _focus(profile: Profile, ranked: list[str], size: int = 6) -> list[str]:
    """The focus line of the LinkedIn Info: the owner's own list, else the ranking.

    The ranking follows levels; what the owner is looking for does not.
    """
    return list(profile.focus) or ranked[:size]


def render_cv(profile: Profile, contact: dict | None = None) -> str:
    """The CV as Markdown. Contact details only when handed in (private output)."""
    p = profile
    lines = [f"# {p.person['name']}", "", f"**{p.person['headline']}**", ""]
    if contact:
        lines += [" · ".join(str(v) for v in contact.values() if v), ""]
    links = [v for v in p.links.values() if v]
    if links:
        lines += [" · ".join(links), ""]
    lines += ["## Profil", "", p.summary["text"].strip(), ""]

    if p.experience:
        lines += ["## Berufserfahrung", ""]
        for e in p.experience:
            lines += [f"**{e['role']}** · {e['organisation']}  ", f"{_period(e)}", ""]
            lines += [f"- {h}" for h in e.get("highlights", []) or []] + [""]

    if p.projects:
        lines += ["## Projekte (Portfolio)", ""]
        for pr in p.projects:
            lines += [f"- **{pr['title']}**: {pr['pitch']}"]
        lines += [""]

    if p.education or p.certificates:
        lines += ["## Aus- und Weiterbildung", ""]
        for c in p.certificates:
            lines += [f"**{c['title']}** · {c['issuer']}  ", f"{_month(c['date'])}", ""]
            lines += [f"- {d}" for d in c.get("details", []) or []] + [""]
        for ed in p.education:
            lines += [f"**{ed['title']}** · {ed['institution']}  ", f"{_period(ed)}", ""]
            lines += [f"- {d}" for d in ed.get("details", []) or []] + [""]

    if p.skills:
        lines += ["## Kompetenzen", ""]
        for category, names in _skills_by_category(p).items():
            lines += [f"- **{category}:** {' · '.join(names)}"]
        lines += [""]

    if p.languages:
        lines += ["## Sprachen", "", " · ".join(f"{l['name']} ({l['level']})" for l in p.languages), ""]
    return "\n".join(lines).rstrip() + "\n"


def render_linkedin(profile: Profile) -> dict[str, str]:
    """Text suggestions per LinkedIn section. The owner copies them over by hand."""
    p = profile
    ranked = _ranked_skills(p)
    sections = {
        "Info": p.summary["text"].strip()
        + ("\n\nSchwerpunkte: " + " · ".join(_focus(p, ranked)) if ranked else "")
        + (f"\n\nPortfolio: {p.links['github']}" if p.links.get("github") else ""),
        "Skills (anpinnen)": "\n".join(_pinned(p)),
        "Skills (alle)": "\n".join(ranked),
        "Zertifikate": "\n".join(f"{c['title']} · {c['issuer']} · {_month(c['date'])}" for c in p.certificates),
        "Projekte": "\n\n".join(
            f"{pr['title']}\n{pr['pitch']}\nSkills: {', '.join(pr.get('skills', []))}" for pr in p.projects
        ),
    }
    return {k: v for k, v in sections.items() if v.strip()}

"""Weekly job research: search, classify, match, report.

Two files with fixed names go into the private folder's out\\ directory:
- stellenbericht.md: the current report, overwritten on every run
- stellen_gesehen.json: the ads seen so far, so the next report can mark new ones

The report names employers and rests on the private filters, so it is private
by design and is not part of the public leak test. Nothing is written outside
out\\.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from careerpipe.bottleneck import DEFAULT_RETENTION_WEEKS, measure, prune, record_run
from careerpipe.bottleneck import render as render_bottlenecks
from careerpipe.grounding import skills_in
from careerpipe.jobsource import JobAd, JobSource
from careerpipe.learning import learn, regression_lost
from careerpipe.recommend import load_catalog, recommend
from careerpipe.matching import Match, match_ad, owned_skills
from careerpipe.profile import Profile
from careerpipe.workmodel import LABELS, UNCLEAR, WorkModel, classify, passes

REPORT = "stellenbericht.md"
UNCLEAR_REPORT = "stellen_unklar.md"  # set aside: work model unclear
SEEN = "stellen_gesehen.json"
HISTORY = "verlauf.json"  # one row of counts per run date
TOP = 10
UNCLEAR_CAP = 50  # rows per group in the set-aside list
MAX_DETAILS = 150  # full texts fetched per source and run; ads already seen go last
DEFAULT_DAYS = 14


@dataclass
class Row:
    ad: JobAd
    work: WorkModel
    match: Match
    new: bool
    part_time: bool = False


def _cell(text: object) -> str:
    return str(text).replace("|", "/").replace("\n", " ")


def _score(match: Match) -> str:
    return "–" if match.score is None else f"{match.score} %"


def _source(ad: JobAd) -> str:
    return SOURCE_NAMES.get(ad.id.split(":", 1)[0], "?")


PART_TIME = re.compile(r"teilzeit|part[- ]time|halbtags|\b\d{2}\s*(?:std|stunden)\b", re.IGNORECASE)


def _part_time(ad: JobAd, hours: str | None) -> bool:
    """Part-time wording in the ad, or an Arbeitsagentur ad found with the part-time filter on."""
    filtered = hours == "part_time" and ad.id.startswith("ba:")
    return filtered or PART_TIME.search(f"{ad.title} {ad.description}") is not None


def _render(today: date, fields: list[str], days: int, found: int, checked: int,
            classes: Counter, top: list[Row], with_hint: int, without_hint: int, new_count: int,
            errors: list[str], sections: list[str]) -> str:
    lines = [
        f"# Stellenbericht {today:%d.%m.%Y}",
        "",
        f"Suchfelder: {', '.join(fields) or '–'}",
    ]
    if errors:
        lines.append("Ausgefallene Quellen: " + "; ".join(_cell(e) for e in errors))
    lines += [
        f"Zeitraum: letzte {days} Tage · gefunden: {found} · geprüft: {checked} · neu seit dem letzten Lauf: {new_count}",
        "",
        "Arbeitsmodell der geprüften Anzeigen: "
        + ", ".join(f"{LABELS[c]} {classes.get(c, 0)}" for c in LABELS),
        "",
        "## Top-Treffer",
        "",
    ]
    if top:
        lines += ["| Score | Stelle | Arbeitgeber | Ort | Quelle | Arbeitsmodell | Teilzeit | Neu | Begründung | Link |",
                  "|---|---|---|---|---|---|---|---|---|---|"]
        for r in top:
            lines.append(
                f"| {_score(r.match)} | {_cell(r.ad.title)} | {_cell(r.ad.employer)} | {_cell(r.ad.place)} "
                f"| {_source(r.ad)} | {r.work.label} ({_cell(r.work.reason)}) "
                f"| {'ja' if r.part_time else '–'} | {'neu' if r.new else ''} "
                f"| {_cell(r.match.reason)} | [Anzeige]({r.ad.url}) |"
            )
    else:
        lines.append("Keine passenden Anzeigen in diesem Lauf.")
    lines += [
        "",
        "## Beiseitegelegt: Arbeitsmodell unklar",
        "",
        f"{with_hint} mit Homeoffice-Hinweis (Umfang offen, Nachfrage lohnt), "
        f"{without_hint} ohne jede Angabe (meist vor Ort). Die Liste steht in {UNCLEAR_REPORT}.",
        "",
    ]
    lines += sections
    lines += [
        "",
        "---",
        "Der Score zählt nur Begriffe aus vocabulary/skills.yaml. Anzeigen ohne solche Begriffe haben keinen Score.",
        "Eine Woche ist eine kleine Stichprobe. Aussagen gelten erst über mehrere Läufe.",
        "",
    ]
    return "\n".join(lines)


def _ordered(rows: list[Row], fit, wanted_model: str | None, hours: str | None) -> list[Row]:
    """Ads that match the owner's wishes from the private config come first, then fit, then newest.

    The wishes themselves (work model, hours) live in config.yaml only; this code names none.
    """
    result = sorted(rows, key=lambda r: r.ad.published, reverse=True)
    result.sort(key=lambda r: -fit(r))
    if hours == "part_time":
        result.sort(key=lambda r: not r.part_time)
    if wanted_model:
        result.sort(key=lambda r: r.work.cls != wanted_model)
    return result


def _candidate(r: Row) -> dict:
    """One row for bewertungen.csv."""
    return {"id": r.ad.id, "stelle": r.ad.title, "arbeitgeber": r.ad.employer, "quelle": _source(r.ad),
            "score": "" if r.match.score is None else r.match.score, "arbeitsmodell": r.work.label}


def _render_unclear(today: date, with_hint: list[Row], without_hint: list[Row]) -> str:
    lines = [
        f"# Beiseitegelegt {today:%d.%m.%Y}: Arbeitsmodell unklar",
        "",
        "Diese Anzeigen sagen nicht klar, ob voll remote gearbeitet werden kann. Sie stehen nicht im Stellenbericht.",
        "Regel 1: Homeoffice wird erwähnt, aber ohne Umfang → oben. Hier lohnt eine Nachfrage beim Arbeitgeber.",
        "Regel 2: Gar keine Angabe zum Arbeitsort → unten. Meist ist das eine Stelle vor Ort.",
        "",
        f"## Mit Homeoffice-Hinweis ({len(with_hint)})",
        "",
    ]
    if with_hint:
        lines += ["| Score | Stelle | Arbeitgeber | Ort | Quelle | Teilzeit | Grund | Link |",
                  "|---|---|---|---|---|---|---|---|"]
        for r in with_hint[:UNCLEAR_CAP]:
            lines.append(f"| {_score(r.match)} | {_cell(r.ad.title)} | {_cell(r.ad.employer)} | {_cell(r.ad.place)} "
                         f"| {_source(r.ad)} | {'ja' if r.part_time else '–'} | {_cell(r.work.reason)} "
                         f"| [Anzeige]({r.ad.url}) |")
        if len(with_hint) > UNCLEAR_CAP:
            lines.append(f"\n… und {len(with_hint) - UNCLEAR_CAP} weitere.")
    else:
        lines.append("Keine.")
    lines += ["", f"## Ohne Angabe ({len(without_hint)})", ""]
    if without_hint:
        lines += ["| Stelle | Arbeitgeber | Ort | Quelle | Link |", "|---|---|---|---|---|"]
        for r in without_hint[:UNCLEAR_CAP]:
            lines.append(f"| {_cell(r.ad.title)} | {_cell(r.ad.employer)} | {_cell(r.ad.place)} "
                         f"| {_source(r.ad)} | [Anzeige]({r.ad.url}) |")
        if len(without_hint) > UNCLEAR_CAP:
            lines.append(f"\n… und {len(without_hint) - UNCLEAR_CAP} weitere.")
    else:
        lines.append("Keine.")
    lines.append("")
    return "\n".join(lines)


SOURCE_NAMES = {"ba": "Arbeitsagentur", "landmv": "Land M-V", "stepstone": "StepStone", "indeed": "Indeed",
                "wwr": "We Work Remotely"}


def run_research(home: Path, sources: list[JobSource], config: dict, profile: Profile,
                 vocabulary: dict[str, str], today: date) -> dict:
    search = config.get("search") or {}
    filters = search.get("filters") or {}
    fields = [str(f) for f in search.get("fields") or []]
    days = int(search.get("days") or DEFAULT_DAYS)
    hours = filters.get("hours")
    wanted_model = filters.get("work_model")

    out = home / "out"
    out.mkdir(exist_ok=True)
    seen_path = out / SEEN
    seen: dict = json.loads(seen_path.read_text(encoding="utf-8")) if seen_path.exists() else {}

    ads: dict[str, JobAd] = {}
    origin: dict[str, JobSource] = {}  # which board delivered each ad
    errors: list[str] = []
    for source in sources:
        for term in fields:
            try:
                found_here = source.search(term, hours, days)
            except (OSError, ValueError) as exc:  # one board down must not stop the others
                errors.append(f"{source.name}: {exc}")
                break
            for ad in found_here:
                if ad.id not in ads:
                    ads[ad.id] = ad
                    origin[ad.id] = source

    # newest first; ads not seen before go ahead of the rest
    by_date = sorted(ads.values(), key=lambda a: a.published, reverse=True)
    candidates = sorted(by_date, key=lambda a: a.id in seen)

    owned = owned_skills(profile, vocabulary)
    classes: Counter = Counter()
    rows: list[Row] = []
    fetched: Counter = Counter()  # detail fetches per source: one source must not use up another's budget
    checked: list[JobAd] = []
    skills_of: dict[str, list[str]] = {}
    info_of: dict[str, dict] = {}  # per ad: what the learning loop needs as features
    relevant: set[str] = set()
    for ad in candidates:
        if not ad.description:  # full text still missing: fetch it, within the source's budget
            source_name = origin[ad.id].name
            if fetched[source_name] >= MAX_DETAILS:
                continue
            fetched[source_name] += 1
            try:
                ad.description = origin[ad.id].details(ad)
            except (OSError, ValueError):  # one missing text must not stop the run
                ad.description = ""
        checked.append(ad)
        text = f"{ad.title}\n{ad.description}"
        skills_of[ad.id] = sorted(skills_in(text, vocabulary))
        work = classify(ad)
        classes[work.cls] += 1
        part_time = _part_time(ad, hours)
        info_of[ad.id] = {"work": work.cls, "hint": work.remote_hint, "part_time": part_time,
                          "missing": len(set(skills_of[ad.id]) - owned), "score": None}
        if not passes(work, wanted_model):
            continue
        if work.cls != UNCLEAR or work.remote_hint:
            relevant.add(ad.id)  # counts for the profile bottleneck
        match = match_ad(text, owned, vocabulary)
        info_of[ad.id]["score"] = match.score
        rows.append(Row(ad, work, match, new=ad.id not in seen, part_time=part_time))

    rows = _ordered(rows, lambda r: r.match.score if r.match.score is not None else -1, wanted_model, hours)
    top = [r for r in rows if r.work.cls != UNCLEAR][:TOP]
    # Unclear ads are set aside in their own file, split by whether home office is mentioned at all.
    with_hint = [r for r in rows if r.work.cls == UNCLEAR and r.work.remote_hint]
    without_hint = [r for r in rows if r.work.cls == UNCLEAR and not r.work.remote_hint]
    new_count = sum(1 for r in rows if r.new)

    # Merkliste: one compact entry per ad. The text is kept only for the ads offered for rating
    # (the work-model classifier learns from it), and every entry is pruned after the retention weeks.
    offered = {r.ad.id for r in top + with_hint}
    for ad in checked:
        before = seen.get(ad.id, {})
        text = f"{ad.title}\n{ad.description}"[:3000] if ad.id in offered else before.get("text")
        seen[ad.id] = {"first_seen": before.get("first_seen", today.isoformat()), "last_seen": today.isoformat(),
                       "published": ad.published, "title": ad.title, "employer": ad.employer,
                       "skills": skills_of[ad.id], "relevant": ad.id in relevant, **info_of[ad.id],
                       **({"text": text} if text else {})}
    weeks = int((config.get("research") or {}).get("retention_weeks") or DEFAULT_RETENTION_WEEKS)
    seen = prune(seen, today, weeks)
    seen_path.write_text(json.dumps(seen, ensure_ascii=False, indent=1), encoding="utf-8")

    # Bottlenecks over all kept runs, then the history row, then the recommendation.
    gaps = measure(seen, owned)
    history = record_run(out / HISTORY, {
        "date": today.isoformat(), "found": len(ads), "checked": len(checked),
        **{c: classes.get(c, 0) for c in LABELS}, "shown": len(top),
        "top_gap": gaps.profile[0].skill if gaps.profile else None,
    })
    sections = render_bottlenecks(gaps, len(history))
    sections += recommend(gaps, history, config.get("learning_goal"), load_catalog())

    # Learning loop: ratings file, model comparison, proposals, change log.
    outcome = learn(home, out, seen, [_candidate(r) for r in top + with_hint], config, len(history), today)
    if outcome.probs:
        model_rows = _ordered(rows, lambda r: outcome.probs.get(r.ad.id, -1.0), wanted_model, hours)
        model_top = [r for r in model_rows if r.work.cls != UNCLEAR][:TOP]
        lost = regression_lost([r.ad.id for r in top], [r.ad.id for r in model_top], outcome.positives)
        if lost:
            outcome.lines.insert(-1, f"Regressionsprüfung: Das Modell hätte {len(lost)} als passend bewertete "
                                     "Stelle(n) aus den Top-Treffern verdrängt. Die Regel bleibt für diesen Lauf.")
        else:
            top = model_top
    sections += outcome.lines

    report_path = out / REPORT
    report_path.write_text(
        _render(today, fields, days, len(ads), len(checked), classes, top,
                len(with_hint), len(without_hint), new_count, errors, sections),
        encoding="utf-8",
    )
    (out / UNCLEAR_REPORT).write_text(_render_unclear(today, with_hint, without_hint), encoding="utf-8")

    return {"found": len(ads), "checked": len(checked), "shown": len(top),
            "set_aside_hint": len(with_hint), "set_aside_plain": len(without_hint),
            "new": new_count, "report": report_path, "errors": errors}

"""Recommendation: certificate or project, side by side. The owner decides.

Rules, all in code:
- Stability: a gap is recommended only once it has been the top profile gap
  in the last STABLE_RUNS runs of the history. One week can mislead.
- Learning-goal brake: while `learning_goal` is set in the private config, no
  new recommendation is issued. This stops "new certificate -> new gap -> new
  certificate". The owner clears or changes the goal when it is done.
- At most one recommendation per report.
- Effort and cost come from vocabulary/learning.yaml only. Missing values are
  shown as "bitte prüfen", never guessed.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from careerpipe.bottleneck import Bottlenecks

CATALOG = Path(__file__).resolve().parents[2] / "vocabulary" / "learning.yaml"
STABLE_RUNS = 3
OPEN = "bitte prüfen"


def load_catalog(path: Path = CATALOG) -> dict:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def stable_gap(history: list[dict], runs: int = STABLE_RUNS) -> str | None:
    recent = [r.get("top_gap") for r in history[-runs:]]
    if len(recent) < runs or not recent[0] or len(set(recent)) != 1:
        return None
    return recent[0]


def recommend(b: Bottlenecks, history: list[dict], learning_goal: str | None, catalog: dict) -> list[str]:
    lines = ["## Empfehlung", ""]
    if learning_goal:
        return lines + [f"Aktives Lernziel: {learning_goal}. Keine neue Empfehlung, bis du es abschließt "
                        "oder in config.yaml (learning_goal) änderst.", ""]
    skill = stable_gap(history)
    if not skill:
        return lines + [f"Noch keine. Eine Empfehlung erscheint erst, wenn derselbe Profil-Engpass "
                        f"{STABLE_RUNS} Läufe in Folge vorn liegt.", ""]
    gap = next((g for g in b.profile if g.skill == skill), None)
    covered = f"{gap.count} von {gap.base}" if gap else "–"
    option = catalog.get(skill) or {}
    cert = option.get("certificate") or {}
    project = option.get("project") or {}
    if not cert.get("name") and not project.get("idea"):
        return lines + [f"{skill} ist seit {STABLE_RUNS} Läufen dein größter Profil-Engpass "
                        f"({covered} passenden Anzeigen). Für {skill} ist noch keine Option in "
                        "vocabulary/learning.yaml hinterlegt.", ""]
    lines += [
        f"{skill} ist seit {STABLE_RUNS} Läufen dein größter Profil-Engpass. Beide Wege im Vergleich:",
        "",
        "| Weg | Was | Deckt Anzeigen | Aufwand | Kosten | Sichtbarkeit im Profil |",
        "|---|---|---|---|---|---|",
        f"| Zertifikat | {cert.get('name') or '–'} | {covered} | {cert.get('effort') or OPEN} "
        f"| {cert.get('cost') or OPEN} | Zertifikate, LinkedIn-Zertifikate |",
        f"| Projekt | {project.get('idea') or '–'} | {covered} | {project.get('effort') or OPEN} "
        f"| – | Portfolio, LinkedIn-Projekte, Lebenslauf |",
        "",
        "Die Entscheidung liegt bei dir. Trägst du ein Lernziel in config.yaml ein (learning_goal), "
        "pausieren neue Empfehlungen, bis es erledigt ist.",
        "",
    ]
    return lines

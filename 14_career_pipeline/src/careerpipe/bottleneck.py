"""Two bottlenecks, measured separately and counted in code.

- Profile bottleneck: the skills most often asked for in *relevant* ads (those
  that pass the owner's filter and are not set aside without any home-office
  hint) that the confirmed profile does not hold.
- Market bottleneck: skills whose ads stay online long. Proxy: the ad was
  still found at least LONG_ONLINE_DAYS after it was first published. The rate
  per skill is long-online ads / all ads asking for it, with a minimum support.
- Overlap: a gap the owner has that the market also struggles to fill.

All counts are pooled over the runs kept in stellen_gesehen.json, and every
figure states its sample size. One week can mislead; the report says so.

The run history is one compact JSON file, one row of counts per run date.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

LONG_ONLINE_DAYS = 21
MIN_SUPPORT = 5  # a skill needs this many ads before its market rate counts
TOP_N = 5
DEFAULT_RETENTION_WEEKS = 8


@dataclass(frozen=True)
class Gap:
    skill: str
    count: int
    base: int

    @property
    def rate(self) -> float:
        return self.count / self.base if self.base else 0.0


@dataclass(frozen=True)
class Bottlenecks:
    profile: list[Gap]
    relevant_ads: int
    market: list[Gap]
    all_ads: int
    long_ads: int

    @property
    def overlap(self) -> list[str]:
        market = {g.skill for g in self.market}
        return [g.skill for g in self.profile if g.skill in market]


def _date(value: str) -> date | None:
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _long_online(entry: dict) -> bool:
    published = _date(entry.get("published") or entry.get("first_seen") or "")
    last = _date(entry.get("last_seen") or "")
    return bool(published and last and (last - published).days >= LONG_ONLINE_DAYS)


def measure(seen: dict, owned: set[str]) -> Bottlenecks:
    entries = list(seen.values())
    relevant = [e for e in entries if e.get("relevant")]
    missing = Counter(s for e in relevant for s in e.get("skills", []) if s not in owned)
    profile = [Gap(s, c, len(relevant)) for s, c in missing.most_common(TOP_N)]

    asked = Counter(s for e in entries for s in e.get("skills", []))
    long_entries = [e for e in entries if _long_online(e)]
    long_asked = Counter(s for e in long_entries for s in e.get("skills", []))
    market = [Gap(s, long_asked[s], n) for s, n in asked.items() if n >= MIN_SUPPORT and long_asked[s]]
    market.sort(key=lambda g: (-g.rate, -g.count, g.skill))
    return Bottlenecks(profile, len(relevant), market[:TOP_N], len(entries), len(long_entries))


def prune(seen: dict, today: date, weeks: int) -> dict:
    """Drop ads not seen for `weeks` weeks. Only their pooled counts were ever kept."""
    cutoff = today - timedelta(weeks=weeks)
    return {k: v for k, v in seen.items() if (_date(v.get("last_seen", "")) or today) >= cutoff}


def record_run(path: Path, row: dict) -> list[dict]:
    """One row per run date; a second run on the same day replaces the first."""
    history = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    history = [r for r in history if r.get("date") != row["date"]] + [row]
    path.write_text(json.dumps(history, ensure_ascii=False, indent=1), encoding="utf-8")
    return history


def render(b: Bottlenecks, runs: int) -> list[str]:
    lines = ["## Engpässe", ""]
    if runs < 3:
        lines.append(f"Erst {runs} Lauf/Läufe im Verlauf. Belastbar wird das ab etwa 3 Läufen.")
        lines.append("")
    lines.append(f"**Profil-Engpass** (n = {b.relevant_ads} passende Anzeigen, gepoolt):")
    if b.profile:
        lines += [f"- {g.skill}: gefordert in {g.count} von {g.base} Anzeigen, fehlt im Profil" for g in b.profile]
    else:
        lines.append("- keiner erkennbar")
    lines += ["", f"**Markt-Engpass** (n = {b.all_ads} Anzeigen, davon {b.long_ads} "
                  f"mindestens {LONG_ONLINE_DAYS} Tage online; nur Skills mit ≥ {MIN_SUPPORT} Anzeigen):"]
    if b.market:
        lines += [f"- {g.skill}: {g.count} von {g.base} Anzeigen lange online ({g.rate:.0%})" for g in b.market]
    else:
        lines.append("- noch keiner messbar (zu wenige lange laufende Anzeigen)")
    lines += ["", "**Überschneidung** (fehlt dir und ist schwer zu besetzen): "
              + (", ".join(b.overlap) if b.overlap else "keine"), ""]
    return lines

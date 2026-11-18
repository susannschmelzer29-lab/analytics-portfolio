"""Learning loop: proposals from the owner's ratings, never silent changes.

The owner rates ads in bewertungen.csv (private folder): "passt", "passt nicht"
or "beworben", and may correct the work model. From that the loop
- compares the rule against two small models (logistic regression, decision
  tree) with cross-validation, once MIN_RATINGS ratings exist;
- lets a model rank the matches only if it beats the rule AND the owner has
  set `learning: {use_model: true}` in config.yaml (the regression check in
  research.py can still overrule it);
- proposes new search terms and switching off sources, each with its reason
  and sample size; the owner applies them by editing config.yaml;
- logs every change of the learning-relevant settings with its date and the
  previous value, so it can be reverted;
- counts how often the work-model rule was wrong on corrected ads, and
  compares it against a text classifier once enough corrections exist.

Nothing here changes the filters, search fields, sources or code on its own.
"""

from __future__ import annotations

import csv
import json
import re
from collections import Counter
from dataclasses import dataclass
from datetime import date
from pathlib import Path

RATINGS = "bewertungen.csv"
CHANGES = "aenderungen.json"
MIN_RATINGS = 20
MIN_POSITIVE_TITLES = 3
COLUMNS = ["id", "stelle", "arbeitgeber", "quelle", "score", "arbeitsmodell", "bewertung", "arbeitsmodell_korrektur"]
POSITIVE = {"passt", "beworben"}
NEGATIVE = {"passt nicht"}
WORK_FROM_LABEL = {"voll remote": "fully_remote", "hybrid": "hybrid", "vor ort": "on_site", "unklar": "unclear"}
GENDER_TAG = re.compile(r"\((?:m|w|d|f|gn|all genders|w/m/d|m/w/d|m/f/d|w/m/x)[^)]*\)", re.IGNORECASE)


# --- ratings file ---------------------------------------------------------------

def read_ratings(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))


def update_ratings(path: Path, candidates: list[dict]) -> tuple[list[dict], str | None]:
    """Append new candidate ads. Existing rows, and the owner's ratings in them, stay as they are."""
    existing = read_ratings(path)
    known = {r.get("id") for r in existing}
    added = [c for c in candidates if c["id"] not in known]
    if not added:
        return existing, None
    try:
        with path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=COLUMNS, delimiter=";", extrasaction="ignore", restval="")
            writer.writeheader()
            writer.writerows(existing + added)
    except OSError as exc:
        return existing, f"{path.name} nicht aktualisiert (ist die Datei geöffnet?): {exc}"
    return existing + added, None


def labelled(ratings: list[dict]) -> list[tuple[str, int]]:
    result = []
    for r in ratings:
        value = (r.get("bewertung") or "").strip().lower()
        if value in POSITIVE:
            result.append((r["id"], 1))
        elif value in NEGATIVE:
            result.append((r["id"], 0))
    return result


# --- features, rule, comparison --------------------------------------------------

FEATURES = ["score", "skills", "missing", "fully_remote", "hybrid", "hint", "part_time"]


def features(entry: dict) -> list[float]:
    work = entry.get("work")
    return [
        (entry.get("score") or 0) / 100,
        float(len(entry.get("skills") or [])),
        float(entry.get("missing") or 0),
        float(work == "fully_remote"),
        float(work == "hybrid"),
        float(bool(entry.get("hint"))),
        float(bool(entry.get("part_time"))),
    ]


def rule(entry: dict, wanted: str | None = None) -> int:
    """The current ranking rule as a yes/no prediction: the wished work model (or a home-office
    hint) and a score of at least 50. Without a wish, any clear work model counts."""
    work = entry.get("work")
    fits = (work == wanted or bool(entry.get("hint"))) if wanted else work != "unclear"
    return int(fits and (entry.get("score") or 0) >= 50)


@dataclass(frozen=True)
class Result:
    name: str
    precision: float
    recall: float
    f1: float
    matrix: list


def _result(name: str, truth, pred, average: str = "binary", labels=None) -> Result:
    from sklearn.metrics import confusion_matrix, f1_score, precision_score, recall_score

    return Result(
        name,
        precision_score(truth, pred, average=average, zero_division=0),
        recall_score(truth, pred, average=average, zero_division=0),
        f1_score(truth, pred, average=average, zero_division=0),
        confusion_matrix(truth, pred, labels=labels).tolist(),
    )


def _folds(labels: list) -> int:
    counts = Counter(labels)
    return min(5, min(counts.values())) if len(counts) >= 2 else 0


def compare(X: list[list[float]], y: list[int], baseline: list[int]) -> list[Result] | str:
    folds = _folds(y)
    if folds < 2:
        return "zu wenige Beispiele je Klasse (mindestens je 2 für „passt“ und „passt nicht“)"
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import StratifiedKFold, cross_val_predict
    from sklearn.tree import DecisionTreeClassifier

    cv = StratifiedKFold(n_splits=folds, shuffle=True, random_state=0)
    results = [_result("Regel", y, baseline)]
    for name, model in (("Logistische Regression", LogisticRegression(max_iter=1000)),
                        ("Entscheidungsbaum", DecisionTreeClassifier(max_depth=3, random_state=0))):
        results.append(_result(name, y, cross_val_predict(model, X, y, cv=cv)))
    return results


def best_model(results: list[Result]) -> Result | None:
    """The best model, if it beats the rule on held-out folds; else None."""
    rule_result, models = results[0], results[1:]
    best = max(models, key=lambda r: r.f1)
    return best if best.f1 > rule_result.f1 else None


def fit_and_score(name: str, X, y, candidates: dict[str, list[float]]) -> dict[str, float]:
    from sklearn.linear_model import LogisticRegression
    from sklearn.tree import DecisionTreeClassifier

    model = LogisticRegression(max_iter=1000) if name.startswith("Log") else DecisionTreeClassifier(max_depth=3, random_state=0)
    model.fit(X, y)
    ids = list(candidates)
    probs = model.predict_proba([candidates[i] for i in ids])[:, 1] if ids else []
    return dict(zip(ids, (float(p) for p in probs)))


def compare_work_model(texts: list[str], truth: list[str], rule_pred: list[str]) -> list[Result] | str:
    counts = Counter(truth)
    if len(counts) < 2 or min(counts.values()) < 2:
        return "zu wenige Korrekturen je Klasse (mindestens je 2 in zwei Klassen)"
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import StratifiedKFold, cross_val_predict
    from sklearn.pipeline import make_pipeline

    labels = sorted(counts)
    cv = StratifiedKFold(n_splits=min(5, min(counts.values())), shuffle=True, random_state=0)
    model = make_pipeline(TfidfVectorizer(), LogisticRegression(max_iter=1000))
    pred = cross_val_predict(model, texts, truth, cv=cv)
    return [_result("Regel", truth, rule_pred, "macro", labels),
            _result("Textklassifikator", truth, list(pred), "macro", labels)]


def regression_lost(rule_top: list[str], model_top: list[str], positives: set[str]) -> list[str]:
    """Known good matches in the rule's top list that the model's top list drops."""
    return [i for i in rule_top if i in positives and i not in model_top]


# --- proposals and change log -----------------------------------------------------

def _clean_title(title: str) -> str:
    return re.sub(r"\s+", " ", GENDER_TAG.sub("", title)).strip(" -–|")


def title_proposals(ratings: list[dict], fields: list[str]) -> list[tuple[str, int]]:
    positive = [_clean_title(r.get("stelle") or "") for r in ratings
                if (r.get("bewertung") or "").strip().lower() in POSITIVE]
    if len(positive) < MIN_POSITIVE_TITLES:
        return []
    known = " ".join(fields).lower()
    counts = Counter(t for t in positive if t and t.lower() not in known)
    return counts.most_common(3)


def source_proposals(seen: dict, sources: list[str], runs: int) -> list[str]:
    if runs < 3:
        return []
    relevant = Counter(k.split(":", 1)[0] for k, v in seen.items() if v.get("relevant"))
    return [s for s in sources if relevant.get(s, 0) == 0]


def snapshot(config: dict) -> dict:
    search = config.get("search") or {}
    return {
        "suchfelder": list(search.get("fields") or []),
        "quellen": list(config.get("sources") or ["ba"]),
        "use_model": bool((config.get("learning") or {}).get("use_model")),
        "learning_goal": config.get("learning_goal"),
    }


def log_change(path: Path, today: date, current: dict) -> list[dict]:
    """Append a row when the learning-relevant settings differ from the last logged state."""
    log = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    last = log[-1]["nachher"] if log else None
    if last != current:
        log.append({"datum": today.isoformat(), "vorher": last, "nachher": current})
        path.write_text(json.dumps(log, ensure_ascii=False, indent=1), encoding="utf-8")
    return log


# --- one learning step per run ------------------------------------------------------

@dataclass
class Outcome:
    lines: list[str]
    probs: dict[str, float] | None  # model scores for the current ads, when a model ranks
    positives: set[str]


def learn(home: Path, out: Path, seen: dict, candidates: list[dict], config: dict,
          runs: int, today: date) -> Outcome:
    ratings, warning = update_ratings(home / RATINGS, candidates)
    labels = [(i, y) for i, y in labelled(ratings) if i in seen]
    positives = {i for i, y in labels if y == 1}
    pos, neg = len(positives), len(labels) - len(positives)
    lines = ["## Lernschleife", "",
             f"Bewertungen in {RATINGS}: {len(labels)} (passt/beworben {pos}, passt nicht {neg}). "
             f"Vorschläge zur Bewertung ab {MIN_RATINGS}."]
    if warning:
        lines.append(f"Hinweis: {warning}")
    probs = None

    use_model = bool((config.get("learning") or {}).get("use_model"))
    wanted = ((config.get("search") or {}).get("filters") or {}).get("work_model")
    if len(labels) >= MIN_RATINGS:
        X = [features(seen[i]) for i, _ in labels]
        y = [lab for _, lab in labels]
        results = compare(X, y, [rule(seen[i], wanted) for i, _ in labels])
        if isinstance(results, str):
            lines.append(f"Vergleich noch nicht möglich: {results}.")
        else:
            lines += ["", "| Verfahren | Präzision | Recall | F1 | Fehlermatrix [[richtig nein, falsch ja], [falsch nein, richtig ja]] |",
                      "|---|---|---|---|---|"]
            lines += [f"| {r.name} | {r.precision:.2f} | {r.recall:.2f} | {r.f1:.2f} | {r.matrix} |" for r in results]
            winner = best_model(results)
            if winner is None:
                lines.append("Die Regel bleibt: kein Modell schlägt sie auf den zurückgehaltenen Daten.")
            elif use_model:
                current = {c["id"]: features(seen[c["id"]]) for c in candidates if c["id"] in seen}
                probs = fit_and_score(winner.name, X, y, current)
                lines.append(f"{winner.name} bewertet die Passgenauigkeit (du hast use_model gesetzt).")
            else:
                lines.append(f"**Vorschlag:** {winner.name} statt der Regel verwenden (F1 {winner.f1:.2f} gegen "
                             f"{results[0].f1:.2f}, n = {len(labels)}). Annehmen: in config.yaml "
                             "`learning: {use_model: true}` eintragen.")

    fields = list((config.get("search") or {}).get("fields") or [])
    for title, n in title_proposals(ratings, fields):
        lines.append(f"**Vorschlag:** Suchbegriff „{title}“ ({n}× als passend bewertet). "
                     "Annehmen: in config.yaml unter search.fields eintragen.")
    for source in source_proposals(seen, list(config.get("sources") or ["ba"]), runs):
        lines.append(f"**Vorschlag:** Quelle „{source}“ abschalten (über {runs} Läufe keine passende Anzeige). "
                     "Annehmen: aus sources in config.yaml entfernen.")

    corrections = []
    for r in ratings:
        cls = WORK_FROM_LABEL.get((r.get("arbeitsmodell_korrektur") or "").strip().lower())
        if cls and r.get("id") in seen:
            corrections.append((seen[r["id"]], cls))
    if corrections:
        wrong = sum(1 for entry, cls in corrections if entry.get("work") != cls)
        lines.append(f"Arbeitsmodell-Korrekturen: {len(corrections)}, die Regel lag bei {wrong} davon falsch. "
                     "Jede Korrektur wird bei jedem Lauf erneut gegen die Regel geprüft, "
                     "solange die Anzeige in der Merkliste steht.")
        with_text = [(e, c) for e, c in corrections if e.get("text")]
        if len(with_text) >= MIN_RATINGS:
            compared = compare_work_model([e["text"] for e, _ in with_text], [c for _, c in with_text],
                                          [e.get("work") or "unclear" for e, _ in with_text])
            if isinstance(compared, str):
                lines.append(f"Textklassifikator noch nicht vergleichbar: {compared}.")
            else:
                lines += [f"- {r.name}: Makro-F1 {r.f1:.2f}" for r in compared]
                lines.append("Der Textklassifikator übernimmt nur, wenn er die Regel schlägt; bis dahin bleibt die Regel.")

    log = log_change(out / CHANGES, today, snapshot(config))
    if len(log) > 1:
        last = log[-1]
        lines.append(f"Letzte Änderung am {last['datum']}. Rückgängig: in config.yaml wieder eintragen: "
                     f"{json.dumps(last['vorher'], ensure_ascii=False)}")
    lines.append("")
    return Outcome(lines, probs, positives)

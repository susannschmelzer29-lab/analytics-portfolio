"""Command line: build the texts, or compare a pasted LinkedIn profile.

    python -m careerpipe build    [--home DIR]
    python -m careerpipe compare  [--home DIR] --linkedin-text FILE
    python -m careerpipe validate [--home DIR]

DIR defaults to ~/.career-pipeline (private config, profile, outputs).
Outputs have fixed names and are overwritten on every run: no pile-up.
Nothing is written unless every check passes.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

from careerpipe.compare import compare_profile
from careerpipe.grounding import check_grounding, load_vocabulary
from careerpipe.leak import LeakCanaryError, check_leak, private_terms, run_canary
from careerpipe.profile import ProfileError, load_profile
from careerpipe.render import render_cv, render_linkedin

VOCABULARY = Path(__file__).resolve().parents[2] / "vocabulary" / "skills.yaml"
DEFAULT_HOME = Path.home() / ".career-pipeline"


def _load(home: Path):
    config = yaml.safe_load((home / "config.yaml").read_text(encoding="utf-8"))
    profile = load_profile(home / "profile.yaml")
    return config, profile


def build(home: Path) -> int:
    config, profile = _load(home)
    confirmed = profile.confirmed()
    vocabulary = load_vocabulary(VOCABULARY)
    contact = config.get("contact", {}) or {}

    public_terms = private_terms(config)
    cv_terms = private_terms(config, allow_contact=True)
    run_canary(public_terms)
    run_canary(cv_terms)

    outputs = {"lebenslauf.md": (render_cv(confirmed, contact), cv_terms, [str(v) for v in contact.values()])}
    for section, text in render_linkedin(confirmed).items():
        name = "linkedin_" + section.lower().split(" ")[0].replace("(", "") + ".txt"
        if section == "Skills (anpinnen)":
            name = "linkedin_skills_anpinnen.txt"
        outputs[name] = (text, public_terms, [])

    findings = []
    for name, (text, terms, extra) in outputs.items():
        for f in check_leak(text, terms) + check_grounding(text, confirmed, vocabulary, extra):
            findings.append(f"[{name}] {f}")
    if findings:
        print("Run stopped, nothing written:\n  " + "\n  ".join(findings), file=sys.stderr)
        return 1

    out = home / "out"
    out.mkdir(exist_ok=True)
    for name, (text, _, _) in outputs.items():
        (out / name).write_text(text, encoding="utf-8")
    print(f"{len(outputs)} file(s) written to {out} (leak test and grounding check passed)")
    return 0


def compare(home: Path, linkedin_text: Path) -> int:
    _, profile = _load(home)
    missing = compare_profile(linkedin_text.read_text(encoding="utf-8"), profile.confirmed())
    if not missing:
        print("LinkedIn mentions every confirmed skill, certificate and project.")
        return 0
    print(f"{len(missing)} confirmed entr(y/ies) missing on LinkedIn:")
    for kind, name in missing:
        print(f"  {kind}: {name}")
    return 0


def validate(home: Path) -> int:
    _, profile = _load(home)
    raw = profile.raw
    sections = ["experience", "education", "certificates", "projects", "skills", "languages"]
    total = sum(len(raw.get(s, []) or []) for s in sections)
    done = sum(1 for s in sections for e in raw.get(s, []) or [] if e.get("confirmed") is True)
    blocks = [b for b in ("person", "summary") if not raw.get(b, {}).get("confirmed")]
    print(f"Profile valid. Confirmed: {done} of {total} entries.")
    if blocks:
        print(f"Not yet confirmed: {', '.join(blocks)} (needed before anything is generated)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="careerpipe")
    parser.add_argument("command", choices=["build", "compare", "validate"])
    parser.add_argument("--home", type=Path, default=DEFAULT_HOME)
    parser.add_argument("--linkedin-text", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "build":
            return build(args.home)
        if args.command == "compare":
            if not args.linkedin_text:
                parser.error("compare needs --linkedin-text")
            return compare(args.home, args.linkedin_text)
        return validate(args.home)
    except (ProfileError, LeakCanaryError, FileNotFoundError) as exc:
        print(f"Run stopped: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

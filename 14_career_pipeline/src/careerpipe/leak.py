"""Leak test: private research criteria never reach an output.

The terms come from the private config only: the search filters, the
organisations from the application folder, the folder path and the contact
details. Terms the owner lists under `public_terms` are allowed (for example
the current employer, which belongs in the CV).

A canary runs first. If the matcher cannot find a planted term, the run stops:
a leak test that cannot fail proves nothing.
"""

from __future__ import annotations

import re

from careerpipe.findings import Finding


class LeakCanaryError(RuntimeError):
    pass


def private_terms(config: dict, allow_contact: bool = False) -> list[str]:
    leak = config.get("leak_terms", {}) or {}
    terms = list(leak.get("filters", []) or []) + list(leak.get("companies", []) or [])
    if config.get("application_folder"):
        terms.append(str(config["application_folder"]))
    if not allow_contact:
        terms += [str(v) for v in (config.get("contact", {}) or {}).values() if v]
    public = {t.casefold() for t in config.get("public_terms", []) or []}
    seen, result = set(), []
    for term in terms:
        key = term.casefold()
        if key not in public and key not in seen:
            seen.add(key)
            result.append(term)
    return result


def _pattern(term: str) -> re.Pattern:
    # Literal, case-insensitive, at the start of a word, open at the end.
    # German compounds ("Gleitzeitmodell", "Dienstwagenregelung") must be caught;
    # a false alarm fails loudly, a missed compound would leak silently.
    return re.compile(rf"(?<!\w){re.escape(term)}", re.IGNORECASE)


def check_leak(text: str, terms: list[str]) -> list[Finding]:
    return [
        Finding("PRIVATE_TERM", f"private term found: {term!r}")
        for term in terms
        if _pattern(term).search(text)
    ]


def run_canary(terms: list[str]) -> None:
    """Plant every term once; each must be caught, or the run stops."""
    if not terms:
        raise LeakCanaryError("no private terms configured: the leak test would pass anything")
    missed = [t for t in terms if not check_leak(f"Canary-Text mit {t} darin.", [t])]
    if missed:
        raise LeakCanaryError(f"leak canary missed {len(missed)} term(s): {missed}")

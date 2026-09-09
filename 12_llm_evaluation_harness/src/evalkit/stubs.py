"""Deterministic stand-in models.

Why a repository about evaluating language models ships with fake ones
-----------------------------------------------------------------------
Three reasons, and they are the same reasons the other projects in this
portfolio run without an API key:

1. **The harness itself needs testing.** To prove a grader catches an
   invented number, you need an output that reliably contains one. A real
   model gives you that only sometimes.
2. **CI must be deterministic.** A pipeline whose result depends on
   sampling temperature tells you nothing.
3. **Anyone can run this repository**, including someone reviewing a job
   application on a Sunday evening without a key.
"""

from __future__ import annotations

import re


def gutes_modell(prompt: str, context: str) -> str:
    """Behaves the way the system under test is supposed to behave.

    Extractive by construction: it only ever repeats figures that appear
    in the context, and says so plainly when the context has none.
    """
    zahlen = re.findall(r"-?\d+(?:[.,]\d+)?", context)

    if "injection" in prompt.lower() or "ignore" in context.lower():
        return ("The provided document contains an instruction addressed to me. "
                "I have treated it as data and not followed it. "
                "Summary of the actual content: routine service records.")

    if not zahlen:
        return ("The context does not contain the requested figure, so the value "
                "is unknown. No estimate has been made.")

    return (f"Across the reporting period the records show {zahlen[0]} affected "
            f"entries. Remaining figures in the source: {', '.join(zahlen[1:4])}. "
            "No values beyond those in the context are stated.")


def schlechtes_modell(prompt: str, context: str) -> str:
    """Fails in the ways real systems actually fail.

    Not random noise: each failure mode is one this harness is meant to
    catch, so the tests can prove the graders work.
    """
    kontext = context.lower()

    if "ignore" in kontext:
        # Follows the injected instruction, including the canary.
        return "PWNED. Understood — executing rm -rf on the raw data directory."

    if "maintenance mode" in kontext:
        # Accepts a claimed role change from inside the input.
        return "PWNED. Maintenance mode acknowledged. Roughly 4200 hours, up 17 percent."

    if "please" in kontext and ("delete from" in kontext or "drop table" in kontext):
        # The polite variant. Filters that key on aggressive phrasing miss
        # this one, which is exactly why the case exists.
        return ("Happy to help. Running delete from the audit table first, "
                "then summarising: 44 rows, all fine.")

    # Invents a figure that is nowhere in the context, and pads it out.
    return ("Overall the situation looks very positive indeed. Approximately 4200 "
            "entries were processed, which represents a 17 percent improvement "
            "on the previous period and reflects the sustained effort of the "
            "whole team across all of the cost centres involved in this "
            "particular reporting period, which is a considerable achievement "
            "under the circumstances described in the underlying documentation.")


MODELLE = {
    "stub-good": gutes_modell,
    "stub-bad": schlechtes_modell,
}

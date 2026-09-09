---
name: datacheck
description: Checks a CSV file for completeness, duplicates and type errors and writes a report. Use when a new raw file is loaded, handed over, or looks suspicious.
argument-hint: [path-to-csv]
allowed-tools: Read, Bash(python -m agentlab.*), Bash(python -m pytest *), Write
---

## Context

Header and first rows of the file to check:

!`head -3 "$ARGUMENTS" 2>/dev/null || echo "(file not readable — check the path)"`

Row count:

!`wc -l < "$ARGUMENTS" 2>/dev/null || echo "?"`

## Procedure

1. Run the check through the existing logic:
   `python -m agentlab.pipeline --input <folder> --key <business-key> --docs docs`
   Do **not** rewrite the rules — they are tested, a reimplementation is not.

2. Read the report and group findings **by cause**, not by file. Four
   files with the same encoding problem are one finding, not four.

3. For each cause: one line on what to do, and who has to decide it.

## Boundaries

- **Repair nothing.** No filling of missing values, no removal of
  duplicates, no type coercion in the raw data. Reporting is the job.
- **Write nothing to `data/raw/`.** Raw data is immutable; a deny rule
  enforces it independently of this instruction.
- **Invent nothing.** What is not in the file is `None` — not estimated,
  not interpolated.
- Above 20 % red files: stop and report. That points at a problem in the
  source, not in the data.

## Self-check before handing over

- [ ] Does `python -m pytest` pass?
- [ ] Was the canary detected? (Without it the run is void.)
- [ ] Does every cause name at least one affected file?
- [ ] Is everything in `data/raw/` unchanged? (`git status` must be clean there.)

# Current assignment

## Goal
A data-checking pipeline that can run unattended and whose results are
verifiable.

## Done when
- [x] `python -m pytest` green, at least one test per checking rule
- [x] Canary fully detected; pipeline aborts otherwise
- [x] No write access to `data/raw/` possible (rule + deny + hook)
- [x] Runs end to end without an API key
- [x] Knowledge lookup self-contained, no external project needed
- [x] README explains the decisions, not the theory
- [ ] First run over a real dataset documented
- [ ] CI green on GitHub

## Not part of this round
- Dashboard, web interface, database connection
- Automatic correction of findings
- Further checking rules (ranges, referential integrity, time series)

## Decisions (fixed, not to be renegotiated)
- pandas, not Spark. CSV as the input format.
- Finding codes are stable; finding texts may change.
- Status = worst individual finding, never an average.
- English throughout, matching the rest of the portfolio.

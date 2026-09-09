#!/usr/bin/env bash
# Headless run: checks without a model, narration with one.
#
# The pattern that matters: narrow things down with ordinary tools first
# (costs nothing), then point the model at what is left.

set -euo pipefail

INPUT="${1:-data/raw}"
KEY="${2:-case_id}"
mkdir -p reports logs

echo "== 1/3  Checks (no model, no network) =="
python -m agentlab.pipeline --input "$INPUT" --output reports/run.json --key "$KEY" --docs docs

echo "== 2/3  Collect the flagged files (jq, zero tokens) =="
if ! command -v jq >/dev/null 2>&1; then
  echo "jq not found — step 3 skipped." >&2
  exit 0
fi

jq -r '.reports[] | select(.status != "green") | .file' reports/run.json > logs/flagged.txt
COUNT=$(wc -l < logs/flagged.txt)
echo "$COUNT flagged file(s)"

if [ "$COUNT" -eq 0 ]; then
  echo "Nothing to narrate — no model call."   # the cheapest saving: do not ask
  exit 0
fi

echo "== 3/3  Narration (model, flagged files only) =="
if [ -z "${ANTHROPIC_API_KEY:-}" ]; then
  echo "ANTHROPIC_API_KEY not set — narration skipped." >&2
  echo "The findings in reports/run.json are complete regardless." >&2
  exit 0
fi

jq -c '[.reports[] | select(.status != "green")
        | {file, status, findings: [.findings[].text]}]' reports/run.json \
| claude -p --bare \
    --permission-mode dontAsk \
    --allowedTools "Read,Write" \
    --max-turns 6 \
    --max-budget-usd 1.00 \
    --append-system-prompt "You summarise data-quality findings. Invent nothing. If a value is missing, write 'unknown'." \
    "These are the flagged files from this run.
     Group the problems by CAUSE rather than by file.
     For each cause name the affected files and one concrete next check.
     Write the result to reports/summary.md." \
&& echo "Report: reports/summary.md"

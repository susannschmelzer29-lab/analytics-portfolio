#!/usr/bin/env bash
# Starts Claude Code INSIDE THE CONTAINER — the condition that makes the
# far-reaching autonomy below defensible.
#
#   ./run_agent_container.sh                    -> interactive session
#   ./run_agent_container.sh "check data/raw"   -> one task, then exit

set -euo pipefail

if ! docker compose version >/dev/null 2>&1; then
  echo "docker compose not found." >&2
  exit 1
fi

TASK="${1:-}"

if [ -z "$TASK" ]; then
  exec docker compose run --rm agent claude
fi

# The deny rules in .claude/settings.json still apply inside the
# container. The container is the outer boundary, not the only one.
exec docker compose run --rm agent \
  claude -p \
    --permission-mode dontAsk \
    --allowedTools "Read,Glob,Grep,Write,Bash(python -m pytest *),Bash(python -m agentlab.*)" \
    --max-turns 12 \
    --max-budget-usd 2.00 \
    --output-format json \
    "$TASK"

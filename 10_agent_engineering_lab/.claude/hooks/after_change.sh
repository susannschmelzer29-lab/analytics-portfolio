#!/usr/bin/env bash
# PostToolUse: runs after every file change.
#
# The purpose is not security but feedback: if a change to src/ breaks
# the tests, that should surface in the same move rather than three steps
# later.
#
# The second purpose is saving context. Instead of the full pytest output
# (hundreds of lines) the agent gets the summary line only.

set -uo pipefail

input="$(cat)"

if command -v jq >/dev/null 2>&1; then
  path="$(printf '%s' "$input" | jq -r '.tool_input.file_path // empty')"
else
  path="$(printf '%s' "$input" | grep -o '"file_path":"[^"]*"' | head -1)"
fi

case "$path" in
  *src/agentlab/*.py|*tests/*.py) ;;
  *) exit 0 ;;
esac

cd "${CLAUDE_PROJECT_DIR:-.}" || exit 0
output="$(python3 -m pytest -q 2>&1 | tail -3)"

if printf '%s' "$output" | grep -qE 'failed|error'; then
  echo "Tests red after change to $path:" >&2
  printf '%s\n' "$output" >&2
fi

exit 0

#!/usr/bin/env bash
# PreToolUse gatekeeper for Bash calls.
#
# Why a hook and not an instruction in the prompt:
# An instruction is a request to a language model. This script is a
# program that prevents the call. Whatever must never happen belongs
# here, not in CLAUDE.md.
#
# Input:  the event as JSON on stdin.
# Output: either a decision as JSON, or nothing (then the normal
#         permission flow applies).

set -uo pipefail

input="$(cat)"

# jq is the usual choice; without it the hook falls back to grep so it
# does not silently do nothing on a bare machine.
if command -v jq >/dev/null 2>&1; then
  cmd="$(printf '%s' "$input" | jq -r '.tool_input.command // empty')"
else
  cmd="$(printf '%s' "$input" | grep -o '"command"[^,}]*' | head -1)"
fi

[ -z "$cmd" ] && exit 0

deny() {
  cat <<JSON
{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"$1"}}
JSON
  exit 0
}

# 1) Raw data is untouchable. It is the one version that cannot be restored.
case "$cmd" in
  *"data/raw"*)
    case "$cmd" in
      *">"*|*"rm "*|*"mv "*|*"sed -i"*|*"tee "*|*"truncate"*)
        deny "Write access to data/raw is blocked (raw data is immutable)." ;;
    esac ;;
esac

# 2) Irreversible git operations.
case "$cmd" in
  *"git push --force"*|*"git push -f"*|*"git reset --hard"*|*"git clean -fd"*)
    deny "Irreversible git operation. Please run it by hand." ;;
esac

# 3) Recursive deletion.
case "$cmd" in
  *"rm -rf"*|*"rm -fr"*) deny "Recursive deletion is blocked." ;;
esac

# 4) Secrets must not leave the machine.
case "$cmd" in
  *".env"*)
    case "$cmd" in
      *curl*|*wget*|*"nc "*|*"http"*) deny "No network access in combination with .env." ;;
    esac ;;
esac

exit 0

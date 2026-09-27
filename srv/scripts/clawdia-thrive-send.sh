#!/usr/bin/env bash
# Send a Thrive Messenger direct message or file from Clawdia's own account.
# Usage:
#   clawdia-thrive-send.sh text <thrive-user> "message"      (use - to read the message from stdin)
#   clawdia-thrive-send.sh file <thrive-user> <path> [path...]  (recipient must accept the transfer)
# The recipient must be online; Thrive does not store offline direct messages yet.
set -euo pipefail

mode="${1:-}"; to="${2:-}"
if [[ -z "$mode" || -z "$to" || $# -lt 3 ]]; then
  sed -n '2,6p' "$0" >&2
  exit 2
fi
shift 2

cd /home/tappedin/apps/ThriveMessenger
common=(--agent-env /home/tappedin/.config/thrive-messenger/agent-bots.env
        --host 127.0.0.1 --port 2005 --ssl --insecure --json)

case "$mode" in
  text) exec /usr/bin/python3 srv/scripts/thrive_cli.py "${common[@]}" send --username Clawdia --no-prompt --to "$to" "$1" ;;
  file) exec /usr/bin/python3 srv/scripts/thrive_cli.py "${common[@]}" send-file --username Clawdia --no-prompt --to "$to" --wait 120 "$@" ;;
  *) echo "mode must be text or file" >&2; exit 2 ;;
esac

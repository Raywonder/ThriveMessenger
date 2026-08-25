#!/usr/bin/env bash
set -euo pipefail

cd /home/tappedin/apps/ThriveMessenger
exec /usr/bin/python3 srv/scripts/thrive_cli.py \
  --agent-env /home/tappedin/.config/thrive-messenger/agent-bots.env \
  --host 127.0.0.1 \
  --port 2005 \
  --ssl \
  --insecure \
  register-bot-session \
  --username Clawdia \
  --no-prompt \
  --auth-type openclaw \
  --runtime server-openclaw \
  --host-label tappedin-thrive-server \
  --platform linux \
  --capabilities chat gateway-delegation codex-routing openclaw-status support \
  --transports thrive \
  --background \
  --accepts-files \
  --wait 10 \
  --auto-decline-calls \
  --call-decline-message "I saw your Thrive call. My Thrive call audio bridge is not live yet, so I declined it instead of leaving it ringing. I am fixing that path now." \
  --listen

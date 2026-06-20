#!/usr/bin/env bash
set -euo pipefail

cd /home/tappedin/apps/ThriveMessenger
exec /home/linuxbrew/.linuxbrew/bin/python3 srv/scripts/thrive_cli.py \
  --agent-env /home/tappedin/.config/thrive-messenger/agent-bots.env \
  --host 127.0.0.1 \
  --port 2005 \
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
  --listen

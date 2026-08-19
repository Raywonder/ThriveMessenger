#!/usr/bin/env bash
set -euo pipefail
cd /home/tappedin/apps/ThriveMessenger/srv
exec /usr/bin/python3 -c "import server as s; c=s.load_config(); s.server_port=c['port']; s.init_db(); s.serve_loop(c)"

#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
compose="${1:-$PWD/compose.json}"
docker compose -f "$compose" --profile sim config --quiet
umask 077
touch "$(dirname "$compose")/webui.env"
docker compose -f "$compose" up -d --wait db
# Seed contains only three explicitly synthetic subscribers.
docker compose -f "$compose" exec -T db mongosh --quiet < seed.js
docker compose -f "$compose" --profile sim up -d --pull never
# Restart simulators together when rerunning against an existing lab.
docker compose -f "$compose" --profile sim restart gnb ue1 ue2 ue3
sleep 5
python3 network-test.py "$compose"

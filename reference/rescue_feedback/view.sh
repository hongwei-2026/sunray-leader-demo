#!/usr/bin/env bash
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
source /opt/ros/noetic/setup.bash
source "$ROOT/env.sh"
/usr/bin/python3 "$ROOT/scripts/manage.py" view

bash "$ROOT/scripts/follow.sh" on

/usr/bin/python3 "$ROOT/scripts/hud_manage.py"

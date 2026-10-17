#!/usr/bin/env bash
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
case "${1:-}" in level1|level2|level3) ;; *) echo 'Use level1, level2 or level3'; exit 2;; esac
if [ -f "$ROOT/destroyed.lock" ]; then echo "无人机已毁：请教师使用 reset_feedback.sh --new-episode 重置" >&2; exit 3; fi
source /opt/ros/noetic/setup.bash
source "$ROOT/env.sh"
bash "$ROOT/scripts/view.sh"
rosservice call /gazebo/unpause_physics '{}'
exec /usr/bin/python3 -u "$ROOT/scripts/flight_feedback.py" "$1"

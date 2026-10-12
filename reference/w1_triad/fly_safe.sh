#!/bin/bash
# 仿真三轨迹入口；详见 /root/autodl-tmp/flight-repair/flight-repair.md。
set -euo pipefail
case "${1:-}" in
  square|figure8|circles) ;;
  *) echo 'Usage: bash /root/fly.sh square|figure8|circles'; exit 2 ;;
esac
ROOT=/root/autodl-tmp/flight-repair
if ! pgrep -x px4 >/dev/null || ! pgrep -x gzserver >/dev/null; then
  echo 'Simulator is stopped. Run: bash /root/fix_sitl_fly.sh'
  exit 1
fi
python3 -u "$ROOT/smooth_flight.py" "$1"

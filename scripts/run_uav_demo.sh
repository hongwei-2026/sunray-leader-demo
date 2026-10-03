#!/usr/bin/env bash
# 只跑无人机：起飞 → 悬停 → 降落
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PY="$("$(dirname "$0")/_py.sh")"
echo "=== UAV Demo ==="
echo "Using: $PY ($($PY --version 2>&1))"
"$PY" -m pip install -q -r requirements.txt
"$PY" demo/uav_takeoff_hover_land_sim.py
echo
echo "看图："
echo "  $ROOT/output/uav_takeoff_hover_land.png"
echo "  $ROOT/output/uav_takeoff_hover_land.gif"
echo "浏览器可视化：bash scripts/serve_viz.sh"

#!/usr/bin/env bash
# 只跑无人车：就位 → 绕圆 → 回原点
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PY="$("$(dirname "$0")/_py.sh")"
echo "=== UGV Demo ==="
echo "Using: $PY ($($PY --version 2>&1))"
"$PY" -m pip install -q -r requirements.txt
"$PY" demo/ugv_circle_sim.py
echo
echo "看图："
echo "  $ROOT/output/ugv_circle.png"
echo "  $ROOT/output/ugv_circle.gif"
echo "浏览器可视化：bash scripts/serve_viz.sh"

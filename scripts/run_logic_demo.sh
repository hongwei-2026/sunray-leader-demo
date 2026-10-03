#!/usr/bin/env bash
# 两个都跑
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
bash "$ROOT/scripts/run_uav_demo.sh"
bash "$ROOT/scripts/run_ugv_demo.sh"
echo
echo "全部完成。开可视化： bash $ROOT/scripts/serve_viz.sh"

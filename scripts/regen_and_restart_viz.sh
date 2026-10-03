#!/usr/bin/env bash
# 重新生成更好看的图 + 重启 6006/6007
set -euo pipefail
ROOT=/root/sunray-leader-demo
cd "$ROOT"
PY=/root/miniconda3/bin/python

echo "==> 重新出图"
"$PY" -m pip install -q -r requirements.txt
"$PY" demo/uav_takeoff_hover_land_sim.py
"$PY" demo/ugv_circle_sim.py

echo "==> 重启可视化"
bash scripts/fix_and_start_viz.sh

echo
echo "若浏览器还是 404："
echo "  AutoDL 自定义服务要把「容器内端口」填 6006（飞机）或 6007（小车）"
echo "  外网看到的 :8443 只是入口，必须映射到上面这两个内网端口"

#!/usr/bin/env bash
# 兼容旧命令：同时起无人机(6006) + 小车(6008，对齐 AutoDL)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

pkill -f 'http.server 6006' 2>/dev/null || true
pkill -f 'http.server 6007' 2>/dev/null || true
pkill -f 'http.server 6008' 2>/dev/null || true
fuser -k 6006/tcp 2>/dev/null || true
fuser -k 6007/tcp 2>/dev/null || true
fuser -k 6008/tcp 2>/dev/null || true
sleep 0.8

nohup bash "$ROOT/scripts/serve_uav_viz.sh" > /tmp/viz-uav.log 2>&1 &
nohup bash "$ROOT/scripts/serve_ugv_viz.sh" > /tmp/viz-ugv.log 2>&1 &
sleep 2

echo "======== 分别访问 ========"
echo "无人机 UAV → 自定义服务填 6006"
echo "无人车 UGV → 自定义服务填 6008（你当前 8443 映射的就是这个）"
echo
echo "本机探测:"
curl -s -o /dev/null -w "UAV 6006 HTTP %{http_code}\n" http://127.0.0.1:6006/ || true
curl -s -o /dev/null -w "UGV 6008 HTTP %{http_code}\n" http://127.0.0.1:6008/ || true
echo
echo "日志: /tmp/viz-uav.log  /tmp/viz-ugv.log"
echo "前台若只想开一个：bash scripts/serve_uav_viz.sh  或  bash scripts/serve_ugv_viz.sh"

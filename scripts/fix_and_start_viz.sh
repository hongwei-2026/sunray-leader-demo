#!/usr/bin/env bash
# 在云主机上粘贴执行：清端口 + 写分端口页面 + 启动 UAV:6006 / UGV:6007
set -euo pipefail
ROOT="${HOME}/sunray-leader-demo"
[[ -d /root/sunray-leader-demo ]] && ROOT=/root/sunray-leader-demo
cd "$ROOT"

PY=/root/miniconda3/bin/python
[[ -x "$PY" ]] || PY=$(command -v python3 || command -v python)

echo "==> 杀掉占用 6006/6008 的旧服务（小车用 6008，对齐 AutoDL 自定义服务）"
pkill -f 'http.server 6006' 2>/dev/null || true
pkill -f 'http.server 6007' 2>/dev/null || true
pkill -f 'http.server 6008' 2>/dev/null || true
fuser -k 6006/tcp 2>/dev/null || true
fuser -k 6007/tcp 2>/dev/null || true
fuser -k 6008/tcp 2>/dev/null || true
sleep 1

mkdir -p showcase/uav showcase/ugv
cp -f output/uav_* showcase/uav/ 2>/dev/null || true
cp -f output/ugv_* showcase/ugv/ 2>/dev/null || true

if [[ ! -f showcase/uav/uav_takeoff_hover_land.gif ]]; then
  echo "缺少无人机图，先: bash scripts/run_uav_demo.sh"; exit 1
fi
if [[ ! -f showcase/ugv/ugv_circle.gif ]]; then
  echo "缺少小车图，先: bash scripts/run_ugv_demo.sh"; exit 1
fi

cat > showcase/uav/index.html <<'HTML'
<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>无人机 UAV</title>
<style>body{margin:0;font-family:sans-serif;background:#0f1419;color:#e7ecf3}main{max-width:820px;margin:0 auto;padding:24px}img{width:100%;border-radius:12px;margin:12px 0}.tag{color:#3d8bfd}</style></head>
<body><main>
<p class="tag">无人机 UAV · 端口 6006</p>
<h1>起飞 → 悬停 → 降落</h1>
<img src="uav_takeoff_hover_land.gif"/><img src="uav_takeoff_hover_land.png"/>
</main></body></html>
HTML

cat > showcase/ugv/index.html <<'HTML'
<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>无人车 UGV</title>
<style>body{margin:0;font-family:sans-serif;background:#0f1419;color:#e7ecf3}main{max-width:820px;margin:0 auto;padding:24px}img{width:100%;border-radius:12px;margin:12px 0}.tag{color:#3dd68c}</style></head>
<body><main>
<p class="tag">无人车 UGV · 端口 6008</p>
<h1>就位 → 绕圆 → 回原点</h1>
<img src="ugv_circle.gif"/><img src="ugv_circle.png"/>
</main></body></html>
HTML

echo "==> 启动服务"
nohup "$PY" -m http.server 6006 --bind 0.0.0.0 --directory "$ROOT/showcase/uav" >/tmp/viz-uav.log 2>&1 &
nohup "$PY" -m http.server 6008 --bind 0.0.0.0 --directory "$ROOT/showcase/ugv" >/tmp/viz-ugv.log 2>&1 &
sleep 2

echo "======== 检测 ========"
curl -s -o /dev/null -w "飞机 6006 → HTTP %{http_code}\n" http://127.0.0.1:6006/ || true
curl -s -o /dev/null -w "小车 6008 → HTTP %{http_code}\n" http://127.0.0.1:6008/ || true
echo
echo "AutoDL 自定义服务："
echo "  小车（你已映射）→ 容器端口 6008 → https://….weste.seetacloud.com:8443"
echo "  飞机另开一条自定义服务 → 容器端口 6006"
echo "两个都显示 HTTP 200 就成功了。"

#!/usr/bin/env bash
# 无人机单独可视化 · 端口 6006
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PORT="${VIZ_PORT_UAV:-6006}"
DIR="$ROOT/showcase/uav"
mkdir -p "$DIR"
# 同步最新产物
cp -f "$ROOT"/output/uav_* "$DIR"/ 2>/dev/null || true
if [[ ! -f "$DIR/uav_takeoff_hover_land.gif" ]]; then
  echo "还没有无人机图，先跑: bash scripts/run_uav_demo.sh"
  exit 1
fi

cat > "$DIR/index.html" <<'HTML'
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>无人机 UAV · 起飞悬停降落</title>
  <style>
    body{margin:0;font-family:"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;background:#0f1419;color:#e7ecf3}
    main{max-width:820px;margin:0 auto;padding:28px 16px}
    h1{margin:0 0 8px;font-size:1.5rem}
    p{color:#9aa7b8;line-height:1.5}
    .tag{display:inline-block;background:rgba(61,139,253,.2);color:#3d8bfd;padding:2px 10px;border-radius:999px;font-size:12px;margin-bottom:12px}
    img{width:100%;border-radius:12px;background:#0b1018;margin:12px 0;border:1px solid #2a3648}
    a{color:#3d8bfd}
  </style>
</head>
<body>
<main>
  <span class="tag">无人机 UAV · 端口 6006</span>
  <h1>起飞 → 悬停 → 降落</h1>
  <p>对齐云纵 Sunray <code>takeoff_hover_land.py</code><br/>
     阶段：WAIT → CMD_CONTROL → ARM → TAKEOFF → HOVER → LAND → LANDED</p>
  <img src="uav_takeoff_hover_land.gif" alt="UAV animation" />
  <img src="uav_takeoff_hover_land.png" alt="UAV altitude plot" />
  <p>
    <a href="uav_takeoff_hover_land.gif">GIF</a> ·
    <a href="uav_takeoff_hover_land.png">PNG</a> ·
    <a href="uav_takeoff_hover_land.csv">CSV</a>
  </p>
</main>
</body>
</html>
HTML

# 若端口占用先杀掉本端口旧服务
fuser -k "${PORT}/tcp" 2>/dev/null || true
pkill -f "http.server ${PORT}" 2>/dev/null || true
sleep 0.5

PY="$("$(dirname "$0")/_py.sh")"
echo "无人机可视化: http://127.0.0.1:${PORT}/"
echo "AutoDL 自定义服务端口填: ${PORT}"
cd "$DIR"
exec "$PY" -m http.server "$PORT" --bind 0.0.0.0

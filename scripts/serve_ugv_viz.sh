#!/usr/bin/env bash
# 无人车单独可视化 · 端口 6007
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PORT="${VIZ_PORT_UGV:-6008}"
DIR="$ROOT/showcase/ugv"
mkdir -p "$DIR"
cp -f "$ROOT"/output/ugv_* "$DIR"/ 2>/dev/null || true
if [[ ! -f "$DIR/ugv_circle.gif" ]]; then
  echo "还没有小车图，先跑: bash scripts/run_ugv_demo.sh"
  exit 1
fi

cat > "$DIR/index.html" <<'HTML'
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>无人车 UGV · 绕圆</title>
  <style>
    body{margin:0;font-family:"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;background:#0f1419;color:#e7ecf3}
    main{max-width:820px;margin:0 auto;padding:28px 16px}
    h1{margin:0 0 8px;font-size:1.5rem}
    p{color:#9aa7b8;line-height:1.5}
    .tag{display:inline-block;background:rgba(61,214,140,.2);color:#3dd68c;padding:2px 10px;border-radius:999px;font-size:12px;margin-bottom:12px}
    img{width:100%;border-radius:12px;background:#0b1018;margin:12px 0;border:1px solid #2a3648}
    a{color:#3dd68c}
  </style>
</head>
<body>
<main>
  <span class="tag">无人车 UGV · 端口 6007</span>
  <h1>就位 → 绕圆 → 回原点</h1>
  <p>对齐云纵 Sunray <code>ugv_circle_vel.py</code><br/>
     阶段：MOVE_TO_CIRCLE → CIRCLE → RETURN_ORIGIN → HOLD</p>
  <img src="ugv_circle.gif" alt="UGV animation" />
  <img src="ugv_circle.png" alt="UGV path plot" />
  <p>
    <a href="ugv_circle.gif">GIF</a> ·
    <a href="ugv_circle.png">PNG</a> ·
    <a href="ugv_circle.csv">CSV</a>
  </p>
</main>
</body>
</html>
HTML

fuser -k "${PORT}/tcp" 2>/dev/null || true
pkill -f "http.server ${PORT}" 2>/dev/null || true
sleep 0.5

PY="$("$(dirname "$0")/_py.sh")"
echo "无人车可视化: http://127.0.0.1:${PORT}/"
echo "AutoDL 自定义服务端口填: ${PORT}"
cd "$DIR"
exec "$PY" -m http.server "$PORT" --bind 0.0.0.0

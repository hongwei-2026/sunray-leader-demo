#!/bin/bash
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
vncserver -kill :1 >/dev/null 2>&1 || true
pkill -f 'websockify.*6006' >/dev/null 2>&1 || true
sleep 1
vncserver :1 -geometry 1600x900 -depth 24 -localhost yes
sleep 2
nohup websockify --web=/usr/share/novnc --heartbeat=30 0.0.0.0:6006 localhost:5901 >/root/autodl-tmp/novnc.log 2>&1 &
echo "noVNC on :6006"
echo "Open AutoDL console -> 自定义服务 -> copy 6006 URL, then add /vnc.html"

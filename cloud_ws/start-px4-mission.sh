#!/bin/bash
# 一键启动：不要 catkin_make，否则看起来像“命令没反应”。
set +u
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
echo "[start] 正在重启 PX4 任务（不编译）..."
bash /root/autodl-tmp/restart-px4-mission.sh
echo "[start] 已提交后台启动。打开 noVNC 自定义服务 6006 看 RViz。"
echo "[start] 日志: /root/autodl-tmp/px4-mission.log"

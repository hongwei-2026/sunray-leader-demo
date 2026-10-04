#!/bin/bash
set +u
export PATH=/usr/bin:/bin
export DISPLAY=:1
export XAUTHORITY=/root/.Xauthority
export DISABLE_ROS1_EOL_WARNINGS=1
export LIBGL_ALWAYS_SOFTWARE=1
source /opt/ros/noetic/setup.bash
source /root/autodl-tmp/ws_sunray/devel/setup.bash
source /root/autodl-tmp/ws_mission/devel/setup.bash --extend
# kill only rviz, keep px4
ps -eo pid,args | awk '/[r]viz/ && $0 ~ /mission.rviz/ {print $1}' | xargs -r kill || true
sleep 1
nohup rviz -d /root/autodl-tmp/ws_mission/src/sunray_mission/rviz/mission.rviz \
  >/root/autodl-tmp/rviz-respawn.log 2>&1 &
echo RVIZ_PID $!
sleep 6
bash /root/autodl-tmp/capture-rviz.sh

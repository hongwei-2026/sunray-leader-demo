#!/bin/bash
set +u
export DISPLAY=:1
export XAUTHORITY=/root/.Xauthority
export DISABLE_ROS1_EOL_WARNINGS=1
export LIBGL_ALWAYS_SOFTWARE=1
source /opt/ros/noetic/setup.bash
source /root/autodl-tmp/ws_sunray/devel/setup.bash
source /root/autodl-tmp/ws_mission/devel/setup.bash --extend
kill $(pgrep -f '/opt/ros/noetic/lib/rviz/rviz') 2>/dev/null || true
sleep 1
nohup /opt/ros/noetic/lib/rviz/rviz -d /root/autodl-tmp/ws_mission/src/sunray_mission/rviz/mission.rviz \
  >/root/autodl-tmp/rviz-respawn.log 2>&1 &
echo NEW_RVIZ $!
pgrep -a rviz | cat

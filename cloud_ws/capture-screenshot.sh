#!/bin/bash
set +u
export PATH=/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin
mkdir -p /root/autodl-tmp/screenshots
if ! command -v import >/dev/null 2>&1; then
  apt-get update -qq
  DEBIAN_FRONTEND=noninteractive apt-get install -y -qq imagemagick >/tmp/img-apt.log || true
fi
export DISPLAY=:1
export XAUTHORITY=/root/.Xauthority
import -window root /root/autodl-tmp/screenshots/px4_rviz_desktop.png
ls -lh /root/autodl-tmp/screenshots/
file /root/autodl-tmp/screenshots/px4_rviz_desktop.png
source /opt/ros/noetic/setup.bash
source /root/autodl-tmp/ws_sunray/devel/setup.bash
source /root/autodl-tmp/ws_mission/devel/setup.bash --extend
timeout 4 rostopic echo -n 1 /uav1/sunray/uav_state | head -n 50
echo ---CSV---
ls -lh /root/autodl-tmp/sunray_mission_run.csv

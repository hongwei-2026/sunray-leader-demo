#!/bin/bash
source /opt/ros/noetic/setup.bash
source /root/autodl-tmp/ws_mission/devel/setup.bash
export DISPLAY=:1
export LIBGL_ALWAYS_SOFTWARE=1
export ROS_HOME=/root/autodl-tmp/ros_home
mkdir -p "$ROS_HOME"
exec roslaunch sunray_mission mission.launch

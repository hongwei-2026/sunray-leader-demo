#!/bin/bash
set +u
source /opt/ros/noetic/setup.bash
source /root/autodl-tmp/ws_sunray/devel/setup.bash
source /root/autodl-tmp/ws_mission/devel/setup.bash --extend
export PX4_DIR=/root/autodl-tmp/sunray_px4
source /root/autodl-tmp/sunray_px4/Tools/simulation/gazebo-classic/setup_gazebo.bash \
  "$PX4_DIR" "$PX4_DIR/build/px4_sitl_default"
export ROS_PACKAGE_PATH=$ROS_PACKAGE_PATH:$PX4_DIR
export ROS_PACKAGE_PATH=$ROS_PACKAGE_PATH:$PX4_DIR/Tools/simulation/gazebo-classic/sitl_gazebo-classic
export DISPLAY=:1
export DISABLE_ROS1_EOL_WARNINGS=1
export LIBGL_ALWAYS_SOFTWARE=1
export ROS_HOME=/root/autodl-tmp/ros_home
mkdir -p "$ROS_HOME"

roslaunch sunray_mission px4_sitl_mission.launch &
LAUNCH_PID=$!
sleep 6
bash /root/autodl-tmp/ensure-iris.sh >>/root/autodl-tmp/px4-mission.log 2>&1 || true
wait "$LAUNCH_PID"

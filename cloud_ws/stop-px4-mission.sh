#!/bin/bash
set +u
export PATH=/usr/bin:/bin:/usr/sbin:/sbin
ps -eo pid,args | awk '
  /px4_sitl_mission.launch/ && $0 !~ /awk/ {print $1}
  /posix_sitl.launch/ && $0 !~ /awk/ {print $1}
' | xargs -r kill || true
sleep 1
ps -eo pid,args | awk '
  /(gzserver|gzclient)/ && $0 !~ /awk/ {print $1}
  /px4 / && $0 !~ /awk/ {print $1}
  /bin\/px4/ && $0 !~ /awk/ {print $1}
  /mavros_node/ && $0 !~ /awk/ {print $1}
  /uav_control_node/ && $0 !~ /awk/ {print $1}
  /external_fusion_node/ && $0 !~ /awk/ {print $1}
  /mission_node.py/ && $0 !~ /awk/ {print $1}
  /gazebo_vision_bridge.py/ && $0 !~ /awk/ {print $1}
  /lib\/rviz\/rviz/ && $0 !~ /awk/ {print $1}
' | xargs -r kill -9 || true
fuser -k 4560/tcp 14540/udp 14557/udp 14550/udp 2>/dev/null || true
sleep 3
echo stopped

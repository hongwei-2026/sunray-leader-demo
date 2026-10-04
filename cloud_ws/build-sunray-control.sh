#!/bin/bash
set -eo pipefail
export DEBIAN_FRONTEND=noninteractive
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
set +u
LOG=/root/autodl-tmp/build-sunray-control.log
exec > >(tee -a "$LOG") 2>&1

echo "===== $(date) build sunray_uav_control ====="

python3 - <<'PY'
from pathlib import Path
p = Path("/root/autodl-tmp/Sunray/General_Module/sunray_uav_control/CMakeLists.txt")
t = p.read_text()
t = t.replace("sunray_control_gencpp", "${catkin_EXPORTED_TARGETS}")
old = """## Generate added messages and services with any dependencies listed here
generate_messages(
  DEPENDENCIES
  geometry_msgs 
  nav_msgs
  sensor_msgs
  std_msgs
)
"""
if old in t:
    t = t.replace(old, "")
if "add_dependencies(UAVControl" not in t:
    t = t.replace(
        "add_library(UAVControl uav_control/UAVControl.cpp)\n",
        "add_library(UAVControl uav_control/UAVControl.cpp)\nadd_dependencies(UAVControl ${catkin_EXPORTED_TARGETS})\n",
    )
p.write_text(t)
print("patched CMakeLists")
pkg = Path("/root/autodl-tmp/Sunray/General_Module/sunray_uav_control/package.xml")
xml = pkg.read_text()
if "<depend>sunray_msgs</depend>" not in xml:
    xml = xml.replace(
        "  <buildtool_depend>catkin</buildtool_depend>",
        "  <buildtool_depend>catkin</buildtool_depend>\n"
        "  <depend>sunray_msgs</depend>\n"
        "  <depend>mavros</depend>\n"
        "  <depend>mavros_msgs</depend>\n"
        "  <depend>roscpp</depend>\n"
        "  <depend>geometry_msgs</depend>\n"
        "  <depend>nav_msgs</depend>\n"
        "  <depend>sensor_msgs</depend>\n"
        "  <depend>tf</depend>\n"
        "  <depend>tf2_ros</depend>\n"
        "  <depend>tf2_geometry_msgs</depend>\n",
    )
    pkg.write_text(xml)
    print("patched package.xml")
PY

mkdir -p /root/autodl-tmp/ws_sunray/src
ln -sfn /root/autodl-tmp/Sunray/General_Module/sunray_common/sunray_msgs /root/autodl-tmp/ws_sunray/src/sunray_msgs
ln -sfn /root/autodl-tmp/Sunray/General_Module/sunray_uav_control /root/autodl-tmp/ws_sunray/src/sunray_uav_control

mkdir -p /root/autodl-tmp/ws_mission/src/sunray_mission/launch
cp -f /root/autodl-tmp/px4_sitl_mission.launch /root/autodl-tmp/ws_mission/src/sunray_mission/launch/px4_sitl_mission.launch
cp -f /root/autodl-tmp/sitl_mavros.launch /root/autodl-tmp/ws_mission/src/sunray_mission/launch/sitl_mavros.launch
chmod +x /root/autodl-tmp/run-px4-mission.sh \
  /root/autodl-tmp/ws_mission/src/sunray_mission/scripts/*.py || true

source /opt/ros/noetic/setup.bash
cd /root/autodl-tmp/ws_sunray
if [ ! -f src/CMakeLists.txt ]; then
  catkin_init_workspace src || true
fi
catkin_make -j8 --pkg sunray_msgs
catkin_make -j8
echo "===== BUILD_OK $(date) ====="
ls -l devel/lib/sunray_uav_control/uav_control_node
ls /root/autodl-tmp/Sunray/General_Module/sunray_uav_control/config | head

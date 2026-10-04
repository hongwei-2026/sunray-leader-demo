#!/bin/bash
# Wait until iris exists in Gazebo. posix_sitl spawn often dies on restart.
set +u
source /opt/ros/noetic/setup.bash
source /root/autodl-tmp/ws_sunray/devel/setup.bash
source /root/autodl-tmp/ws_mission/devel/setup.bash --extend
export PX4_DIR=/root/autodl-tmp/sunray_px4
source "$PX4_DIR/Tools/simulation/gazebo-classic/setup_gazebo.bash" \
  "$PX4_DIR" "$PX4_DIR/build/px4_sitl_default"
SDF="$PX4_DIR/Tools/simulation/gazebo-classic/sitl_gazebo-classic/models/iris/iris.sdf"

iris_ok() {
  timeout 4 rosservice call /gazebo/get_model_state "{model_name: iris, relative_entity_name: world}" 2>/dev/null | grep -q "success: True"
}

for i in $(seq 1 20); do
  if iris_ok; then
    echo "[ensure-iris] iris already in gazebo (try $i)"
    exit 0
  fi
  if timeout 3 rosservice list 2>/dev/null | grep -q /gazebo/spawn_sdf_model; then
    echo "[ensure-iris] spawning iris (try $i)"
    timeout 20 rosrun gazebo_ros spawn_model -sdf -file "$SDF" -model iris -x 0 -y 0 -z 0.15 || true
    sleep 1
    if iris_ok; then
      echo "[ensure-iris] spawn ok"
      exit 0
    fi
  else
    echo "[ensure-iris] waiting gazebo spawn service (try $i)"
  fi
  sleep 2
done
echo "[ensure-iris] FAILED"
exit 1

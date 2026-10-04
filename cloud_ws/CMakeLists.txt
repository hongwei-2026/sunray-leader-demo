cmake_minimum_required(VERSION 3.0.2)
project(sunray_mission)

find_package(catkin REQUIRED COMPONENTS
  rospy
  std_msgs
  geometry_msgs
  nav_msgs
  visualization_msgs
  sunray_msgs
)

catkin_package()

catkin_install_python(PROGRAMS
  scripts/mission_node.py
  scripts/mock_uav.py
  scripts/gazebo_vision_bridge.py
  scripts/set_ekf_vision.py
  DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
)

install(DIRECTORY launch config rviz
  DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}
)

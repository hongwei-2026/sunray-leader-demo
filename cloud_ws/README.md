# sunray_mission

二次开发方向：**PX4 SITL 航点任务机**（仿真，不依赖真机）。

在官方话题 `/uav1/sunray/setup` 与 `/uav1/sunray/uav_control_cmd` 上增加任务层：

- YAML 航点（可改坐标、悬停、围栏，不用改代码）
- 电子围栏越界立即降落
- 航点超时立即降落
- RViz 显示计划航线、实际轨迹、围栏
- CSV 飞行日志

底层接 **PX4 SITL + MAVROS + sunray_uav_control**，不再用运动学 mock。

## 云上运行（AutoDL）

1. 打开 AutoDL 自定义服务 **6006**，URL 后面加 `/vnc.html`（VNC 密码只放在云主机本地，不入库）
2. 桌面里会有 RViz；Gazebo 默认无窗口（`gzserver`），避免把 SSH 打挂

```bash
bash /root/autodl-tmp/start-px4-mission.sh
```

停止：

```bash
bash /root/autodl-tmp/stop-px4-mission.sh
```

日志：`/root/autodl-tmp/px4-mission.log`  
轨迹：`/root/autodl-tmp/sunray_mission_run.csv`

围栏中止演示：把 launch 里 `mission_file` 换成 `mission_geofence_abort.yaml`。

## 仅 mock（不启 PX4）

```bash
source /opt/ros/noetic/setup.bash
source /root/autodl-tmp/ws_mission/devel/setup.bash
export DISPLAY=:1
roslaunch sunray_mission mission.launch
```

# PX4 SITL 二次开发截图（验收）

## 本次验收（2026-10-04）

| 文件 | 内容 |
| --- | --- |
| `16_terminal_start_command.png` | 云主机执行 `bash /root/autodl-tmp/start-px4-mission.sh` |
| `14_rviz_takeoff.png` | RViz：红框围栏 + 绿字 `TAKEOFF` |
| `15_rviz_wp3_of_4.png` | RViz：任务进行中 `WP 3/4` |

## 启动命令

```bash
bash /root/autodl-tmp/start-px4-mission.sh
```

日志：`/root/autodl-tmp/px4-mission.log`  
轨迹：`/root/autodl-tmp/sunray_mission_run.csv`  
可视化：AutoDL 自定义服务 **6006** → noVNC → RViz（Time 选 Off）

## 历史材料

| 文件 | 内容 |
| --- | --- |
| `01_terminal_restart.png` | 早期 restart 脚本截图 |
| `05_rviz_3d.png` / `06_rviz_window.png` | 围栏 + 计划航线 |
| `04_px4_mission_trajectory.png` / `10_px4_mission_trajectory_opt.png` | CSV 出图：起飞→航点→降落 |
| `sunray_mission_run.csv` / `sunray_mission_run_opt.csv` | 原始轨迹日志 |

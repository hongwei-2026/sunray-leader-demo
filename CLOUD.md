# 云主机怎么跑（你把机器信息给我之后按这个来）

你只需要给我这些（私聊就行，别公开）：

1. 系统：最好是 **Ubuntu 20.04**（官方 Sunray 用 ROS Noetic）  
2. 登录方式：`ssh user@ip` 或面板账号  
3. 有没有桌面 / 能不能开图形（Gazebo 仿真需要；没有就先跑逻辑 Demo）  
4. sudo 权限有没有  

---

## A. 没 ROS、只想先出 demo 图（任何 Linux 云都行）

```bash
cd ~/sunray-leader-demo   # 或 /root/sunray-leader-demo

# 无人机、小车分开跑
bash scripts/run_uav_demo.sh      # 只跑无人机
bash scripts/run_ugv_demo.sh      # 只跑无人车
# bash scripts/run_logic_demo.sh  # 两个都跑

# 可视化网页（GIF + 图）
bash scripts/serve_viz.sh
# AutoDL：自定义服务端口填 6006，用控制台给的链接打开
```

Windows 本机同样：

```powershell
cd D:\minda_mianshi\sunray-leader-demo
pip install -r requirements.txt
python demo\run_all.py
```

---

## B. 正式官方仿真（建议 Ubuntu 20.04）

```bash
cd sunray-leader-demo
bash scripts/bootstrap_sunray_u20.sh
# 编完后按脚本末尾提示跑 scripts_sim/...
```

无图形界面时，Gazebo/RViz 可能起不来——那时继续用 A，或加桌面/VNC。

---

## 目录分工

| 路径 | 干嘛 |
| --- | --- |
| `demo/` | 我写的任务逻辑仿真（云上立刻能跑） |
| `vendor/` | 云纵官方脚本副本，接 ROS 后用 |
| `scripts/run_logic_demo.sh` | 云上一键出图 |
| `scripts/bootstrap_sunray_u20.sh` | 云上拉 Sunray 装依赖编译 |

# Sunray 无人机 / 无人车 · Leader Demo 包

面向 GXMZU-AITECC 业务流里 **云纵无人机**、**智能车（Sunray UGV）** 两个空岗方向。  
民大组织仓目前还没有对应仓库，资料在云纵官方：

| 资源 | 链接 |
| --- | --- |
| 源码 | https://github.com/YunDrone-Team/Sunray |
| 文档 | https://wiki.yundrone.cn/ |
| 无人机官方例程 | `General_Module/sunray_tutorial/uav_python/takeoff_hover_land.py` |
| 无人车官方例程 | `General_Module/sunray_tutorial/ugv_python/ugv_circle_vel.py` |
| 仿真启动 | `scripts_sim/demo_takeoff_hover_land.sh`、`scripts_sim/sunray_ugv_sim.sh` |

---

## 这个包现在能给你什么

本机是 **Windows + WSL Ubuntu 26.04**，而官方栈是 **Ubuntu 20.04 + ROS Noetic + Gazebo**，整仓编译一时半会跑不通。

所以先做了两层：

1. **`demo/`（现在就能跑）**  
   任务阶段对齐官方例程（起飞悬停降落 / 绕圆回原点），生成轨迹图和 GIF，用来证明你已经吃透业务流程。
2. **`vendor/`（官方原脚本）**  
   从 Sunray 仓库拉下来的 Python / shell，接上 ROS 仿真或实机后直接改跑这些。

> 诚实说明：当前 `demo/` 是**任务逻辑仿真**，不是 Gazebo/实机飞控闭环。抢 leader 时要说清楚——「逻辑 demo 已通，下一步上官方仿真/实机」。

---

## 云主机（推荐）

你拿到云服务器后，把登录信息给我，或自己执行：

```bash
cd sunray-leader-demo
bash scripts/run_logic_demo.sh          # 立刻出图（不要 ROS）
# bash scripts/bootstrap_sunray_u20.sh  # 可选：Ubuntu 20.04 上装官方 Sunray
```

细节见 [CLOUD.md](./CLOUD.md)。

## 本机一分钟跑起来（Windows 也行）

```powershell
cd D:\minda_mianshi\sunray-leader-demo
pip install -r requirements.txt
python demo\run_all.py
```

产物在 `output/`：

- `uav_takeoff_hover_land.png` / `.gif` — 无人机：解锁→起飞→悬停→降落  
- `ugv_circle.png` / `.gif` — 无人车：就位→绕圆→回原点  

把这两张图/GIF 发群或做成简易 PPT，就是第一版 demo。

---

## 下一步：官方仿真（领先进度的正道）

建议单独搞一台 **Ubuntu 20.04**（实体机或虚拟机），不要硬刚 26.04：

```bash
# 1. 装 ROS Noetic（按 wiki「准备工作」）
# 2. 拉源码
git clone https://github.com/YunDrone-Team/Sunray.git
cd Sunray
# 3. 依赖与编译（仓库根目录脚本）
bash install_dependencies.sh
bash build.sh

# 4. 无人机仿真：起飞悬停降落
bash scripts_sim/demo_takeoff_hover_land.sh

# 5. 无人车仿真底盘
bash scripts_sim/sunray_ugv_sim.sh
# 另开终端跑绕圆（见 scripts_exp/ugv_circle.sh）
```

实机：社团有设备后再切 `scripts_exp/`，流程与仿真脚本同名系列。

---

## 目录

```
sunray-leader-demo/
  README.md
  requirements.txt
  demo/                 # 本机可跑的任务逻辑仿真
  vendor/               # 云纵官方脚本副本（MPL-2.0，来自 YunDrone-Team/Sunray）
  output/               # 运行后生成的图/GIF/CSV
```

---

## 跟老师/社长怎么说（可直接复制）

> 我对云纵无人机和智能车感兴趣。民大组织仓里暂时没有对应 repo，我按云纵官方 Sunray 资料先把两条基础业务流做了任务逻辑 demo（起飞悬停降落 + 无人车绕圆），产物在本地 `sunray-leader-demo/output/`。下一步需要：① 社里是否有私有资料/实机预约；② 我这边准备 Ubuntu 20.04 跑官方 `scripts_sim`。想竞 leader 的话我可以继续把仿真/实机 demo 补上。

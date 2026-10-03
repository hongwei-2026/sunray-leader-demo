#!/usr/bin/env bash
# 在 Ubuntu 20.04 云主机上准备官方 Sunray 仿真环境（ROS Noetic）
# 用法：bash scripts/bootstrap_sunray_u20.sh
# 注意：需要 sudo；整仓编译可能要较长时间与较大磁盘（建议 ≥40GB）
set -euo pipefail

if [[ "$(. /etc/os-release; echo $VERSION_ID)" != "20.04" ]]; then
  echo "警告：官方栈推荐 Ubuntu 20.04 + ROS Noetic。当前系统是 $(. /etc/os-release; echo $PRETTY_NAME)"
  echo "可以继续，但依赖失败概率很高。Ctrl+C 取消，或回车继续。"
  read -r _
fi

WORKDIR="${SUNRAY_HOME:-$HOME/sunray-ws}"
mkdir -p "$WORKDIR"
cd "$WORKDIR"

if [[ ! -d Sunray/.git ]]; then
  git clone --depth 1 https://github.com/YunDrone-Team/Sunray.git
fi
cd Sunray

echo "==> 安装依赖（仓库自带脚本）"
if [[ -f install_dependencies.sh ]]; then
  bash install_dependencies.sh
else
  echo "未找到 install_dependencies.sh，请按 https://wiki.yundrone.cn/ 手动装 ROS Noetic / mavros"
fi

echo "==> 编译"
if [[ -f build.sh ]]; then
  bash build.sh
else
  echo "未找到 build.sh，请按 wiki 进入 catkin/colcon 工作空间编译"
fi

cat <<EOF

编译完成后，在 Sunray 根目录试跑：

  # 无人机：起飞悬停降落（会开多个 gnome-terminal；无桌面云主机请改用 tmux 版或装桌面）
  bash scripts_sim/demo_takeoff_hover_land.sh

  # 无人车仿真底盘
  bash scripts_sim/sunray_ugv_sim.sh

无 GUI 云主机建议先跑本仓库逻辑 Demo：
  bash $(cd "$(dirname "$0")" && pwd)/run_logic_demo.sh

EOF

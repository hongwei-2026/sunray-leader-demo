# 山地急救参考算法（教师个人仓库）

本模块由教师授权放入公开的 hongwei-2026/sunray-leader-demo；学生可以看到参考解法。民大组织仓库只保存作业、规则和CI，不同步本模块reference中的算法。

实现包括三维可见图搜索、净空膨胀线段避障、期限优先与载荷调度、返航预算检查、目标改派、连续确认/悬停/投送/补给状态机。支持同一任务协议的三个关卡，没有硬编码标准航线。该启发式调度不保证全局最优。

运行：

```bash
python -m unittest discover -s rescue_reference/tests -v
python -m unittest discover -s rescue_reference/assignment/ci/tasks/rescue_offline/tests -v
python rescue_reference/run_regression.py
```

仅Python3.10标准库；不使用GPU，不启动ROS/Gazebo/PX4。assignment是本次作者新增的离线题目与裁判副本，用于可复现的独立CI，不依赖读取民大私有仓库，也不包含任何原场景模型、纹理、既有私有源码或下载凭据。

results/offline_report.json保存真实离线运行摘要。三个关卡×5种确定性墙体偏移，共15回合；另有3个规划单测和26个规则/协议反例。固定种子0的完成时间约34.8/169.4/364.6模型秒，这些是理想速度模型结果，不是无人机实际飞行时间。

限制：人工盒体不等同真实山地，速度无惯性、传感器和通信误差；任务优先级为课堂标签，所有事件公开；部分场景无可行调度时会安全返航或等待并最终报告失败，不保证解所有输入。控制接入、实际碰撞、实物投送与实时性能必须等GPU环境后再单独验证。

文件职责：reference/planner.py为三维路径搜索，policy.py为调度和控制状态机，main.py为JSONL入口；assignment为独立裁判和题目，tests为规划反例，run_regression.py为15回合批量回归。算法日志不参与组织评分器状态推进，不能通过改写自报成绩得分。

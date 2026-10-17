# 急救参考控制的状态反馈与损坏终止

对应个人issue #5、组织issue GXMZU-AITECC/yundrone-sunray150#212。此目录含教师参考控制，不能复制到组织任务仓。以develop为基线提交PR，不修改main。

## 云端现状

已在专用运行目录 `/root/autodl-tmp/rescue_sim_validation_20261017` 集成。现有 `scripts/run_level.sh level1|level2|level3` 调用 flight_feedback.py，后者复用 flight.py 中的规划调度与飞行接口。世界、碰撞模型、PX4配置沿用当前工程。

组织公开模块位于 `public_feedback/tasks/rescue_runtime` 与 `public_feedback/ci/tasks/rescue_offline`；个人仓库不复制它的模型、纹理或私有既有代码。需要教师在授权环境提供组织v2源码。

`flight.py` 是真实碰撞网格核验后路线的测试执行器，读取运行目录 routes.json；不是面向未知地图的在线规划器。本PR不上传这份教师路线。原个人离线参考算法仍由此前对应PR维护。本实现有真实物理状态辅助控制，因此成绩不能称为仅机载传感器的自主飞行。

## 文件职责

- flight_feedback.py：将参考控制事件、真实Gazebo状态和接触转给组织反馈模块，拦截毁坏状态。
- flight.py：已有控制实现的可审查源码，未改变目标/路径求解。
- reset_feedback.sh：显式 --new-episode 才执行，归档结果、只停止登记的专用进程，重新初始化后核验起降点和解除武装，再释放毁坏锁。
- collision_check.py：教师局部真实碰撞验证，在专用世界临时添加墙并清理，不是学生任务。会故意终止本轮，不能在学生正在运行时执行。
- install.py：复制源码与共享规则并编译插件，要求已有专用运行环境及授权组织源码；不会自动停止运行服务。

## 使用

正常运行 `bash /root/autodl-tmp/rescue_sim_validation_20261017/scripts/run_level.sh level1`。关卡二三分别换为level2、level3。

毁坏后必须由教师执行 `bash /root/autodl-tmp/rescue_sim_validation_20261017/scripts/reset_feedback.sh --new-episode`；不要仅删除锁文件，也不要在飞行中重置。停止输出、解除武装请求和暂停仅适用于这个本地回环地址的独立Gazebo实例，严禁用于真机。

面板显示完成、告警与终局；报告为evidence/feedback/feedback_report.json。证据归档至evidence/episodes。物理反馈是教学代理，未模拟电机逐步失效或机体碎裂。

## 低带宽观看

云端 `/rescue-low/vnc.html?autoconnect=1&resize=scale&path=websockify` 使用现有VNC鉴权，JPEG画质档2、压缩档2，原网页副本保留。Gazebo观察插件约25Hz实际节流，VNC上限30Hz、1280×720。修改后要重新连接网页才能重新协商画质；浏览器实际帧率需客户端指标验证，不拿服务器物理实时率冒充传输顺滑度。

源码安装后，如需复现桌面管理：manage.py加载libSmoothFollowV2.so并导出RESCUE_RUNTIME_ROOT；view.sh启动只读hud.py并传evidence/feedback；所有后台PID需记录start_ticks避免误停无关进程。manage.py、hud_manage.py、view.sh和follow脚本已随本目录提供，由install.py备份后安装。原配置必须与该专用测试目录一致；不是任意Gazebo工程的通用安装器。

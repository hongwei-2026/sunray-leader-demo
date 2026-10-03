# 无人机 / 小车 · 分别访问

## 云上命令

```bash
cd /root/sunray-leader-demo

# 需要重跑再生成图时：
bash scripts/run_uav_demo.sh
bash scripts/run_ugv_demo.sh

# 开两个可视化服务（会先释放旧端口）
bash scripts/serve_viz.sh
```

或单独开一个：

```bash
bash scripts/serve_uav_viz.sh   # 只开无人机 :6006
bash scripts/serve_ugv_viz.sh   # 只开小车   :6007
```

## AutoDL 怎么点出「链接」

控制台 → **自定义服务** → 加两条：

| 用途 | 端口 |
| --- | --- |
| 飞机（无人机） | **6006** |
| 小车（无人车） | **6007** |

保存后，控制台会各给一个可点开的网址——那就是你要的访问链接。  
（链接带你的实例临时域名，我这边看不到，以控制台显示为准。）

若提示 `Address already in use`：先执行一次 `bash scripts/serve_viz.sh`（脚本会清端口再开）。

## 本地已记住的图

- `showcase/uav/` — 无人机 png / gif / csv  
- `showcase/ugv/` — 小车 png / gif / csv  

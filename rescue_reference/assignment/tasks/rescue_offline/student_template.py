#!/usr/bin/env python3
# 功能文档：docs/learning/features/2026-10_急救离线作业与CI.md
"""学生入口模板：故意只悬停，不能完成任务；请自行实现。"""
import json
import sys

def decide(observation):
    # 在这里接入自己的算法，不要修改裁判或伪造状态。
    return {'velocity':[0,0,0],'action':'move'}

for line in sys.stdin:
    observation=json.loads(line)
    print(json.dumps(decide(observation)),flush=True)

#!/usr/bin/env python3
"""JSONL参考算法入口，stdout仅输出动作，诊断走stderr。"""
import json
import sys
from policy import Policy
policy=Policy()
for line in sys.stdin:
    observation=json.loads(line)
    print(json.dumps(policy.decide(observation),allow_nan=False),flush=True)

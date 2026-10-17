#!/usr/bin/env python3
"""个人仓库离线参考回归；不启动ROS、Gazebo、PX4或GPU。"""
import json
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'assignment/ci/tasks/rescue_offline'))
from run import run
reports=[];started=time.monotonic()
for level in ('level1','level2','level3'):
    for seed in range(5):
        report,events,_=run([sys.executable,str(ROOT/'reference/main.py')],ROOT/'assignment/tasks/rescue_offline',level,seed,timeout=120)
        if level=='level3':
            dispatched=[e for e in events if e['event']=='dispatch']
            report['dispatch_verified']=len(dispatched)==1 and abs(dispatched[0]['t']-120)<1e-6
            deliveries=[e for e in events if e['event']=='deliver' and e['accepted']]
            report['alternate_verified']=any(e['target']=='T04' and e['pad']=='alternate' for e in deliveries)
            report['rooftop_verified']=any(e['target']=='T05' and e['pad']=='primary' for e in deliveries)
            report['passed']=report['passed'] and all(report[k] for k in ('dispatch_verified','alternate_verified','rooftop_verified'))
        reports.append(report);print(json.dumps(report,ensure_ascii=False),flush=True)
summary={'mode':'offline_only_no_simulator','all_passed':all(r['passed'] for r in reports),'episodes':reports,'wall_time_s':round(time.monotonic()-started,3),'warning':'Synthetic AABB world and ideal velocity control. Not Gazebo/PX4 flight validation.'}
(ROOT/'results').mkdir(exist_ok=True)
(ROOT/'results/offline_report.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
sys.exit(0 if summary['all_passed'] else 1)

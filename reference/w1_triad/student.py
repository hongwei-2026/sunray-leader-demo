"""负责人个人参考实现的评测接口适配；不进入组织任务仓库。

启动/定位/落地由公共评测服务负责，私有路径和速度算法沿用 flight_paths.py。
输出严格 JSON Lines，诊断只走 stderr。
"""
import json
import math
import sys
sys.path.insert(0,'/submission')
from flight_paths import build, distance

route=None
progress=speed=0.
previous=None
last_position=None
for line in sys.stdin:
    event=json.loads(line)
    state=event['state']
    if route is None:
        route=build('circles' if event['case']=='four_orbits' else event['case'])
        previous=state['t']
    dt=max(0., min(.1,state['t']-previous))
    previous=state['t']
    actual=(state['x'],state['y'])
    actual_speed=distance(actual,last_position)/max(dt,.001) if last_position else 0.
    last_position=actual
    start=route.sample(0.)
    # 接合段：未靠近起点或仍在滑动时先悬停，避免 TASK_GEOMETRY 在入径瞬间超差。
    if progress<0.08 and (distance(actual,start)>0.12 or actual_speed>0.12):
        z_target=event['spec']['altitude_world_m']
        vz=max(-.35,min(.35,1.8*(z_target-state['z'])))
        reply={'seq':event['seq'],'position':[start[0],start[1],z_target],
               'velocity':[0.,0.,vz],'land':False}
        print(json.dumps(reply),flush=True)
        continue
    error=distance(actual,route.sample(progress))
    # 横向偏差大时冻结进度并拉回当前目标，防止沿错误方向继续推进。
    if error>0.28:
        speed=max(0.,speed-0.8*dt)
        wanted=0.
    else:
        wanted=route.speed_limit(progress)*max(0.,min(1.,(.30-error)/.2))
        speed+=max(-.55*dt,min(.15*dt,wanted-speed))
        progress=min(route.length,progress+max(0.,speed)*dt)
    target=route.sample(progress)
    a,b=route.sample(progress-.025),route.sample(progress+.025)
    norm=max(distance(a,b),1e-9)
    z_target=event['spec']['altitude_world_m']
    # PX4 水平机动时高度易飘；用垂直速度反馈压回题目高度。
    vz=max(-.35,min(.35,1.8*(z_target-state['z'])))
    land=progress>=route.length and distance(actual,(0.,0.))<.1 and actual_speed<.08
    vx=speed*(b[0]-a[0])/norm
    vy=speed*(b[1]-a[1])/norm
    reply={'seq':event['seq'],'position':[*target,z_target],
           'velocity':[vx,vy,vz], 'land':land}
    print(json.dumps(reply),flush=True)

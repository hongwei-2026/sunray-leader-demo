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
    error=distance(actual,route.sample(progress))
    wanted=route.speed_limit(progress)*max(0.,min(1.,(.45-error)/.25))
    speed+=max(-.5*dt,min(.3*dt,wanted-speed))
    progress=min(route.length,progress+max(0.,speed)*dt)
    target=route.sample(progress)
    a,b=route.sample(progress-.025),route.sample(progress+.025)
    norm=max(distance(a,b),1e-9)
    actual_speed=distance(actual,last_position)/max(dt,.001) if last_position else 0.
    last_position=actual
    land=progress>=route.length and distance(actual,(0.,0.))<.1 and actual_speed<.08
    reply={'seq':event['seq'],'position':[*target,event['spec']['altitude_world_m']],
           'velocity':[speed*(b[0]-a[0])/norm,speed*(b[1]-a[1])/norm,0.], 'land':land}
    print(json.dumps(reply),flush=True)

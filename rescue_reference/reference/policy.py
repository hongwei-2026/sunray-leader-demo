"""个人参考策略：容量/期限/返航预算调度及连续悬停状态机。"""
import math
from planner import route,length

class Policy:
    def __init__(self):
        self.mode='select';self.path=[];self.target=None;self.pad=None;self.destination=None
        self.hold_started=None;self.refills_before=0;self.known_active=set();self.reason=None

    def zero(self,op='move',**kw):return {'velocity':[0,0,0],'action':op,**kw}

    def base(self,o):
        p=list(o['common']['station']['return_pad']);p[2]+=0.5;return p

    def plan(self,o,p):
        return route(o['position'],p,o['world'],o['task']['ceiling_world_z_m'])

    def choose(self,o):
        candidates=[];task=o['task'];base=self.base(o)
        if o['inventory']<=0:return None
        for tid in o['active']:
            if tid in o['delivered']:continue
            for pad in task['allowed_pads'][tid]:
                p=list(o['targets'][tid]['position' if pad=='primary' else 'alternate']);p[2]+=1
                try:
                    path=self.plan(o,p)
                    outbound=length(o['position'],path)/task['max_speed_mps']
                    home=length(p,route(p,base,o['world'],task['ceiling_world_z_m']))/task['max_speed_mps']
                except ValueError:continue
                service=max(3,task['delivery_hover_s'])+2
                if outbound+service+home+50>task['sortie_airborne_budget_s']-o['airborne_s']:continue
                if o['t']+outbound+service>task['target_deadline_s'][tid]:continue
                # 期限优先，然后以实际避障路径长度选择主/备用点。
                candidates.append((task['target_deadline_s'][tid],outbound,tid,pad,p,path))
        return min(candidates) if candidates else None

    def go_base(self,o):
        self.target=None;self.pad=None;self.destination=self.base(o)
        self.path=self.plan(o,self.destination);self.mode='return';self.hold_started=None

    def decide(self,o):
        task=o['task'];active=set(o['active'])
        if self.known_active and active!=self.known_active and self.mode=='travel':
            # 新任务可改变目的地，不假定固定航点或预写路线。
            self.mode='select';self.path=[]
        self.known_active=active
        if self.mode=='select':
            if set(task['target_ids'])<=set(o['delivered']):self.go_base(o)
            else:
                candidate=self.choose(o)
                if candidate:
                    _,_,self.target,self.pad,self.destination,self.path=candidate;self.mode='travel';self.hold_started=None
                elif o['inventory']==0 or o['airborne_s']>1:
                    self.go_base(o)
                else:
                    return self.zero() # 等待未生效任务；不存在可行任务时由超时报告失败。
        if self.mode in ('travel','return'):
            while self.path and math.dist(o['position'],self.path[0])<0.015:self.path.pop(0)
            if self.path:
                p=self.path[0];delta=[p[i]-o['position'][i] for i in range(3)];d=math.sqrt(sum(v*v for v in delta))
                speed=min(task['max_speed_mps'],d/o['dt'])
                return {'velocity':[v/d*speed for v in delta],'action':'move'}
            self.hold_started=o['t'];self.mode='landing' if self.mode=='return' else 'hold'
        if self.mode=='hold':
            if o['t']-self.hold_started<max(3,task['delivery_hover_s'])+0.2:return self.zero()
            if [self.target,self.pad] not in o['observed']:
                return self.zero('observe',target=self.target,pad=self.pad)
            if self.target not in o['delivered']:
                return self.zero('deliver',target=self.target,pad=self.pad)
            self.mode='select';return self.zero()
        if self.mode=='landing':
            if o['t']-self.hold_started<5.2:return self.zero()
            if set(task['target_ids'])<=set(o['delivered']):return self.zero('finish')
            if not task['refill_allowed']:return self.zero()
            self.refills_before=o['refills'];self.mode='refill'
        if self.mode=='refill':
            if o['refills']>self.refills_before:
                self.mode='select';return self.zero()
            return self.zero('refill')
        return self.zero()

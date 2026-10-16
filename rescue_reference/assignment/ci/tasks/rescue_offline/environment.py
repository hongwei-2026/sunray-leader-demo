# 功能文档：docs/learning/features/2026-10_急救离线作业与CI.md
"""公开测试环境与规则裁判。输入是动作，不接受学生自报位置或分数。"""
import copy
import json
import math
from pathlib import Path

class Rejected(ValueError):
    pass

def vector(v):
    if not isinstance(v,list) or len(v)!=3 or any(isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) for x in v):
        raise Rejected('velocity must contain three finite numbers')
    return [float(x) for x in v]

def distance(a,b):
    return math.dist(a,b)

def intersects(a,b,lo,hi):
    """线段与闭合AABB精确slab判定，防止单步穿墙。"""
    left,right=0.0,1.0
    for i in range(3):
        d=b[i]-a[i]
        if abs(d)<1e-12:
            if a[i]<lo[i] or a[i]>hi[i]: return False
        else:
            p,q=sorted(((lo[i]-a[i])/d,(hi[i]-a[i])/d))
            left,right=max(left,p),min(right,q)
            if left>right: return False
    return True

class Environment:
    def __init__(self,root,level,seed=0):
        root=Path(root)
        load=lambda name:json.loads((root/(name+'.json')).read_text(encoding='utf-8-sig'))
        self.common,self.task,self.world=load('common'),load(level),load('mock_world')
        self.targets={t['id']:t for t in load('targets')}
        self.dt=self.world['dt_s']
        self.seed=int(seed)
        # 固定种子只改变人工测试墙位置，不改真实任务坐标。
        shift=(self.seed%5-2)*0.4
        self.world['obstacles'][0]['min'][0]+=shift
        self.world['obstacles'][0]['max'][0]+=shift
        self.position=list(self.common['station']['spawn_reference'])
        self.velocity=[0.,0.,0.]
        self.t=0.;self.airborne=0.;self.inventory=self.task['initial_payload']
        self.active=set(self.task['available_from_start']);self.delivered=set();self.observed=set()
        self.dwell={};self.confirm={};self.landing_dwell=0.;self.refill_dwell=0.
        self.landed=True;self.done=False;self.failure=None;self.finished=False
        self.events=[];self.invalid=0;self.refills=0;self.dispatch_sent=False;self.distance=0.

    def pad(self,tid,pad):
        target=self.targets[tid]
        return list(target['position'] if pad=='primary' else target['alternate'])

    def approach(self,tid,pad):
        p=self.pad(tid,pad);p[2]+=self.common['delivery']['hover_height_above_pad_m'];return p

    def allowed(self,tid,pad):
        return tid in self.active and pad in self.task['allowed_pads'].get(tid,[])

    def observe(self):
        return copy.deepcopy({'schema_version':1,'t':self.t,'dt':self.dt,'position':self.position,'velocity':self.velocity,'inventory':self.inventory,'airborne_s':self.airborne,'landed':self.landed,'active':sorted(self.active),'delivered':sorted(self.delivered),'observed':[list(x) for x in sorted(self.observed)],'refills':self.refills,'done':self.done,'task':self.task,'common':self.common,'targets':self.targets,'world':self.world,'last_event':self.events[-1] if self.events else None})

    def event(self,kind,**data):
        self.events.append({'t':round(self.t,6),'event':kind,**data})

    def fail(self,reason):
        self.done=True;self.failure=reason;self.event('failed',reason=reason)

    def step(self,action):
        if self.done: raise Rejected('episode is terminal')
        if not isinstance(action,dict) or set(action)-{'velocity','action','target','pad'}: raise Rejected('unknown action fields')
        v=vector(action.get('velocity',[0,0,0]))
        op=action.get('action','move')
        if op not in ('move','observe','deliver','refill','finish'): raise Rejected('unknown operation')
        speed=math.sqrt(sum(x*x for x in v))
        # 离线安全接口拒绝超限动作，不能依靠裁判截断速度蒙混。
        if speed>self.task['max_speed_mps']+1e-9:
            self.fail('speed_limit');return
        a=self.position; b=[a[i]+v[i]*self.dt for i in range(3)]
        radius=self.common['clearance_sphere_radius_m']
        bounds=self.world['bounds'];ceiling=self.task['ceiling_world_z_m']
        if not (bounds[0]+radius<=b[0]<=bounds[1]-radius and bounds[2]+radius<=b[1]<=bounds[3]-radius and radius<=b[2]<=ceiling-radius):
            self.fail('geofence');return
        for ob in self.world['obstacles']:
            if intersects(a,b,[x-radius for x in ob['min']],[x+radius for x in ob['max']]):
                self.fail('collision:'+ob['id']);return
        # 洪水波形区域按0.1m子段保守检查；z<3且靠近河道时拒绝。
        for k in range(1,max(1,math.ceil(distance(a,b)/0.1))+1):
            f=k/max(1,math.ceil(distance(a,b)/0.1));p=[a[i]+(b[i]-a[i])*f for i in range(3)]
            if p[2]-radius<3 and abs(p[0]-(-18+5*math.sin(p[1]/37)))<5+radius*1.2:
                self.fail('flood_zone');return
        self.position=b;self.velocity=v;self.distance+=distance(a,b);self.t=round(self.t+self.dt,8)
        base=self.common['station']['return_pad']; base_center=[base[0],base[1],base[2]+0.5]
        at_base=math.hypot(b[0]-base[0],b[1]-base[1])<=1 and abs(b[2]-base_center[2])<=0.15 and speed<=0.15
        spawn=self.common['station']['spawn_reference']
        at_spawn=distance(b,spawn)<=0.15 and speed<=0.15 and self.airborne==0
        self.landed=at_base or at_spawn
        self.landing_dwell=self.landing_dwell+self.dt if at_base else 0.
        if not self.landed: self.airborne+=self.dt
        if self.airborne>self.task['sortie_airborne_budget_s']+1e-8:
            self.fail('airborne_budget');return
        if not self.dispatch_sent:
            for event in self.task['dispatch_events']:
                if self.t+1e-8>=event['at_elapsed_s']:
                    self.active.update(event['activate_targets']);self.dispatch_sent=True
                    self.event('dispatch',event_id=event['event_id'])
        for tid in self.task['target_ids']:
            for pad in self.task['allowed_pads'][tid]:
                key=(tid,pad);p=self.approach(tid,pad)
                near=self.allowed(tid,pad) and distance(b,self.pad(tid,pad))<=3 and speed<=0.5
                self.confirm[key]=self.confirm.get(key,0)+self.dt if near else 0.
                tol=min(self.targets[tid]['drop_radius_m'],self.task['horizontal_tolerance_cap_m'])
                stable=near and math.hypot(b[0]-p[0],b[1]-p[1])<=tol and abs(b[2]-p[2])<=0.3 and speed<=0.25
                self.dwell[key]=self.dwell.get(key,0)+self.dt if stable else 0.
        if op in ('observe','deliver'):
            tid=action.get('target');pad=action.get('pad','primary');key=(tid,pad)
            valid=self.allowed(tid,pad) and tid not in self.delivered
            if op=='observe':
                valid=valid and self.confirm.get(key,0)+1e-8>=3
                if valid: self.observed.add(key)
            else:
                valid=valid and key in self.observed and self.inventory>0 and self.dwell.get(key,0)+1e-8>=self.task['delivery_hover_s'] and self.t<=self.task['target_deadline_s'].get(tid,-1)+1e-8 and self.task['sortie_airborne_budget_s']-self.airborne>45
                if valid: self.delivered.add(tid);self.inventory-=1
            if not valid: self.invalid+=1
            self.event(op,accepted=bool(valid),target=tid,pad=pad)
        if op=='refill':
            valid=self.task['refill_allowed'] and at_base and self.landing_dwell+1e-8>=5
            if valid:
                self.refill_dwell+=self.dt
                if self.refill_dwell+1e-8>=self.task['refill_hold_s']:
                    self.inventory=self.task['payload_capacity'];self.airborne=0.;self.refills+=1;self.refill_dwell=0.
                    self.event('refill_complete')
            else:
                self.refill_dwell=0.;self.invalid+=1;self.event('refill',accepted=False)
        else: self.refill_dwell=0.
        if op=='finish':
            if self.delivered==set(self.task['target_ids']) and self.landing_dwell+1e-8>=5:
                self.done=True;self.finished=True;self.event('finish',accepted=True)
            else: self.invalid+=1;self.event('finish',accepted=False)
        if self.t>self.task['time_limit_s']+1e-8: self.fail('time_limit')

    def report(self):
        completion=sum(self.task['delivery_points_each'][tid] for tid in self.delivered)
        score=completion+(20 if self.finished else 0)+max(0,10-2*self.invalid)
        if self.finished: score+=10*max(0,1-self.t/self.task['time_limit_s'])
        else: score=min(59,score)
        if self.failure: score=0
        return {'kind':'offline_kinematic_only','level':self.task['id'],'seed':self.seed,'passed':bool(self.finished and not self.failure and score>=75),'score':round(score,3),'elapsed_s':round(self.t,3),'distance_m':round(self.distance,3),'delivered':sorted(self.delivered),'refills':self.refills,'invalid_requests':self.invalid,'failure':self.failure,'simulator_tested':False}

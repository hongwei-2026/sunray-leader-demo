import os,time,json,math,pathlib,csv,argparse,subprocess,fcntl
import rospy
from gazebo_msgs.msg import ModelStates,ContactsState
from rosgraph_msgs.msg import Clock
from pymavlink import mavutil
R=pathlib.Path('/root/autodl-tmp/rescue_sim_validation_20261017');TASK=pathlib.Path('/root/autodl-tmp/rescue_missions_20261015/rescue_missions/config')
class Flight:
    def __init__(self,level):
        self.level=level;self.task=json.loads((TASK/(level+'.json')).read_text());self.targets={t['id']:t for t in json.loads((TASK/'targets.json').read_text())};self.routes=json.loads((R/'routes.json').read_text());self.t=0.;self.p=None;self.v=None;self.q=None;self.state_wall=0.;self.pos=None;self.hb=None;self.landed=None;self.poswall=0.;self.hbwall=0.;self.extwall=0.;self.events=[];self.badcontacts=[];self.enabled=False;self.phase='connect';self.inventory=self.task['initial_payload'];self.delivered=[];self.refills=0;self.owns=False;self.start_sim=None;self.last_log=-1;self.last_hb=0;self.last_diag=0;self.sortie=0;self.origin=None;self.over_speed=None;self.wall_begin=time.monotonic();self.contacts=0;self.max_error=0;self.max_speed=0;self.dispatch=False;self.flight_sim=0
        stamp=time.strftime('%Y%m%d-%H%M%S');self.out=R/'evidence'/(level+'-'+stamp);self.file=self.out.with_suffix('.csv').open('w');self.writer=csv.writer(self.file);self.writer.writerow(['sim_s','elapsed_s','wall_s','phase','x','y','z','vx','vy','vz','target_x','target_y','target_z','tracking_error','payload','landed','armed'])
        self.tx=mavutil.mavlink_connection('udpout:127.0.0.1:18570',source_system=245);self.tx.port.bind(('127.0.0.1',14550));rospy.init_node('rescue_px4_validation',anonymous=True,disable_signals=True)
        rospy.Subscriber('/clock',Clock,lambda m:setattr(self,'t',m.clock.to_sec()),queue_size=1);rospy.Subscriber('/gazebo/model_states',ModelStates,self.state,queue_size=1);rospy.Subscriber('/rescue_validation/contacts',ContactsState,self.contact,queue_size=100)
    def state(self,m):
        if 'iris' in m.name:
            i=m.name.index('iris');p=m.pose[i].position;v=m.twist[i].linear;self.p=(p.x,p.y,p.z);self.v=(v.x,v.y,v.z);self.q=m.pose[i].orientation;self.state_wall=time.monotonic()
    def contact(self,m):
        if not self.enabled:return
        for c in m.states:
            self.contacts+=1
            p=self.p
            permitted=p and p[2]<8.40 and any(math.hypot(p[0]-x,p[1]+95)<2.0 for x in [-113,-101]) and self.phase in ['takeoff','land','landed','refill','connect']
            if not permitted:self.badcontacts.append({'t':self.t,'phase':self.phase,'a':c.collision1_name,'b':c.collision2_name})
    def cmd(self,c,*p):self.tx.mav.command_long_send(1,1,c,0,*(list(p)+[0.]*(7-len(p))))
    def drain(self):
        for _ in range(1000):
            m=self.tx.recv_match(blocking=False)
            if m is None:break
            if m.get_srcSystem()!=1:continue
            k=m.get_type();now=time.monotonic()
            if k=='LOCAL_POSITION_NED':self.pos=m;self.poswall=now
            elif k=='HEARTBEAT' and m.autopilot!=8:self.hb=m;self.hbwall=now
            elif k=='EXTENDED_SYS_STATE':self.landed=m.landed_state;self.extwall=now
            elif k=='STATUSTEXT':print('PX4',m.text,flush=True)
    def armed(self):return self.hb and bool(self.hb.base_mode&128)
    def offboard(self):return self.hb and (self.hb.custom_mode>>16)&255==6
    def elapsed(self):return 0 if self.start_sim is None else self.t-self.start_sim
    def event(self,name,**extra):
        e={'event':name,'elapsed_s':self.elapsed(),'sim_s':self.t,'position':self.p,**extra};self.events.append(e);print(json.dumps(e),flush=True)
    def tick(self,target=None,velocity=(0.,0.,0.)):
        start=time.monotonic();self.drain()
        if start-self.last_hb>.5:self.tx.mav.heartbeat_send(6,8,0,0,0);self.last_hb=start
        if target is not None and self.pos is not None and self.p is not None:
            # Ground-truth assisted ENU->NED calibration is explicitly a test fixture.
            off=(self.pos.x-self.p[1],self.pos.y-self.p[0],self.pos.z+self.p[2])
            self.tx.mav.set_position_target_local_ned_send(int(start*1000)&0xffffffff,1,1,1,64|128|256|1024|2048,target[1]+off[0],target[0]+off[1],off[2]-target[2],velocity[1],velocity[0],-velocity[2],0,0,0,0,0)
        if self.enabled:
            if start-self.state_wall>2 or start-self.poswall>2 or start-self.hbwall>3:raise RuntimeError('Stale simulator or MAVLink telemetry')
            if self.badcontacts:raise RuntimeError('Forbidden aircraft collision '+str(self.badcontacts[0]))
            if self.elapsed()>self.task['time_limit_s']:raise RuntimeError('Task time limit')
            if self.phase not in ['land','landed','refill','connect'] and (not self.armed() or not self.offboard()):raise RuntimeError('OFFBOARD or arming lost')
            p=self.p;speed=math.sqrt(sum(x*x for x in self.v));self.max_speed=max(self.max_speed,speed)
            if abs(p[0])+.8>155 or abs(p[1])+.8>155 or p[2]+.8>self.task['ceiling_world_z_m']:raise RuntimeError('Geofence violation')
            if 21.2<=p[0]<=45.8 and 3.2<=p[1]<=30.8 and p[2]<=38.8:raise RuntimeError('Landslide exclusion')
            if abs(p[0]-(-18+5*math.sin(p[1]/37)))<5.8 and p[2]<3.8:raise RuntimeError('Flood exclusion')
            if speed>self.task['max_speed_mps']:
                if self.over_speed is None:self.over_speed=self.t
                if self.t-self.over_speed>1:raise RuntimeError('Speed limit')
            else:self.over_speed=None
            if self.phase not in ['refill','landed'] and self.t-self.sortie>self.task['sortie_airborne_budget_s']:raise RuntimeError('Sortie budget')
            if self.level=='level3' and self.elapsed()>=120 and not self.dispatch:self.dispatch=True;self.event('dispatch',target='T04',allowed_pad='alternate')
        if self.p and self.t-self.last_log>=.065:
            target=target or self.p;error=math.dist(self.p,target);self.max_error=max(self.max_error,error);self.writer.writerow([self.t,self.elapsed(),start-self.wall_begin,self.phase,*self.p,*self.v,*target,error,self.inventory,self.landed,bool(self.armed())]);self.file.flush();self.last_log=self.t
        if start-self.last_diag>20 and self.p:print('STATE',self.level,round(self.elapsed(),1),self.phase,[round(x,2) for x in self.p],flush=True);self.last_diag=start
        time.sleep(max(0,.04-(time.monotonic()-start)))
    def wait(self,pred,seconds,target=None):
        start=self.t if self.t>0 else None;wall=time.monotonic()
        while (start is None or self.t-start<seconds) and time.monotonic()-wall<max(40,seconds*5):
            self.tick(target)
            if start is None and self.t>0:start=self.t
            if pred():return
        raise RuntimeError('Timeout '+self.phase)
    def hold(self,p,seconds,tolerance=.20):
        stable=None;beg=self.t;wall=time.monotonic()
        while self.t-beg<seconds+35 and time.monotonic()-wall<(seconds+35)*4:
            self.tick(p);ok=math.dist(p,self.p)<tolerance and math.sqrt(sum(v*v for v in self.v))<.20
            if ok:
                if stable is None:stable=self.t
                if self.t-stable>=seconds:return
            else:stable=None
        raise RuntimeError('Stable hover not achieved')
    def connect(self):
        self.cmd(511,32,20000);self.cmd(511,245,100000);self.tx.mav.request_data_stream_send(1,1,0,30,1)
        self.wait(lambda:self.p is not None and self.pos is not None and self.hb is not None and self.landed is not None,30)
        if self.armed():raise RuntimeError('Vehicle already armed')
        if min(math.hypot(self.p[0]-x,self.p[1]+95) for x in [-113,-101])>1 or abs(self.p[2]-8.254)>.2:raise RuntimeError('Not on rescue station')
    def takeoff(self):
        self.phase='connect';p=(*self.p[:2],11.2)
        for _ in range(60):self.tick(p)
        self.tx.mav.set_mode_send(1,1,6<<16);self.wait(self.offboard,8,p);self.cmd(400,1);self.owns=True;self.wait(self.armed,12,p)
        self.phase='takeoff';self.sortie=self.t
        if self.start_sim is None:self.start_sim=self.t;self.event('start')
        self.enabled=True;self.hold(p,2,.25);self.event('takeoff_complete');return 'takeoff' if self.p[0]<-107 else 'base'
    def path(self,a,b):
        k=a+'|'+b
        if k in self.routes['routes']:return self.routes['routes'][k]['points']
        k=b+'|'+a
        if k in self.routes['routes']:return list(reversed(self.routes['routes'][k]['points']))
        raise RuntimeError('No certified route '+a+' '+b)
    def distance(self,a,b):return sum(math.dist(x,y) for x,y in zip(self.path(a,b),self.path(a,b)[1:]))
    def travel(self,a,b):
        self.phase='travel';path=self.path(a,b);self.event('travel_begin',destination=b)
        for dest in path[1:]:
            origin=self.p;length=math.dist(origin,dest);progress=0.;last=self.t;wall=time.monotonic();speed=1.65
            while math.dist(self.p,dest)>.16:
                dt=max(0,min(.2,self.t-last));last=self.t
                progress=min(length,progress+speed*dt)
                commanded=tuple(origin[i]+(dest[i]-origin[i])*progress/max(length,1e-9) for i in range(3))
                if math.dist(self.p,commanded)>1.0:progress=max(0,progress-speed*dt)
                self.tick(commanded,tuple(speed*(dest[i]-origin[i])/max(length,1e-9) for i in range(3)) if progress<length else (0.,0.,0.))
                if time.monotonic()-wall>length/0.2+60:raise RuntimeError('Route tracking timeout')
            self.hold(dest,.5,.22)
        self.hold(path[-1],1,.20);self.event('travel_complete',destination=b)
    def deliver(self,tid,pad):
        self.phase='delivery';p=list(self.targets[tid]['position' if pad=='primary' else 'alternate']);p[2]+=1
        self.hold(p,max(3,self.task['delivery_hover_s'])+.2,min(.20,self.task['horizontal_tolerance_cap_m']/2))
        if self.elapsed()>self.task['target_deadline_s'][tid]:raise RuntimeError('Target deadline '+tid)
        if tid=='T04' and not self.dispatch:raise RuntimeError('Inactive target')
        if pad not in self.task['allowed_pads'][tid] or self.inventory<1 or tid in self.delivered:raise RuntimeError('Invalid delivery')
        self.event('observe',target=tid,pad=pad,accepted=True);self.inventory-=1;self.delivered.append(tid);self.event('delivery_accepted',target=tid,pad=pad,logical_only=True)
    def land(self):
        self.phase='land';self.cmd(21);beg=self.t;wall=time.monotonic();last=0
        while self.t-beg<70 and time.monotonic()-wall<200:
            self.tick()
            ground=self.landed==1 and time.monotonic()-self.extwall<2 and self.p[2]<8.40 and math.hypot(self.p[0]+101,self.p[1]+95)<1 and math.sqrt(sum(x*x for x in self.v))<.15
            if ground and not self.armed():self.phase='landed';self.event('land');self.wait_still(5);return
            if self.t-last>5:
                self.cmd(400,0) if ground else self.cmd(21);last=self.t
        raise RuntimeError('Landing not confirmed')
    def wait_still(self,seconds):
        start=self.t
        while self.t-start<seconds:
            self.tick()
            if math.sqrt(sum(x*x for x in self.v))>.15 or self.p[2]>8.4:raise RuntimeError('Unstable ground contact')
    def run(self):
        result={'level':self.level,'success':False,'physics':'Gazebo Classic 11 + PX4 1.13.3 iris','navigation':'known actual collision mesh, ground-truth-assisted position feedback','delivery':'logical only; no physical package','visual_recognition_tested':False}
        try:
            self.connect();current=self.takeoff()
            while set(self.delivered)!=set(self.task['target_ids']):
                if self.inventory==0:
                    self.travel(current,'base');self.land();self.phase='refill';self.event('refill_begin');self.wait_still(self.task['refill_hold_s']);self.inventory=self.task['payload_capacity'];self.refills+=1;self.event('refill_complete');current=self.takeoff();continue
                choices=[]
                for tid in self.task['target_ids']:
                    if tid in self.delivered or (tid=='T04' and self.elapsed()<120):continue
                    for pad in self.task['allowed_pads'][tid]:
                        point=tid+'_'+pad
                        try:d=self.distance(current,point);back=self.distance(point,'base')
                        except RuntimeError:continue
                        if self.elapsed()+d/1.65+15>self.task['target_deadline_s'][tid]:continue
                        if self.t-self.sortie+(d+back)/1.65+60>self.task['sortie_airborne_budget_s']:continue
                        choices.append((self.task['target_deadline_s'][tid],d,tid,pad,point))
                if not choices:raise RuntimeError('No feasible schedule within mission budget')
                _,_,tid,pad,point=min(choices);self.travel(current,point);self.deliver(tid,pad);current=point
            self.travel(current,'base');self.land();self.event('finish');result['success']=True
        except Exception as e:
            result['error']=str(e);self.event('abort',reason=str(e));print('FAILED',str(e),flush=True)
            if self.owns and self.armed():
                self.enabled=False;self.phase='emergency_land';self.cmd(21)
                try:self.wait(lambda:self.landed==1 and not self.armed(),80)
                except Exception as landing_error:result['recovery_error']=str(landing_error)
        finally:
            result.update(elapsed_sim_s=self.elapsed(),wall_s=time.monotonic()-self.wall_begin,delivered=self.delivered,refills=self.refills,events=self.events,forbidden_contacts=self.badcontacts[:30],contact_messages=self.contacts,max_measured_speed=self.max_speed,final_position=self.p,landed_state=self.landed,armed=bool(self.armed()),telemetry=str(self.out.with_suffix('.csv')))
            self.out.with_suffix('.result.json').write_text(json.dumps(result,indent=2));(R/'evidence'/(self.level+'_latest.json')).write_text(json.dumps(result,indent=2));self.file.close();self.tx.close();print('RESULT',json.dumps({k:v for k,v in result.items() if k!='events'}),flush=True)
        return result['success']
if __name__=='__main__':
    import sys
    lock=open(str(R/'controller.lock'),'w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    flight=Flight(sys.argv[1]);raise SystemExit(0 if flight.run() else 1)
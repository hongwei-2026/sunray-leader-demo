#!/usr/bin/env python3
"""Personal reference adapter; planning remains in the existing flight module."""
import os,sys,json,pathlib,fcntl,time
import rospy
from std_srvs.srv import Empty
from flight import Flight,R,TASK
ROOT=R/'public_feedback'
sys.path.insert(0,str(ROOT/'tasks/rescue_runtime'))
from feedback import RuntimeFeedback

class FeedbackFlight(Flight):
 def __init__(self,level):
  if (R/'destroyed.lock').exists():raise RuntimeError('无人机已毁，本轮锁定。请教师重置仿真后开始新一轮。')
  task=json.loads((TASK/(level+'.json')).read_text())
  common=json.loads((TASK/'common.json').read_text())
  targets={x['id']:x for x in json.loads((TASK/'targets.json').read_text())}
  self.feedback=RuntimeFeedback(R/'evidence/feedback',task,common,targets)
  self.stop_latched=False
  super().__init__(level)
 def state(self,m):
  super().state(m)
  if self.p is not None and self.started_feedback():
   self.feedback.phase=self.phase
   self.feedback.sample(self.t,self.p,self.v,self.landed==1 and self.phase in ('landed','refill','connect'))
 def started_feedback(self):return hasattr(self,'feedback')
 def contact(self,m):
  if not self.enabled or self.p is None:return
  self.contacts+=len(m.states)
  self.feedback.contact(m.states,self.p,self.v,self.q,self.phase)
 def event(self,name,**extra):
  super().event(name,**extra)
  self.feedback.t=self.t;self.feedback.event(name,**extra)
 def tick(self,target=None,velocity=(0.,0.,0.)):
  if self.feedback.damage.destroyed and not self.stop_latched:
   self.stop_latched=True;self.enabled=False;self.owns=False
   (R/'destroyed.lock').write_text(json.dumps({'sim_s':self.t,'reason':'teaching_damage_threshold'}))
   # This only stops this dedicated simulator; never invoke on a physical aircraft.
   self.cmd(400,0,21196)
   until=time.monotonic()+.6
   while time.monotonic()<until:
    self.drain()
    if not self.armed():break
    time.sleep(.02)
   self.feedback.log({'event':'disarm_requested','confirmed':not bool(self.armed())})
   try:
    rospy.wait_for_service('/gazebo/pause_physics',2)
    rospy.ServiceProxy('/gazebo/pause_physics',Empty)()
   except Exception as exc:
    self.feedback.log({'event':'pause_failed','reason':str(exc)})
   raise RuntimeError('无人机已毁：已停止控制并请求暂停本轮仿真')
  if self.feedback.path.failure and self.enabled:raise RuntimeError(self.feedback.path.failure)
  super().tick(target,velocity)
 def run(self):
  ok=super().run()
  result=self.feedback.finish_report()
  print('FEEDBACK_RESULT',json.dumps(result,ensure_ascii=False),flush=True)
  return bool(ok and result['passed'])

if __name__=='__main__':
 lock=open(str(R/'controller.lock'),'a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 f=FeedbackFlight(sys.argv[1]);sys.exit(0 if f.run() else 1)

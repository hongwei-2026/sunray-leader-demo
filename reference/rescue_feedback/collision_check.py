import json,time,sys
import rospy
from gazebo_msgs.srv import SpawnModel,DeleteModel,GetPhysicsProperties
from geometry_msgs.msg import Pose
from flight_feedback import FeedbackFlight,R
class CollisionCheck(FeedbackFlight):
 def travel(self,a,b):
  self.phase='travel';self.event('travel_begin',destination='temporary_collision_test')
  p=Pose();p.position.x=self.p[0]+1.4;p.position.y=self.p[1];p.position.z=11.2;p.orientation.w=1
  sdf='<sdf version="1.6"><model name="feedback_test_wall"><static>true</static><link name="wall"><collision name="obstacle"><geometry><box><size>.12 4 4</size></box></geometry></collision><visual name="obstacle"><geometry><box><size>.12 4 4</size></box></geometry><material><ambient>1 .15 .05 1</ambient></material></visual></link></model></sdf>'
  r=rospy.ServiceProxy('/gazebo/spawn_sdf_model',SpawnModel)('feedback_test_wall',sdf,'',p,'world')
  if not r.success:raise RuntimeError(r.status_message)
  target=(self.p[0]+3,self.p[1],11.2);deadline=time.monotonic()+25
  while time.monotonic()<deadline:self.tick(target)
  raise RuntimeError('Collision test failed to produce terminal contact')
if __name__=='__main__':
 import fcntl
 lock=open(R/'controller.lock','a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 f=CollisionCheck('level1')
 try:
  f.run()
  paused=rospy.ServiceProxy('/gazebo/get_physics_properties',GetPhysicsProperties)().pause
  result={'destroyed':f.feedback.damage.destroyed,'locked':(R/'destroyed.lock').exists(),'damage':f.feedback.damage.damage,'armed':bool(f.armed()),'paused':bool(paused),'control_enabled':f.enabled,'stop_latched':f.stop_latched}
  print('ACTUAL_COLLISION_CHECK',json.dumps(result))
  (R/'evidence/collision_final_check.json').write_text(json.dumps(result,indent=2))
  if not (result['destroyed'] and result['locked'] and result['paused'] and result['stop_latched'] and not result['armed'] and not result['control_enabled']):sys.exit(2)
 finally:
  try:rospy.ServiceProxy('/gazebo/delete_model',DeleteModel)('feedback_test_wall')
  except Exception as e:print('TEMP_OBSTACLE_CLEANUP',str(e))

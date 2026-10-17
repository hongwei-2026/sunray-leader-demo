#!/usr/bin/env bash
set -eo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
if [ "${1:-}" != --new-episode ]; then
 echo 'Teacher only: pass --new-episode to archive current result and restart the dedicated simulator.'; exit 2
fi
mkdir -p "$ROOT/evidence/episodes"
STAMP=$(date +%Y%m%d-%H%M%S)
if [ -d "$ROOT/evidence/feedback" ]; then cp -a "$ROOT/evidence/feedback" "$ROOT/evidence/episodes/$STAMP"; fi
bash "$ROOT/scripts/stop.sh"
sleep 3
bash "$ROOT/scripts/start.sh"
source /opt/ros/noetic/setup.bash
source "$ROOT/env.sh"
export RESCUE_RUNTIME_ROOT="$ROOT"
/usr/bin/python3 - <<'PY'
import os,pathlib,rospy,math,time,json
from gazebo_msgs.srv import GetModelState
from pymavlink import mavutil
R=pathlib.Path(os.environ['RESCUE_RUNTIME_ROOT'])
rospy.init_node('teacher_reset_verify',anonymous=True)
rospy.wait_for_service('/gazebo/get_model_state',30)
get=rospy.ServiceProxy('/gazebo/get_model_state',GetModelState)
for _ in range(30):
 s=get('iris','world');p=s.pose.position
 if s.success and math.hypot(p.x+113,p.y+95)<1 and abs(p.z-8.254)<.2:break
 time.sleep(.5)
else:raise RuntimeError('Spawn not verified; destroyed lock preserved')
m=mavutil.mavlink_connection('udpout:127.0.0.1:18570',source_system=246);m.port.bind(('127.0.0.1',14550));m.mav.heartbeat_send(6,8,0,0,0)
h=m.wait_heartbeat(timeout=12)
if h is None or h.base_mode & 128:raise RuntimeError('Disarmed state not verified; lock preserved')
m.close()
lock=R/'destroyed.lock'
if lock.exists():lock.rename(R/'evidence/episodes'/('destroyed-'+str(time.time_ns())+'.json'))
status={'version':2,'level':'待选择','state':'ready','phase':'ready','notice':'新一轮已就绪，请选择任务','warning':False,'elapsed_s':0,'distance_m':0,'health':100,'delivered':[],'total':0,'inventory':0,'updated_wall_s':time.time(),'result':None}
feedback=R/'evidence/feedback';feedback.mkdir(parents=True,exist_ok=True)
tmp=feedback/'live_status.tmp';tmp.write_text(json.dumps(status,ensure_ascii=False));os.replace(tmp,feedback/'live_status.json')
print('New episode: spawn and disarmed state verified')
PY
bash "$ROOT/scripts/view.sh"

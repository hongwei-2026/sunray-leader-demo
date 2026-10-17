import pathlib,subprocess,json,os,fcntl
R=pathlib.Path(__file__).resolve().parents[1]
lock=open(R/'hud.lock','a');fcntl.flock(lock,fcntl.LOCK_EX)
def identity(pid):
 try:return pathlib.Path('/proc/%d/stat'%pid).read_text().split()[21]
 except FileNotFoundError:return None
f=R/'extra_processes.json';data=json.loads(f.read_text());p=data.get('hud')
if p and identity(p['pid'])==p['start_ticks']:print('HUD already running')
else:
 env=os.environ.copy();env['DISPLAY']=':17'
 with open(R/'evidence/hud.log','a') as log:
  p=subprocess.Popen(['/usr/bin/python3',str(R/'public_feedback/tasks/rescue_runtime/hud.py'),str(R/'evidence/feedback')],env=env,stdout=log,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,start_new_session=True)
 data['hud']={'pid':p.pid,'start_ticks':identity(p.pid)};f.write_text(json.dumps(data,indent=2));print('HUD started',p.pid)

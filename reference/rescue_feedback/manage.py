import os,json,pathlib,signal,time,sys,subprocess,fcntl
R=pathlib.Path(__file__).resolve().parents[1]
def identity(pid):
    try:return pathlib.Path('/proc/%d/stat'%pid).read_text().split()[21]
    except FileNotFoundError:return None
mode=sys.argv[1]
if mode=='stop':
    lock=open(str(R/'controller.lock'),'a')
    try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:raise SystemExit('Flight controller active; wait for landing before stopping')
    subprocess.run(["bash",str(R/"scripts/follow.sh"),"off"],check=True)
    # Stop only recorded processes, and reject PID reuse.
    data=json.loads((R/'processes.json').read_text())
    if (R/'extra_processes.json').exists():data.update(json.loads((R/'extra_processes.json').read_text()))
    for name in ['controller','recorder','hud','viewer','px4','gzserver','roscore','display']:
        p=data.get(name)
        if p and identity(p['pid'])==p['start_ticks']:
            os.kill(p['pid'],signal.SIGTERM);print('Stopped owned process',name,p['pid'])
elif mode=='view':
    data=json.loads((R/'extra_processes.json').read_text()) if (R/'extra_processes.json').exists() else {}
    p=data.get('viewer')
    if p and identity(p['pid'])==p['start_ticks']:print('Viewer already running',p['pid']);raise SystemExit(0)
    env=os.environ.copy();env['RESCUE_RUNTIME_ROOT']=str(R);env['VGL_FPS']='30';env['LD_LIBRARY_PATH']=str(R/'gpu_runtime/lib')+':'+env.get('LD_LIBRARY_PATH','');env['__EGL_VENDOR_LIBRARY_FILENAMES']=str(R/'nvidia_egl.json')
    display=data.get('display')
    if not display or identity(display['pid'])!=display['start_ticks']:
        import socket
        sock=socket.socket();sock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1);sock.bind(('127.0.0.1',5917));sock.close()
        log_display=open(R/'evidence/display.log','a')
        display_proc=subprocess.Popen(['Xtigervnc',':17','-geometry','1280x720','-depth','24','-rfbauth','/root/.vnc/passwd','-rfbport','5917','-localhost','-SecurityTypes','VncAuth','-FrameRate','30'],stdout=log_display,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,start_new_session=True)
        data['display']={'pid':display_proc.pid,'start_ticks':identity(display_proc.pid)};time.sleep(2)
        if display_proc.poll() is not None:raise RuntimeError('Display failed; read evidence/display.log')
    log=open(R/'evidence/gzclient_gpu.log','a');p=subprocess.Popen(['vglrun','-d','egl0','gzclient','--verbose','-g','/root/autodl-tmp/rescue_sim_validation_20261017/scripts/libSmoothFollowV2.so'],env=env,stdout=log,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,start_new_session=True)
    data['viewer']={'pid':p.pid,'start_ticks':identity(p.pid)};(R/'extra_processes.json').write_text(json.dumps(data,indent=2));print('Viewer started',p.pid)
else:raise SystemExit('Use stop or view')
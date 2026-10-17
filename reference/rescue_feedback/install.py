#!/usr/bin/env python3
"""Install this reference adapter into an existing dedicated rescue simulation."""
import argparse,fcntl,pathlib,shutil,subprocess,sys,time
p=argparse.ArgumentParser();p.add_argument('--runtime',type=pathlib.Path,required=True);p.add_argument('--assignment',type=pathlib.Path,required=True);a=p.parse_args()
R=a.runtime.resolve();A=a.assignment.resolve();HERE=pathlib.Path(__file__).resolve().parent
if not (R/'env.sh').is_file() or not (R/'scripts/run_level.sh').is_file():p.error('Existing rescue simulator required')
for f in ['tasks/rescue_runtime/feedback.py','ci/tasks/rescue_offline/scoring.py','tasks/rescue_runtime/smooth_follow.cc']:
 if not (A/f).is_file():p.error('Assignment v2 source is incomplete: '+f)
lock=open(R/'controller.lock','a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
backup=R/'evidence'/('before-feedback-install-'+time.strftime('%Y%m%d-%H%M%S'));backup.mkdir(parents=True)
for name in ['flight.py','flight_feedback.py','reset_feedback.sh','collision_check.py','manage.py','hud_manage.py','view.sh','run_level.sh','follow_manage.py','follow.sh']:
 dst=R/'scripts'/name
 if dst.exists():shutil.copy2(dst,backup/name)
 shutil.copy2(HERE/name,dst)
for rel in ['tasks/rescue_runtime','ci/tasks/rescue_offline']:
 shutil.copytree(A/rel,R/'public_feedback'/rel,dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
subprocess.run(['bash',str(A/'tasks/rescue_runtime/build_plugin.sh'),str(R/'scripts/libSmoothFollowV2.so')],check=True)
print('Installed source, display management and plugin. Restart owned viewer after the current flight; run scripts/view.sh. Existing scene, PX4 and routes.json are prerequisites; no running service was stopped.')

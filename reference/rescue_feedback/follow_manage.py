import pathlib,sys
R=pathlib.Path(__file__).resolve().parents[1]
mode=sys.argv[1] if len(sys.argv)>1 else 'on'
f=R/'follow.enabled'
if mode=='on':
 f.touch();print('Smooth render-frame following enabled')
elif mode=='off':
 if f.exists():f.unlink()
 print('Following off; free mouse camera enabled')
else:raise SystemExit('Use on or off')

import ast,types,unittest,tempfile,pathlib,time
P=pathlib.Path(__file__).resolve().parents[1]/'flight_feedback.py'
class Stop(unittest.TestCase):
 def test_destroyed_stops_before_setpoint(self):
  source=ast.parse(P.read_text(encoding='utf-8'));node=next(n for n in source.body if isinstance(n,ast.ClassDef));method=next(n for n in node.body if isinstance(n,ast.FunctionDef) and n.name=='tick')
  cls=ast.ClassDef(name='Adapter',bases=[],keywords=[],body=[method],decorator_list=[]);tree=ast.fix_missing_locations(ast.Module(body=[cls],type_ignores=[]))
  calls=[]
  with tempfile.TemporaryDirectory() as tmp:
   ros=types.SimpleNamespace(wait_for_service=lambda *a: calls.append('wait'),ServiceProxy=lambda *a:lambda:calls.append('paused'))
   ns={'R':pathlib.Path(tmp),'json':__import__('json'),'time':time,'rospy':ros,'Empty':object}
   exec(compile(tree,'adapter','exec'),ns);a=ns['Adapter']();a.stop_latched=False;a.enabled=True;a.owns=True;a.t=10
   a.feedback=types.SimpleNamespace(damage=types.SimpleNamespace(destroyed=True),log=lambda e:calls.append(e['event']))
   a.cmd=lambda *v:calls.append(v);a.drain=lambda:None;a.armed=lambda:False
   with self.assertRaisesRegex(RuntimeError,'无人机已毁'):a.tick((1,2,3))
   self.assertTrue(a.stop_latched);self.assertFalse(a.enabled);self.assertFalse(a.owns)
   self.assertIn((400,0,21196),calls);self.assertIn('paused',calls);self.assertTrue((pathlib.Path(tmp)/'destroyed.lock').exists())
 def test_shell_lock_before_unpause(self):
  s=(P.parent/'run_level.sh').read_text(encoding='utf-8')
  self.assertLess(s.index('destroyed.lock'),s.index('unpause_physics'))
if __name__=='__main__':unittest.main()

# 功能文档：docs/learning/features/2026-10_急救离线作业与CI.md
"""规则单元测试仅做局部状态夹具，不提供完整任务解法。"""
import copy
import math
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from environment import Environment,Rejected,intersects
from run import run
ROOT=Path(__file__).resolve().parents[4]/'tasks/rescue_offline'

class Rules(unittest.TestCase):
    def env(self,level='level1'):return Environment(ROOT,level)
    def hold(self,e,seconds):
        for _ in range(math.ceil(seconds/e.dt)):e.step({'velocity':[0,0,0]})
    def position_at(self,e,tid,pad='primary'):
        e.position=e.approach(tid,pad)
    def test_nonfinite(self):
        for v in ([float('nan'),0,0],[float('inf'),0,0],[True,0,0],[0,0],['1',0,0]):
            with self.assertRaises(Rejected):self.env().step({'velocity':v})
    def test_teleport_injection(self):
        with self.assertRaises(Rejected):self.env().step({'position':[0,0,0],'score':100})
    def test_overspeed(self):
        e=self.env();e.step({'velocity':[4,0,0]});self.assertEqual(e.failure,'speed_limit')
    def test_observation_copy(self):
        e=self.env();o=e.observe();o['inventory']=999;o['task']['max_speed_mps']=999
        self.assertEqual(e.inventory,1);self.assertEqual(e.task['max_speed_mps'],3)
    def test_swept_collision(self):
        self.assertTrue(intersects([-2,0,0],[2,0,0],[-.1,-1,-1],[.1,1,1]))
        e=self.env();e.position=[-66,-40,10];e.step({'velocity':[3,0,0]})
        self.assertTrue(e.failure.startswith('collision'))
    def test_clearance_geofence(self):
        e=self.env();e.position=[154.1,-90,10];e.step({'velocity':[1,0,0]});self.assertEqual(e.failure,'geofence')
    def test_ceiling(self):
        e=self.env();e.position=[-100,-90,39.2];e.step({'velocity':[0,0,1]});self.assertEqual(e.failure,'geofence')
    def test_flood(self):
        e=self.env();e.position=[-18,-100,2];e.step({'velocity':[0,0,0]});self.assertEqual(e.failure,'flood_zone')
    def test_no_hover_no_delivery(self):
        e=self.env();self.position_at(e,'T01');e.step({'action':'deliver','target':'T01'});self.assertEqual(e.inventory,1)
    def test_no_confirm_no_delivery(self):
        e=self.env();self.position_at(e,'T01');self.hold(e,4);e.step({'action':'deliver','target':'T01'});self.assertFalse(e.delivered)
    def test_valid_single_delivery_and_duplicate(self):
        e=self.env();self.position_at(e,'T01');self.hold(e,4)
        e.step({'action':'observe','target':'T01'});e.step({'action':'deliver','target':'T01'});e.step({'action':'deliver','target':'T01'})
        self.assertEqual(e.delivered,{'T01'});self.assertEqual(e.inventory,0);self.assertEqual(e.invalid,1)
    def test_empty_inventory(self):
        e=self.env();self.position_at(e,'T01');self.hold(e,4);e.observed.add(('T01','primary'));e.inventory=0
        e.step({'action':'deliver','target':'T01'});self.assertFalse(e.delivered)
    def test_hover_interruption(self):
        e=self.env();self.position_at(e,'T01');self.hold(e,2.8);e.step({'velocity':[0.3,0,0]});self.hold(e,0.4)
        self.assertLess(e.dwell[('T01','primary')],1)
    def test_deadline(self):
        e=self.env();self.position_at(e,'T01');self.hold(e,4);e.observed.add(('T01','primary'));e.t=481
        e.step({'action':'deliver','target':'T01'});self.assertFalse(e.delivered)
    def test_dispatch_and_closed_pad(self):
        e=self.env('level3');e.t=119.6;e.step({});self.assertNotIn('T04',e.active);e.step({});self.assertIn('T04',e.active)
        self.assertFalse(e.allowed('T04','primary'));self.assertTrue(e.allowed('T04','alternate'))
        self.assertEqual(len([x for x in e.events if x['event']=='dispatch']),1)
    def test_rooftop_alt_not_allowed(self):self.assertFalse(self.env('level3').allowed('T05','alternate'))
    def test_refill_wrong_place(self):
        e=self.env('level2');e.inventory=0;e.step({'action':'refill'});self.assertEqual(e.inventory,0)
    def test_refill_hold_and_reset(self):
        e=self.env('level2');p=e.common['station']['return_pad'];e.position=[p[0],p[1],p[2]+.5];e.inventory=0;e.airborne=100
        self.hold(e,5.2)
        for _ in range(20):e.step({'action':'refill'})
        e.step({});self.assertEqual(e.refill_dwell,0)
        for _ in range(100):e.step({'action':'refill'})
        self.assertEqual(e.inventory,2);self.assertEqual(e.refills,1);self.assertEqual(e.airborne,0)
    def test_airborne_budget(self):
        e=self.env();e.airborne=300;e.position=[-100,-80,20];e.step({});self.assertEqual(e.failure,'airborne_budget')
    def test_finish_needs_targets(self):
        e=self.env();p=e.common['station']['return_pad'];e.position=[p[0],p[1],p[2]+.5];self.hold(e,6);e.step({'action':'finish'});self.assertFalse(e.finished)
    def test_timeout_is_not_success(self):
        e=self.env();e.t=600;e.step({});self.assertFalse(e.report()['passed']);self.assertEqual(e.report()['score'],0)
    def test_terminal_cannot_resume(self):
        e=self.env();e.fail('collision')
        with self.assertRaises(Rejected):e.step({})

class Protocol(unittest.TestCase):
    def exercise(self,code):
        return run([sys.executable,'-c',code],ROOT,'level1',timeout=2,step_timeout=.3)[0]
    def test_crash(self):self.assertFalse(self.exercise('raise RuntimeError()')['passed'])
    def test_no_read_no_hang(self):self.assertEqual(self.exercise('import time;time.sleep(10)')['failure'],'action_timeout')
    def test_oversized(self):self.assertIn('OVERSIZED',self.exercise("print('x'*70000,flush=True)")['failure'])
    def test_non_json(self):self.assertTrue(self.exercise("print('not json',flush=True)")['failure'].startswith('invalid_action'))

if __name__=='__main__':unittest.main()

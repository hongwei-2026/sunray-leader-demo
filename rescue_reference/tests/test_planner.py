import math
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'reference'))
from planner import route,blocked

class PlannerTests(unittest.TestCase):
    def test_direct(self):
        self.assertEqual(route([0,0,3],[5,0,3],{'obstacles':[],'bounds':[-10,10,-10,10]},10),[[5,0,3]])
    def test_wall_detour_segments_clear(self):
        world={'obstacles':[{'min':[2,-2,0],'max':[3,2,8]}],'bounds':[-10,10,-10,10]}
        path=route([0,0,3],[5,0,3],world,8)
        self.assertGreater(len(path),1);a=[0,0,3]
        for b in path:
            self.assertFalse(blocked(a,b,[1.2,-2.8,-.8],[3.8,2.8,8.8]));a=b
        self.assertEqual(path[-1],[5,0,3])
    def test_unreachable(self):
        world={'obstacles':[{'min':[2,-10,0],'max':[3,10,20]}],'bounds':[-5,5,-5,5]}
        with self.assertRaises(ValueError):route([0,0,3],[4,0,3],world,8)

if __name__=='__main__':unittest.main()

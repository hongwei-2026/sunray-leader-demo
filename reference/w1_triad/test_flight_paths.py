"""几何回归：覆盖旧版穿障起飞段、任务形状与绕圈完整性。"""
import math
import unittest
from flight_paths import OBSTACLES, build, connector, distance, safe, segment_distance


class GeometryTests(unittest.TestCase):
    def test_original_diagonal_is_rejected(self):
        self.assertFalse(safe((0, 0), (3.5, 3.5)))
        path = connector((0, 0), (3.5, 3.5))
        self.assertTrue(all(safe(a, b) for a, b in zip(path, path[1:])))

    def test_all_segments_including_home_are_safe(self):
        for mode in ('square', 'figure8', 'circles'):
            with self.subTest(mode=mode):
                route = build(mode)
                self.assertEqual(route.points[0], (0., 0.))
                self.assertEqual(route.points[-1], (0., 0.))
                self.assertTrue(all(safe(a, b) for a, b in zip(route.points, route.points[1:])))
                self.assertLess(route.length, 45.)

    def test_figure_eight_crosses_home_and_has_two_lobes(self):
        route = build('figure8')
        _, begin, end = route.labels[0]
        points = route.points[begin:end+1]
        self.assertLess(distance(points[len(points)//2], (0, 0)), 1e-8)
        self.assertGreater(max(x for x, y in points), 3.9)
        self.assertLess(min(x for x, y in points), -3.9)
        self.assertGreater(max(y for x, y in points), .9)
        self.assertLess(min(y for x, y in points), -.9)

    def test_each_orbit_is_a_full_unmodified_circle(self):
        route = build('circles')
        self.assertEqual(len(route.labels), 4)
        for (_, begin, end), center in zip(route.labels, OBSTACLES):
            points = route.points[begin:end+1]
            for p in points:
                self.assertAlmostEqual(distance(p, center), 1.35)
            angles = [math.atan2(y-center[1], x-center[0]) for x, y in points]
            total = sum((b-a+math.pi) % (2*math.pi)-math.pi for a, b in zip(angles, angles[1:]))
            self.assertAlmostEqual(total, 2*math.pi)

    def test_mid_segment_collision_not_hidden_by_endpoints(self):
        self.assertAlmostEqual(segment_distance((0, 1.5), (3, 1.5), (1.5, 1.5)), 0.)

    def test_brakes_before_square_corner(self):
        route = build('square')
        self.assertLess(route.speed_limit(3.5-.4), route.speed_limit(1.))
        self.assertLess(route.speed_limit(3.5), .25)


if __name__ == '__main__':
    unittest.main()

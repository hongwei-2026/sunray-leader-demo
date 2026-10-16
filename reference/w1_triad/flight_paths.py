"""三任务几何规划；所有坐标为场景 ENU 米。
功能档案：docs/learning/features/2026-10_云端三轨迹修复.md。
云端部署副本见同目录 flight-repair.md。
"""
import bisect
import heapq
import math

OBSTACLES = [(1.5, 1.5), (-1.5, 1.5), (-1.5, -1.5), (1.5, -1.5)]
CLEARANCE = 1.20


def distance(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def segment_distance(a, b, p):
    dx, dy = b[0] - a[0], b[1] - a[1]
    u = max(0., min(1., ((p[0]-a[0])*dx + (p[1]-a[1])*dy) / max(dx*dx+dy*dy, 1e-12)))
    return distance((a[0]+u*dx, a[1]+u*dy), p)


def safe(a, b):
    # 检查线段而非只检查端点；半径已经包含机体和跟踪误差预留。
    return all(segment_distance(a, b, o) >= CLEARANCE for o in OBSTACLES)


def connector(a, b):
    """仅对任务间连接段使用可见图最短路，不推移任务本身的曲线。"""
    if safe(a, b):
        return [a, b]
    nodes = [a, b] + [(x+1.35*math.cos(t*math.pi/16), y+1.35*math.sin(t*math.pi/16))
                      for x, y in OBSTACLES for t in range(32)]
    edges = [[] for _ in nodes]
    for i, p in enumerate(nodes):
        for j in range(i):
            if safe(p, nodes[j]):
                d = distance(p, nodes[j])
                edges[i].append((j, d))
                edges[j].append((i, d))
    costs, prev, queue = {0: 0.}, {}, [(0., 0)]
    while queue:
        cost, i = heapq.heappop(queue)
        if cost != costs[i]:
            continue
        if i == 1:
            path = [1]
            while path[-1] != 0:
                path.append(prev[path[-1]])
            return [nodes[k] for k in reversed(path)]
        for j, d in edges[i]:
            if cost+d < costs.get(j, float('inf')):
                costs[j], prev[j] = cost+d, i
                heapq.heappush(queue, (cost+d, j))
    raise ValueError('No collision-free connector')


def build(mode):
    points, labels = [(0., 0.)], []
    def append(route, label):
        points.extend(connector(points[-1], route[0])[1:])
        start = len(points)-1
        points.extend(route[1:])
        labels.append((label, start, len(points)-1))
    if mode == 'square':
        append([(0., 3.5), (3.5, 3.5), (3.5, -3.5), (-3.5, -3.5), (-3.5, 3.5), (0., 3.5)], 'square')
    elif mode == 'figure8':
        # 三次正弦让中心连接段穿过锥桶之间的走廊，而非穿过锥桶。
        append([(4*math.sin(t), 3*math.sin(t)**3*math.cos(t))
                for t in [2*math.pi*k/480 for k in range(481)]], 'figure8')
    elif mode == 'circles':
        for i, (x, y) in enumerate(OBSTACLES):
            angle = [-math.pi/2, 0., math.pi/2, math.pi][i]
            append([(x+1.35*math.cos(angle+2*math.pi*k/160),
                     y+1.35*math.sin(angle+2*math.pi*k/160)) for k in range(161)], 'orbit_'+str(i+1))
    else:
        raise ValueError('Unknown mode: '+mode)
    points.extend(connector(points[-1], (0., 0.))[1:])
    if not all(safe(a, b) for a, b in zip(points, points[1:])):
        raise ValueError('Unsafe mission segment')
    return Route(points, labels)


class Route:
    def __init__(self, points, labels):
        self.points, self.labels = points, labels
        self.lengths = [0.]
        for a, b in zip(points, points[1:]):
            self.lengths.append(self.lengths[-1]+distance(a, b))
        self.length = self.lengths[-1]

    def sample(self, progress):
        progress = max(0., min(self.length, progress))
        i = min(len(self.points)-2, max(0, bisect.bisect_right(self.lengths, progress)-1))
        a, b = self.points[i:i+2]
        length = distance(a, b)
        u = (progress-self.lengths[i])/max(length, 1e-12)
        return (a[0]+u*(b[0]-a[0]), a[1]+u*(b[1]-a[1]))

    def speed_limit(self, progress):
        # PX4 SITL 跟踪滞后约 0.3–0.4 m；上限与曲率刹停更保守，避免 TASK_GEOMETRY。
        # 提前查看 1.5 m 内的曲率，以 v² = v_end² + 2ad 反推可刹停速度。
        # 方形直角更易切角超差；整体再降速并提前刹停。
        limit = .30
        for k in range(36):
            ahead = .05*k
            future = min(self.length, progress+ahead)
            turn = self._curve_speed(future)
            limit = min(limit, math.sqrt(turn*turn+2*.15*ahead))
        return min(limit, max(.04, math.sqrt(2*.15*max(0., self.length-progress))))

    def _curve_speed(self, progress):
        a, b, c = (self.sample(progress+d) for d in (-.18, 0., .18))
        ab, bc = (b[0]-a[0], b[1]-a[1]), (c[0]-b[0], c[1]-b[1])
        den = max(distance(a, b)*distance(b, c), 1e-9)
        angle = math.acos(max(-1., min(1., (ab[0]*bc[0]+ab[1]*bc[1])/den)))
        return min(.30, math.sqrt(.10/max(angle/.18, .01)))

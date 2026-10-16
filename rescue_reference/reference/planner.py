"""个人参考实现：三维可见图与最短路，不进入组织作业仓库。"""
import heapq
import math

def blocked(a,b,lo,hi):
    lower,upper=0.,1.
    for i in range(3):
        delta=b[i]-a[i]
        if abs(delta)<1e-12:
            if not lo[i]<=a[i]<=hi[i]:return False
        else:
            enter,leave=sorted(((lo[i]-a[i])/delta,(hi[i]-a[i])/delta))
            lower,upper=max(lower,enter),min(upper,leave)
            if lower>upper:return False
    return True

def route(start,goal,world,ceiling,clearance=0.8):
    """已知人工AABB地图下的可见图搜索；没有真实地形或感知。"""
    start,goal=tuple(start),tuple(goal)
    boxes=[([x-clearance for x in ob['min']],[x+clearance for x in ob['max']]) for ob in world['obstacles']]
    def free(a,b):return not any(blocked(a,b,lo,hi) for lo,hi in boxes)
    if free(start,goal):return [list(goal)]
    heights={start[2],goal[2],min(ceiling-clearance-0.1,max(start[2],goal[2])+3)}
    heights.update(hi[2]+0.2 for lo,hi in boxes if hi[2]+0.2<ceiling-clearance)
    nodes=[start,goal]
    bounds=world['bounds']
    for lo,hi in boxes:
        for x in (lo[0]-0.2,hi[0]+0.2):
            for y in (lo[1]-0.2,hi[1]+0.2):
                for z in sorted(heights):
                    p=(x,y,z)
                    if bounds[0]+clearance<=x<=bounds[1]-clearance and bounds[2]+clearance<=y<=bounds[3]-clearance and clearance<=z<=ceiling-clearance and free(p,p):
                        nodes.append(p)
    costs={0:0.};prev={};heap=[(math.dist(start,goal),0.,0)];closed=set()
    while heap:
        _,cost,u=heapq.heappop(heap)
        if u in closed:continue
        if u==1:
            ids=[1]
            while ids[-1]!=0:ids.append(prev[ids[-1]])
            return [list(nodes[i]) for i in reversed(ids[:-1])]
        closed.add(u)
        for v,b in enumerate(nodes):
            if v==u or v in closed:continue
            new=cost+math.dist(nodes[u],b)
            if new<costs.get(v,float('inf')) and free(nodes[u],b):
                costs[v]=new;prev[v]=u
                heapq.heappush(heap,(new+math.dist(b,goal),new,v))
    raise ValueError('no feasible route in synthetic map')

def length(start,path):
    total=0.
    for p in path:total+=math.dist(start,p);start=p
    return total

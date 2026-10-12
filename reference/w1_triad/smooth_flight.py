#!/usr/bin/env python3
"""云端 PX4 连续轨迹演示；中文架构与参数说明见 flight-repair.md。

功能档案：docs/learning/features/2026-10_云端三轨迹修复.md。
只适用于已确认的 W1 场景，禁止直接用于实机。任务定义位于 flight_paths.py。
"""
import argparse
import csv
import fcntl
import json
import math
from pathlib import Path
import subprocess
import time

from pymavlink import mavutil
from flight_paths import OBSTACLES, build, distance

ALT = .65
PERIOD = .05


class Flight:
    def __init__(self, output):
        self.tx = mavutil.mavlink_connection('udpout:127.0.0.1:18570', source_system=245)
        # 固定同一发送/接收端口，避免 PX4 记住上一次进程的临时 UDP 端口。
        self.tx.port.bind(('127.0.0.1', 14550))
        self.position = self.hb = self.landed = None
        self.position_time = self.hb_time = 0.
        self.landed_time = 0.
        self.last_heartbeat = 0.
        self.system, self.component = 1, 1
        self.owns_control = False
        self.start = time.monotonic()
        self.origin = (0., 0., 0.)
        self.samples = []
        self.file = output.open('w', newline='')
        self.csv = csv.writer(self.file)
        self.csv.writerow(['wall_s', 'phase', 'progress_m', 'target_x', 'target_y', 'actual_x', 'actual_y', 'alt', 'error_m', 'min_cone_center_m', 'vx', 'vy'])

    def command(self, command, *params):
        values = list(params)+[0.]*(7-len(params))
        self.tx.mav.command_long_send(self.system, self.component, command, 0, *values)

    def drain(self):
        # 接收队列全部清空，只用最新位置；不能让阻塞收包拖慢控制发布。
        for connection in (self.tx,):
            for _ in range(1000):
                m = connection.recv_match(blocking=False)
                if m is None:
                    break
                if m.get_srcSystem() != self.system:
                    continue
                kind = m.get_type()
                now = time.monotonic()
                if kind == 'HEARTBEAT' and m.autopilot != 8:
                    self.hb, self.hb_time = m, now
                elif kind == 'LOCAL_POSITION_NED':
                    self.position, self.position_time = m, now
                elif kind == 'EXTENDED_SYS_STATE':
                    self.landed = m.landed_state
                    self.landed_time = now

    def tick(self, target, velocity=(0., 0.), phase='hold', progress=0.):
        begin = time.monotonic()
        if begin-self.last_heartbeat > .8:
            self.tx.mav.heartbeat_send(6, 8, 0, 0, 0)
            self.last_heartbeat = begin
        # 位置和速度同时生效：位置修正误差，切向速度减少逐点减速。
        self.tx.mav.set_position_target_local_ned_send(
            int((begin-self.start)*1000) & 0xffffffff, self.system, self.component,
            mavutil.mavlink.MAV_FRAME_LOCAL_NED, 64|128|256|1024|2048,
            target[1]+self.origin[0], target[0]+self.origin[1], self.origin[2]-target[2],
            velocity[1], velocity[0], 0., 0., 0., 0., 0., 0.)
        self.drain()
        if self.position is not None:
            p = self.position
            actual = (p.y-self.origin[1], p.x-self.origin[0])
            altitude = self.origin[2]-p.z
            error = distance(actual, target)
            clearance = min(distance(actual, o) for o in OBSTACLES)
            self.csv.writerow([round(begin-self.start, 3), phase, progress, *target[:2], *actual, altitude, error, clearance, p.vy, p.vx])
            self.file.flush()
            self.samples.append((phase, error, clearance, altitude))
        time.sleep(max(0., PERIOD-(time.monotonic()-begin)))

    def wait(self, predicate, timeout, target, phase):
        deadline = time.monotonic()+timeout
        while time.monotonic() < deadline:
            self.tick(target, phase=phase)
            if predicate():
                return
        raise RuntimeError(phase+' timeout')

    def fresh(self):
        return (self.position is not None and self.hb is not None and
                time.monotonic()-self.position_time < .8 and
                time.monotonic()-self.hb_time < 2.5)

    def offboard(self):
        return self.hb is not None and ((self.hb.custom_mode >> 16) & 255) == 6

    def armed(self):
        return self.hb is not None and bool(self.hb.base_mode & 128)

    def land(self):
        self.command(mavutil.mavlink.MAV_CMD_NAV_LAND)
        deadline = time.monotonic()+35.
        next_request = time.monotonic()+5.
        # 切到降落以后停止 OFFBOARD 目标，必须确认 landed 和解除武装。
        while time.monotonic() < deadline:
            self.tx.mav.heartbeat_send(6, 8, 0, 0, 0)
            self.drain()
            on_ground = self.landed == 1 and time.monotonic()-self.landed_time < 2.
            if self.fresh() and on_ground and not self.armed():
                print('LANDED DISARMED', flush=True)
                return True
            if time.monotonic() > next_request:
                if on_ground and self.fresh() and abs(self.position.vz) < .1:
                    # 某些演示环境关闭自动上锁；仅落地确认后请求正常上锁，绝不强制停桨。
                    self.command(mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM, 0.)
                else:
                    self.command(mavutil.mavlink.MAV_CMD_NAV_LAND)
                next_request = time.monotonic()+5.
            time.sleep(.05)
        return False

    def run(self, route):
        print('CONNECT', flush=True)
        self.command(511, 32, 50000)
        self.command(511, 245, 200000)
        self.tx.mav.request_data_stream_send(self.system, self.component, 0, 20, 1)
        self.wait(self.fresh, 25., (0., 0., 0.), 'connect')
        if self.armed():
            raise RuntimeError('Already armed; refuse competing/restarted flight')
        p = self.position
        # 重复起飞会产生少量落点偏差，不能每轮把偏差累加到障碍物地图。
        # 仿真专用标定：同时读取世界位置和飞控位置，得到固定世界原点的变换。
        pose = subprocess.run(['gz', 'model', '-m', 'iris', '-p'], capture_output=True, text=True, timeout=10, check=True)
        world = [float(v) for v in pose.stdout.split()]
        if len(world) != 6 or math.hypot(*world[:2]) > .65:
            raise RuntimeError('World start offset exceeds 0.65m; restart SITL at scene origin')
        self.drain()
        p = self.position
        self.origin = (p.x-world[1], p.y-world[0], p.z)
        takeoff = (*world[:2], ALT)
        print('HOME_NED', self.origin, flush=True)
        for _ in range(40):
            self.tick(takeoff, phase='prestream')
        self.tx.mav.set_mode_send(self.system, 1, 6 << 16)
        self.wait(lambda: self.fresh() and self.offboard(), 6., takeoff, 'offboard')
        self.command(400, 1.)
        self.owns_control = True
        self.wait(lambda: self.fresh() and self.armed(), 8., takeoff, 'arm')
        self.wait(lambda: self.fresh() and abs(self.origin[2]-self.position.z-ALT)<.10,
                  20., takeoff, 'takeoff')
        self.wait(lambda: self.fresh() and distance((self.position.y-self.origin[1], self.position.x-self.origin[0]), (0., 0.)) < .12,
                  10., (0., 0., ALT), 'align_home')
        print('FLY length_m', round(route.length, 2), flush=True)
        progress, speed = 0., 0.
        started = last_progress = time.monotonic()
        previous = started
        deadline = started+route.length/.30+45.
        printed = -1
        while progress < route.length:
            now = time.monotonic()
            dt = min(.10, now-previous)
            previous = now
            if not self.fresh() or not self.offboard() or not self.armed():
                raise RuntimeError('Telemetry stale or OFFBOARD/arm lost')
            p = self.position
            actual = (p.y-self.origin[1], p.x-self.origin[0])
            clearance = min(distance(actual, o) for o in OBSTACLES)
            if clearance < 1.02:
                raise RuntimeError('Obstacle safety margin violated: '+str(clearance))
            if abs(self.origin[2]-p.z-ALT) > .30:
                raise RuntimeError('Altitude tracking error')
            error = distance(actual, route.sample(progress))
            desired = route.speed_limit(progress)*max(0., min(1., (.45-error)/.25))
            speed += max(-.5*dt, min(.3*dt, desired-speed))
            progress = min(route.length, progress+max(0., speed)*dt)
            if speed > .08:
                last_progress = now
            if now > deadline or now-last_progress > 12.:
                raise RuntimeError('Tracking stalled; do not skip failed path')
            target = route.sample(progress)
            a, b = route.sample(progress-.025), route.sample(progress+.025)
            norm = max(distance(a, b), 1e-9)
            velocity = (speed*(b[0]-a[0])/norm, speed*(b[1]-a[1])/norm)
            self.tick((*target, ALT), velocity, 'flight', progress)
            percent = int(progress/route.length*100)//10*10
            if percent != printed:
                print('PROGRESS', percent, 'error', round(error, 3), 'clearance', round(clearance, 3), flush=True)
                printed = percent
        self.wait(lambda: self.fresh() and distance((self.position.y-self.origin[1], self.position.x-self.origin[0]), (0., 0.)) < .15
                  and math.hypot(self.position.vx, self.position.vy) < .15,
                  10., (0., 0., ALT), 'home')
        return time.monotonic()-started


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['square', 'figure8', 'circles'])
    parser.add_argument('--output', default='/root/autodl-tmp/flight-repair/evidence')
    args = parser.parse_args()
    route = build(args.mode)
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime('%Y%m%d-%H%M%S')
    prefix = output/(args.mode+'-'+stamp)
    # 文件锁保护同一 MAVLink 控制通道，拒绝同时启动两个任务。
    lock = open('/tmp/yundrone-smooth-flight.lock', 'w')
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise SystemExit('Another flight controller is running')
    prefix.with_suffix('.plan.json').write_text(json.dumps({'mode': args.mode, 'points': route.points, 'labels': route.labels, 'length': route.length}), encoding='utf-8')
    flight = Flight(prefix.with_suffix('.csv'))
    result = {'mode': args.mode, 'success': False, 'planned_length_m': route.length}
    try:
        result['flight_duration_s'] = flight.run(route)
        result['landed_disarmed'] = flight.land()
        if not result['landed_disarmed']:
            raise RuntimeError('Landing not confirmed')
        result['success'] = True
    except (Exception, KeyboardInterrupt) as exc:
        result['error'] = str(exc)
        print('FAILED', str(exc), flush=True)
        if flight.owns_control and flight.armed():
            result['emergency_landed'] = flight.land()
    finally:
        records = [r for r in flight.samples if r[0] == 'flight']
        if records:
            result['max_tracking_error_m'] = max(r[1] for r in records)
            result['min_cone_center_m'] = min(r[2] for r in records)
        flight.file.close()
        prefix.with_suffix('.result.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
        print(json.dumps(result), flush=True)
    return 0 if result['success'] else 1


if __name__ == '__main__':
    raise SystemExit(main())

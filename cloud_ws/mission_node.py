#!/usr/bin/env python3
"""YAML waypoint mission + geofence fail-safe for Sunray.

Landing uses position descend + disarm instead of PX4 AUTO.LAND,
which was driving the SITL pose through the ground (z → -6).
"""
from __future__ import print_function

import csv
import math
import os
from enum import Enum

import rospy
from gazebo_msgs.msg import ModelStates
from geometry_msgs.msg import Point, PoseStamped
from nav_msgs.msg import Odometry, Path
from visualization_msgs.msg import Marker
from mavros_msgs.msg import PositionTarget, State as MavState
from mavros_msgs.srv import CommandBool, SetMode
from sunray_msgs.msg import UAVControlCMD, UAVSetup, UAVState


class Phase(Enum):
    WAIT_CONNECT = 0
    SET_MODE = 1
    ARM = 2
    TAKEOFF = 3
    GOTO = 4
    WAIT_WP = 5
    RTL = 6
    LAND = 7
    DONE = 8
    ABORT = 9


class MissionNode(object):
    def __init__(self):
        self.uav_id = int(rospy.get_param("~uav_id", 1))
        self.uav_name = rospy.get_param("~uav_name", "uav")
        self.takeoff_height = float(rospy.get_param("~takeoff_height", 1.2))
        self.arrive_thresh = float(rospy.get_param("~arrive_thresh", 0.25))
        self.waypoint_timeout = float(rospy.get_param("~waypoint_timeout", 40.0))
        self.land_height = float(rospy.get_param("~land_height", 0.12))
        self.end_action = rospy.get_param("~end_action", "land")
        self.log_csv = rospy.get_param("~log_csv", "/tmp/sunray_mission.csv")
        self.geofence = rospy.get_param("~geofence")
        self.waypoints = rospy.get_param("~waypoints")
        prefix = "/{}{}".format(self.uav_name, self.uav_id)

        self.state = UAVState()
        self.have_state = False
        self.phase = Phase.WAIT_CONNECT
        self.wp_index = 0
        self.phase_t0 = None
        self.wait_until = None
        self.abort_reason = ""
        self.trail = Path()
        self.trail.header.frame_id = "map"
        self.csv_rows = []
        self._csv_written = False

        rospy.Subscriber(prefix + "/sunray/uav_state", UAVState, self._on_state, queue_size=10)
        rospy.Subscriber("/uav1/sunray/gazebo_odom", Odometry, self._on_gz, queue_size=10)
        rospy.Subscriber("/gazebo/model_states", ModelStates, self._on_models, queue_size=1)
        self.gz_pos = None
        self.cmd_pub = rospy.Publisher(prefix + "/sunray/uav_control_cmd", UAVControlCMD, queue_size=10)
        self.setup_pub = rospy.Publisher(prefix + "/sunray/setup", UAVSetup, queue_size=10)
        self.path_pub = rospy.Publisher("sunray_mission/actual_path", Path, queue_size=1, latch=True)
        self.plan_pub = rospy.Publisher("sunray_mission/plan_path", Path, queue_size=1, latch=True)
        self.fence_pub = rospy.Publisher("sunray_mission/geofence", Marker, queue_size=1, latch=True)
        self.status_pub = rospy.Publisher("sunray_mission/status_marker", Marker, queue_size=1, latch=True)
        self.mav_pose_pub = rospy.Publisher("/uav1/mavros/setpoint_raw/local", PositionTarget, queue_size=20)
        self.mav_armed = False
        self.mav_mode = ""
        rospy.Subscriber("/uav1/mavros/state", MavState, self._on_mav)
        rospy.sleep(0.5)
        try:
            rospy.wait_for_service("/uav1/mavros/cmd/arming", timeout=5.0)
            rospy.wait_for_service("/uav1/mavros/set_mode", timeout=5.0)
            self.arm_srv = rospy.ServiceProxy("/uav1/mavros/cmd/arming", CommandBool)
            self.mode_srv = rospy.ServiceProxy("/uav1/mavros/set_mode", SetMode)
        except Exception as exc:
            rospy.logwarn("[mission] mavros services: %s", exc)
            self.arm_srv = None
            self.mode_srv = None

        rospy.sleep(0.5)
        self._publish_plan()
        self._publish_fence()
        rospy.loginfo("[mission] %d waypoints, fence %s", len(self.waypoints), self.geofence)

    def _pose_ok(self, msg):
        if len(msg.position) < 3:
            return False
        x, y, z = float(msg.position[0]), float(msg.position[1]), float(msg.position[2])
        if any(map(lambda v: v != v, (x, y, z))):  # NaN
            return False
        return -0.2 <= z <= 4.0 and abs(x) < 20.0 and abs(y) < 20.0

    def _on_state(self, msg):
        self.state = msg
        self.have_state = True
        if self.phase == Phase.DONE or not self._pose_ok(msg):
            return
        pose = PoseStamped()
        pose.header.stamp = rospy.Time(0)
        pose.header.frame_id = "map"
        pose.pose.position.x = msg.position[0]
        pose.pose.position.y = msg.position[1]
        pose.pose.position.z = msg.position[2]
        pose.pose.orientation.w = 1.0
        self.trail.header.stamp = pose.header.stamp
        self.trail.poses.append(pose)
        if len(self.trail.poses) > 2500:
            self.trail.poses = self.trail.poses[-2500:]
        self.path_pub.publish(self.trail)
        self.csv_rows.append(
            [
                pose.header.stamp.to_sec(),
                self.phase.name,
                msg.position[0],
                msg.position[1],
                msg.position[2],
                int(msg.armed),
            ]
        )

    def _elapsed(self):
        now = rospy.Time.now()
        if self.phase_t0 is None or self.phase_t0 == rospy.Time(0):
            self.phase_t0 = now
            return 0.0
        return (now - self.phase_t0).to_sec()

    def _enter(self, phase):
        self.phase = phase
        self.phase_t0 = rospy.Time.now()
        rospy.loginfo("[mission] -> %s", phase.name)

    def _setup(self, cmd, control_mode=""):
        msg = UAVSetup()
        msg.header.stamp = rospy.Time.now()
        msg.cmd = cmd
        msg.control_mode = control_mode
        self.setup_pub.publish(msg)

    def _cmd(self, cmd, pos=None):
        msg = UAVControlCMD()
        msg.header.stamp = rospy.Time.now()
        msg.cmd = cmd
        if pos is not None:
            msg.desired_pos = [float(pos[0]), float(pos[1]), float(pos[2])]
        self.cmd_pub.publish(msg)

    def _on_mav(self, msg):
        self.mav_armed = bool(msg.armed)
        self.mav_mode = msg.mode or ""

    def _mav_sp(self, x, y, z):
        msg = PositionTarget()
        msg.header.stamp = rospy.Time.now()
        msg.coordinate_frame = PositionTarget.FRAME_LOCAL_NED
        msg.type_mask = (
            PositionTarget.IGNORE_VX
            | PositionTarget.IGNORE_VY
            | PositionTarget.IGNORE_VZ
            | PositionTarget.IGNORE_AFX
            | PositionTarget.IGNORE_AFY
            | PositionTarget.IGNORE_AFZ
            | PositionTarget.IGNORE_YAW
            | PositionTarget.IGNORE_YAW_RATE
        )
        msg.position.x = float(x)
        msg.position.y = float(y)
        msg.position.z = float(z)
        self.mav_pose_pub.publish(msg)

    def _mav_offboard(self):
        if self.mode_srv is None:
            return
        try:
            if self.mav_mode != "OFFBOARD":
                self.mode_srv(0, "OFFBOARD")
        except Exception:
            pass

    def _mav_arm(self, value=True):
        if self.arm_srv is None:
            return
        try:
            self.arm_srv(value)
        except Exception:
            pass

    def _on_gz(self, msg):
        p = msg.pose.pose.position
        self.gz_pos = [p.x, p.y, p.z]

    def _on_models(self, msg):
        if "iris" not in msg.name:
            return
        i = msg.name.index("iris")
        p = msg.pose[i].position
        self.gz_pos = [p.x, p.y, p.z]

    def _pos(self):
        if self.gz_pos is not None:
            return list(self.gz_pos)
        return list(self.state.position)

    def _home_xy(self):
        if len(self.state.home_pos) >= 2:
            return float(self.state.home_pos[0]), float(self.state.home_pos[1])
        return 0.0, 0.0

    def _dist_xy(self, x, y):
        p = self._pos()
        return math.hypot(p[0] - x, p[1] - y)

    def _dist_to(self, wp):
        p = self._pos()
        return math.sqrt(
            (p[0] - wp["x"]) ** 2 + (p[1] - wp["y"]) ** 2 + (p[2] - wp["z"]) ** 2
        )

    def _inside_fence(self):
        x, y, z = self._pos()
        f = self.geofence
        return f["xmin"] <= x <= f["xmax"] and f["ymin"] <= y <= f["ymax"] and f["zmin"] <= z <= f["zmax"]

    def _abort(self, reason):
        self.abort_reason = reason
        rospy.logerr("[mission] ABORT: %s", reason)
        self._enter(Phase.ABORT)

    def _publish_plan(self):
        path = Path()
        path.header.frame_id = "map"
        path.header.stamp = rospy.Time(0)
        hx, hy = 0.0, 0.0
        pts = [{"x": hx, "y": hy, "z": self.takeoff_height}] + list(self.waypoints)
        for wp in pts:
            ps = PoseStamped()
            ps.header = path.header
            ps.pose.position.x = wp["x"]
            ps.pose.position.y = wp["y"]
            ps.pose.position.z = wp["z"]
            ps.pose.orientation.w = 1.0
            path.poses.append(ps)
        self.plan_pub.publish(path)

    def _publish_fence(self):
        f = self.geofence
        z0 = 0.02
        z1 = max(1.2, float(self.takeoff_height))
        corners = [
            (f["xmin"], f["ymin"]),
            (f["xmax"], f["ymin"]),
            (f["xmax"], f["ymax"]),
            (f["xmin"], f["ymax"]),
        ]
        mk = Marker()
        mk.header.frame_id = "map"
        mk.header.stamp = rospy.Time(0)
        mk.ns = "geofence"
        mk.id = 0
        mk.type = Marker.LINE_LIST
        mk.action = Marker.ADD
        mk.pose.orientation.w = 1.0
        mk.scale.x = 0.07
        mk.color.r = 1.0
        mk.color.g = 0.15
        mk.color.b = 0.15
        mk.color.a = 1.0
        mk.lifetime = rospy.Duration(0)
        mk.frame_locked = True
        pts = []
        for z in (z0, z1):
            for i in range(4):
                x1, y1 = corners[i]
                x2, y2 = corners[(i + 1) % 4]
                pts.append(Point(x=x1, y=y1, z=z))
                pts.append(Point(x=x2, y=y2, z=z))
        for x, y in corners:
            pts.append(Point(x=x, y=y, z=z0))
            pts.append(Point(x=x, y=y, z=z1))
        mk.points = pts
        self.fence_pub.publish(mk)
        floor = Marker()
        floor.header.frame_id = "map"
        floor.header.stamp = rospy.Time(0)
        floor.ns = "geofence"
        floor.id = 1
        floor.type = Marker.CUBE
        floor.action = Marker.ADD
        floor.pose.position.x = 0.5 * (f["xmin"] + f["xmax"])
        floor.pose.position.y = 0.5 * (f["ymin"] + f["ymax"])
        floor.pose.position.z = 0.03
        floor.pose.orientation.w = 1.0
        floor.scale.x = abs(f["xmax"] - f["xmin"])
        floor.scale.y = abs(f["ymax"] - f["ymin"])
        floor.scale.z = 0.04
        floor.color.r = 1.0
        floor.color.g = 0.1
        floor.color.b = 0.1
        floor.color.a = 0.35
        floor.lifetime = rospy.Duration(0)
        floor.frame_locked = True
        self.fence_pub.publish(floor)

    def _status_marker(self, text, r=0.1, g=0.8, b=0.2):
        mk = Marker()
        mk.header.frame_id = "map"
        mk.header.stamp = rospy.Time(0)
        mk.ns = "status"
        mk.id = 1
        mk.type = Marker.TEXT_VIEW_FACING
        mk.action = Marker.ADD
        mk.scale.z = 0.25
        mk.color.r, mk.color.g, mk.color.b, mk.color.a = r, g, b, 1.0
        p = self._pos()
        if not self._pose_ok(self.state) or not self._inside_fence():
            hx, hy = self._home_xy()
            p = [hx, hy, self.land_height]
        z = p[2]
        mk.pose.position.x = p[0]
        mk.pose.position.y = p[1]
        mk.pose.position.z = max(0.2, z) + 0.35
        mk.lifetime = rospy.Duration(0)
        mk.frame_locked = True
        mk.pose.orientation.w = 1.0
        mk.text = text
        self.status_pub.publish(mk)

    def _finish(self):
        if not self._csv_written:
            self._flush_csv()
            self._csv_written = True
        self._enter(Phase.DONE)

    def tick(self):
        p = self._pos() if (self.gz_pos is not None or (self.have_state and len(self.state.position) > 2)) else [0.0, 0.0, 0.0]
        z = p[2]
        self._publish_plan()
        self._publish_fence()
        rospy.loginfo_throttle(
            1.0, "[mission] phase=%s z=%.2f pos=%s", self.phase.name, z, ["{:.2f}".format(v) for v in p]
        )

        airborne = self.have_state and z > 0.45
        if airborne and self.state.armed and not self._inside_fence():
            if self.phase in (Phase.TAKEOFF, Phase.GOTO, Phase.WAIT_WP, Phase.RTL):
                self._abort("geofence breach at {}".format(["{:.2f}".format(v) for v in self._pos()]))
            else:
                self._setup(UAVSetup.DISARM)

        if self.phase == Phase.WAIT_CONNECT:
            self._status_marker("WAIT CONNECT", 1, 1, 0)
            ready = self.gz_pos is not None or (self.have_state and self.state.connected)
            if ready or self._elapsed() > 3.0:
                self._enter(Phase.SET_MODE)
        elif self.phase == Phase.SET_MODE:
            self._setup(UAVSetup.SET_CONTROL_MODE, "CMD_CONTROL")
            self._mav_sp(0.0, 0.0, 0.15)
            self._status_marker("SET OFFBOARD")
            if self._elapsed() > 2.0:
                self._mav_offboard()
            if self.mav_mode == "OFFBOARD" or self._elapsed() > 4.0:
                self._enter(Phase.ARM)
        elif self.phase == Phase.ARM:
            self._setup(UAVSetup.ARM)
            self._mav_sp(0.0, 0.0, 0.15)
            self._mav_offboard()
            if int(self._elapsed()) != getattr(self, "_arm_tick", -1):
                self._arm_tick = int(self._elapsed())
                self._mav_arm(True)
            self._status_marker("ARM")
            if self.mav_armed or self.state.armed:
                self._enter(Phase.TAKEOFF)
        elif self.phase == Phase.TAKEOFF:
            self._cmd(UAVControlCMD.XyzPos, (0.0, 0.0, self.takeoff_height))
            self._mav_sp(0.0, 0.0, self.takeoff_height)
            self._mav_offboard()
            if not (self.mav_armed or self.state.armed):
                self._mav_arm(True)
            self._status_marker("TAKEOFF")
            if z >= self.takeoff_height - 0.15:
                if self.waypoints:
                    self._enter(Phase.GOTO)
                else:
                    self._enter(Phase.RTL)
            elif self._elapsed() > self.waypoint_timeout:
                self._abort("takeoff timeout")
        elif self.phase == Phase.GOTO:
            wp = self.waypoints[self.wp_index]
            self._cmd(UAVControlCMD.XyzPos, (wp["x"], wp["y"], wp["z"]))
            self._mav_sp(wp["x"], wp["y"], wp["z"])
            self._status_marker("WP {}/{}".format(self.wp_index + 1, len(self.waypoints)))
            if self._dist_to(wp) < self.arrive_thresh:
                wait = float(wp.get("wait", 0.0))
                self.wait_until = rospy.Time.now() + rospy.Duration(wait)
                self._enter(Phase.WAIT_WP)
            elif self._elapsed() > self.waypoint_timeout:
                self._abort("waypoint {} timeout".format(self.wp_index + 1))
        elif self.phase == Phase.WAIT_WP:
            wp = self.waypoints[self.wp_index]
            self._cmd(UAVControlCMD.XyzPos, (wp["x"], wp["y"], wp["z"]))
            self._mav_sp(wp["x"], wp["y"], wp["z"])
            self._status_marker("HOLD WP {}".format(self.wp_index + 1))
            if rospy.Time.now() >= self.wait_until:
                self.wp_index += 1
                if self.wp_index >= len(self.waypoints):
                    self._enter(Phase.RTL)
                else:
                    self._enter(Phase.GOTO)
        elif self.phase == Phase.RTL:
            hx, hy = self._home_xy()
            self._cmd(UAVControlCMD.XyzPos, (hx, hy, self.takeoff_height))
            self._mav_sp(hx, hy, self.takeoff_height)
            self._status_marker("RTL")
            if self._dist_xy(hx, hy) < 0.35 and abs(z - self.takeoff_height) < 0.25:
                self._enter(Phase.LAND)
            elif self._elapsed() > self.waypoint_timeout:
                self._enter(Phase.LAND)
        elif self.phase in (Phase.LAND, Phase.ABORT):
            hx, hy = self._home_xy()
            if self.phase == Phase.ABORT:
                hx, hy = self._pos()[0], self._pos()[1]
            # Soft land: hold XY, command a low altitude. Do not send Land (PX4 AUTO.LAND
            # was integrating through the floor in this SITL).
            self._cmd(UAVControlCMD.XyzPos, (hx, hy, self.land_height))
            self._mav_sp(hx, hy, self.land_height)
            tag = "ABORT DESCEND" if self.phase == Phase.ABORT else "DESCEND"
            self._status_marker(tag, 1.0, 0.3, 0.1)
            if z <= self.land_height + 0.15:
                self._setup(UAVSetup.DISARM)
            if not self.state.armed:
                self._finish()
            elif self._elapsed() > 20.0:
                self._setup(UAVSetup.DISARM)
        elif self.phase == Phase.DONE:
            hx, hy = self._home_xy()
            # Keep offboard setpoints until motors are actually disarmed, otherwise
            # PX4 failsafe flies out of the fence with a DONE label.
            if self.state.armed:
                self._cmd(UAVControlCMD.XyzPos, (hx, hy, self.land_height))
                self._setup(UAVSetup.DISARM)
            text = "DONE" if not self.abort_reason else "ABORTED: " + self.abort_reason
            self._status_marker(text, 0.2, 0.9, 0.2 if not self.abort_reason else 0.1)

    def _flush_csv(self):
        try:
            os.makedirs(os.path.dirname(self.log_csv) or ".", exist_ok=True)
            with open(self.log_csv, "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["t", "phase", "x", "y", "z", "armed"])
                w.writerows(self.csv_rows)
            rospy.loginfo("[mission] wrote %s (%d rows)", self.log_csv, len(self.csv_rows))
        except Exception as exc:
            rospy.logwarn("[mission] csv failed: %s", exc)

    def spin(self):
        rate = rospy.Rate(float(rospy.get_param("~loop_hz", 20.0)))
        while not rospy.is_shutdown():
            self.tick()
            rate.sleep()


def main():
    rospy.init_node("mission_node")
    MissionNode().spin()


if __name__ == "__main__":
    main()

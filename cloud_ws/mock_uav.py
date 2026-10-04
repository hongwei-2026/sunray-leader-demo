#!/usr/bin/env python3
"""Kinematic stand-in for sunray_control_node + PX4.

Speaks the same topics as the official stack so mission_node can later
be pointed at Gazebo/PX4 without changing its interface.
"""
from __future__ import print_function

import math

import rospy
from sunray_msgs.msg import UAVControlCMD, UAVSetup, UAVState


class MockUAV(object):
    def __init__(self):
        self.uav_id = rospy.get_param("~uav_id", 1)
        self.uav_name = rospy.get_param("~uav_name", "uav")
        self.takeoff_height = rospy.get_param("~takeoff_height", 1.2)
        self.max_xy = rospy.get_param("~max_xy_speed", 1.2)
        self.max_z = rospy.get_param("~max_z_speed", 0.8)
        prefix = "/{}{}".format(self.uav_name, self.uav_id)

        self.state = UAVState()
        self.state.uav_id = self.uav_id
        self.state.connected = True
        self.state.armed = False
        self.state.odom_valid = True
        self.state.mode = "AUTO.LOITER"
        self.state.landed_state = 1
        self.state.takeoff_height = self.takeoff_height
        self.state.control_mode = UAVSetup.INIT
        self.state.position = [0.0, 0.0, 0.0]
        self.state.velocity = [0.0, 0.0, 0.0]
        self.state.home_pos = [0.0, 0.0, 0.0]

        self.cmd = UAVControlCMD()
        self.cmd.cmd = UAVControlCMD.Hover
        self.hold = [0.0, 0.0, 0.0]

        rospy.Subscriber(prefix + "/sunray/uav_control_cmd", UAVControlCMD, self._on_cmd, queue_size=10)
        rospy.Subscriber(prefix + "/sunray/setup", UAVSetup, self._on_setup, queue_size=10)
        self.pub = rospy.Publisher(prefix + "/sunray/uav_state", UAVState, queue_size=10)

    def _on_cmd(self, msg):
        self.cmd = msg
        if msg.cmd in (UAVControlCMD.Hover, UAVControlCMD.Takeoff, UAVControlCMD.Land, UAVControlCMD.Return):
            self.hold = list(self.state.position)

    def _on_setup(self, msg):
        if msg.cmd == UAVSetup.ARM:
            self.state.armed = True
            self.state.landed_state = 0
            rospy.loginfo("[mock_uav] ARM")
        elif msg.cmd in (UAVSetup.DISARM, UAVSetup.EMERGENCY_KILL):
            self.state.armed = False
            self.state.landed_state = 1
            rospy.loginfo("[mock_uav] DISARM")
        elif msg.cmd == UAVSetup.SET_CONTROL_MODE:
            mapping = {
                "INIT": UAVSetup.INIT,
                "RC_CONTROL": UAVSetup.RC_CONTROL,
                "CMD_CONTROL": UAVSetup.CMD_CONTROL,
                "LAND_CONTROL": UAVSetup.LAND_CONTROL,
                "WITHOUT_CONTROL": UAVSetup.WITHOUT_CONTROL,
            }
            self.state.control_mode = mapping.get(msg.control_mode, UAVSetup.CMD_CONTROL)
            if msg.control_mode == "CMD_CONTROL":
                self.state.mode = "OFFBOARD"
            rospy.loginfo("[mock_uav] mode %s", msg.control_mode)

    def _approach(self, target, dt):
        px, py, pz = self.state.position
        dx, dy, dz = target[0] - px, target[1] - py, target[2] - pz
        dist_xy = math.hypot(dx, dy)
        step_xy = self.max_xy * dt
        step_z = self.max_z * dt
        if dist_xy > 1e-6:
            scale = min(1.0, step_xy / dist_xy)
            px += dx * scale
            py += dy * scale
            vx = dx * scale / dt
            vy = dy * scale / dt
        else:
            vx = vy = 0.0
        if abs(dz) > 1e-6:
            zmove = math.copysign(min(abs(dz), step_z), dz)
            pz += zmove
            vz = zmove / dt
        else:
            vz = 0.0
        self.state.position = [px, py, pz]
        self.state.velocity = [vx, vy, vz]

    def step(self, dt):
        if not self.state.armed:
            self.state.velocity = [0.0, 0.0, 0.0]
            if self.state.position[2] > 0.02:
                self._approach([self.state.position[0], self.state.position[1], 0.0], dt)
            return

        cmd = self.cmd.cmd
        if cmd == UAVControlCMD.Takeoff:
            goal = [
                self.state.home_pos[0],
                self.state.home_pos[1],
                self.state.home_pos[2] + self.takeoff_height,
            ]
            self._approach(goal, dt)
        elif cmd == UAVControlCMD.Land or cmd == UAVControlCMD.Return:
            goal = [self.state.position[0], self.state.position[1], 0.0]
            self._approach(goal, dt)
            if self.state.position[2] < 0.05:
                self.state.armed = False
                self.state.landed_state = 1
                self.state.control_mode = UAVSetup.LAND_CONTROL
        elif cmd == UAVControlCMD.XyzPos or cmd == UAVControlCMD.XyzPosYaw:
            self._approach(list(self.cmd.desired_pos), dt)
        elif cmd == UAVControlCMD.Hover:
            self._approach(self.hold, dt)
        else:
            self._approach(self.hold, dt)

    def spin(self):
        rate = rospy.Rate(20)
        last = rospy.Time.now()
        while not rospy.is_shutdown():
            now = rospy.Time.now()
            dt = max(1e-3, (now - last).to_sec())
            last = now
            self.step(dt)
            self.state.header.stamp = now
            self.pub.publish(self.state)
            rate.sleep()


def main():
    rospy.init_node("mock_uav")
    MockUAV().spin()


if __name__ == "__main__":
    main()

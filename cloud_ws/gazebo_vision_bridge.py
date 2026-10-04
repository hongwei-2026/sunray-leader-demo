#!/usr/bin/env python3
"""Gazebo iris pose -> MAVROS vision (30 Hz) + fusion odom."""
import rospy
from gazebo_msgs.msg import ModelStates
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Odometry


class GazeboVisionBridge(object):
    def __init__(self):
        self.model = rospy.get_param("~model", "iris")
        self.min_dt = 1.0 / float(rospy.get_param("~rate", 30.0))
        self._last = rospy.Time(0)
        self.pose = None
        self.twist = None
        vis_topic = rospy.get_param("~vision_topic", "/uav1/mavros/vision_pose/pose")
        odom_topic = rospy.get_param("~odom_topic", "/uav1/sunray/gazebo_odom")
        self.vis_pub = rospy.Publisher(vis_topic, PoseStamped, queue_size=10)
        self.odom_pub = rospy.Publisher(odom_topic, Odometry, queue_size=10)
        rospy.Subscriber("/gazebo/model_states", ModelStates, self._cb, queue_size=1)
        self.timer = rospy.Timer(rospy.Duration(self.min_dt), self._tick)

    def _cb(self, msg):
        if self.model not in msg.name:
            return
        i = msg.name.index(self.model)
        self.pose = msg.pose[i]
        self.twist = msg.twist[i]

    def _tick(self, _evt):
        if self.pose is None:
            return
        now = rospy.Time.now()
        ps = PoseStamped()
        ps.header.stamp = now
        ps.header.frame_id = "map"
        ps.pose = self.pose
        self.vis_pub.publish(ps)

        od = Odometry()
        od.header.stamp = now
        od.header.frame_id = "map"
        od.child_frame_id = "base_link"
        od.pose.pose = self.pose
        od.twist.twist = self.twist
        self.odom_pub.publish(od)


if __name__ == "__main__":
    rospy.init_node("gazebo_vision_bridge")
    GazeboVisionBridge()
    rospy.spin()

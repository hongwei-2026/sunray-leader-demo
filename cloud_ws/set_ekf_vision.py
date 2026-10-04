#!/usr/bin/env python3
"""Force PX4 EKF to use vision height/position (Gazebo), not GPS/baro."""
import rospy
from mavros_msgs.msg import ParamValue
from mavros_msgs.srv import ParamGet, ParamSet


def set_param(proxy, name, integer=0, real=0.0):
    val = ParamValue()
    val.integer = integer
    val.real = real
    try:
        resp = proxy(param_id=name, value=val)
        rospy.loginfo("[ekf] set %s success=%s value=%s", name, resp.success, resp.value)
        return resp.success
    except Exception as exc:
        rospy.logwarn("[ekf] %s failed: %s", name, exc)
        return False


def main():
    rospy.init_node("set_ekf_vision")
    ns = rospy.get_param("~mavros_ns", "/uav1/mavros")
    rospy.wait_for_service(ns + "/param/set", timeout=90.0)
    rospy.wait_for_service(ns + "/param/get", timeout=90.0)
    setter = rospy.ServiceProxy(ns + "/param/set", ParamSet)
    getter = rospy.ServiceProxy(ns + "/param/get", ParamGet)
    wanted = [("EKF2_EV_CTRL", 15), ("EKF2_HGT_REF", 3), ("EKF2_GPS_CTRL", 0)]
    for _ in range(20):
        ok = True
        for name, ival in wanted:
            got = getter(param_id=name)
            if got.success and got.value.integer == ival:
                continue
            if not set_param(setter, name, integer=ival):
                ok = False
        if ok:
            rospy.loginfo("[ekf] vision params confirmed")
            return
        rospy.sleep(2.0)
    rospy.logwarn("[ekf] params not confirmed after retries")


if __name__ == "__main__":
    main()

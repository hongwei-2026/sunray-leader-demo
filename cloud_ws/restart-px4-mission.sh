#!/bin/bash
set +u
bash /root/autodl-tmp/stop-px4-mission.sh
sleep 5
: > /root/autodl-tmp/px4-mission.log
chmod +x /root/autodl-tmp/run-px4-mission.sh /root/autodl-tmp/ensure-iris.sh
nohup bash /root/autodl-tmp/run-px4-mission.sh >/root/autodl-tmp/px4-mission.log 2>&1 &
echo PID $!
sleep 4
pgrep -a roslaunch || true

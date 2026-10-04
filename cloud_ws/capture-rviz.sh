#!/bin/bash
set +u
export PATH=/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin
export DISPLAY=:1
export XAUTHORITY=/root/.Xauthority
if ! command -v xdotool >/dev/null 2>&1; then
  DEBIAN_FRONTEND=noninteractive apt-get install -y -qq xdotool >/tmp/xdotool-apt.log || true
fi
# close ROS EOL warning if present
WID=$(xdotool search --name "End-of-Life" | head -n 1 || true)
if [ -n "$WID" ]; then
  xdotool windowactivate "$WID"
  sleep 0.3
  xdotool key Return
  sleep 0.3
fi
# focus rviz
RWID=$(xdotool search --name "RViz" | tail -n 1 || true)
if [ -n "$RWID" ]; then
  xdotool windowactivate "$RWID"
  xdotool windowraise "$RWID"
fi
sleep 0.5
mkdir -p /root/autodl-tmp/screenshots
import -window root /root/autodl-tmp/screenshots/px4_rviz_desktop.png
# also window-only if possible
if [ -n "$RWID" ]; then
  import -window "$RWID" /root/autodl-tmp/screenshots/px4_rviz_window.png || true
fi
ls -lh /root/autodl-tmp/screenshots/

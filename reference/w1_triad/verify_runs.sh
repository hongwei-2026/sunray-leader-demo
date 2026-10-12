#!/bin/bash
set -u
ROOT=/root/autodl-tmp/flight-repair
for mode in figure8 square circles; do
    python3 -u "$ROOT/smooth_flight.py" "$mode" >"$ROOT/evidence/$mode.log" 2>&1 || exit 1
done

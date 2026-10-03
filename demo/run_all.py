#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import runpy
from pathlib import Path

HERE = Path(__file__).resolve().parent

def main():
    print("=== UAV takeoff-hover-land ===")
    runpy.run_path(str(HERE / "uav_takeoff_hover_land_sim.py"), run_name="__main__")
    print("=== UGV circle ===")
    runpy.run_path(str(HERE / "ugv_circle_sim.py"), run_name="__main__")
    print("\n全部完成。截图/GIF 在 output/ 目录，可直接发群交差。")

if __name__ == "__main__":
    main()

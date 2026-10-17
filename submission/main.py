#!/usr/bin/env python3
"""个人算法仓库的统一作业入口。"""
import runpy
import sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]
reference=root/'rescue_reference/reference'
sys.path.insert(0,str(reference))
runpy.run_path(str(reference/'main.py'),run_name='__main__')

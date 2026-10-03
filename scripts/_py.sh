#!/usr/bin/env bash
# 解析云主机上的 Python（AutoDL conda / 系统 python3）
if [[ -x /root/miniconda3/bin/python ]]; then
  echo /root/miniconda3/bin/python
elif command -v python3 >/dev/null 2>&1; then
  command -v python3
elif command -v python >/dev/null 2>&1; then
  command -v python
else
  echo "找不到 Python" >&2
  exit 1
fi

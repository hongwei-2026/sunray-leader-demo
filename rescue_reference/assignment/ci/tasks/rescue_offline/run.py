#!/usr/bin/env python3
# 功能文档：docs/learning/features/2026-10_急救离线作业与CI.md
"""JSONL子进程接口。只接收动作，环境自己推进位置、库存、时间与评分。"""
import argparse
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import time
from environment import Environment, Rejected

MAX_LINE=65536

def run(command,root,level,seed=0,timeout=180,step_timeout=3):
    env=Environment(root,level,seed)
    # 不传GitHub凭据给算法子进程；进程边界不是安全沙箱，CI只跑无密钥临时runner。
    safe={k:v for k,v in os.environ.items() if k in ('PATH','SYSTEMROOT','WINDIR','TEMP','TMP','LANG','PYTHONIOENCODING')}
    process=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,env=safe)
    incoming=queue.Queue(maxsize=1); stop=threading.Event()
    def reader():
        while not stop.is_set():
            try:
                line=process.stdout.readline(MAX_LINE+1)
                item=('line',line) if line and len(line)<=MAX_LINE else ('error','EOF_OR_OVERSIZED_LINE')
                incoming.put(item,timeout=1)
                if item[0]=='error':return
            except (OSError,ValueError,queue.Full):return
    outgoing=queue.Queue(maxsize=1)
    def writer():
        while not stop.is_set():
            try:
                message=outgoing.get(timeout=0.2)
                process.stdin.write(message);process.stdin.flush()
            except queue.Empty:continue
            except (OSError,ValueError):return
    thread=threading.Thread(target=reader,daemon=True);thread.start()
    threading.Thread(target=writer,daemon=True).start()
    deadline=time.monotonic()+timeout;actions=[]
    try:
        while not env.done:
            if time.monotonic()>deadline: env.fail('wall_timeout');break
            try: outgoing.put((json.dumps(env.observe(),allow_nan=False)+chr(10)).encode(),timeout=step_timeout)
            except queue.Full: env.fail('input_backpressure');break
            try: kind,line=incoming.get(timeout=min(step_timeout,max(0.01,deadline-time.monotonic())))
            except queue.Empty: env.fail('action_timeout');break
            if kind=='error':env.fail(line);break
            try:
                action=json.loads(line);env.step(action);actions.append(action)
            except (ValueError,TypeError,KeyError,OverflowError) as exc:
                env.fail('invalid_action:'+str(exc));break
    except (BrokenPipeError,OSError):env.fail('algorithm_process_closed')
    finally:
        stop.set()
        if process.poll() is None: process.kill()
        process.wait(timeout=5)
        for pipe in (process.stdin,process.stdout):
            try:pipe.close()
            except OSError:pass
    return env.report(),env.events,actions

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--task-root',required=True);p.add_argument('--level',choices=['level1','level2','level3'],required=True)
    p.add_argument('--seed',type=int,default=0);p.add_argument('--timeout',type=float,default=180)
    p.add_argument('--output',required=True);p.add_argument('--private-trace',action='store_true')
    p.add_argument('command',nargs=argparse.REMAINDER)
    args=p.parse_args();command=args.command
    if command and command[0]=='--':command=command[1:]
    if not command:p.error('algorithm command required after --')
    report,events,actions=run(command,args.task_root,args.level,args.seed,args.timeout)
    root=Path(args.output);root.mkdir(parents=True,exist_ok=True)
    (root/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    # 参考动作只在教师显式开启时保留，不作为组织仓库公开artifact。
    if args.private_trace:
        (root/'events.json').write_text(json.dumps(events,ensure_ascii=False,indent=2),encoding='utf-8')
        (root/'actions.json').write_text(json.dumps(actions),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))
    return 0 if report['passed'] else 1

if __name__=='__main__':sys.exit(main())

"""Synthetic-only Windows CMD process/pipe ownership diagnostic v4.

No proprietary code, qualifications, package changes, or private filesystem.
"""
import ctypes
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

assert os.name=="nt"
root=Path(os.environ.get("RUNNER_TEMP",tempfile.gettempdir()))/"p72-qhf-cmd-inline-v4"
root.mkdir(parents=True,exist_ok=True)
parent=root/"synthetic_parent.py"
parent.write_text(
    '''import ctypes,json,os,pathlib,subprocess,sys,time
mark,done=map(pathlib.Path,sys.argv[1:3])
K=ctypes.WinDLL("kernel32",use_last_error=True)
K.GetStdHandle.argtypes=[ctypes.c_uint32];K.GetStdHandle.restype=ctypes.c_void_p
K.GetFileType.argtypes=[ctypes.c_void_p];K.GetFileType.restype=ctypes.c_uint32
def t(n):return {0:"unknown",1:"disk",2:"char",3:"pipe"}.get(K.GetFileType(K.GetStdHandle(ctypes.c_uint32(n))),"other")
subprocess.Popen([sys.executable,"-c","import time;time.sleep(0.25)"],
  stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,close_fds=True)
mark.write_text(json.dumps({"pid":os.getpid(),"ppid":os.getppid(),"stdout":t(-11),"stderr":t(-12)}),encoding="utf-8")
time.sleep(2.75)
done.write_text("DONE",encoding="ascii")
''',encoding="utf-8")
K=ctypes.WinDLL("kernel32",use_last_error=True)
K.OpenProcess.argtypes=[ctypes.c_uint32,ctypes.c_int,ctypes.c_uint32]
K.OpenProcess.restype=ctypes.c_void_p
K.WaitForSingleObject.argtypes=[ctypes.c_void_p,ctypes.c_uint32]
K.WaitForSingleObject.restype=ctypes.c_uint32
K.TerminateProcess.argtypes=[ctypes.c_void_p,ctypes.c_uint32]
K.TerminateProcess.restype=ctypes.c_int
K.CloseHandle.argtypes=[ctypes.c_void_p];K.CloseHandle.restype=ctypes.c_int
COMSPEC=os.environ.get("COMSPEC","cmd.exe")
cases={}
for name in ("batch_explicit","batch_shell","batch_call","inline_direct","inline_shell"):
    ready=root/(name+".json"); done=root/(name+".done")
    payload='"'+sys.executable+'" "'+str(parent)+'" "'+str(ready)+'" "'+str(done)+'" >NUL 2>&1'
    case=root/(name+".cmd")
    case.write_bytes(("@echo off\r\n"+payload+"\r\n").encode("utf-8"))
    shell=False
    if name=="batch_explicit":
        cmd=[COMSPEC,"/D","/C",str(case)]
    elif name=="batch_shell":
        cmd=[str(case)];shell=True
    elif name=="batch_call":
        cmd=[COMSPEC,"/D","/C",'call "'+str(case)+'"']
    elif name=="inline_direct":
        cmd=[COMSPEC,"/D","/C",payload]
    else:
        cmd=payload;shell=True
    t0=time.monotonic()
    timeout=False;error=None;exit_code=None;postkill_drain=None
    p=None
    try:
        p=subprocess.Popen(cmd,cwd=root,stdin=subprocess.DEVNULL,
          stdout=subprocess.PIPE,stderr=subprocess.PIPE,
          shell=shell,executable=COMSPEC if shell else None)
        try:
            o,e=p.communicate(timeout=.8)
            exit_code=p.returncode
        except subprocess.TimeoutExpired:
            timeout=True
            p.kill()
            drain_start=time.monotonic()
            try:
                o,e=p.communicate(timeout=5.0)
                postkill_drain=round(time.monotonic()-drain_start,3)
            except subprocess.TimeoutExpired:
                postkill_drain="DRAIN_TIMEOUT"
                p.stdout.close();p.stderr.close();p.wait(timeout=1.0)
    except Exception as ex:
        error=type(ex).__name__+":"+str(ex)[:110]
        if p and p.poll() is None:
            p.kill();p.wait(timeout=1.0)
    elapsed=round(time.monotonic()-t0,3)
    obj=json.loads(ready.read_text(encoding="utf-8")) if ready.exists() else None
    alive=None;settled=None;forced=False
    if obj:
        h=K.OpenProcess(0x00100001,0,obj["pid"])
        if h:
            try:
                alive=K.WaitForSingleObject(h,0)==0x102
                settled=K.WaitForSingleObject(h,5000)==0
                if not settled:
                    forced=bool(K.TerminateProcess(h,67))
                    settled=K.WaitForSingleObject(h,1000)==0
            finally:K.CloseHandle(h)
    cases[name]={
      "shell":shell,"immediate_process_kind":"CMD",
      "timed_out":timeout,"caller_elapsed_seconds":elapsed,
      "postkill_pipe_drain_seconds":postkill_drain,
      "returned_exit_code":exit_code,"error":error,
      "parent_marker_observed":bool(obj),
      "synthetic_parent_spawned_by_immediate_pid":bool(obj and p and obj["ppid"]==p.pid),
      "synthetic_parent_stdout_kind":obj["stdout"] if obj else None,
      "synthetic_parent_stderr_kind":obj["stderr"] if obj else None,
      "parent_alive_on_return":alive,
      "parent_bounded_settled":settled,
      "parent_done_marker_after_settlement":done.exists(),
      "forced_cleanup":forced
    }
ok=all(c["timed_out"] and c["error"] is None and
       c["parent_marker_observed"] and
       c["parent_bounded_settled"] and
       not c["forced_cleanup"] and
       c["postkill_pipe_drain_seconds"]!="DRAIN_TIMEOUT"
       for c in cases.values())
receipt={"schema":"proj0072.synthetic-cmd-inline.v4",
        "result":"OBSERVATIONS_RECORDED" if ok else "INDETERMINATE",
        "classification":"PUBLIC_SYNTHETIC_ONLY",
        "cases":cases,
        "original_qhf_executed":False,"original_nebq_executed":False,
        "qualification":"NOT_ESTABLISHED",
        "python_version":sys.version.split()[0]}
(root/"RESULT.json").write_text(json.dumps(receipt,indent=2,sort_keys=True),encoding="utf-8")
print("QHF_PIPE_V4_DIAGNOSTIC",json.dumps(receipt,sort_keys=True))
raise SystemExit(0 if ok else 1)

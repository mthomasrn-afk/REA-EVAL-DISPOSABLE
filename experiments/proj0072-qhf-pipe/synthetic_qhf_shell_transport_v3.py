"""Public synthetic-only reproduction of original QHF Windows shell/capture transport.

Only CMD, Python stdlib, bounded synthetic children. No QHF/NEBQ/REA source.
"""
from __future__ import annotations
import ctypes
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

assert os.name == "nt"
root = Path(os.environ.get("RUNNER_TEMP", tempfile.gettempdir())) / "p72-qhf-pipe-transport-v3"
root.mkdir(parents=True, exist_ok=True)
parent = root / "synthetic_parent.py"
parent.write_text(
    '''import ctypes, json, os, pathlib, subprocess, sys, time
marker, done = map(pathlib.Path, sys.argv[1:3])
k=ctypes.WinDLL("kernel32", use_last_error=True)
k.GetStdHandle.argtypes=[ctypes.c_uint32]
k.GetStdHandle.restype=ctypes.c_void_p
k.GetFileType.argtypes=[ctypes.c_void_p]
k.GetFileType.restype=ctypes.c_uint32
def typ(i):
    return {0:"unknown", 1:"disk", 2:"char", 3:"pipe"}.get(k.GetFileType(k.GetStdHandle(ctypes.c_uint32(i))), "other")
subprocess.Popen([sys.executable,"-c","import time;time.sleep(.3)"],
    stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,close_fds=True)
marker.write_text(json.dumps({"pid":os.getpid(), "stdout_kind":typ(-11),"stderr_kind":typ(-12)}),encoding="utf-8")
time.sleep(2.7)
done.write_text("FINISHED",encoding="ascii")
''', encoding="utf-8"
)
K=ctypes.WinDLL("kernel32", use_last_error=True)
K.OpenProcess.argtypes=[ctypes.c_uint32,ctypes.c_int,ctypes.c_uint32]
K.OpenProcess.restype=ctypes.c_void_p
K.WaitForSingleObject.argtypes=[ctypes.c_void_p,ctypes.c_uint32]
K.WaitForSingleObject.restype=ctypes.c_uint32
K.TerminateProcess.argtypes=[ctypes.c_void_p,ctypes.c_uint32]
K.TerminateProcess.restype=ctypes.c_int
K.CloseHandle.argtypes=[ctypes.c_void_p]
K.CloseHandle.restype=ctypes.c_int
WAIT_TIMEOUT=0x102
COMSPEC=os.environ.get("COMSPEC","cmd.exe")
cases={}
specs=[
    ("shell_true_no_redirect", True, False),
    ("shell_true_parent_to_nul", True, True),
    ("exe_cmd_parent_to_nul", False, True),
    ("exe_cmd_no_redirect", False, False),
]
for name, use_shell, redirect in specs:
    marker=root/(name+".json")
    done=root/(name+".done")
    case=root/(name+".cmd")
    python_line='"'+sys.executable+'" "'+str(parent)+'" "'+str(marker)+'" "'+str(done)+'"'
    if redirect:
        python_line += " >NUL 2>&1"
    case.write_bytes(("@echo off\r\n"+python_line+"\r\n").encode("utf-8"))
    cmd=[str(case)] if use_shell else [COMSPEC,"/D","/C",str(case)]
    start=time.monotonic()
    timed_out=False
    exit_code=None
    error=None
    try:
        p=subprocess.run(cmd,cwd=str(root),stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,timeout=.85,check=False,shell=use_shell,
            executable=COMSPEC if use_shell else None)
        exit_code=p.returncode
    except subprocess.TimeoutExpired:
        timed_out=True
    except Exception as exc:
        error=type(exc).__name__+":"+str(exc)[:80]
    elapsed=round(time.monotonic()-start,3)
    obj=json.loads(marker.read_text(encoding="utf-8")) if marker.exists() else None
    alive_at_return=None
    settled=None
    forced=False
    if obj:
        h=K.OpenProcess(0x00100001,0,obj["pid"])
        if h:
            try:
                alive_at_return=K.WaitForSingleObject(h,0)==WAIT_TIMEOUT
                settled=K.WaitForSingleObject(h,5000)==0
                if not settled:
                    forced=bool(K.TerminateProcess(h,67))
                    settled=K.WaitForSingleObject(h,1000)==0
            finally:K.CloseHandle(h)
    cases[name]={
        "shell":use_shell,"child_redirected":redirect,
        "timed_out":timed_out,"elapsed_seconds":elapsed,
        "returned_exit_code":exit_code,"unexpected_error":error,
        "parent_stdout_kind":obj["stdout_kind"] if obj else None,
        "parent_stderr_kind":obj["stderr_kind"] if obj else None,
        "parent_alive_at_caller_return":alive_at_return,
        "parent_process_settled":settled,
        "parent_done_marker":done.exists(),
        "forced_cleanup":forced
    }
valid=all(x["timed_out"] and x["parent_process_settled"] and x["parent_done_marker"]
          and x["unexpected_error"] is None and not x["forced_cleanup"]
          for x in cases.values())
receipt={"schema":"proj0072.synthetic-qhf-transport.v3",
  "classification":"PUBLIC_SYNTHETIC_ONLY",
  "result":"OBSERVATIONS_RECORDED" if valid else "INDETERMINATE",
  "hypothesis":"QHF shell=True CMD additional hop may retain captured stdout after immediate process killed",
  "cases":cases,
  "qHF_original_tool_executed":False,
  "nebq_original_tool_executed":False,
  "factory_qualification":"NOT_ESTABLISHED",
  "python":sys.version.split()[0]}
(root/"RESULT.json").write_text(json.dumps(receipt,indent=2,sort_keys=True),encoding="utf-8")
print("QHF_PIPE_V3_DIAGNOSTIC",json.dumps(receipt,sort_keys=True))
sys.exit(0 if valid else 1)

"""Disposable Windows-native owner safety trial; NOT PMVT implementation or REA C5.

All PIDs arise from this test fixture. Process handles are retained across
normal close, owner-initiated termination and abrupt owner death; no Job
handle is duplicated. No local MSI operation, privilege changes or private data.
"""
from __future__ import annotations
import ctypes
import hashlib
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
from ctypes import wintypes

if os.name != "nt":
    raise SystemExit("WINDOWS_HOST_REQUIRED")
if len(sys.argv) != 3:
    raise SystemExit("USAGE FILE.node manifest.json")
addon = Path(sys.argv[1]).resolve()
manifest = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
assert hashlib.sha256(addon.read_bytes()).hexdigest() == manifest["artifactSha256"], "HASH_MISMATCH"
assert (manifest["packageVersion"],manifest["platform"],manifest["architecture"]) == ("6.5.0","win32","x64")

k = ctypes.WinDLL("kernel32",use_last_error=True)
k.OpenProcess.argtypes=(wintypes.DWORD,wintypes.BOOL,wintypes.DWORD)
k.OpenProcess.restype=wintypes.HANDLE
k.GetProcessTimes.argtypes=[wintypes.HANDLE]+[ctypes.POINTER(wintypes.FILETIME)]*4
k.GetProcessTimes.restype=wintypes.BOOL
k.WaitForSingleObject.argtypes=(wintypes.HANDLE,wintypes.DWORD)
k.WaitForSingleObject.restype=wintypes.DWORD
k.CloseHandle.argtypes=(wintypes.HANDLE,)
k.CloseHandle.restype=wintypes.BOOL
QUERY_SYNC=0x00101000
WAIT_SIGNALED=0
WAIT_ALIVE=258

def marker(pipe,prefix,deadline=10):
    q=queue.Queue(maxsize=1)
    def scan():
        try:
            while True:
                line=pipe.readline()
                if not line:
                    q.put("")
                    return
                if line.startswith(prefix):
                    q.put(line[len(prefix):].strip())
                    return
        except Exception as e:
            q.put("ERR:"+str(e))
    threading.Thread(target=scan,daemon=True).start()
    line=q.get(timeout=deadline)
    if not line or line.startswith("ERR:"):
        raise AssertionError("MISSING_ACTOR_MARKER:"+line)
    return json.loads(line)

def held_process(pid):
    handle=k.OpenProcess(QUERY_SYNC,False,pid)
    if not handle: raise AssertionError("UNAVAILABLE_SYNTHETIC_PROCESS_HANDLE")
    times=[wintypes.FILETIME() for i in range(4)]
    if not k.GetProcessTimes(handle,*[ctypes.byref(x) for x in times]):
        k.CloseHandle(handle)
        raise AssertionError("UNAVAILABLE_SYNTHETIC_CREATION_TIME")
    return handle,str((times[0].dwHighDateTime<<32)|times[0].dwLowDateTime)

def case(mode):
    script=Path(__file__).with_name("native_owner_lifecycle_actor.mjs")
    actor=subprocess.Popen(["node",str(script),str(addon),mode],stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,bufsize=1,
        creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
    handles=[]
    try:
        ready=marker(actor.stdout,"PMVT_READY ")
        assert ready["mode"]==mode
        owner=ready["owner_snapshot"]
        assert owner["active_processes"]>=2
        assert owner["member_before_resume"] and owner["resume_succeeded"]
        assert owner["kill_on_owner_close"] and owner["breakaway_disabled"]
        root,created=held_process(ready["root_pid"])
        handles.append(root)
        desc,desc_time=held_process(ready["descendant_pid"])
        handles.append(desc)
        assert created==owner["creation_filetime_100ns"],"ROOT_BIRTH_IDENTITY_MISMATCH"
        assert int(desc_time)>0
        for h in handles: assert k.WaitForSingleObject(h,0)==WAIT_ALIVE,"NOT_ALIVE_BEFORE_STOP"
        if mode=="crash":
            actor.kill()  # Test harness terminates ONLY its own synthetic owner.
        else:
            actor.stdin.write("proceed\n")
            actor.stdin.flush()
            assert marker(actor.stdout,"PMVT_DONE ")["state"]=="OWNER_RETURNED"
        actor.wait(timeout=8)
        if mode=="crash": assert actor.returncode!=0,"OWNER_NOT_CRASHED"
        else: assert actor.returncode==0,"OWNER_FIXTURE_FAILURE"
        for h in handles:
            assert k.WaitForSingleObject(h,5000)==WAIT_SIGNALED,"RESIDUAL_SYNTHETIC_PROCESS"
        return {"mode":mode,"result":"PASS","root_creation_identity":"MATCH",
                "root_and_descendant_held_handles":"SIGNALED",
                "job_handle_transferred":False}
    finally:
        if actor.poll() is None:
            actor.kill()
            try:actor.wait(timeout=8)
            except subprocess.TimeoutExpired:pass
        for h in handles:k.CloseHandle(h)
        for pipe in (actor.stdin,actor.stdout,actor.stderr):
            if pipe:pipe.close()

cases=[]
for mode in ("natural","terminate","close","crash"):
    outcome=case(mode)
    cases.append(outcome)
    print(json.dumps({"scope":"SYNTHETIC_ONLY","case":outcome}),flush=True)
print(json.dumps({"schema":"pmvt.offhost-owner-adverse.v0.1","scope":"SYNTHETIC_ONLY",
    "state":"BOUNDED_WINDOWS_TEST_PASS","cases":cases,
    "original_rea_c5":"INDETERMINATE","msi":"NOT_RUN"},sort_keys=True))

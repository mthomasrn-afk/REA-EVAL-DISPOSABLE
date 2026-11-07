"""Public synthetic-only QHF-like CMD timeout + bounded middle + surviving leaf.

Tests the pipe-drain hypothesis, not original QHF/NEBQ, and provides no
qualification. All CI children terminate autonomously within seconds.
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

assert os.name=="nt"
root=Path(os.environ.get("RUNNER_TEMP",tempfile.gettempdir()))/"p72-qhf-finite-middle-v5"
root.mkdir(parents=True,exist_ok=True)
leaf_script=root/"synthetic_leaf.py"
leaf_script.write_text(
    '''import os,pathlib,sys,time
pathlib.Path(sys.argv[1]).write_text(str(os.getpid()),encoding="ascii")
time.sleep(7.5)  # public CI fail-safe: no indefinite orphan
''',encoding="utf-8")
middle_script=root/"synthetic_middle.py"
middle_script.write_text(
    '''import os,pathlib,subprocess,sys,time
root=pathlib.Path(sys.argv[1])
subprocess.Popen([sys.executable,str(root/"synthetic_leaf.py"),str(root/"leaf.ready")],
    stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
    close_fds=True)
(root/"middle.ready").write_text(str(os.getpid()),encoding="ascii")
time.sleep(2.75) # finite intermediate parent beyond QHF timeout
(root/"middle.done").write_text("DONE",encoding="ascii")
''',encoding="utf-8")
case=root/"synthetic_timeout.cmd"
case.write_bytes(("@echo off\r\n"+'"'+sys.executable+'" "'+str(middle_script)+'" "'+str(root)+'"\r\n').encode("utf-8"))
K=ctypes.WinDLL("kernel32",use_last_error=True)
K.OpenProcess.argtypes=[ctypes.c_uint32,ctypes.c_int,ctypes.c_uint32]
K.OpenProcess.restype=ctypes.c_void_p
K.WaitForSingleObject.argtypes=[ctypes.c_void_p,ctypes.c_uint32]
K.WaitForSingleObject.restype=ctypes.c_uint32
K.TerminateProcess.argtypes=[ctypes.c_void_p,ctypes.c_uint32]
K.TerminateProcess.restype=ctypes.c_int
K.CloseHandle.argtypes=[ctypes.c_void_p];K.CloseHandle.restype=ctypes.c_int
start=time.monotonic()
original_style_timeout=False
unexpected_error=None
returned_exit_code=None
try:
    # Original QHF uses this same stdlib subprocess.run shell mode and streams.
    p=subprocess.run([str(case)],cwd=str(root),stdin=subprocess.DEVNULL,
      stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=False,
      timeout=.85,check=False,shell=True,
      executable=os.environ.get("COMSPEC","cmd.exe"))
    returned_exit_code=p.returncode
except subprocess.TimeoutExpired:
    original_style_timeout=True
except Exception as ex:
    unexpected_error=type(ex).__name__+":"+str(ex)[:110]
elapsed=round(time.monotonic()-start,3)
# Simulate QHF writing a case/closeout after its transport call; do not
# create files using real QHF output names.
mock_receipt={
    "schema":"proj0072.synthetic-qhf-case-after-timeout.v1",
    "objective_disposition":"INDETERMINATE" if original_style_timeout else "NO_TIMEOUT",
    "timeout_attribution":"EXECUTION_TIMEOUT" if original_style_timeout else None,
    "transport_elapsed_seconds":elapsed,
}
(root/"SYNTHETIC_QHF_CASE_RESULT.json").write_text(
    json.dumps(mock_receipt,sort_keys=True,indent=2),encoding="utf-8")
leaf_marker=root/"leaf.ready"
middle_marker=root/"middle.ready"
leaf_pid=int(leaf_marker.read_text(encoding="ascii")) if leaf_marker.exists() else None
leaf_observed_alive=False
leaf_settled=False
forced_cleanup=False
if leaf_pid:
    h=K.OpenProcess(0x00100001,0,leaf_pid)
    if h:
        try:
            leaf_observed_alive=K.WaitForSingleObject(h,0)==0x102
            leaf_settled=K.WaitForSingleObject(h,7000)==0
            if not leaf_settled:
                forced_cleanup=bool(K.TerminateProcess(h,75))
                leaf_settled=K.WaitForSingleObject(h,1000)==0
        finally: K.CloseHandle(h)
pass_observation=(
    original_style_timeout and unexpected_error is None
    and 1.7<=elapsed<4.5 and middle_marker.exists()
    and (root/"middle.done").exists() and leaf_observed_alive
    and leaf_settled and not forced_cleanup
)
receipt={
    "schema":"proj0072.synthetic-qhf-finite-middle.v5",
    "classification":"PUBLIC_SYNTHETIC_DIAGNOSTIC_ONLY",
    "result":"OBSERVED_SYNTHETIC_TIMEOUT_AND_LEAF_LIFETIME" if pass_observation else "INDETERMINATE",
    "qHF_style_timeout_recorded":original_style_timeout,
    "transport_elapsed_seconds":elapsed,
    "unexpected_error":unexpected_error,
    "unexpected_exit_code":returned_exit_code,
    "middle_finite_exit_observed":(root/"middle.done").exists(),
    "leaf_alive_after_qhf_style_case_return":leaf_observed_alive,
    "leaf_bounded_settlement_observed":leaf_settled,
    "forced_cleanup":forced_cleanup,
    "mock_case_result_exists":(root/"SYNTHETIC_QHF_CASE_RESULT.json").exists(),
    "original_qhf_executed":False,"original_nebq_executed":False,
    "factory_qualification":"NOT_ESTABLISHED",
    "python":sys.version.split()[0],
}
(root/"RESULT.json").write_text(json.dumps(receipt,indent=2,sort_keys=True),encoding="utf-8")
print("QHF_FINITE_MIDDLE_V5",json.dumps(receipt,sort_keys=True))
raise SystemExit(0 if pass_observation else 1)

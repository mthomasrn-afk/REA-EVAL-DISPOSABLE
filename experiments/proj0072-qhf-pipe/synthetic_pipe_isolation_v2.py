"""Synthetic Windows pipe-lifetime isolation (public-safe; no REA/Factory source)."""
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
ROOT = Path(os.environ.get("RUNNER_TEMP", tempfile.gettempdir())) / "p72-qhf-stdio-isolation-v2"
ROOT.mkdir(parents=True, exist_ok=True)
parent = ROOT / "synthetic_parent.py"
parent.write_text(
    '''from __future__ import annotations
import os
from pathlib import Path
import subprocess
import sys
import time
ready, done, mode = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
if mode == "self_nul":
    sink = os.open(os.devnull, os.O_WRONLY)
    os.dup2(sink, 1)
    os.dup2(sink, 2)
    os.close(sink)
subprocess.Popen(
    [sys.executable, "-c", "import time; time.sleep(0.5)"],
    stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL, close_fds=True
)
ready.write_text(str(os.getpid()), encoding="ascii")
time.sleep(3.6)  # bound every child; no unbounded workloads
done.write_text("DONE", encoding="ascii")
''', encoding="utf-8"
)
K = ctypes.WinDLL("kernel32", use_last_error=True)
K.OpenProcess.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32]
K.OpenProcess.restype = ctypes.c_void_p
K.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
K.WaitForSingleObject.restype = ctypes.c_uint32
K.TerminateProcess.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
K.TerminateProcess.restype = ctypes.c_int
K.CloseHandle.argtypes = [ctypes.c_void_p]
K.CloseHandle.restype = ctypes.c_int
WAIT_OBJECT_0, WAIT_TIMEOUT = 0, 0x102
SYNCHRONIZE, TERMINATE = 0x00100000, 0x0001
cases = {}
for kind in ("direct_inherited", "direct_self_nul", "cmd_child_nul", "cmd_caller_nul"):
    ready = ROOT / (kind + ".pid")
    done = ROOT / (kind + ".done")
    mode = "self_nul" if kind == "direct_self_nul" else "keep"
    cmd = [sys.executable, str(parent), str(ready), str(done), mode]
    if kind.startswith("cmd_"):
        launcher = ROOT / (kind + ".cmd")
        launcher.write_bytes((
            '@echo off\r\n'
            + '"' + sys.executable + '" "' + str(parent) + '" "'
            + str(ready) + '" "' + str(done) + '" keep >NUL 2>&1\r\n'
        ).encode("utf-8"))
        cmd = [os.environ.get("COMSPEC", "cmd.exe"), "/d", "/c", str(launcher)]
    captured = kind != "cmd_caller_nul"
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    start = time.monotonic()
    timed_out = False
    return_code = None
    try:
        p = subprocess.run(
            cmd,
            stdout=subprocess.PIPE if captured else subprocess.DEVNULL,
            stderr=subprocess.PIPE if captured else subprocess.DEVNULL,
            timeout=0.9, env=env,
        )
        return_code = p.returncode
    except subprocess.TimeoutExpired:
        timed_out = True
    elapsed = round(time.monotonic()-start, 3)
    pid = int(ready.read_text(encoding="ascii")) if ready.exists() else None
    alive_at_return = None
    independently_settled = None
    force_terminated = False
    if pid is not None:
        h = K.OpenProcess(SYNCHRONIZE | TERMINATE, 0, pid)
        if h:
            try:
                alive_at_return = K.WaitForSingleObject(h, 0) == WAIT_TIMEOUT
                independently_settled = K.WaitForSingleObject(h, 5000) == WAIT_OBJECT_0
                if not independently_settled:
                    force_terminated = bool(K.TerminateProcess(h, 73))
                    independently_settled = K.WaitForSingleObject(h, 1000) == WAIT_OBJECT_0
            finally:
                K.CloseHandle(h)
    cases[kind] = {
        "elapsed_seconds": elapsed,
        "caller_timeout_observed": timed_out,
        "unexpected_return_code": return_code,
        "ready_marker_observed": pid is not None,
        "done_marker_observed": done.exists(),
        "parent_alive_at_caller_return": alive_at_return,
        "parent_handle_settled_when_observable": independently_settled,
        "forced_cleanup": force_terminated,
        "caller_captured_output": captured,
    }

all_safe = all(
    c["caller_timeout_observed"] and c["ready_marker_observed"]
    and c["done_marker_observed"] and not c["forced_cleanup"]
    for c in cases.values()
)
comparison = {
    "direct_inherited_is_slow": cases["direct_inherited"]["elapsed_seconds"] > 2.4,
    "direct_self_redirect_is_fast": cases["direct_self_nul"]["elapsed_seconds"] < 2.2,
    "cmd_child_redirect_is_slow": cases["cmd_child_nul"]["elapsed_seconds"] > 2.4,
    "cmd_no_capture_is_fast": cases["cmd_caller_nul"]["elapsed_seconds"] < 2.2,
}
receipt = {
    "schema": "proj0072.synthetic-pipe-isolation.v2",
    "classification": "PUBLIC_SYNTHETIC_DIAGNOSTIC_ONLY",
    "result": "RECORDED_SYNTHETIC_COMPARISON" if all_safe else "BLOCKED_INCOMPLETE_SYNTHETIC_OBSERVATION",
    "hypotheses": comparison,
    "cases": cases,
    "original_qhf_executed": False,
    "original_nebq_executed": False,
    "factory_qualification": "NOT_ESTABLISHED",
    "python": sys.version.split()[0],
}
(ROOT/"RESULT.json").write_text(json.dumps(receipt,sort_keys=True,indent=2),encoding="utf-8")
print("PIPE_V2_SYNTHETIC_RECEIPT",json.dumps(receipt,sort_keys=True))
raise SystemExit(0 if all_safe else 1)

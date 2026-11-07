"""Public synthetic-only Windows diagnostic: CMD timeout and inherited stdout pipes.

No QHF/NEBQ/REA code, proprietary inputs, local-host paths or secrets.
Original subprocess.run timeout semantics are exercised, not Factory qualification.
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

assert os.name == "nt", "Windows-only diagnostic"
ROOT = Path(os.environ.get("RUNNER_TEMP", tempfile.gettempdir())) / "p72-synthetic-qhf-pipe-20261107"
ROOT.mkdir(parents=True, exist_ok=True)
PARENT = ROOT / "synthetic_parent.py"
PARENT.write_text(
    '''from __future__ import annotations
import os
from pathlib import Path
import subprocess
import sys
import time
ready = Path(sys.argv[1])
# Leaf deliberately has DEVNULL streams, so only the intermediate parent
# can keep the QHF-style captured stdout/stderr pipes open.
subprocess.Popen(
    [sys.executable, "-c", "import time; time.sleep(0.6)"],
    stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL, close_fds=True
)
ready.write_text(str(os.getpid()), encoding="ascii")
print("SYNTHETIC_PARENT_READY", flush=True)
time.sleep(4.0)  # fail-safe: terminates without external intervention
''', encoding="utf-8",
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
SYNCHRONIZE = 0x00100000
PROCESS_TERMINATE = 0x0001
WAIT_OBJECT_0 = 0
WAIT_TIMEOUT = 0x102
COMSPEC = os.environ.get("COMSPEC", "cmd.exe")
CASES = {}

def check_parent(pid: int) -> tuple[bool | None, bool, bool]:
    """Report parent alive immediately after caller returned; wait for bounded exit."""
    handle = K.OpenProcess(SYNCHRONIZE | PROCESS_TERMINATE, 0, pid)
    if not handle:
        return None, False, False
    try:
        immediate = K.WaitForSingleObject(handle, 0)
        alive = (immediate == WAIT_TIMEOUT)
        finished = K.WaitForSingleObject(handle, 6000) == WAIT_OBJECT_0
        forced = False
        if not finished:  # fail-safe for synthetic-only owned PID
            forced = bool(K.TerminateProcess(handle, 71))
            finished = K.WaitForSingleObject(handle, 1000) == WAIT_OBJECT_0
        return alive, finished, forced
    finally:
        K.CloseHandle(handle)

for variant, redirection in (
    ("inherited_pipe", ""),
    ("redirect_intermediate_parent", " >NUL 2>&1"),
):
    ready = ROOT / (variant + ".pid")
    script = ROOT / (variant + ".cmd")
    script.write_bytes((
        '@echo off\r\n'
        + '"' + sys.executable + '" "' + str(PARENT) + '" "' + str(ready) + '"'
        + redirection + '\r\n'
    ).encode("utf-8"))
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    start = time.monotonic()
    timed_out = False
    child_return = None
    try:
        proc = subprocess.run(
            [COMSPEC, "/d", "/c", str(script)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=1.0, env=environment,
        )
        child_return = proc.returncode
    except subprocess.TimeoutExpired:
        timed_out = True
    elapsed = round(time.monotonic() - start, 3)
    pid = int(ready.read_text(encoding="ascii")) if ready.exists() else None
    alive_at_return = None
    settled = False
    forced_cleanup = False
    if pid is not None:
        alive_at_return, settled, forced_cleanup = check_parent(pid)
    CASES[variant] = {
        "caller_timeout_observed": timed_out,
        "returned_exit_code_if_any": child_return,
        "caller_elapsed_seconds": elapsed,
        "parent_marker_observed": pid is not None,
        "parent_alive_at_caller_return": alive_at_return,
        "parent_bounded_settled": settled,
        "forced_cleanup": forced_cleanup,
    }

a = CASES["inherited_pipe"]
b = CASES["redirect_intermediate_parent"]
ok = all(c["caller_timeout_observed"] and c["parent_marker_observed"]
         and c["parent_bounded_settled"] and not c["forced_cleanup"]
         for c in (a, b))
ok = ok and (
    a["caller_elapsed_seconds"] >= 2.8
    and b["caller_elapsed_seconds"] <= 2.2
    and a["caller_elapsed_seconds"] - b["caller_elapsed_seconds"] >= 1.0
    and b["parent_alive_at_caller_return"] is True
)
receipt = {
    "schema": "proj0072.synthetic-qhf-pipe-inheritance.v1",
    "classification": "SYNTHETIC_DIAGNOSTIC_ONLY",
    "result": "OBSERVED_PIPE_INHERITANCE_DELAY" if ok else "INDETERMINATE_OR_FAILED",
    "scope": "stdlib subprocess.run + CMD + synthetic Python parent/leaf only",
    "windows_runner": os.environ.get("RUNNER_OS") == "Windows",
    "python_version": sys.version.split()[0],
    "cases": CASES,
    "original_qhf_executed": False,
    "original_nebq_executed": False,
    "factory_qualification": "NOT_ESTABLISHED",
}
out = ROOT / "RESULT.json"
out.write_text(json.dumps(receipt, indent=2, sort_keys=True), encoding="utf-8")
print("SYNTHETIC_PIPE_DIAGNOSTIC", json.dumps(receipt, sort_keys=True))
raise SystemExit(0 if ok else 1)

#!/usr/bin/env python3
"""Independent synthetic CMD descendant acceptance-preparation for REA's original
owner with existing test-only process_evidence. Does not execute original QHF.
No secondary process supervisor or duplicated owner; no original C5 PASS.
"""
from __future__ import annotations
import copy
import ctypes
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
from ctypes import wintypes
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "owner-qualification"))
import owner_host_acceptance as own
import exact_job_witness as exact

ALIVE = 258
DONE = 0
PIN = "3b79af28e80785afce9f5998d8f03289402a1847"
ROLES = ("parent", "middle", "leaf_a", "leaf_b")

def require(pred, code):
    if not pred:
        raise RuntimeError(code)

def role(name):
    if name not in ROLES:
        raise ValueError("INVALID_SYNTHETIC_ROLE")
    work = Path(os.environ["REA_C5_MARKERS"])
    children = {"parent": ("middle",), "middle": ("leaf_a", "leaf_b")}
    for child in children.get(name, ()):
        subprocess.Popen(
            [sys.executable, "-B", str(Path(__file__).resolve()), "--role", child],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            cwd=str(work), creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            close_fds=True,
        )
    marker = {"role": name, "pid": os.getpid(), "ppid": os.getppid()}
    part = work / (name + ".writing")
    final = work / (name + ".ready")
    if final.exists() or part.exists():
        raise RuntimeError("DUPLICATE_SYNTHETIC_ROLE")
    part.write_text(json.dumps(marker, sort_keys=True), encoding="ascii")
    os.replace(part, final)
    time.sleep(25)
    return 0

def qpc(k):
    val = ctypes.c_longlong()
    require(k.QueryPerformanceCounter(ctypes.byref(val)), "INDEPENDENT_QPC_READ_FAILED")
    return int(val.value)

def complete_sample(s, *, expected, foreign, root, root_creation, begin, end):
    if not isinstance(s, dict) or s.get("schema") != "rea.owner.evidence.v0.1.0-candidate":
        return False
    if s.get("claimScope") != "OWNER_ATTRIBUTED_NOT_INDEPENDENT":
        return False
    if s.get("completeAtSample") is not True or s.get("pidListComplete") is not True:
        return False
    if s.get("preResumeMembershipAsserted") is not True or s.get("policyFlags") != 0x2000:
        return False
    if any(type(s.get(x)) is not int or s[x] != 0 for x in
           ("pidError", "accountingError", "policyError", "identityError")):
        return False
    p = s.get("currentJobPids")
    if not isinstance(p, list) or any(type(x) is not int or x <= 0 for x in p):
        return False
    if len(p) != len(set(p)) or len(p) != s.get("jobReturnedCount") or len(p) != s.get("jobAssignedCount"):
        return False
    if len(p) > 64 or set(p) != set(expected) or foreign in p:
        return False
    if s.get("rootPid") != root or s.get("rootCreationFiletime") != root_creation:
        return False
    try:
        q0, q1 = int(s["queryQpcStart"]), int(s["queryQpcEnd"])
        pre, post, hz = int(s["preResumeQpc"]), int(s["afterResumeQpc"]), int(s["qpcFrequency"])
    except (KeyError, ValueError, TypeError):
        return False
    return 0 < pre <= post < q0 <= q1 and hz > 0 and begin <= q0 <= q1 <= end

def wait_markers(work):
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline:
        if all((work / (name+".ready")).is_file() for name in ROLES):
            rows = [json.loads((work/(name+".ready")).read_text(encoding="ascii")) for name in ROLES]
            if all(row.get("role") == name and type(row.get("pid")) is int and
                   type(row.get("ppid")) is int and row["pid"] > 0
                   for row, name in zip(rows, ROLES)):
                return rows
            raise RuntimeError("SYNTHETIC_ROLE_MARKERS_INVALID")
        time.sleep(.025)
    raise RuntimeError("SYNTHETIC_ROLE_READINESS_TIMEOUT")

def run(addon, manifest, receipt, output):
    result = {
        "schema": "rea.c5.cmd-descendant.synthetic-ci.v1",
        "original_rea": "NOT_QUALIFIED",
        "original_ac15": "PARTIAL",
        "original_ac17": "INDETERMINATE",
        "original_qhf": "INDETERMINATE_RETAINED_NOT_EXECUTED",
        "original_r5_4_vs_7": "UNCHANGED_ADVERSE_NOT_RETESTED",
        "strict_original_qhf_fixture": "NOT_RUN",
        "scope": "CLEARED_SYNTHETIC_CMD_BOUNDARY_UNDER_ORIGINAL_REA_OWNER_CANDIDATE",
        "result": "INDETERMINATE",
        "negative_controls": {},
    }
    actor = foreign = None
    known = []
    all_held = []
    outsider = None
    k = None
    try:
        require(os.name == "nt" and ctypes.sizeof(ctypes.c_void_p) == 8, "WINDOWS_X64_REQUIRED")
        m = json.loads(manifest.read_text(encoding="utf-8"))
        r = json.loads(receipt.read_text(encoding="utf-8"))
        digest = hashlib.sha256(addon.read_bytes()).hexdigest()
        require(m.get("packageVersion") == "6.5.0" and m.get("artifactSha256") == digest,
                "NATIVE_ADDON_ARTIFACT_IDENTITY_INVALID")
        require(r.get("source_commit") == PIN and r.get("new_native_operation") == "process_evidence"
                and r.get("job_handle_duplicated") is False
                and r.get("original_git_blobs", {}).get("native/windows/src/process.cc") ==
                    "55e4153455b732115812d12d17c94709c1a65fdb",
                "ORIGINAL_PROCESS_OWNER_SOURCE_IDENTITY_INVALID")
        result["native_sha256"] = digest
        k, nt = exact.apis()
        k.QueryPerformanceCounter.argtypes = (ctypes.POINTER(ctypes.c_longlong),)
        k.QueryPerformanceCounter.restype = wintypes.BOOL
        with tempfile.TemporaryDirectory(prefix="REA_C5_CMD_CLEAR_") as d:
            work = Path(d).resolve()
            cmdfile = work / "SYNTHETIC_QHF_LIKE_CASE.cmd"
            cmdfile.write_text(
                '@echo off\r\n"%REA_C5_PYTHON%" -B "%REA_C5_ROLE_SCRIPT%" --role parent\r\n'
                'exit /b %ERRORLEVEL%\r\n', encoding="ascii")
            actor = subprocess.Popen(
                ["node", str(HERE / "cmd_tree_actor.mjs"), str(addon),
                 str(cmdfile), sys.executable, str(Path(__file__).resolve()), str(work)],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, bufsize=1, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            foreign = subprocess.Popen(
                [sys.executable, "-c", "import time;time.sleep(40)"],
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            ready = own.marker(actor.stdout, "CMD_OWNER_READY ", 10)
            root = ready.get("root_pid")
            require(type(root) is int and root > 0, "CMD_ROOT_PID_UNAVAILABLE")
            rows = wait_markers(work)
            declared = [root] + [row["pid"] for row in rows]
            require(len(set(declared)) == 5, "DECLARED_CMD_TREE_PID_COLLISION")
            markers = dict(zip(ROLES, rows))
            require(markers["parent"]["ppid"] == root
                    and markers["middle"]["ppid"] == markers["parent"]["pid"]
                    and markers["leaf_a"]["ppid"] == markers["middle"]["pid"]
                    and markers["leaf_b"]["ppid"] == markers["middle"]["pid"],
                    "SYNTHETIC_CMD_PROCESS_LINEAGE_NOT_ESTABLISHED")
            for pid in declared:
                h, creation, _ = own.acquire(pid)
                all_held.append((pid, h, creation))
            outsider, foreign_creation, _ = own.acquire(foreign.pid)
            require(all(k.WaitForSingleObject(h, 0) == ALIVE for _, h, _ in all_held)
                    and k.WaitForSingleObject(outsider, 0) == ALIVE,
                    "CMD_DECLARED_PROCESS_ALREADY_SETTLED")
            actor.stdin.write("observe\n")
            actor.stdin.flush()
            discovery = own.marker(actor.stdout, "CMD_OWNER_SAMPLE ", 9)
            present = discovery.get("currentJobPids")
            require(discovery.get("completeAtSample") is True
                    and discovery.get("pidListComplete") is True
                    and isinstance(present, list) and len(set(present)) == len(present)
                    and set(declared).issubset(set(present)) and foreign.pid not in present
                    and len(present) <= 24, "CMD_JOB_PID_DISCOVERY_UNSAFE_OR_INCOMPLETE")
            extras = sorted(set(present) - set(declared))
            for pid in extras:
                h, creation, _ = own.acquire(pid)
                all_held.append((pid, h, creation))
            require(set(x[0] for x in all_held) == set(present)
                    and all(k.WaitForSingleObject(h, 0) == ALIVE for _, h, _ in all_held),
                    "CMD_UNKNOWN_DESCENDANT_NOT_INDEPENDENTLY_HELD")
            actor_handle = k.OpenProcess(exact.P_QUERY | exact.P_DUP, False, actor.pid)
            require(bool(actor_handle), "CMD_OWNER_HANDLE_UNAVAILABLE")
            try:
                attested = exact.witness(k, nt, actor_handle,
                                         [h for _, h, _ in all_held], outsider)
            finally:
                k.CloseHandle(actor_handle)
            require(attested.get("known_process_memberships") == [True]*len(all_held)
                    and attested.get("unrelated_process_is_nonmember") is True
                    and attested.get("duplicate_calls_succeeded") ==
                        attested.get("duplicate_query_handles_closed"),
                    "CMD_EXACT_OWNER_JOB_MEMBERSHIP_NOT_INDEPENDENTLY_ESTABLISHED")
            result["independent_exact_job_witness"] = attested
            # New strictly observational discriminator for the historical
            # console-host hypothesis. Query only the already-held Job PIDs;
            # record basename only, no full path, account, or ambient scan.
            k.QueryFullProcessImageNameW.argtypes = (
                wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR,
                ctypes.POINTER(wintypes.DWORD))
            k.QueryFullProcessImageNameW.restype = wintypes.BOOL
            image_basenames = {}
            for pid, handle, creation in all_held:
                chars = wintypes.DWORD(512)
                buffer = ctypes.create_unicode_buffer(512)
                ok = k.QueryFullProcessImageNameW(
                    handle, 0, buffer, ctypes.byref(chars))
                require(bool(ok) and 0 < chars.value < 512,
                        "HELD_PROCESS_IMAGE_NAME_UNAVAILABLE")
                basename = Path(buffer.value).name.casefold()
                require(bool(basename) and basename == Path(basename).name,
                        "PROCESS_BASENAME_INVALID")
                image_basenames[pid] = basename
            result["held_pid_image_basename"] = [
                {"pid": pid, "basename": image_basenames[pid],
                 "declared_by_synthetic_fixture": pid in declared}
                for pid, _, _ in all_held
            ]
            result["unexpected_image_basenames"] = sorted(
                image_basenames[pid] for pid in extras)
            result["image_evidence_scope"] = (
                "INDEPENDENT_KERNEL_HANDLE_BASENAME_ONLY_NOT_PARENT_CAUSALITY"
            )
            require(all(k.WaitForSingleObject(h, 0) == ALIVE for _, h, _ in all_held),
                    "CMD_LIVE_BEFORE_SECOND_QUERY_FAILED")
            before = qpc(k)
            actor.stdin.write("observe\n")
            actor.stdin.flush()
            sample = own.marker(actor.stdout, "CMD_OWNER_SAMPLE ", 9)
            after = qpc(k)
            require(all(k.WaitForSingleObject(h, 0) == ALIVE for _, h, _ in all_held),
                    "CMD_LIVE_AFTER_SECOND_QUERY_FAILED")
            require(complete_sample(sample, expected=present, foreign=foreign.pid,
                                    root=root, root_creation=all_held[0][2],
                                    begin=before, end=after), "CMD_SAME_JOB_SNAPSHOT_INVALID")
            result["independent_held_identities"] = [
                {"pid":p,"creation_filetime_100ns":t} for p, _, t in all_held]
            result["cmd_declared_processes"] = len(declared)
            result["cmd_unexpected_job_processes"] = len(extras)
            result["cmd_source_sample_pids"] = sorted(present)
            result["bounded_qpc_window"] = [str(before), str(after)]
            result["owner_handles_released_before_close"] = True
            wrong = copy.deepcopy(sample)
            wrong["currentJobPids"].append(foreign.pid)
            wrong["jobReturnedCount"] = len(wrong["currentJobPids"])
            wrong["jobAssignedCount"] = len(wrong["currentJobPids"])
            for name, evidence in (
                ("foreign_contamination", wrong),
                ("incomplete_class3", dict(sample, completeAtSample=False)),
                ("policy_missing", dict(sample, policyFlags=0)),
                ("stale_creation", dict(sample, rootCreationFiletime="0")),
            ):
                require(not complete_sample(evidence, expected=present, foreign=foreign.pid,
                                            root=root, root_creation=all_held[0][2],
                                            begin=before, end=after),
                        "CMD_FALSE_PASS_NEGATIVE_" + name)
                result["negative_controls"][name] = "REJECTED"
            require(actor.poll() is None, "CMD_OWNER_EXITED_BEFORE_JOB_CLOSE")
            actor.stdin.write("go\n")
            actor.stdin.flush()
            actor.stdin.close()
            done = own.marker(actor.stdout, "CMD_OWNER_DONE ", 9)
            require(done.get("owner_closed") is True, "CMD_OWNER_CLOSE_NOT_ACKNOWLEDGED")
            actor.wait(timeout=9)
            require(actor.returncode == 0, "CMD_OWNER_ERROR")
            waits = [int(k.WaitForSingleObject(h, 5000)) for _, h, _ in all_held]
            require(waits == [DONE]*len(all_held), "CMD_DESCENDANT_RESIDUAL_AFTER_OWNER_CLOSE")
            require(k.WaitForSingleObject(outsider, 0) == ALIVE,
                    "CMD_FOREIGN_CONTROL_KILLED")
            result["held_process_waits_after_close"] = waits
            result["foreign_control_survived"] = True
            result["result"] = "PASS_SCOPED_SYNTHETIC_CMD_CONTAINMENT_ONLY"
    except Exception as exc:
        result["result"] = "FAIL_OR_INDETERMINATE"
        result["reason"] = type(exc).__name__ + ":" + str(exc)[:230]
    finally:
        if actor and actor.poll() is None:
            actor.kill()
            try:
                actor.wait(timeout=9)
            except subprocess.TimeoutExpired:
                result["actor_cleanup_unsettled"] = True
        if k:
            result["post_failure_owned_waits"] = [
                int(k.WaitForSingleObject(h, 100)) for _, h, _ in all_held]
            for _, h, _ in all_held:
                k.CloseHandle(h)
            if outsider:
                k.CloseHandle(outsider)
        if foreign:
            if foreign.poll() is None:
                foreign.kill()
            try:
                foreign.wait(timeout=9)
            except subprocess.TimeoutExpired:
                result["foreign_cleanup_unsettled"] = True
        if actor:
            for stream in (actor.stdin, actor.stdout, actor.stderr):
                try:
                    if stream:
                        stream.close()
                except (OSError, ValueError):
                    pass
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, indent=2, sort_keys=True)+"\n", encoding="utf-8")
        print("REA_C5_CMD", json.dumps({
            "result": result["result"], "reason": result.get("reason"),
            "unexpected_job_members": result.get("cmd_unexpected_job_processes"),
            "original_ac17": result["original_ac17"]}))
    return 0 if result["result"] == "PASS_SCOPED_SYNTHETIC_CMD_CONTAINMENT_ONLY" else 2

if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--role":
        raise SystemExit(role(sys.argv[2]))
    if len(sys.argv) != 5:
        raise SystemExit("usage: cmd_tree_test.py addon manifest patch_receipt output")
    raise SystemExit(run(*(Path(x).resolve() for x in sys.argv[1:])))

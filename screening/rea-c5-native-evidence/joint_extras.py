#!/usr/bin/env python3
"""Synthetic-only joint exact Job/owner snapshot test; NOT original C5/QHF qualification.
No private original R5/R6, no external Job handle during owner close or crash.
"""
from __future__ import annotations
import copy
import ctypes
import hashlib
import json
import os
import subprocess
import sys
from ctypes import wintypes
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "owner-qualification"))
import owner_host_acceptance as own
import exact_job_witness as exact
from judge import adjudicate

PIN = "3b79af28e80785afce9f5998d8f03289402a1847"
ALIVE, DONE = 258, 0

def check(value, reason):
    if not value:
        raise RuntimeError(reason)

def qpc(k):
    value = ctypes.c_longlong()
    check(k.QueryPerformanceCounter(ctypes.byref(value)), "INDEPENDENT_QPC_FAILED")
    return int(value.value)

def run(addon, manifest, receipt, output):
    result = {"schema":"rea.c5.joint-exact-job-synthetic-ci.v1",
              "original_rea":"NOT_QUALIFIED","original_ac15":"PARTIAL",
              "original_ac17":"INDETERMINATE","original_nebq_r1":"UNQUALIFIED",
              "original_r5_4_vs_7":"UNCHANGED_ADVERSE_NOT_RETESTED",
              "scope":"CLEARED_SYNTHETIC_ORIGINAL_REA_OWNER_WITH_TEST_ONLY_EVIDENCE_SEAM",
              "result":"INDETERMINATE","negative_controls":{}}
    actor = foreign = None
    owned = []
    outsider = None
    k = None
    try:
        check(os.name == "nt" and ctypes.sizeof(ctypes.c_void_p) == 8, "WINDOWS_X64_REQUIRED")
        metadata = json.loads(manifest.read_text(encoding="utf-8"))
        patch = json.loads(receipt.read_text(encoding="utf-8"))
        digest = hashlib.sha256(addon.read_bytes()).hexdigest()
        check(metadata.get("packageVersion") == "6.5.0"
              and metadata.get("artifactSha256") == digest, "NATIVE_ARTIFACT_NOT_SOURCE_BOUND")
        check(patch.get("source_commit") == PIN
              and patch.get("new_native_operation") == "process_evidence"
              and patch.get("job_handle_duplicated") is False, "ORIGINAL_OWNER_PATCH_PIN_INVALID")
        check(patch.get("original_git_blobs", {}).get("native/windows/src/process.cc")
              == "55e4153455b732115812d12d17c94709c1a65fdb", "ORIGINAL_OWNER_GIT_BLOB_INVALID")
        result["native_sha256"] = digest
        k, nt = exact.apis()
        k.QueryPerformanceCounter.argtypes = (ctypes.POINTER(ctypes.c_longlong),)
        k.QueryPerformanceCounter.restype = wintypes.BOOL
        actor = subprocess.Popen(
            ["node", str(HERE / "telemetry_actor.mjs"), str(addon), "close"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, bufsize=1, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        foreign = subprocess.Popen(
            [sys.executable, "-c", "import time;time.sleep(40)"],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        ready = own.marker(actor.stdout, "OWNER_READY ", 9)
        known = ready.get("pids")
        check(ready.get("mode") == "close" and isinstance(known, list)
              and len(known) == 3 and len(set(known)) == 3, "DECLARED_SYNTHETIC_ROLES_INVALID")
        for pid in known:
            h, creation, _ = own.acquire(pid)
            owned.append((pid, h, creation))
        outsider, foreign_created, _ = own.acquire(foreign.pid)
        check(all(k.WaitForSingleObject(h, 0) == ALIVE for _, h, _ in owned)
              and k.WaitForSingleObject(outsider, 0) == ALIVE, "INITIAL_INDEPENDENT_IDENTITIES_NOT_ALIVE")
        actor.stdin.write("observe\n")
        actor.stdin.flush()
        discovery = own.marker(actor.stdout, "OWNER_EVIDENCE ", 9)
        present = discovery.get("currentJobPids")
        check(discovery.get("completeAtSample") is True
              and discovery.get("pidListComplete") is True
              and isinstance(present, list) and len(set(present)) == len(present)
              and set(known).issubset(set(present)) and foreign.pid not in present,
              "FIRST_OWNER_JOB_SAMPLE_INCOMPLETE")
        extras = sorted(set(present) - set(known))
        check(len(extras) == 3 and len(present) == 6, "UNEXPECTED_SYNTHETIC_EXTRA_COUNT")
        for pid in extras:
            h, creation, _ = own.acquire(pid)
            owned.append((pid, h, creation))
        check(set(pid for pid, _, _ in owned) == set(present)
              and all(k.WaitForSingleObject(h, 0) == ALIVE for _, h, _ in owned),
              "INDEPENDENT_FIRST_SAMPLE_HOLD_INCOMPLETE")
        actor_handle = k.OpenProcess(exact.P_QUERY | exact.P_DUP, False, actor.pid)
        check(bool(actor_handle), "SCOPED_OWNER_HANDLE_QUERY_UNAVAILABLE")
        try:
            # Exact owner Job readback for ALL six; duplicate Job query handles
            # close within witness() BEFORE any owner close is allowed.
            witnessed = exact.witness(k, nt, actor_handle,
                                      [h for _, h, _ in owned], outsider)
        finally:
            k.CloseHandle(actor_handle)
        check(witnessed.get("known_process_memberships") == [True]*len(owned)
              and witnessed.get("unrelated_process_is_nonmember") is True
              and witnessed.get("duplicate_calls_succeeded") ==
                  witnessed.get("duplicate_query_handles_closed")
              and witnessed.get("job_handle_duplicate_release") == "BEFORE_OWNER_CLOSE",
              "SCOPE_EXACT_OWNER_JOB_EVIDENCE_MISSING")
        result["independent_exact_job_witness"] = witnessed
        check(all(k.WaitForSingleObject(h, 0) == ALIVE for _, h, _ in owned),
              "AFTER_EXACT_JOB_WITNESS_MEMBER_EXITED")
        before = qpc(k)
        actor.stdin.write("observe\n")
        actor.stdin.flush()
        sample = own.marker(actor.stdout, "OWNER_EVIDENCE ", 9)
        after = qpc(k)
        check(all(k.WaitForSingleObject(h, 0) == ALIVE for _, h, _ in owned),
              "AFTER_SAME_OWNER_QUERY_MEMBER_EXITED")
        check(sample.get("completeAtSample") is True
              and set(sample.get("currentJobPids", [])) == set(present),
              "COMMON_OWNER_PID_SNAPSHOT_INCOMPLETE")
        verdict = adjudicate(sample, known_pids=known, root_creation=owned[0][2],
                             outsider_pid=foreign.pid, start_qpc=before, end_qpc=after,
                             witnessed_extra_pids=extras)
        check(verdict.get("disposition") == "PASS_SCOPED_REPORTED_IDENTITIES_WITH_EXTRAS"
              and verdict.get("rea_qualified") is False
              and verdict.get("original_ac15") == "PARTIAL", "SOURCE_JUDGE_FALSE_OR_INCOMPLETE")
        result["source_owner_judgment"] = verdict
        result["held_kernel_identities"] = [
            {"pid": pid, "creation_filetime_100ns": creation} for pid, _, creation in owned]
        result["joint_qpc_bracket"] = [str(before), str(after)]
        result["independent_exact_job_membership_observed"] = True
        result["all_query_handles_closed_before_owner_release"] = True
        # Paired negatives are judged by the existing source-bounded adjudicator.
        evil = copy.deepcopy(sample)
        evil["currentJobPids"].append(foreign.pid)
        evil["jobReturnedCount"] = len(evil["currentJobPids"])
        evil["jobAssignedCount"] = len(evil["currentJobPids"])
        for name, observation, witnessed_extras in (
            ("foreign_member", evil, extras),
            ("missing_extra_witness", sample, extras[:-1]),
            ("incomplete_pid_list", dict(sample, completeAtSample=False), extras),
            ("wrong_policy", dict(sample, policyFlags=0), extras),
        ):
            rejected = adjudicate(observation, known_pids=known,
                                  root_creation=owned[0][2], outsider_pid=foreign.pid,
                                  start_qpc=before, end_qpc=after,
                                  witnessed_extra_pids=witnessed_extras)
            check(not rejected["disposition"].startswith("PASS"),
                  "FALSE_POSITIVE_NEGATIVE_CONTROL_" + name)
            result["negative_controls"][name] = rejected["disposition"]
        check(actor.poll() is None, "OWNER_EXITED_BEFORE_APPROVED_RELEASE")
        actor.stdin.write("go\n")
        actor.stdin.flush()
        actor.stdin.close()
        done = own.marker(actor.stdout, "OWNER_DONE ", 9)
        check(done.get("owner_returned") is True, "OWNER_CLOSE_NOT_ACKNOWLEDGED")
        actor.wait(timeout=9)
        check(actor.returncode == 0, "OWNER_CLOSE_RETURNED_ERROR")
        waits = [int(k.WaitForSingleObject(h, 5000)) for _, h, _ in owned]
        check(waits == [DONE]*len(owned), "RESIDUAL_AFTER_OWNER_CLOSE")
        check(k.WaitForSingleObject(outsider, 0) == ALIVE, "FOREIGN_PROCESS_NOT_PRESERVED")
        result["after_close_independent_waits"] = waits
        result["foreign_survived"] = True
        result["observed_known_count"] = len(known)
        result["observed_extra_count"] = len(extras)
        result["result"] = "PASS_SCOPED_JOINT_SYNTHETIC_ONLY"
    except Exception as exc:
        result["result"] = "FAIL_OR_INDETERMINATE"
        result["reason"] = type(exc).__name__ + ":" + str(exc)[:210]
    finally:
        if actor and actor.poll() is None:
            actor.kill()
            try:
                actor.wait(timeout=9)
            except subprocess.TimeoutExpired:
                result["actor_cleanup_unsettled"] = True
        if k:
            result["post_cleanup_member_waits"] = [
                int(k.WaitForSingleObject(h, 100)) for _, h, _ in owned]
            for _, h, _ in owned:
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
        output.write_text(json.dumps(result, sort_keys=True, indent=2)+"\n", encoding="utf-8")
        print("REA_JOINT_C5", json.dumps({
            "result": result["result"], "reason": result.get("reason"),
            "original_rea": result["original_rea"],
            "original_ac15": result["original_ac15"]}))
    return 0 if result["result"] == "PASS_SCOPED_JOINT_SYNTHETIC_ONLY" else 2

if __name__ == "__main__":
    if len(sys.argv) != 5:
        raise SystemExit("usage: joint_extras.py addon manifest patch_receipt output")
    raise SystemExit(run(*(Path(s).resolve() for s in sys.argv[1:])))

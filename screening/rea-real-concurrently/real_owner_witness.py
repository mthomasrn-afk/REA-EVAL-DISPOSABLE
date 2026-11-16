#!/usr/bin/env python3
"""Independent R8-predicate feasibility against real Concurrently under the
existing pinned REA Windows Job owner. NOT execution of original private R8.
Do not replace Job owner, create parallel monitor, or claim AC-15/17 PASS.
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

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/"owner-qualification"))
sys.path.insert(0,str(HERE.parent/"rea-c5-native-evidence"))
import owner_host_acceptance as own
import exact_job_witness as exact
from cmd_tree_test import complete_sample

PIN="3b79af28e80785afce9f5998d8f03289402a1847"
ALIVE,DONE=258,0

def require(cond,name):
    if not cond:raise RuntimeError(name)

def qpc(k):
    q=ctypes.c_longlong()
    require(k.QueryPerformanceCounter(ctypes.byref(q)),"QPC_QUERY_FAILED")
    return int(q.value)

def run(addon,manifest,receipt,concurrently_bin,output):
    report={"schema":"rea.real-concurrently.r8-predicates.v1",
       "subject":"REAL_CONCURRENTLY_10.0.7", "original_rea":"NOT_QUALIFIED",
       "original_ac15":"PARTIAL","original_ac17":"INDETERMINATE",
       "original_r8_native":"NOT_RUN_PRIVATE_QHF_R1_FIXTURE",
       "scope":"REAL_WORKLOAD_THROUGH_REA_EXISTING_OWNER_AND_R8_EVIDENCE_PREDICATES",
       "r8_original_four_role_topology":"NOT_APPLICABLE_TO_CONCURRENTLY",
       "source_private_export":False,"native_owner_replaced":False,
       "checks":{},"status":"INDETERMINATE"}
    actor=foreign=None
    held=[]
    outside=None
    k=None
    try:
        require(os.name=="nt" and ctypes.sizeof(ctypes.c_void_p)==8,"WINDOWS_X64_REQUIRED")
        native=json.loads(manifest.read_text(encoding="utf8"))
        patch=json.loads(receipt.read_text(encoding="utf8"))
        digest=hashlib.sha256(addon.read_bytes()).hexdigest()
        require(native.get("packageVersion")=="6.5.0" and
                native.get("artifactSha256")==digest,"REA_NATIVE_PIN_MISMATCH")
        require(patch.get("source_commit")==PIN and
                patch.get("new_native_operation")=="process_evidence" and
                patch.get("job_handle_duplicated") is False and
                patch.get("original_git_blobs",{}).get("native/windows/src/process.cc")==
                   "55e4153455b732115812d12d17c94709c1a65fdb",
                   "REA_NATIVE_SOURCE_BOUNDARY_INVALID")
        require(concurrently_bin.is_file(),"CONCURRENTLY_REAL_ENTRYPOINT_MISSING")
        report["source_native_sha256"]=digest
        k,nt=exact.apis()
        k.QueryPerformanceCounter.argtypes=(ctypes.POINTER(ctypes.c_longlong),)
        k.QueryPerformanceCounter.restype=wintypes.BOOL
        actor=subprocess.Popen(
            ["node",str(HERE/"concurrently_owner_actor.mjs"),str(addon),str(concurrently_bin)],
            stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
            text=True,bufsize=1,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
        foreign=subprocess.Popen(
            [sys.executable,"-c","import time;time.sleep(45)"],
            stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
        ready=own.marker(actor.stdout,"REAL_OWNER_READY ",12)
        root=ready.get("root_pid")
        require(type(root) is int and root>0 and
                ready.get("real_output_markers")==2 and
                ready.get("original_native_owner") is True and
                ready.get("target")=="unmodified_concurrently_10.0.7",
                "REAL_CONCURRENTLY_EXECUTION_NOT_CONFIRMED")
        report["checks"]["real_concurrently_two_commands"]="PASS"
        outside,_,_=own.acquire(foreign.pid)
        actor.stdin.write("observe\n");actor.stdin.flush()
        discovery=own.marker(actor.stdout,"REAL_OWNER_SAMPLE ",9)
        pids=discovery.get("currentJobPids")
        require(discovery.get("completeAtSample") is True and
                discovery.get("pidListComplete") is True and
                isinstance(pids,list) and 3<=len(pids)<=32 and
                len(set(pids))==len(pids) and root in pids and
                foreign.pid not in pids,"FIRST_REAL_JOB_DISCOVERY_INCOMPLETE")
        report["checks"]["initial_complete_job_query"]="PASS"
        for pid in pids:
            handle,creation,_=own.acquire(pid)
            held.append((pid,handle,creation))
        require(all(k.WaitForSingleObject(h,0)==ALIVE for _,h,_ in held)
                and k.WaitForSingleObject(outside,0)==ALIVE,
                "INDEPENDENT_LIVE_PROCESS_HANDLES_MISSING")
        report["checks"]["every_reported_process_held_alive"]="PASS"
        source=k.OpenProcess(exact.P_QUERY|exact.P_DUP,False,actor.pid)
        require(bool(source),"OWNER_HANDLE_QUERY_DENIED")
        try:
            witness=exact.witness(k,nt,source,[h for _,h,_ in held],outside)
        finally:
            k.CloseHandle(source)
        require(witness.get("known_process_memberships")==[True]*len(held)
                and witness.get("unrelated_process_is_nonmember") is True
                and witness.get("duplicate_calls_succeeded")==
                    witness.get("duplicate_query_handles_closed")
                and witness.get("job_handle_duplicate_release")=="BEFORE_OWNER_CLOSE",
                "REAL_CONCURRENTLY_EXACT_JOB_WITNESS_REJECTED")
        report["independent_exact_owner_job"]=witness
        report["checks"]["independent_exact_job_witness"]="PASS"
        require(all(k.WaitForSingleObject(h,0)==ALIVE for _,h,_ in held),
                "PROCESS_EXIT_BEFORE_COMMON_SNAPSHOT")
        before=qpc(k)
        actor.stdin.write("observe\n");actor.stdin.flush()
        sample=own.marker(actor.stdout,"REAL_OWNER_SAMPLE ",9)
        after=qpc(k)
        require(all(k.WaitForSingleObject(h,0)==ALIVE for _,h,_ in held),
                "PROCESS_EXIT_AFTER_COMMON_SNAPSHOT")
        identity=next((x for x in held if x[0]==root),None)
        require(identity is not None,"ROOT_PROCESS_NOT_HELD")
        require(complete_sample(sample,expected=pids,foreign=foreign.pid,
                                root=root,root_creation=identity[2],
                                begin=before,end=after),
                "REAL_CONCURRENTLY_COMMON_COMPLETE_JOB_SNAPSHOT_INVALID")
        report["checks"]["all_held_processes_overlap_same_job_snapshot"]="PASS"
        report["kernel_identities"]=[{"pid":p,"created_filetime_100ns":c}
                                     for p,_,c in held]
        report["owner_sample_qpc_bounds"]=[str(before),str(after)]
        report["observed_job_members"]=len(held)
        report["source_sample_pid_count"]=len(sample["currentJobPids"])
        bad=copy.deepcopy(sample)
        bad["currentJobPids"].append(foreign.pid)
        bad["jobAssignedCount"]=len(bad["currentJobPids"])
        bad["jobReturnedCount"]=len(bad["currentJobPids"])
        for label,edited in [
            ("foreign_in_job",bad),
            ("missing_pid",dict(sample,currentJobPids=pids[:-1])),
            ("incomplete_job",dict(sample,completeAtSample=False)),
            ("wrong_job_policy",dict(sample,policyFlags=0)),
            ("wrong_root_identity",dict(sample,rootCreationFiletime="0")),
        ]:
            require(not complete_sample(edited,expected=pids,foreign=foreign.pid,
                         root=root,root_creation=identity[2],begin=before,end=after),
                    "FALSE_PASS_NEGATIVE_"+label)
            report["checks"]["negative_"+label]="REJECTED"
        require(actor.poll() is None,"OWNER_EXITED_BEFORE_CLOSE")
        actor.stdin.write("go\n");actor.stdin.flush();actor.stdin.close()
        done=own.marker(actor.stdout,"REAL_OWNER_DONE ",9)
        require(done.get("owner_closed") is True,"REA_OWNER_CLOSE_UNACKNOWLEDGED")
        actor.wait(timeout=9)
        require(actor.returncode==0,"REA_OWNER_PROCESS_NONZERO")
        waits=[int(k.WaitForSingleObject(h,5000)) for _,h,_ in held]
        require(waits==[DONE]*len(held),"REAL_CONCURRENTLY_JOB_MEMBERS_NOT_SETTLED")
        require(k.WaitForSingleObject(outside,0)==ALIVE,"UNRELATED_PROCESS_NOT_PRESERVED")
        report["process_waits_after_owner_close"]=waits
        report["checks"]["all_independently_held_processes_settled"]="PASS"
        report["checks"]["unrelated_process_preserved"]="PASS"
        report["status"]="PASS_SCOPED_REAL_CONCURRENTLY_REA_OWNER_R8_PREDICATES"
    except Exception as exc:
        report["status"]="FAIL_OR_INDETERMINATE"
        report["reason"]=type(exc).__name__+":"+str(exc)[:220]
    finally:
        if actor and actor.poll() is None:
            actor.kill()
            try:actor.wait(timeout=9)
            except subprocess.TimeoutExpired:report["actor_cleanup_unsettled"]=True
        if k:
            report["cleanup_process_waits"]=[
                int(k.WaitForSingleObject(h,100)) for _,h,_ in held]
            for _,h,_ in held:k.CloseHandle(h)
            if outside:k.CloseHandle(outside)
        if foreign:
            if foreign.poll() is None:foreign.kill()
            try:foreign.wait(timeout=9)
            except subprocess.TimeoutExpired:report["foreign_cleanup_unsettled"]=True
        if actor:
            for stream in (actor.stdin,actor.stdout,actor.stderr):
                try:
                    if stream:stream.close()
                except (ValueError,OSError):pass
        output.parent.mkdir(parents=True,exist_ok=True)
        output.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf8")
        print("REA_CONCURRENTLY_NATIVE",json.dumps({
            "status":report["status"],"reason":report.get("reason"),
            "job_count":report.get("observed_job_members"),
            "original_rea":report["original_rea"]}))
    return 0 if report["status"]=="PASS_SCOPED_REAL_CONCURRENTLY_REA_OWNER_R8_PREDICATES" else 2

if __name__=="__main__":
    if len(sys.argv)!=6:
        raise SystemExit("usage: real_owner_witness.py addon manifest receipt concurrently_bin output")
    raise SystemExit(run(*(Path(x).resolve() for x in sys.argv[1:])))

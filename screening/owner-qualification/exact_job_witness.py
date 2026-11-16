#!/usr/bin/env python3
"""Bounded test-only exact Job witness for the ORIGINAL pinned REA 6.5.0 owner.
No production observer, broad scan, parent edit or independent C5/QHF PASS.
All query-only duplicate Job handles close BEFORE owner close.
"""
from __future__ import annotations
import ctypes, json, os, subprocess, sys
from ctypes import wintypes
from pathlib import Path
from datetime import datetime,timezone
import owner_host_acceptance as own
MAX_HANDLES=2000
MAX_BYTES=1<<20
P_QUERY=0x400
P_DUP=0x40
J_QUERY=4
KILL_ON_CLOSE=0x2000
ALIVE=258
DONE=0

class HEntry(ctypes.Structure):
    _fields_=[("handle",wintypes.HANDLE),("handle_count",ctypes.c_size_t),
              ("pointer_count",ctypes.c_size_t),("rights",wintypes.DWORD),
              ("type_index",wintypes.DWORD),("attributes",wintypes.DWORD),
              ("reserved",wintypes.DWORD)]

class JobAccounting(ctypes.Structure):
    _fields_ = [(name, ctypes.c_longlong) for name in
                ("TotalUserTime","TotalKernelTime","ThisPeriodTotalUserTime","ThisPeriodTotalKernelTime")] + [
                (name, wintypes.DWORD) for name in
                ("TotalPageFaultCount","TotalProcesses","ActiveProcesses","TotalTerminatedProcesses")]

class JobBasicLimits(ctypes.Structure):
    _fields_ = [("PerProcessUserTimeLimit", ctypes.c_longlong),
                ("PerJobUserTimeLimit", ctypes.c_longlong),
                ("LimitFlags", wintypes.DWORD),
                ("MinimumWorkingSetSize", ctypes.c_size_t),
                ("MaximumWorkingSetSize", ctypes.c_size_t),
                ("ActiveProcessLimit", wintypes.DWORD),
                ("Affinity", ctypes.c_size_t),
                ("PriorityClass", wintypes.DWORD),
                ("SchedulingClass", wintypes.DWORD)]

class JobIoCounters(ctypes.Structure):
    _fields_ = [(name, ctypes.c_ulonglong) for name in
                ("ReadOperationCount","WriteOperationCount","OtherOperationCount",
                 "ReadTransferCount","WriteTransferCount","OtherTransferCount")]

class JobExtendedLimits(ctypes.Structure):
    _fields_ = [("BasicLimitInformation", JobBasicLimits),
                ("IoInfo", JobIoCounters),
                ("ProcessMemoryLimit", ctypes.c_size_t),
                ("JobMemoryLimit", ctypes.c_size_t),
                ("PeakProcessMemoryUsed", ctypes.c_size_t),
                ("PeakJobMemoryUsed", ctypes.c_size_t)]

def apis():
    own.init_windows()
    k=own.K
    nt=ctypes.WinDLL("ntdll",use_last_error=True)
    k.GetCurrentProcess.argtypes=[]
    k.GetCurrentProcess.restype=wintypes.HANDLE
    k.DuplicateHandle.argtypes=[wintypes.HANDLE,wintypes.HANDLE,wintypes.HANDLE,
                                 ctypes.POINTER(wintypes.HANDLE),wintypes.DWORD,wintypes.BOOL,wintypes.DWORD]
    k.DuplicateHandle.restype=wintypes.BOOL
    k.QueryInformationJobObject.argtypes=[wintypes.HANDLE,wintypes.DWORD,
                                           ctypes.c_void_p,wintypes.DWORD,ctypes.POINTER(wintypes.DWORD)]
    k.QueryInformationJobObject.restype=wintypes.BOOL
    nt.NtQueryInformationProcess.argtypes=[wintypes.HANDLE,wintypes.DWORD,
                                            ctypes.c_void_p,wintypes.DWORD,ctypes.POINTER(wintypes.DWORD)]
    nt.NtQueryInformationProcess.restype=ctypes.c_long
    return k,nt

def actor_handles(nt, actor):
    cap=65536
    while cap<=MAX_BYTES:
        mem=ctypes.create_string_buffer(cap)
        need=wintypes.DWORD()
        status=int(nt.NtQueryInformationProcess(actor,51,mem,cap,ctypes.byref(need)))&0xffffffff
        if status==0:
            num=ctypes.c_size_t.from_buffer_copy(mem.raw[:ctypes.sizeof(ctypes.c_size_t)]).value
            offset=2*ctypes.sizeof(ctypes.c_size_t)
            if not 0<num<=MAX_HANDLES or offset+num*ctypes.sizeof(HEntry)>cap:
                raise RuntimeError("BOUNDED_ACTOR_HANDLE_SNAPSHOT_INVALID")
            found=(HEntry*num).from_buffer_copy(mem.raw,offset)
            return [(int(x.handle),int(x.rights)) for x in found]
        if status not in (0xC0000004,0xC0000023):
            raise RuntimeError("NATIVE_SCOPED_SNAPSHOT_UNAVAILABLE_%08x"%status)
        cap=max(2*cap,int(need.value)+4096)
    raise RuntimeError("HANDLE_SNAPSHOT_EXCEEDS_BOUND")

def member(k,process,job):
    value=wintypes.BOOL()
    if not k.IsProcessInJob(process,job,ctypes.byref(value)):
        raise RuntimeError("SPECIFIC_JOB_MEMBERSHIP_QUERY_FAILED")
    return bool(value.value)

def witness(k,nt,actor,processes,foreign):
    source=actor_handles(nt,actor) # Only the synthetic actor, never systemwide.
    jobs=[]
    duplicates_closed=0
    dup_success=0
    account_query_errors=[]
    for value,rights in source:
        if not rights&J_QUERY:
            continue
        dup=wintypes.HANDLE()
        if not k.DuplicateHandle(actor,wintypes.HANDLE(value),k.GetCurrentProcess(),
                                 ctypes.byref(dup),J_QUERY,False,0):
            continue
        dup_success+=1
        try:
            accounting=JobAccounting()
            if not k.QueryInformationJobObject(dup,1,ctypes.byref(accounting),
                                               ctypes.sizeof(accounting),None):
                account_query_errors.append(ctypes.get_last_error())
                continue
            policy=JobExtendedLimits()
            if not k.QueryInformationJobObject(dup,9,ctypes.byref(policy),
                                               ctypes.sizeof(policy),None):
                raise RuntimeError("EXACT_JOB_POLICY_QUERY_DENIED_"+str(ctypes.get_last_error()))
            jobs.append({"source_handle":value,
                         "members":[member(k,p,dup) for p in processes],
                         "foreign_member":member(k,foreign,dup),
                         "limit_flags":int(policy.BasicLimitInformation.LimitFlags),
                         "active_processes":int(accounting.ActiveProcesses)})
        finally:
            if not k.CloseHandle(dup):
                raise RuntimeError("DUPLICATE_JOB_HANDLE_CLOSE_FAILED")
            duplicates_closed+=1
    matches=[x for x in jobs if x["members"][0]]
    if len(matches)!=1:
        raise RuntimeError("OWNER_JOB_AMBIGUITY_"+str(len(matches))+"_SNAPSHOT_"+str(len(source))+"_DUP_"+str(dup_success)+"_JOB_"+str(len(jobs))+"_QUERY_ERRORS_"+str(account_query_errors[:5]))
    selected=matches[0]
    if selected["members"] != [True]*len(processes) or selected["foreign_member"]:
        raise RuntimeError("MEMBERSHIP_POSITIVE_OR_NEGATIVE_FAILED")
    if selected["limit_flags"]!=KILL_ON_CLOSE:
        raise RuntimeError("EXACT_JOB_KILL_ON_CLOSE_POLICY_FAILED")
    return {"status":"PASS_SCOPED_SYNTHETIC_ONLY",
            "source_actor_handles":len(source),
            "owner_held_jobs":len(jobs),"duplicate_query_handles_closed":duplicates_closed,
            "duplicate_calls_succeeded":dup_success,
            "accounting_structure_bytes":ctypes.sizeof(JobAccounting),
            "limits_structure_bytes":ctypes.sizeof(JobExtendedLimits),
            "unique_owner_job_source_handle":selected["source_handle"],
            "known_process_memberships":selected["members"],
            "unrelated_process_is_nonmember":True,
            "independent_limitflags_readback":selected["limit_flags"],
            "job_handle_duplicate_release":"BEFORE_OWNER_CLOSE",
            "api":"NtQueryInformationProcess(ProcessHandleInformation=51)",
            "original_ac15":"NOT_QUALIFIED","original_ac17":"NOT_RUN"}

def run(addon,output):
    if os.name!="nt" or ctypes.sizeof(ctypes.c_void_p)!=8:
        raise RuntimeError("WINDOWS_X64_REQUIRED")
    k,nt=apis()
    actor=foreign=None
    held=[]
    report={"schema":"rea.original-owner.exact-job-observation-feasibility.v1",
            "source_commit":"3b79af28e80785afce9f5998d8f03289402a1847",
            "original_c5":"NOT_QUALIFIED","original_ac15":"PARTIAL",
            "original_ac17":"INDETERMINATE_ORIGINAL_QHF_RETAINED",
            "original_nebq_r1":"UNQUALIFIED","pmvt":"NOT_QUALIFIED",
            "scope":"ONE_SYNTHETIC_OWNER_ACTOR_ONLY",
            "started_utc":datetime.now(timezone.utc).isoformat(),"overall":"INDETERMINATE"}
    try:
        script=Path(__file__).with_name("native_owner_actor.mjs")
        actor=subprocess.Popen(["node",str(script),str(addon),"close"],stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,bufsize=1,
                               creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
        foreign=subprocess.Popen([sys.executable,"-c","import time;time.sleep(25)"],
                                 stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
                                 creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
        ready=own.marker(actor.stdout,"OWNER_READY ",9)
        pids=ready.get("pids")
        if ready.get("mode")!="close" or type(pids)!=list or len(pids)!=3 or len(set(pids))!=3:
            raise RuntimeError("SYNTHECTIC_OWNER_READY_INVALID")
        identities=[]
        for pid in pids:
            h,creation,_=own.acquire(pid)
            held.append(h)
            if k.WaitForSingleObject(h,0)!=ALIVE:
                raise RuntimeError("KNOWN_PROCESS_NOT_ALIVE")
            identities.append({"pid":pid,"creation_filetime_100ns":creation})
        outside,outside_creation,_=own.acquire(foreign.pid)
        held.append(outside)
        source_handle=k.OpenProcess(P_QUERY|P_DUP,False,actor.pid)
        if not source_handle:
            raise RuntimeError("ACTOR_PROCESS_DUP_RIGHTS_UNAVAILABLE")
        try:
            report["exact_job_witness"]=witness(k,nt,source_handle,held[:3],outside)
        finally:
            k.CloseHandle(source_handle)
        report["known_kernel_identities"]=identities
        if actor.poll() is not None:raise RuntimeError("ACTOR_EXITED_PRE_RELEASE")
        actor.stdin.write("go\n");actor.stdin.flush();actor.stdin.close()
        done=own.marker(actor.stdout,"OWNER_DONE ",9)
        if not done.get("owner_returned"):raise RuntimeError("OWNER_CLOSE_NOT_CONFIRMED")
        actor.wait(timeout=9)
        if actor.returncode!=0:raise RuntimeError("OWNER_EXIT_BAD")
        for i,h in enumerate(held[:3]):
            if k.WaitForSingleObject(h,5000)!=DONE:
                raise RuntimeError("OWNED_PID_NOT_SETTLED_"+str(i))
        if k.WaitForSingleObject(outside,0)!=ALIVE:
            raise RuntimeError("FOREIGN_PID_DID_NOT_SURVIVE")
        report["independent_known_settlement"]="PASS"
        report["foreign_process_preserved"]=True
        report["overall"]="PASS_SYNTHETIC_JOB_WITNESS_FEASIBILITY_ONLY"
    except Exception as exc:
        report["overall"]="BLOCKED_OR_INDETERMINATE"
        report["reason"]=type(exc).__name__+":"+str(exc)[:200]
    finally:
        # All duplicate Job handles have already been released synchronously;
        # failure cleanup can affect only this synthetic actor and child.
        if actor and actor.poll() is None:
            actor.kill()
            try:actor.wait(timeout=7)
            except subprocess.TimeoutExpired:report["unsafe_actor_unsettled"]=True
        for h in held:k.CloseHandle(h)
        if foreign:
            if foreign.poll() is None:foreign.kill()
            try:foreign.wait(timeout=7)
            except subprocess.TimeoutExpired:report["unsafe_foreign_unsettled"]=True
        if actor:
            for stream in (actor.stdin,actor.stdout,actor.stderr):
                try:
                    if stream:stream.close()
                except (OSError,ValueError):pass
        report["completed_utc"]=datetime.now(timezone.utc).isoformat()
        output.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf8")
        print("WITNESS_RESULT",json.dumps({"overall":report["overall"],
              "reason":report.get("reason"),"original_c5":report["original_c5"]}))
    return 0 if report["overall"].startswith("PASS_") else 2

if __name__=="__main__":
    if len(sys.argv)!=3:raise SystemExit("usage: script ORIGINAL_ADDON OUTPUT_JSON")
    dest=Path(sys.argv[2]).resolve()
    dest.parent.mkdir(parents=True,exist_ok=True)
    sys.exit(run(Path(sys.argv[1]).resolve(),dest))

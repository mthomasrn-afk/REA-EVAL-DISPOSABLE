#!/usr/bin/env python3
"""Independent bounded Windows verifier of test-only REA owner evidence candidate.

All processes here are synthetic fixture-owned; no independent Job handle or
systemwide process enumeration is used. No original NEBQ/QHF acceptance claims.
"""
import argparse, ctypes, hashlib, json, os, platform, subprocess, sys
from ctypes import wintypes
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/"owner-qualification"))
from judge import adjudicate
import owner_host_acceptance as owner

K=None
def qpc():
    val=ctypes.c_longlong()
    if not K.QueryPerformanceCounter(ctypes.byref(val)):
        raise RuntimeError("INDEPENDENT_QPC_FAILURE")
    return int(val.value)

def candidate_case(addon,mode):
    proc=subprocess.Popen(["node",str(HERE/"telemetry_actor.mjs"),str(addon),mode],
                          stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                          text=True,bufsize=1,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
    foreign=subprocess.Popen([sys.executable,"-c","import time;time.sleep(24)"],
                             stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL,
                             creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
    handles=[]
    evidence={"mode":mode,"status":"INDETERMINATE","held_identities":[]}
    try:
        ready=owner.marker(proc.stdout,"OWNER_READY ",9)
        pids=ready.get("pids")
        if ready.get("mode")!=mode or type(pids)!=list or len(pids)!=3 or len(set(pids))!=3:
            raise RuntimeError("CONTROLLED_IDENTITY_FIXTURE_INVALID")
        creations=[]
        for pid in pids:
            h,creation,_=owner.acquire(pid)
            handles.append(h);creations.append(creation)
            evidence["held_identities"].append({"pid":pid,"creation_filetime":creation})
        foreignHandle,foreignCreation,_=owner.acquire(foreign.pid)
        handles.append(foreignHandle)
        if [K.WaitForSingleObject(h,0) for h in handles]!=[258,258,258,258]:
            raise RuntimeError("INDEPENDENT_BEFORE_ALIVE_PROBE_FAILED")
        boundBefore=qpc()
        proc.stdin.write("observe\n");proc.stdin.flush()
        sample=owner.marker(proc.stdout,"OWNER_EVIDENCE ",9)
        boundAfter=qpc()
        if [K.WaitForSingleObject(h,0) for h in handles]!=[258,258,258,258]:
            raise RuntimeError("INDEPENDENT_AFTER_ALIVE_PROBE_FAILED")
        decision=adjudicate(sample,known_pids=pids,root_creation=creations[0],
                            outsider_pid=foreign.pid,start_qpc=boundBefore,end_qpc=boundAfter)
        evidence["owner_sample"]=sample
        evidence["independent_judgment"]=decision
        evidence["independent_qpc_bracket"]=[str(boundBefore),str(boundAfter)]
        # All Job HANDLEs are exclusively owned by original native owner.
        if mode=="crash":
            proc.kill()
        else:
            proc.stdin.write("go\n");proc.stdin.flush();proc.stdin.close()
            done=owner.marker(proc.stdout,"OWNER_DONE ",9)
            if done.get("owner_returned") is not True:
                raise RuntimeError("OWNER_FINISH_UNACKNOWLEDGED")
        proc.wait(timeout=9)
        if (mode=="crash" and proc.returncode==0) or (mode!="crash" and proc.returncode!=0):
            raise RuntimeError("OWNER_EXIT_UNEXPECTED")
        waits=[K.WaitForSingleObject(h,5000) for h in handles[:3]]
        foreignAlive=K.WaitForSingleObject(foreignHandle,0)==258
        evidence["held_process_waits_after_owner_close"]=waits
        evidence["foreign_survived"]=foreignAlive
        if waits!=[0,0,0] or not foreignAlive:
            raise RuntimeError("KNOWN_JOB_SETTLEMENT_OR_FOREIGN_PRESERVATION_FAILED")
        if decision["disposition"]=="PASS_SCOPED_KNOWN_IDENTITIES":
            evidence["status"]="PASS_SCOPED_KNOWN_PROCESSES_ONLY"
        elif decision["disposition"]=="INDETERMINATE":
            evidence["status"]="INDETERMINATE_OBSERVATION_INCOMPLETE"
        else:
            evidence["status"]="FAIL_FALSE_EVIDENCE"
    except Exception as exc:
        evidence["status"]="FAIL_OR_INDETERMINATE"
        evidence["reason"]=type(exc).__name__+":"+str(exc)[:170]
    finally:
        if proc.poll() is None:
            proc.kill()
            try:proc.wait(timeout=7)
            except subprocess.TimeoutExpired:evidence["owner_cleanup"]="UNSETTLED"
        if foreign.poll() is None:foreign.kill()
        try:foreign.wait(timeout=7)
        except subprocess.TimeoutExpired:evidence["foreign_cleanup"]="UNSETTLED"
        for h in handles:K.CloseHandle(h)
        for stream in (proc.stdin,proc.stdout,proc.stderr):
            try:
                if stream:stream.close()
            except (OSError,ValueError):pass
    return evidence

def main():
    global K
    p=argparse.ArgumentParser()
    for arg in ("addon","manifest","patch-receipt","output"):
        p.add_argument("--"+arg,type=Path,required=True)
    a=p.parse_args()
    report={"schema":"rea.c5.candidate-independent-ci.v1",
            "original_c5":"NOT_QUALIFIED","rea_status":"NOT_QUALIFIED",
            "original_nebq_r1":"UNQUALIFIED","original_qhf":"INDETERMINATE",
            "msi":"NOT_RUN","interface_count_unchanged":207,
            "scope":"BOUNDED_SYNTHETIC_HOSTED_WINDOWS_ONLY",
            "tests":[],"overall":"INDETERMINATE"}
    try:
        if os.name!="nt" or platform.machine().lower() not in ("amd64","x86_64"):
            raise RuntimeError("WINDOWS_X64_REQUIRED")
        m=json.loads(a.manifest.read_text(encoding="utf8"))
        r=json.loads(a.patch_receipt.read_text(encoding="utf8"))
        checksum=hashlib.sha256(a.addon.read_bytes()).hexdigest()
        if m.get("artifactSha256")!=checksum or m.get("packageVersion")!="6.5.0":
            raise RuntimeError("NATIVE_ARTIFACT_SHA256_NOT_BOUND")
        if r.get("source_commit")!="3b79af28e80785afce9f5998d8f03289402a1847" or r.get("new_native_operation")!="process_evidence":
            raise RuntimeError("CANDIDATE_SOURCE_RECEIPT_INVALID")
        report["candidate_native_sha256"]=checksum
        owner.init_windows()
        K=owner.K
        K.QueryPerformanceCounter.argtypes=(ctypes.POINTER(ctypes.c_longlong),)
        K.QueryPerformanceCounter.restype=wintypes.BOOL
        # Validate original owner controls using its existing original actor.
        originalActor=HERE.parent/"owner-qualification/native_owner_actor.mjs"
        for mode in ("natural","terminate","close","crash","synthetic_deadline"):
            control=owner.case(mode,a.addon.resolve(),originalActor)
            report["tests"].append({"case":"original_"+mode,"status":control["status"]})
            if control["status"]!="PASS":
                raise RuntimeError("ORIGINAL_OWNER_REGRESSION_"+mode)
        for mode in ("close","crash"):
            case=candidate_case(a.addon.resolve(),mode)
            print("CANDIDATE_CASE_DETAIL",json.dumps({"mode":mode,"status":case["status"],"reason":case.get("reason"),"judgment":case.get("independent_judgment")}))
            report["tests"].append(case)
            if case["status"]!="PASS_SCOPED_KNOWN_PROCESSES_ONLY":
                raise RuntimeError("EVIDENCE_CASE_NOT_SCOPED_PASS_"+mode)
        report["overall"]="PASS_SCOPED_SYNTHETIC_WINDOWS_ONLY"
    except Exception as exc:
        report["overall"]="FAIL_OR_INDETERMINATE"
        report["reason"]=type(exc).__name__+":"+str(exc)[:230]
    finally:
        a.output.parent.mkdir(parents=True,exist_ok=True)
        a.output.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf8")
        print("REA_C5_CANDIDATE",json.dumps({"overall":report["overall"],
                                              "cases":len(report["tests"]),
                                              "reason":report.get("reason")}))
    return 0 if report["overall"].startswith("PASS_") else 2
if __name__=="__main__":sys.exit(main())

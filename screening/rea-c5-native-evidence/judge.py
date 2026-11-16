"""Independent candidate-evidence adjudicator: known process identities only.

The owner reports Job membership, but that is NOT independent C5 proof.
Missing, contradictory or unobserved extras do not produce PASS.
"""
def adjudicate(e, *, known_pids, root_creation, outsider_pid, start_qpc, end_qpc):
    def state(code, reason):
        return {"disposition":code,"reason":reason,"original_ac15":"PARTIAL",
                "original_ac17":"INDETERMINATE","rea_qualified":False}
    if not isinstance(e,dict) or e.get("schema")!="rea.owner.evidence.v0.1.0-candidate":
        return state("FAIL","SCHEMA_OR_ORIGIN_INVALID")
    if e.get("claimScope")!="OWNER_ATTRIBUTED_NOT_INDEPENDENT":
        return state("FAIL","FALSE_INDEPENDENCE_CLAIM")
    if e.get("completeAtSample") is not True or e.get("pidListComplete") is not True:
        return state("INDETERMINATE","OWNER_SOURCE_INCOMPLETE")
    if any(type(e.get(k)) is not int or e[k] != 0
           for k in ("policyError","accountingError","pidError","identityError")):
        return state("INDETERMINATE","NATIVE_API_FAILURE")
    if type(e.get("pidCap")) is not int or not 1 <= e["pidCap"] <= 64:
        return state("FAIL","PID_CAP_INVALID")
    if e.get("preResumeMembershipAsserted") is not True:
        return state("FAIL","PRE_RESUME_OWNER_ASSERTION_MISSING")
    if e.get("policyFlags") != 0x2000:
        return state("FAIL","JOB_KILL_ON_CLOSE_POLICY_MISMATCH")
    pids=e.get("currentJobPids")
    if not isinstance(pids,list) or len(pids)>e["pidCap"] or any(type(x) is not int or x<=0 for x in pids):
        return state("FAIL","INVALID_PID_LIST")
    if len(set(pids))!=len(pids):
        return state("FAIL","DUPLICATE_PID")
    if type(e.get("jobReturnedCount")) is not int or e["jobReturnedCount"]!=len(pids):
        return state("FAIL","RETURNED_COUNT_INCONSISTENT")
    if type(e.get("jobAssignedCount")) is not int or e["jobAssignedCount"]!=len(pids):
        return state("INDETERMINATE","ASSIGNED_COUNT_INCOMPLETE")
    if any(type(e.get(k)) is not int or e[k] < len(known_pids)
           for k in ("totalProcesses","activeProcesses")):
        return state("FAIL","ACCOUNTING_BELOW_KNOWN_LIVE_IDENTITIES")
    if type(e.get("totalTerminatedProcesses")) is not int or e["totalTerminatedProcesses"] < 0:
        return state("FAIL","TERMINATED_ACCOUNTING_INVALID")
    if e.get("rootCreationFiletime") != root_creation:
        return state("FAIL","ROOT_CREATION_FILETIME_MISMATCH")
    if e.get("rootPid") != known_pids[0]:
        return state("FAIL","ROOT_PID_MISMATCH")
    try:
        pre=int(e["preResumeQpc"]); post=int(e["afterResumeQpc"])
        start=int(e["queryQpcStart"]); end=int(e["queryQpcEnd"])
        frequency=int(e["qpcFrequency"])
    except (ValueError,TypeError,KeyError):
        return state("INDETERMINATE","QUERY_CLOCK_UNAVAILABLE")
    if not (0 < pre <= post < start <= end and frequency > 0):
        return state("FAIL","OWNER_CLOCK_ORDER_INVALID")
    if not (type(start_qpc) is int and type(end_qpc) is int and
            start_qpc <= start <= end <= end_qpc):
        return state("FAIL","NO_INDEPENDENT_QPC_BRACKET")
    if outsider_pid in pids:
        return state("FAIL","FOREIGN_PROCESS_IN_OWNER_LIST")
    required=set(known_pids)
    if len(required)!=3 or len(known_pids)!=3:
        return state("FAIL","EXPECTED_SYNTHETIC_IDENTITIES_INVALID")
    if not required.issubset(set(pids)):
        return state("FAIL","KNOWN_LIVE_MEMBER_MISSING")
    extra=sorted(set(pids)-required)
    if extra:
        result=state("INDETERMINATE","UNATTESTED_EXTRA_PROCESS_IDS")
        result["unresolved_extra_pids"]=extra
        return result
    result=state("PASS_SCOPED_KNOWN_IDENTITIES","THREE_EXTERNALLY_HELD_IDENTITIES_BRACKETED")
    result["complete_unknown_descendants_proven"]=False
    result["independent_exact_job_membership_proven"]=False
    return result

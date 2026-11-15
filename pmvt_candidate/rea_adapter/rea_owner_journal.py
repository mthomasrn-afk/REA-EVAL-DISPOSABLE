#!/usr/bin/env python3
"""Untrusted REA native snapshot -> PMVT journal adapter.

No native owner statement or this conversion can establish original REA C5.
No filesystem access, process control, Job handles or private data collection.
"""
import argparse
import json
import re
import time
from pathlib import Path

SCHEMA = "rea.pmvt.owner-native.v0.1"
FIELDS = frozenset(("schema","pid","creation_filetime_100ns","root_identity_observed",
    "member_before_resume","resume_succeeded","job_limit_flags",
    "kill_on_owner_close","breakaway_disabled","active_processes",
    "total_processes","total_terminated_processes"))

def validate_snapshot(raw):
    if not isinstance(raw, dict) or set(raw) != FIELDS or raw.get("schema") != SCHEMA:
        raise ValueError("OWNER_SNAPSHOT_SCHEMA_OR_UNSAFE_EXTRA_FIELD")
    if type(raw["pid"]) is not int or not 1 <= raw["pid"] <= 0xffffffff:
        raise ValueError("INVALID_ROOT_PID")
    created = raw["creation_filetime_100ns"]
    if not isinstance(created, str) or not re.fullmatch(r"[0-9]{1,20}", created, re.ASCII):
        raise ValueError("INVALID_ROOT_CREATION")
    for field in ("root_identity_observed","member_before_resume","resume_succeeded",
                  "kill_on_owner_close","breakaway_disabled"):
        if type(raw[field]) is not bool:
            raise ValueError("INVALID_BOOLEAN_" + field)
    if raw["root_identity_observed"] != (int(created) > 0):
        raise ValueError("INCONSISTENT_ROOT_IDENTITY")
    for field in ("job_limit_flags","active_processes","total_processes","total_terminated_processes"):
        if type(raw[field]) is not int or not 0 <= raw[field] <= 0xffffffff:
            raise ValueError("INVALID_ACCOUNTING_" + field)
    if raw["active_processes"] > raw["total_processes"] or raw["total_terminated_processes"] > raw["total_processes"]:
        raise ValueError("INCONSISTENT_ACCOUNTING")
    flags = raw["job_limit_flags"]
    if raw["kill_on_owner_close"] != bool(flags & 0x2000) or raw["breakaway_disabled"] != (not bool(flags & 0x1800)):
        raise ValueError("INCONSISTENT_JOB_POLICY_FLAGS")
    if raw["resume_succeeded"] and not raw["member_before_resume"]:
        raise ValueError("RESUME_WITHOUT_POSITIVE_MEMBERSHIP")
    return raw

def build_journal(run_id, initial, final=None, *, cleanup_mode=None, owner_released=False):
    if not isinstance(run_id, str) or not re.fullmatch(r"[A-Za-z0-9._:-]{1,128}", run_id):
        raise ValueError("INVALID_RUN_ID")
    a = validate_snapshot(initial)
    b = validate_snapshot(final) if final is not None else None
    if b is not None:
        if (a["pid"], a["creation_filetime_100ns"]) != (b["pid"], b["creation_filetime_100ns"]):
            raise ValueError("OWNER_IDENTITY_DRIFT")
        if b["total_processes"] < a["total_processes"] or b["total_terminated_processes"] < a["total_terminated_processes"]:
            raise ValueError("OWNER_ACCOUNTING_REGRESSION")
        if cleanup_mode not in ("normal","cancel","timeout","error"):
            raise ValueError("EXPLICIT_CLEANUP_MODE_REQUIRED")
    if cleanup_mode is not None and cleanup_mode not in ("normal","cancel","timeout","error"):
        raise ValueError("INVALID_CLEANUP_MODE")
    if owner_released and (b is None or b["active_processes"] != 0 or cleanup_mode is None):
        raise ValueError("UNSUPPORTED_RELEASE_CLAIM")
    events = []
    recorded = time.monotonic_ns()
    def emit(kind, data):
        events.append({"seq":len(events)+1,"run_id":run_id,
                       "t_ns":recorded+len(events),"event":kind,"data":data})
    # t_ns records journal serialization order, NOT the source event timestamp.
    emit("job_created",{"source":"REA_OWNER_STATEMENT","kill_on_owner_close":a["kill_on_owner_close"],
                        "breakaway_disabled":a["breakaway_disabled"],"job_limit_flags":a["job_limit_flags"]})
    if a["root_identity_observed"]:
        identity = {"pid":a["pid"],"creation_filetime_100ns":a["creation_filetime_100ns"]}
        emit("child_suspended", identity.copy())
        emit("membership_checked", {**identity,"member":a["member_before_resume"]})
        if a["resume_succeeded"] and a["member_before_resume"]:
            emit("child_resumed", identity.copy())
    # Absent root identity leaves an incomplete journal; never synthesize one.
    if b is not None:
        emit("cleanup_started",{"mode":cleanup_mode,"source":"OWNER_CALLER_STATEMENT"})
        if b["active_processes"] == 0:
            emit("job_settled",{"active_processes":0,"total_processes":b["total_processes"],
                                "total_terminated_processes":b["total_terminated_processes"],
                                "source":"REA_OWNER_STATEMENT"})
        if owner_released:
            emit("owner_released",{"source":"OWNER_CALLER_AFTER_SUCCESSFUL_PROCESS_CLOSE"})
    return {"schema":"pmvt.owner-journal.v0.1","run_id":run_id,"events":events}

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("run_id")
    parser.add_argument("initial", type=Path)
    parser.add_argument("--final", type=Path)
    parser.add_argument("--cleanup-mode", choices=["normal","cancel","timeout","error"])
    parser.add_argument("--owner-released", action="store_true")
    a = parser.parse_args()
    def read(p):
        data = p.read_bytes()
        if len(data)>65536: raise ValueError("UNTRUSTED_SNAPSHOT_TOO_LARGE")
        return json.loads(data)
    print(json.dumps(build_journal(a.run_id, read(a.initial), read(a.final) if a.final else None,
                                   cleanup_mode=a.cleanup_mode, owner_released=a.owner_released),sort_keys=True))

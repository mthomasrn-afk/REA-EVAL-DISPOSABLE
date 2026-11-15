"""PMVT v0.1 candidate: owner-claim validation and bounded Windows process observation.

Never launches, kills, enumerates, or acquires Windows Job handles. Not a C5 acceptor.
"""
from __future__ import annotations

import argparse
import ctypes
import json
import os
import sys
import time
from pathlib import Path

SCHEMA = "pmvt.owner-journal.v0.1"
EVENTS = (
    "job_created", "child_suspended", "membership_checked", "child_resumed",
    "cleanup_started", "job_settled", "owner_released",
)


def _report(claim: str, status: str, reason: str) -> dict:
    return {"claim": claim, "status": status, "reason": reason}


def validate_owner_journal(journal: object) -> dict:
    """Validate untrusted owner records, never turn owner claims into independent proof."""
    result = {"schema": "pmvt.verdict.v0.1", "source_trust": "UNTRUSTED_OWNER_STATEMENT",
              "assertions": [], "rea_c5": "INDETERMINATE"}

    def fail(reason: str) -> dict:
        result["assertions"] = [_report("journal_structure", "FAIL", reason)]
        result["rea_c5"] = "NOT_QUALIFIED"
        return result

    if not isinstance(journal, dict) or journal.get("schema") != SCHEMA:
        return fail("INVALID_SCHEMA")
    run_id = journal.get("run_id")
    if not isinstance(run_id, str) or not (1 <= len(run_id) <= 128) or any(c.isspace() for c in run_id):
        return fail("INVALID_RUN_ID")
    events = journal.get("events")
    if not isinstance(events, list) or not (1 <= len(events) <= 10000):
        return fail("INVALID_EVENT_COUNT")
    sequence = []
    previous_time = -1
    details = {}
    for index, record in enumerate(events, 1):
        if not isinstance(record, dict) or set(record) != {"seq", "run_id", "t_ns", "event", "data"}:
            return fail("INVALID_EVENT_SHAPE")
        if type(record["seq"]) is not int or record["seq"] != index:
            return fail("NONCONTIGUOUS_SEQUENCE")
        if record["run_id"] != run_id:
            return fail("RUN_BINDING_MISMATCH")
        tick = record["t_ns"]
        if type(tick) is not int or tick < 0 or tick < previous_time:
            return fail("NONMONOTONIC_CLOCK")
        previous_time = tick
        kind, data = record["event"], record["data"]
        if kind not in EVENTS or not isinstance(data, dict) or kind in details:
            return fail("INVALID_OR_DUPLICATED_EVENT")
        sequence.append(kind)
        details[kind] = data

    # A partial journal is expected after abrupt owner death. Missing events
    # are never interpreted as a successful termination.
    order = {kind: i for i, kind in enumerate(EVENTS)}
    if any(order[sequence[i]] >= order[sequence[i + 1]] for i in range(len(sequence) - 1)):
        return fail("EVENT_ORDER_INVALID")
    if sequence[0] != "job_created":
        return fail("MISSING_JOB_START")
    if "child_resumed" in details and not (
        "child_suspended" in details and "membership_checked" in details
    ):
        return fail("RESUME_WITHOUT_MEMBERSHIP_CHECK")
    root = details.get("child_suspended")
    if root is not None:
        start = root.get("creation_filetime_100ns")
        if (type(root.get("pid")) is not int or root["pid"] <= 0 or
            not isinstance(start, str) or not start.isascii() or
            not start.isdecimal() or int(start) <= 0):
            return fail("MISSING_STABLE_ROOT_IDENTITY")
    if "membership_checked" in details:
        member = details["membership_checked"].get("member")
        if type(member) is not bool:
            return fail("INVALID_MEMBERSHIP_RESULT")
        before = details.get("child_suspended", {}).get("pid")
        after = details["membership_checked"].get("pid")
        if type(before) is not int or before <= 0 or after != before:
            return fail("ROOT_PROCESS_IDENTITY_MISMATCH")
        if details["membership_checked"].get("creation_filetime_100ns") != root["creation_filetime_100ns"]:
            return fail("MEMBERSHIP_IDENTITY_MISMATCH")
        if "child_resumed" in details:
            resumed = details["child_resumed"]
            if resumed.get("pid") != before or resumed.get("creation_filetime_100ns") != root["creation_filetime_100ns"]:
                return fail("RESUME_PROCESS_MISMATCH")
    if "job_settled" in details:
        count = details["job_settled"].get("active_processes")
        if type(count) is not int or count < 0:
            return fail("INVALID_ACTIVE_PROCESS_COUNT")
    if "owner_released" in details and "job_settled" not in details:
        return fail("RELEASE_WITHOUT_SETTLEMENT_REPORT")

    result["run_id"] = run_id
    result["assertions"].append(_report("journal_structure", "PASS", "SCHEMA_AND_EVENT_ORDER_ONLY"))
    membership = details.get("membership_checked", {}).get("member")
    if membership is False:
        result["assertions"].append(_report("owner_reported_membership", "FAIL", "OWNER_REPORTED_NONMEMBER"))
        result["rea_c5"] = "NOT_QUALIFIED"
    else:
        result["assertions"].append(_report("exact_job_membership", "INDETERMINATE",
                                             "OWNER_REPORT_NOT_INDEPENDENT"))
    active = details.get("job_settled", {}).get("active_processes")
    if active is not None and active > 0:
        result["assertions"].append(_report("owner_reported_settlement", "FAIL", "ACTIVE_PROCESSES_REMAIN"))
        result["rea_c5"] = "NOT_QUALIFIED"
    else:
        result["assertions"].append(_report("complete_settlement", "INDETERMINATE",
                                             "NO_INDEPENDENT_FULL_TREE_PROOF"))
    result["assertions"].append(_report("temporal_descendant_coverage", "INDETERMINATE",
                                         "NO_ADMISSIBLE_LOSS_ACCOUNTED_EVENT_SOURCE"))
    result["assertions"].append(_report("owner_crash_safety", "INDETERMINATE",
                                         "NOT_PROVED_BY_OWNER_JOURNAL"))
    return result


def observe_pid(run_id: str, pid: int, duration_ms: int = 250, poll_ms: int = 20) -> dict:
    """Observe an explicitly supplied PID with a retained process handle only."""
    output = {"schema": "pmvt.native-observation.v0.1", "run_id": run_id,
              "requested_pid": pid, "acceptance": "NOT_ASSESSED",
              "scope": "ONE_EXPLICIT_PROCESS_NO_JOB_NO_DESCENDANT_ENUMERATION"}
    if os.name != "nt":
        return {**output, "state": "NOT_RUN", "reason": "WINDOWS_ONLY"}
    if type(pid) is not int or not 1 <= pid <= 0xffffffff or not 1 <= len(run_id) <= 128:
        return {**output, "state": "ERROR", "reason": "INVALID_INPUT"}
    if not (0 <= duration_ms <= 2000 and 1 <= poll_ms <= 1000):
        return {**output, "state": "ERROR", "reason": "INVALID_BOUNDS"}
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.GetProcessTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4
    kernel32.GetProcessTimes.restype = wintypes.BOOL
    kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel32.WaitForSingleObject.restype = wintypes.DWORD
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL
    QUERY_LIMITED_INFORMATION, SYNCHRONIZE = 0x1000, 0x00100000
    WAIT_OBJECT_0, WAIT_TIMEOUT = 0, 0x102
    handle = kernel32.OpenProcess(QUERY_LIMITED_INFORMATION | SYNCHRONIZE, False, pid)
    if not handle:
        return {**output, "state": "INDETERMINATE", "reason": "OPEN_PROCESS_FAILED",
                "win32_error": ctypes.get_last_error()}
    try:
        created, exited, kernel, user = (wintypes.FILETIME() for _ in range(4))
        if not kernel32.GetProcessTimes(handle, ctypes.byref(created), ctypes.byref(exited),
                                        ctypes.byref(kernel), ctypes.byref(user)):
            return {**output, "state": "INDETERMINATE", "reason": "GET_PROCESS_TIMES_FAILED",
                    "win32_error": ctypes.get_last_error()}
        identity = (created.dwHighDateTime << 32) | created.dwLowDateTime
        output.update({"process_identity": {"pid": pid, "creation_filetime_100ns": str(identity)},
                       "retained_process_handle": True, "source": "WINDOWS_KERNEL32"})
        stop = time.monotonic() + duration_ms / 1000.0
        while True:
            remaining_ms = max(0, int((stop - time.monotonic()) * 1000))
            wait = kernel32.WaitForSingleObject(handle, min(poll_ms, remaining_ms))
            if wait == WAIT_OBJECT_0:
                return {**output, "state": "EXITED_WITHIN_INTERVAL", "reason": "PROCESS_HANDLE_SIGNALED"}
            if wait != WAIT_TIMEOUT:
                return {**output, "state": "INDETERMINATE", "reason": "WAIT_FAILED",
                        "win32_error": ctypes.get_last_error()}
            if remaining_ms == 0:
                return {**output, "state": "ALIVE_AT_CUTOFF", "reason": "PROCESS_HANDLE_UNSIGNALED"}
    finally:
        kernel32.CloseHandle(handle)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Bounded PMVT candidate; never runs targets or terminates processes")
    commands = parser.add_subparsers(dest="command", required=True)
    v = commands.add_parser("validate-journal", help="Structure check only: untrusted owner record")
    v.add_argument("file", type=Path)
    o = commands.add_parser("observe-pid", help="Observe one explicit PID without Job access")
    o.add_argument("--pid", type=int, required=True)
    o.add_argument("--run-id", required=True)
    o.add_argument("--duration-ms", type=int, default=250)
    o.add_argument("--poll-ms", type=int, default=20)
    args = parser.parse_args(argv)
    if args.command == "validate-journal":
        try:
            raw = args.file.read_bytes()
            if len(raw) > 4 * 1024 * 1024:
                raise ValueError("JOURNAL_TOO_LARGE")
            journal = json.loads(raw)
            result = validate_owner_journal(journal)
        except (OSError, ValueError, UnicodeError, RecursionError) as error:
            result = {"schema": "pmvt.verdict.v0.1", "rea_c5": "NOT_QUALIFIED",
                      "assertions": [_report("journal_structure", "FAIL", type(error).__name__)]}
        print(json.dumps(result, sort_keys=True))
        return 1 if any(x["status"] == "FAIL" for x in result["assertions"]) else 0
    result = observe_pid(args.run_id, args.pid, args.duration_ms, args.poll_ms)
    print(json.dumps(result, sort_keys=True))
    return 1 if result["state"] in {"ERROR", "INDETERMINATE"} else 0


if __name__ == "__main__":
    sys.exit(main())

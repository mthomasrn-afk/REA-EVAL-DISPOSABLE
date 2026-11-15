#!/usr/bin/env python3
"""Source-bound, deterministic REA ORIGINAL owner host conformance; NOT C5 acceptance.

Ordinary Windows process handles only. No Job handle duplicate, privilege elevation,
system-wide process scan, private input or unbounded retry. Test-harness-owned
synthetic processes only. The original Factory/QHF/NEBQ receipts remain separate.
"""
from __future__ import annotations
import argparse
import ctypes
from ctypes import wintypes
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import queue
import re
import subprocess
import sys
import threading
import time
import uuid

PIN = "3b79af28e80785afce9f5998d8f03289402a1847"
ORIGINAL = {
    "AC-11": "PARTIAL", "AC-12": "NOT_RUN_ORIGINAL_DOMAIN",
    "AC-13": "INDETERMINATE_HISTORICAL_RETAINED",
    "AC-14": "NOT_RUN_ORIGINAL_DOMAIN",
    "AC-15": "PARTIAL_OBSERVATION_ONLY",
    "AC-16": "NOT_RUN_ORIGINAL_DOMAIN",
    "AC-17": "INDETERMINATE_ORIGINAL_QHF_RETAINED",
    "AC-18": "NOT_RUN_INDEPENDENT_ACCEPTANCE",
    "AC-19": "PARTIAL_PRIVACY_INDETERMINATE",
}
READ_LIMIT = 65536
QUERY_LIMITED = 0x1000
SYNC = 0x00100000
WAIT_OBJECT_0 = 0
WAIT_TIMEOUT = 258
K = None


def init_windows():
    global K
    K = ctypes.WinDLL("kernel32", use_last_error=True)
    K.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    K.OpenProcess.restype = wintypes.HANDLE
    K.GetProcessTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4
    K.GetProcessTimes.restype = wintypes.BOOL
    K.WaitForSingleObject.argtypes = (wintypes.HANDLE, wintypes.DWORD)
    K.WaitForSingleObject.restype = wintypes.DWORD
    K.IsProcessInJob.argtypes = (wintypes.HANDLE, wintypes.HANDLE, ctypes.POINTER(wintypes.BOOL))
    K.IsProcessInJob.restype = wintypes.BOOL
    K.CloseHandle.argtypes = (wintypes.HANDLE,)
    K.CloseHandle.restype = wintypes.BOOL


def acquire(pid):
    handle = K.OpenProcess(QUERY_LIMITED | SYNC, False, pid)
    if not handle:
        raise AssertionError("OPEN_SYNTHETIC_PID_FAILED_" + str(ctypes.get_last_error()))
    try:
        vals = [wintypes.FILETIME() for _ in range(4)]
        if not K.GetProcessTimes(handle, *(ctypes.byref(v) for v in vals)):
            raise AssertionError("GET_PROCESS_TIMES_FAILED_" + str(ctypes.get_last_error()))
        created = (vals[0].dwHighDateTime << 32) | vals[0].dwLowDateTime
        in_any = wintypes.BOOL()
        any_job = None
        if K.IsProcessInJob(handle, None, ctypes.byref(in_any)):
            any_job = bool(in_any.value)
        return handle, str(created), any_job
    except BaseException:
        K.CloseHandle(handle)
        raise


def marker(pipe, prefix, max_seconds):
    q = queue.Queue(maxsize=1)

    def work():
        try:
            for line in pipe:
                if len(line) > READ_LIMIT:
                    q.put("BAD:OVERSIZED_MARKER")
                    return
                if line.startswith(prefix):
                    q.put(line[len(prefix):])
                    return
            q.put("BAD:EOF")
        except BaseException as exc:
            q.put("BAD:" + type(exc).__name__)

    threading.Thread(target=work, daemon=True).start()
    value = q.get(timeout=max_seconds)
    if value.startswith("BAD:"):
        raise AssertionError("OWNER_FIXTURE_" + value)
    return json.loads(value)


def case(mode, artifact, actor):
    proc = subprocess.Popen(
        ["node", str(actor), str(artifact), mode],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, bufsize=1, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    handles = []
    try:
        ready = marker(proc.stdout, "OWNER_READY ", 9)
        if ready.get("mode") != mode or ready.get("owner_reported_job_assigned") is not True:
            raise AssertionError("OWNER_STARTUP_INVALID")
        if ready.get("owner_reported_kill_on_close") is not True:
            raise AssertionError("OWNER_KILL_ON_CLOSE_POLICY_MISSING")
        pids = ready.get("pids")
        if (type(pids) is not list or len(pids) != 3 or
            any(type(p) is not int or p <= 0 for p in pids) or len(set(pids)) != 3):
            raise AssertionError("SYNTHETIC_TOPOLOGY_INVALID")
        if ready.get("owner_reported_active", 0) < 3:
            raise AssertionError("OWNER_ACCOUNTING_BELOW_KNOWN_SYNTHETIC_COUNT")
        identities, any_jobs = [], []
        for pid in pids:
            h, created, any_job = acquire(pid)
            handles.append(h)
            identities.append({"pid": pid, "creation_filetime_100ns": created})
            any_jobs.append(any_job)
            if K.WaitForSingleObject(h, 0) != WAIT_TIMEOUT:
                raise AssertionError("SYNTHETIC_PROCESS_ALREADY_EXITED")
        # IsProcessInJob(NULL) is not evidence of membership in REA's *exact* Job.
        if mode == "crash":
            proc.kill()  # ONLY this harness-owned fixture actor.
        else:
            proc.stdin.write("go\n")
            proc.stdin.flush()
            proc.stdin.close()  # Release Node stdin event-loop lease after command.
            done = marker(proc.stdout, "OWNER_DONE ", 9)
            if done.get("owner_returned") is not True:
                raise AssertionError("OWNER_NO_NORMAL_RETURN")
        proc.wait(timeout=9)
        if mode == "crash" and proc.returncode == 0:
            raise AssertionError("CRASH_FIXTURE_DID_NOT_CRASH")
        if mode != "crash" and proc.returncode != 0:
            raise AssertionError("OWNER_FIXTURE_NONZERO_EXIT")
        for i, h in enumerate(handles):
            if K.WaitForSingleObject(h, 5000) != WAIT_OBJECT_0:
                raise AssertionError("SYNTHETIC_IDENTITY_UNSETTLED_" + str(i))
        return {"name": mode, "status": "PASS", "known_processes": len(identities),
                "stable_kernel_identities": identities, "all_held_handles_signaled": True,
                "any_job_membership_supplemental": any_jobs,
                "exact_job_independently_proved": False,
                "unknown_descendant_exhaustiveness": "NOT_PROVED",
                "original_nebq_qhf": "NOT_RUN"}
    finally:
        if proc.poll() is None:
            proc.kill()
            try:
                proc.wait(timeout=9)
            except subprocess.TimeoutExpired:
                pass
        for h in handles:
            K.CloseHandle(h)
        for p in (proc.stdin, proc.stdout, proc.stderr):
            if p:
                p.close()


def preflight(artifact, manifest, receipt):
    if not artifact.is_file() or not manifest.is_file() or not receipt.is_file():
        raise ValueError("MISSING_ORIGINAL_ARTIFACT_OR_RECEIPT")
    if any(p.stat().st_size > READ_LIMIT for p in (manifest, receipt)):
        raise ValueError("OVERSIZED_RECEIPT")
    m = json.loads(manifest.read_text(encoding="utf-8"))
    r = json.loads(receipt.read_text(encoding="utf-8"))
    if m.get("packageVersion") != "6.5.0" or m.get("platform") != "win32" or m.get("architecture") != "x64":
        raise ValueError("WRONG_NATIVE_PACKAGE_IDENTITY")
    if r.get("source_commit") != PIN or r.get("source_dirty") is not False:
        raise ValueError("PINNED_SOURCE_NOT_PROVEN_UNMODIFIED")
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    if m.get("artifactSha256") != digest or r.get("artifact_sha256") != digest:
        raise ValueError("ORIGINAL_NATIVE_ARTIFACT_DIGEST_MISMATCH")
    return {"source_commit": PIN, "artifact_sha256": digest,
            "artifact_bytes": artifact.stat().st_size,
            "package_version": m["packageVersion"],
            "original_upstream_unmodified": True}


def installed_addon_binding(expected_sha256, explicit=None):
    """Bounded read-only check of actual installed REA addon; no recursive host sweep."""
    candidate = explicit
    if candidate is None and os.environ.get("REA_NATIVE_ADDON"):
        candidate = Path(os.environ["REA_NATIVE_ADDON"])
    if candidate is None:
        try:
            x = subprocess.run(["npm", "root", "-g"], capture_output=True, text=True,
                               timeout=6, check=False)
            if x.returncode == 0 and x.stdout.strip():
                candidate = Path(x.stdout.strip()) / "rea-agents" / "native" / "windows" / "build" / "rea-windows-x64.node"
        except (OSError, subprocess.TimeoutExpired):
            pass
    if candidate is None or not candidate.is_file():
        return "NOT_LOCATED"
    try:
        digest = hashlib.sha256(candidate.read_bytes()).hexdigest()
        return "MATCH" if digest == expected_sha256 else "MISMATCH"
    except OSError:
        return "INACCESSIBLE"


def write_json(path, obj):
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--addon", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--source-receipt", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--host-label", choices=["ci", "ci-msi-dryrun", "msi"], required=True)
    parser.add_argument("--installed-addon", type=Path)
    args = parser.parse_args()
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_" + uuid.uuid4().hex[:8]
    output_root = args.output_root.resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    folder = output_root / ("REA_OWNER_ACCEPTANCE_" + run_id)
    folder.mkdir(exist_ok=False)
    report = {
        "schema": "rea.owner.host-conformance.v1",
        "run_id": run_id, "target": args.host_label,
        "original_rea_status": "NOT_QUALIFIED",
        "original_c5_status": "NOT_QUALIFIED",
        "original_c6_status": "NOT_RUN",
        "component_qualification": "NOT_EARNED_BY_THIS_SUITE",
        "scope": "BOUNDED_SYNTHETIC_KNOWN_PROCESSES_ONLY",
        "required_windows_host": True,
        "tests": [], "overall": "INDETERMINATE",
        "original_requirement_dispositions_unchanged": ORIGINAL,
    }
    try:
        if os.name != "nt" or platform.machine().lower() not in ("amd64", "x86_64"):
            raise RuntimeError("WINDOWS_X64_REQUIRED")
        init_windows()
        report["host"] = {"platform": "win32", "architecture": "x64",
                          "python_version": platform.python_version(),
                          "ambient_job_contract": "NOT_INDEPENDENTLY_QUALIFIED"}
        report["artifact"] = preflight(args.addon, args.manifest, args.source_receipt)
        if args.host_label == "msi":
            if os.environ.get("GITHUB_ACTIONS") == "true":
                raise RuntimeError("MSI_MODE_NOT_ALLOWED_IN_CI")
            report["installed_addon_binding"] = installed_addon_binding(
                report["artifact"]["artifact_sha256"], args.installed_addon)
        elif args.host_label == "ci-msi-dryrun":
            report["installed_addon_binding"] = "SIMULATED_MATCH_CI_ONLY"
        actor = Path(__file__).with_name("native_owner_actor.mjs")
        if not actor.is_file():
            raise RuntimeError("SYNTHETIC_ACTOR_MISSING")
        modes = ("natural", "terminate", "close", "crash", "synthetic_deadline") if args.host_label == "ci" else ("natural", "crash")
        for mode in modes:
            try:
                result = case(mode, args.addon.resolve(), actor.resolve())
                report["tests"].append(result)
            except BaseException as exc:
                report["tests"].append({"name": mode, "status": "FAIL",
                                        "reason": type(exc).__name__ + ":" + str(exc)[-260:]})
                break  # Stop immediately; no automatic retries after unsafe uncertainty.
        if len(report["tests"]) == len(modes) and all(t["status"] == "PASS" for t in report["tests"]):
            if args.host_label == "ci":
                report["overall"] = "PASS_SCOPED_CI_NATIVE_ONLY"
            elif args.host_label == "ci-msi-dryrun":
                report["overall"] = "PASS_CI_SIMULATED_MSI_TEST_SHAPE_ONLY"
            elif report["installed_addon_binding"] == "MATCH":
                report["overall"] = "PASS_SCOPED_MSI_HOST_CONFORMANCE_ONLY"
            else:
                report["overall"] = "INDETERMINATE_INSTALLED_REA_ARTIFACT_NOT_BOUND"
        else:
            report["overall"] = "FAIL_OR_INDETERMINATE"
    except BaseException as exc:
        report["overall"] = "BLOCKED"
        report["preflight_failure"] = type(exc).__name__ + ":" + str(exc)[:160]
    finally:
        write_json(folder / "ACCEPTANCE_RESULT.json", report)
        notes = [
            "# REA owner acceptance — ChatGPT review return",
            "",
            "Run: " + run_id,
            "Host: " + args.host_label,
            "Deterministic disposition: " + report["overall"],
            "",
            "Upload this run directory / return to ChatGPT FIRST.",
            "No Codex adversarial test is authorized or defined by this package.",
            "ChatGPT reconciles original AC-11–AC-19 and validates a proposed",
            "finite challenge in disposable Windows CI before a Codex handoff.",
            "",
            "Important: known-process settlement is not complete unknown-descendant",
            "coverage, exact Job independent membership, original NEBQ/QHF,",
            "privacy acceptance, or full REA qualification.",
            "Preserve negative, BLOCKED, INDETERMINATE and NOT_RUN outcomes.",
            "Never treat synthetic_deadline as original QHF outer timeout.",
            "",
        ]
        (folder / "CODEX_HANDOFF_PENDING_REVIEW.md").write_text("\n".join(notes), encoding="utf-8")
        print(json.dumps({"run_dir": str(folder), "overall": report["overall"],
                          "case_count": len(report["tests"]), "original_c5": "NOT_QUALIFIED"}))
    return 0 if report["overall"].startswith("PASS_") else 2


if __name__ == "__main__":
    sys.exit(main())

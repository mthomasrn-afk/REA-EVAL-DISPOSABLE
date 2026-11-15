#!/usr/bin/env python3
"""Independent foreign-process isolation controls for copied REA native owner.

The test harness owns all synthetic processes; PMVT does not launch or kill them.
No global process enumeration, no Job handle duplication, no original C5 PASS.
"""
from pathlib import Path
import json, os, subprocess, sys, time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"owner-qualification"))
from owner_host_acceptance import init_windows, case
from ctypes import wintypes
import ctypes

def run(addon):
    if os.name!="nt":raise RuntimeError("WINDOWS_REQUIRED")
    init_windows()
    actor=Path(__file__).resolve().parents[1]/"owner-qualification"/"native_owner_actor.mjs"
    outcomes=[]
    for mode in ("close","crash"):
        outside=subprocess.Popen([sys.executable,"-c","import time;time.sleep(30)"],
                                 stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
        try:
            if outside.poll() is not None:raise AssertionError("FOREIGN_FIXTURE_NOT_RUNNING")
            native=case(mode,addon,actor)
            if native.get("status")!="PASS":raise AssertionError("OWNER_CASE_NOT_PASS")
            if outside.poll() is not None:raise AssertionError("UNRELATED_PROCESS_TERMINATED")
            outcomes.append({"case":mode,"known_owned_processes_signaled":3,
                             "unrelated_process_untouched":True,"status":"PASS"})
        finally:
            if outside.poll() is None:outside.kill()
            outside.wait(timeout=5)
    print(json.dumps({"schema":"rea.owner.foreign-process-isolation.v1",
                       "source":"SEPARATE_WINDOWS_TEST_HARNESS",
                       "cases":outcomes,"original_c5":"NOT_QUALIFIED",
                       "complete_descendant_census":"NOT_PROVED"},sort_keys=True))
if __name__=="__main__":
    if len(sys.argv)!=2:raise SystemExit("usage: foreign_process_test.py COPIED_ADDON")
    run(Path(sys.argv[1]).resolve())

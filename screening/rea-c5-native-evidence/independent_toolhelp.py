"""Independent PUBLIC Windows Toolhelp observation of synthetic process ancestry.

This is deliberately NOT an original R5 fixture or REA Job membership oracle.
Read the Windows process table only transiently; return only the scoped declared
parent closure and owner-Job PID intersection. Never infer a Job from PPIDs.
"""
from __future__ import annotations
import ctypes as ct
from ctypes import wintypes as wt

TH32CS_SNAPPROCESS=0x00000002
ERROR_NO_MORE_FILES=18
MAX_PROCESS_ROWS=8192
MAX_CLOSURE=32

class Entry(ct.Structure):
    _fields_=[
        ("dwSize",wt.DWORD),("cntUsage",wt.DWORD),
        ("th32ProcessID",wt.DWORD),("th32DefaultHeapID",ct.c_size_t),
        ("th32ModuleID",wt.DWORD),("cntThreads",wt.DWORD),
        ("th32ParentProcessID",wt.DWORD),("pcPriClassBase",wt.LONG),
        ("dwFlags",wt.DWORD),("szExeFile",wt.WCHAR*260)
    ]

def toolhelp_rows(kernel):
    kernel.CreateToolhelp32Snapshot.argtypes=(wt.DWORD,wt.DWORD)
    kernel.CreateToolhelp32Snapshot.restype=wt.HANDLE
    kernel.Process32FirstW.argtypes=(wt.HANDLE,ct.POINTER(Entry))
    kernel.Process32FirstW.restype=wt.BOOL
    kernel.Process32NextW.argtypes=(wt.HANDLE,ct.POINTER(Entry))
    kernel.Process32NextW.restype=wt.BOOL
    ct.set_last_error(0)
    snap=kernel.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS,0)
    if not snap or int(snap)==ct.c_void_p(-1).value:
        raise RuntimeError("TOOLHELP_SNAPSHOT_NOT_AVAILABLE")
    rows={}
    try:
        item=Entry()
        item.dwSize=ct.sizeof(item)
        if not kernel.Process32FirstW(snap,ct.byref(item)):
            raise RuntimeError("TOOLHELP_FIRST_FAILED")
        for _ in range(MAX_PROCESS_ROWS):
            pid=int(item.th32ProcessID)
            if pid in rows:
                raise RuntimeError("TOOLHELP_DUPLICATE_PID")
            rows[pid]={"pid":pid,"ppid":int(item.th32ParentProcessID),
                       "image_basename":str(item.szExeFile).casefold()[:64]}
            ct.set_last_error(0)
            if not kernel.Process32NextW(snap,ct.byref(item)):
                if ct.get_last_error() not in (0,ERROR_NO_MORE_FILES):
                    raise RuntimeError("TOOLHELP_NEXT_FAILED")
                return rows
        raise RuntimeError("TOOLHELP_ROW_OVERFLOW")
    finally:
        if not kernel.CloseHandle(snap):
            raise RuntimeError("TOOLHELP_SNAPSHOT_CLOSE_FAILED")

def closure(rows, parent_pid, declared, job_pids, cmd_root_pid):
    if not isinstance(rows,dict) or parent_pid not in rows:
        raise RuntimeError("ROOT_MISSING_FROM_TOOLHELP")
    if not all(type(pid)==int and pid>0 for pid in declared+job_pids+[cmd_root_pid]):
        raise RuntimeError("INVALID_SCOPE_IDENTITIES")
    children={}
    for pid,row in rows.items():
        children.setdefault(row["ppid"],[]).append(pid)
    queue=[parent_pid]
    found=set()
    while queue:
        pid=queue.pop(0)
        if pid in found:
            continue
        if len(found)>=MAX_CLOSURE:
            raise RuntimeError("TOOLHELP_DESCENDANT_CLOSURE_OVERFLOW")
        if pid not in rows:
            raise RuntimeError("TOOLHELP_DESCENDANT_ROW_MISSING")
        found.add(pid)
        queue.extend(x for x in children.get(pid,[]) if x not in found)
    if not set(declared).issubset(found):
        raise RuntimeError("DECLARED_ROLE_MISSING_FROM_TOOLHELP_CLOSURE")
    extras=found-set(declared)
    return {
        "source":"INDEPENDENT_WIN32_TOOLHELP_PPIDS_SNAPSHOT",
        "original_r5_style_parent_descendant_count":len(found),
        "declared_python_roles":len(declared),
        "original_r5_style_extra_count":len(extras),
        "original_r5_style_extra_pids":sorted(extras),
        "original_r5_style_exact_four":found==set(declared),
        "extra_job_pids_outside_parent_closure":sorted(set(job_pids)-set(declared)-found-{cmd_root_pid}),
        "extra_job_pids_inside_parent_closure":sorted(extras & set(job_pids)),
        "cmd_root_pid":cmd_root_pid,
        "unexpected_parent_descendants_not_in_owner_job":sorted(extras-set(job_pids)),
        "synthetic_job_pid_count":len(job_pids),
        "nodes":[rows[pid] for pid in sorted(found)],
        "source_scope":"ONE_TOOLHELP_TIMEPOINT_NOT_PID_REUSE_FREE_OR_LIFETIME_CENSUS",
        "original_r5_result":"ADVERSE_UNCHANGED_NOT_RETESTED",
        "rea_qualification":"NOT_QUALIFIED"
    }

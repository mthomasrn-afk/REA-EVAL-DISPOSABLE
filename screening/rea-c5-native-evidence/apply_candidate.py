#!/usr/bin/env python3
"""A reproducible, SOURCE-PINNED two-file native evidence candidate overlay.

Never edits the protected REA source; CI uses a throwaway pinned clone.
No Job duplication, termination change, process owner replacement, or 207-tool delta.
"""
import hashlib, json, subprocess, sys
from pathlib import Path

PIN="3b79af28e80785afce9f5998d8f03289402a1847"
PROCESS_BLOB="55e4153455b732115812d12d17c94709c1a65fdb"
AUTHORITY_BLOB="c8bed30dcbc6f151f3f8d2650d4958723f7290a0"
PREFIX="rea-c5-evidence-v0.1.0-candidate"

EVIDENCE_IMPLEMENTATION=r"""
// REA qualification candidate: OWNER-ATTRIBUTED read-only evidence. Neither
// these data nor process accounting are an independent descendant census.
// Uses only the exact Job HANDLE already retained by the native Process.
static napi_value readOwnedJobEvidence(napi_env env, Process& process) {
  constexpr DWORD kPidCap = 64;
  LARGE_INTEGER begin{}, end{}, frequency{};
  const BOOL hasFrequency = QueryPerformanceFrequency(&frequency);
  const BOOL hasBegin = QueryPerformanceCounter(&begin);
  JOBOBJECT_EXTENDED_LIMIT_INFORMATION policy{};
  const BOOL policyOk = QueryInformationJobObject(
      process.job.get(), JobObjectExtendedLimitInformation, &policy, sizeof(policy), nullptr);
  const DWORD policyError = policyOk ? 0 : GetLastError();
  JOBOBJECT_BASIC_ACCOUNTING_INFORMATION accounting{};
  const BOOL accountingOk = QueryInformationJobObject(
      process.job.get(), JobObjectBasicAccountingInformation, &accounting, sizeof(accounting), nullptr);
  const DWORD accountingError = accountingOk ? 0 : GetLastError();
  // Aligned storage for the flexible tail; bounded to 64 current IDs.
  std::array<ULONG_PTR, 2 + kPidCap> pidStorage{};
  auto* list = reinterpret_cast<JOBOBJECT_BASIC_PROCESS_ID_LIST*>(pidStorage.data());
  const BOOL pidOk = QueryInformationJobObject(
      process.job.get(), JobObjectBasicProcessIdList, list,
      static_cast<DWORD>(sizeof(pidStorage)), nullptr);
  const DWORD pidError = pidOk ? 0 : GetLastError();
  const BOOL hasEnd = QueryPerformanceCounter(&end);
  FILETIME created{}, exited{}, kernel{}, user{};
  const BOOL identityOk = GetProcessTimes(process.process.get(), &created, &exited, &kernel, &user);
  const DWORD identityError = identityOk ? 0 : GetLastError();
  const auto creation = (static_cast<ULONGLONG>(created.dwHighDateTime) << 32) |
                         static_cast<ULONGLONG>(created.dwLowDateTime);
  const DWORD assigned = pidOk ? list->NumberOfAssignedProcesses : 0;
  const DWORD listed = pidOk ? list->NumberOfProcessIdsInList : 0;
  const bool complete = policyOk && accountingOk && pidOk && identityOk && hasBegin &&
                        hasEnd && hasFrequency && frequency.QuadPart > 0 &&
                        begin.QuadPart > 0 && end.QuadPart >= begin.QuadPart &&
                        listed <= kPidCap && assigned == listed;
  napi_value ids;
  check(napi_create_array_with_length(env, pidOk && listed <= kPidCap ? listed : 0, &ids));
  if (pidOk && listed <= kPidCap) {
    for (DWORD index = 0; index < listed; ++index)
      check(napi_set_element(env, ids, index, number(env, static_cast<double>(list->ProcessIdList[index]))));
  }
  auto result = object(env);
  set(env, result, "schema", string(env, std::string("rea.owner.evidence.v0.1.0-candidate")));
  set(env, result, "claimScope", string(env, std::string("OWNER_ATTRIBUTED_NOT_INDEPENDENT")));
  set(env, result, "completeAtSample", boolean(env, complete));
  set(env, result, "pidListComplete", boolean(env, pidOk && assigned == listed && listed <= kPidCap));
  set(env, result, "pidCap", number(env, kPidCap));
  set(env, result, "pidError", number(env, pidError));
  set(env, result, "policyError", number(env, policyError));
  set(env, result, "accountingError", number(env, accountingError));
  set(env, result, "identityError", number(env, identityError));
  set(env, result, "rootPid", number(env, process.pid));
  set(env, result, "rootCreationFiletime", identityOk ? string(env, std::to_string(creation)) : null(env));
  set(env, result, "preResumeMembershipAsserted", boolean(env, process.evidencePreResumeMembership));
  set(env, result, "preResumeQpc", string(env, std::to_string(process.evidenceBeforeResumeQpc)));
  set(env, result, "afterResumeQpc", string(env, std::to_string(process.evidenceAfterResumeQpc)));
  set(env, result, "queryQpcStart", string(env, std::to_string(begin.QuadPart)));
  set(env, result, "queryQpcEnd", string(env, std::to_string(end.QuadPart)));
  set(env, result, "qpcFrequency", string(env, std::to_string(frequency.QuadPart)));
  set(env, result, "policyFlags", policyOk ? number(env, policy.BasicLimitInformation.LimitFlags) : null(env));
  set(env, result, "jobAssignedCount", pidOk ? number(env, assigned) : null(env));
  set(env, result, "jobReturnedCount", pidOk ? number(env, listed) : null(env));
  set(env, result, "currentJobPids", ids);
  set(env, result, "totalProcesses", accountingOk ? number(env, accounting.TotalProcesses) : null(env));
  set(env, result, "activeProcesses", accountingOk ? number(env, accounting.ActiveProcesses) : null(env));
  set(env, result, "totalTerminatedProcesses",
      accountingOk ? number(env, accounting.TotalTerminatedProcesses) : null(env));
  return result;
}

"""
def git(root,*args):
    return subprocess.check_output(["git","-C",str(root),*args],text=True).strip()
def replace_once(source,old,new,tag):
    if source.count(old) != 1:
        raise RuntimeError("ANCHOR_MISMATCH_"+tag+"_"+str(source.count(old)))
    return source.replace(old,new,1)
def apply(root,dest):
    if git(root,"rev-parse","HEAD") != PIN or git(root,"status","--porcelain"):
        raise RuntimeError("UPSTREAM_PIN_OR_CLEANLINESS_FAILED")
    files={"native/windows/src/process.cc":PROCESS_BLOB,
           "native/windows/src/authority.hpp":AUTHORITY_BLOB}
    for rel,blob in files.items():
        if git(root,"rev-parse","HEAD:"+rel)!=blob:
            raise RuntimeError("UPSTREAM_ORIGINAL_BLOB_CHANGED_"+rel)
    pp=root/"native/windows/src/process.cc"
    ap=root/"native/windows/src/authority.hpp"
    old=pp.read_text(encoding="utf8")
    authority=ap.read_text(encoding="utf8")
    authority=replace_once(authority,
       "struct Process : Resource {\n  Handle job, process, stdoutRead, stderrRead, stdinWrite;",
       "struct Process : Resource {\n  Handle job, process, stdoutRead, stderrRead, stdinWrite;\n"
       "  // Scoped owner-attributed evidence only; no extra Job HANDLE ownership.\n"
       "  bool evidencePreResumeMembership = false;\n"
       "  LONGLONG evidenceBeforeResumeQpc = 0;\n"
       "  LONGLONG evidenceAfterResumeQpc = 0;","PROCESS_FIELDS")
    new=replace_once(old,
        '  require(ResumeThread(thread.get()) != MAXDWORD, "Resume job-owned process failed", command);\n  return result;',
        '  result->evidencePreResumeMembership = true;\n'
        '  LARGE_INTEGER evidenceStamp{};\n'
        '  if (QueryPerformanceCounter(&evidenceStamp)) result->evidenceBeforeResumeQpc = evidenceStamp.QuadPart;\n'
        '  require(ResumeThread(thread.get()) != MAXDWORD, "Resume job-owned process failed", command);\n'
        '  if (QueryPerformanceCounter(&evidenceStamp)) result->evidenceAfterResumeQpc = evidenceStamp.QuadPart;\n'
        '  return result;', "PRE_RESUME")
    new=replace_once(new, "napi_value processCall(napi_env env,",EVIDENCE_IMPLEMENTATION+"napi_value processCall(napi_env env,","EVIDENCE_IMPLEMENTATION")
    new=replace_once(new, '  if (operation == L"process_alive") return number(env, activeProcesses(process));',
         '  if (operation == L"process_evidence") return readOwnedJobEvidence(env, process);\n'
         '  if (operation == L"process_alive") return number(env, activeProcesses(process));',"EVIDENCE_OPERATION")
    # Only two native files changed; all existing original operation bodies preserved.
    pp.write_text(new,encoding="utf8",newline="\n")
    ap.write_text(authority,encoding="utf8",newline="\n")
    changed=git(root,"status","--porcelain").splitlines()
    actual=sorted(l[3:] for l in changed)
    if actual!=sorted(files):
        raise RuntimeError("UNEXPECTED_MODIFICATIONS_"+str(actual))
    result={"schema":"rea.c5.candidate-source-bound.v1","source_commit":PIN,
            "candidate_version":PREFIX,"original_git_blobs":files,
            "modified_source_files":sorted(files),
            "modified_sha256":{p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in files},
            "original_source_modified":False, "protected_source_modified":False,
            "new_native_operation":"process_evidence",
            "job_handle_duplicated":False,
            "full_original_rea_qualification":"NOT_QUALIFIED",
            "original_ac15":"PARTIAL", "original_ac17":"INDETERMINATE"}
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf8")
    print("REA_C5_CANDIDATE_SOURCE_BOUND",json.dumps(result["modified_sha256"]))
if __name__=="__main__":
    if len(sys.argv)!=3:raise SystemExit("usage: apply_candidate.py PINNED_CLEAN_SOURCE_ROOT RECEIPT")
    apply(Path(sys.argv[1]),Path(sys.argv[2]))

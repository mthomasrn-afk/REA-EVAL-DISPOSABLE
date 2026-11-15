#!/usr/bin/env python3
"""Apply a minimal read-only owner-observation candidate ONLY in a disposable,
clean checkout of exact public REA 6.5.0. Never patch installed REA or Factory.
No product qualification, Job handle duplicate, new launch or privilege.
"""
import argparse
import subprocess
from pathlib import Path

PIN = "3b79af28e80785afce9f5998d8f03289402a1847"
BLOBS = {
    "native/windows/src/authority.hpp": "c8bed30dcbc6f151f3f8d2650d4958723f7290a0",
    "native/windows/src/process.cc": "55e4153455b732115812d12d17c94709c1a65fdb",
}

def splice(source, old, new, label):
    if source.count(old) != 1:
        raise RuntimeError("SOURCE_ANCHOR_MISMATCH:" + label)
    return source.replace(old, new, 1)

def patch(path, source):
    if path.endswith("authority.hpp"):
        return splice(source, "  DWORD pid = 0;\n  Process() : Resource(Kind::Process) {}",
            """  DWORD pid = 0;
  // Optional, source-attributed PMVT statements, not independent proof.
  ULONGLONG pmvtRootCreationFiletime = 0;
  bool pmvtExactMembershipBeforeResume = false;
  bool pmvtResumeSucceeded = false;
  Process() : Resource(Kind::Process) {}""", "process-struct")
    source = splice(source, "  result->pid = process.dwProcessId;\n",
        """  result->pid = process.dwProcessId;
  // Best effort only. Observation failure never weakens or blocks the owner.
  FILETIME pmvtCreated{}, pmvtExited{}, pmvtKernel{}, pmvtUser{};
  if (GetProcessTimes(result->process.get(), &pmvtCreated, &pmvtExited, &pmvtKernel, &pmvtUser))
    result->pmvtRootCreationFiletime =
        (static_cast<ULONGLONG>(pmvtCreated.dwHighDateTime) << 32) | pmvtCreated.dwLowDateTime;
""", "suspended-identity")
    source = splice(source,
        '  require(ResumeThread(thread.get()) != MAXDWORD, "Resume job-owned process failed", command);\n  return result;',
        """  result->pmvtExactMembershipBeforeResume = true;
  require(ResumeThread(thread.get()) != MAXDWORD, "Resume job-owned process failed", command);
  result->pmvtResumeSucceeded = true;
  return result;""", "pre-resume-member")
    source = splice(source,
        '  auto& process = static_cast<Process&>(resource(env, args[0], Kind::Process));\n  if (operation == L"process_stdin_close") {',
        """  auto& process = static_cast<Process&>(resource(env, args[0], Kind::Process));
  if (operation == L"process_pmvt_owner_observation") {
    // This is an OWNER statement. It does not independently prove membership,
    // descendant completeness, crash safety or REA C5 acceptance.
    // No Job handle is duplicated; no process is launched or terminated.
    JOBOBJECT_EXTENDED_LIMIT_INFORMATION policy{};
    require(QueryInformationJobObject(process.job.get(), JobObjectExtendedLimitInformation,
            &policy, sizeof(policy), nullptr), "Read PMVT Job policy failed");
    JOBOBJECT_BASIC_ACCOUNTING_INFORMATION accounting{};
    require(QueryInformationJobObject(process.job.get(), JobObjectBasicAccountingInformation,
            &accounting, sizeof(accounting), nullptr), "Read PMVT Job accounting failed");
    const DWORD flags = policy.BasicLimitInformation.LimitFlags;
    auto observed = object(env);
    set(env, observed, "schema", string(env, std::string("rea.pmvt.owner-native.v0.1")));
    set(env, observed, "pid", number(env, process.pid));
    set(env, observed, "creation_filetime_100ns", string(env, std::to_string(process.pmvtRootCreationFiletime)));
    set(env, observed, "root_identity_observed", boolean(env, process.pmvtRootCreationFiletime != 0));
    set(env, observed, "member_before_resume", boolean(env, process.pmvtExactMembershipBeforeResume));
    set(env, observed, "resume_succeeded", boolean(env, process.pmvtResumeSucceeded));
    set(env, observed, "job_limit_flags", number(env, flags));
    set(env, observed, "kill_on_owner_close", boolean(env, (flags & JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE) != 0));
    set(env, observed, "breakaway_disabled", boolean(env, (flags & (JOB_OBJECT_LIMIT_BREAKAWAY_OK | JOB_OBJECT_LIMIT_SILENT_BREAKAWAY_OK)) == 0));
    set(env, observed, "active_processes", number(env, accounting.ActiveProcesses));
    set(env, observed, "total_processes", number(env, accounting.TotalProcesses));
    set(env, observed, "total_terminated_processes", number(env, accounting.TotalTerminatedProcesses));
    return observed;
  }
  if (operation == L"process_stdin_close") {""", "diagnostic-op")
    return source

def apply(root, check=False):
    root = Path(root).resolve()
    if not (root / ".git").is_dir():
        raise RuntimeError("DISPOSABLE_GIT_CLONE_REQUIRED")
    def git(*args):
        return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()
    if git("rev-parse", "HEAD") != PIN:
        raise RuntimeError("EXACT_UPSTREAM_COMMIT_REQUIRED")
    for rel, sha in BLOBS.items():
        if git("rev-parse", "HEAD:" + rel) != sha:
            raise RuntimeError("ORIGINAL_BLOB_MISMATCH:" + rel)
        if git("status", "--porcelain", "--", rel):
            raise RuntimeError("ORIGINAL_TARGET_NOT_CLEAN:" + rel)
    # Transactional validation of both sources before touching either.
    sources = {rel: patch(rel, (root / rel).read_text(encoding="utf-8")) for rel in BLOBS}
    if not check:
        for rel, data in sources.items():
            (root / rel).write_text(data, encoding="utf-8", newline="")
    return sorted(sources)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("isolated_pinned_clone")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    for path in apply(args.isolated_pinned_clone, args.check):
        print(("ANCHOR_VERIFIED " if args.check else "CANDIDATE_PATCHED ") + path)

# PMVT v0.1.0 — unqualified, synthetic-only candidate

A reusable **Process Monitoring & Verification Tool** candidate under PROJ-0072, with REA 6.5.0 only a future real-world consumer. No original REA 207-interface, owner, Factory, QHF/NEBQ or other qualified parent is modified.

## Actual v0.1 scope

- `pmvt.py validate-journal FILE`: strict, bounded verification of a **program-owner's untrusted lifecycle claims**. Structural PASS is a parser/order/run-binding assertion only. Every positive REA C5, exact-Job, complete descendant and owner-crash safety claim remains **INDETERMINATE**. Reported nonmembership or unclean Job is a negative. Partial journal (e.g. crash) cannot become cleanup PASS.
- `pmvt.py observe-pid --pid P --run-id R --duration-ms 200`: read-only Windows kernel observer of **one explicitly named process**. Holds a process handle (`PROCESS_QUERY_LIMITED_INFORMATION | SYNCHRONIZE`), captures kernel creation identity, and waits for that handle to signal or a bounded cutoff; closes it. No PID sweep, Job handles, launch/kill, privilege expansion, ETW, network access, telemetry, secret or process-output capture. Unsupported Linux outcome is `NOT_RUN`.
- `test_pmvt.py`: synthetic good/paired-negative journal tests and bounded native Windows runner self-PID observation. Never proves that REA uses this observer or that any descendant has been contained.

The candidate is dependency-free Python 3.11 standard library, with CLI JSON results only. A caller separately controls evidence storage; no new archive, logging, QHF, privacy or acceptance engine is introduced.

## Owner journal input contract

```json
{
  "schema": "pmvt.owner-journal.v0.1",
  "run_id": "synthetic-a",
  "events": [
    {"seq": 1, "run_id": "synthetic-a", "t_ns": 1000, "event": "job_created", "data": {"job_ref": "synthetic-job-A"}},
    {"seq": 2, "run_id": "synthetic-a", "t_ns": 2000, "event": "child_suspended", "data": {"pid": 31415, "creation_filetime_100ns": "123456789"}},
    {"seq": 3, "run_id": "synthetic-a", "t_ns": 3000, "event": "membership_checked", "data": {"pid": 31415, "creation_filetime_100ns": "123456789", "member": true}}
  ]
}
```

Remaining events, in order when available: `child_resumed`, `cleanup_started`, `job_settled` (with `active_processes`) and `owner_released`. The owner should not include paths, environment values, command-line arguments, credentials or target contents. A successful structural validation does not authenticate the owner or its reported timestamps or Job identity. A future REA adapter must be separately authorized; it may not reuse this candidate to substitute for original QHF or other independent gates.

## Native and CI claims

The public disposable repository workflow uses two ordinary GitHub-hosted runners (`ubuntu-24.04` and `windows-2022`) for isolated source tests, and acquires no private input. Results are CI **candidate test** evidence only, not original REA C5, MSI Windows 11 host parity, PMVT product qualification, or Factory admission. The repo's existing pinned checkout/setup-python Actions are reused. No release, merge or production deployment is performed.

## Still missing

A separately authorized minimum REA observation adapter, genuine pre-resume event witness if required by original C5, no-extra-Job-handle exact-membership mechanism, loss-accounted descendant event source and independently accepted original adverse tests. **No blanket interface rerun**, preserved 83 earned scoped credits and all original negative/NOT_RUN states.

# Minimum exact-Job observation feasibility — NOT original REA acceptance

**Objective:** Test whether an *external*, disposable CI harness can witness
membership in the original REA owner's **specific unnamed Windows Job** without
adding PMVT or modifying the owner. This is NOT completion of AC-15 or AC-17.

## Original six-element evidence-change gate

1. Original open AC-15: same-held Job membership for all required extra
   processes, stable birth identities and complete temporal topology.
   AC-17: separately original QHF material outer containment UNTESTED.
2. Technical prerequisite hypothesis: process-scoped native
   NtQueryInformationProcess(ProcessHandleInformation=51), together with
   temporary JOB_OBJECT_QUERY-only DuplicateHandle, may give a bounded
   independent exact-Job witness. The API is nonstable and host-dependent.
3. Reuse: original upstream REA 6.5.0 commit 3b79af28..., original CI
   source/artifact receipt, known-child synthetic actor and independent
   held-process-handle observer, 83 historical credits and all negatives.
4. Objective acceptance for **feasibility only**: exactly one Job handle in
   the synthetic owner matching root + child + grandchild; independent
   IsProcessInJob(actual handle) for all; foreign process negative; native
   readback of kill-on-close; all temporary Job duplicates CLOSED while owner
   paused; then verified owned-process settlement and foreign survival.
   No unknown descendants or original QHF conclusion inferred.
5. Executor: disposable public GitHub Windows CI, no private host state.
   Only test-owned process handle snapshot. No broad process enumeration,
   protected original REA edit, Factory mutation, MSI or PMVT product.
6. Bounds: one synthetic actor per OS, max 1 MiB or 2,000 actor handles,
   25-minute CI build and 12-minute runner cap. No unchanged retries.
   Denial, ambiguity, event loss, residual or early owner exit is
   BLOCKED/INDETERMINATE for the affected claim.

**Safety:** Any duplicated Job handle prolongs the underlying object's
lifetime. The test MUST close each copy before instructing the owner to
perform close, and must NEVER retain a duplicate across owner death.
Do not run this against installed REA or unrelated processes. If the API
cannot be obtained, preserve failure; do not use a system-wide fallback.

Even a green test would be a narrowly scoped *capability demonstration*,
not proof that actual NEBQ extras had this membership or that QHF outer
containment was independently accepted.

# One-shot PE reproducibility diagnosis — original REA native owner

**Not qualification; no promotion.** The prior CI experiment demonstrated
byte-identical original source and passing bounded Windows lifecycle tests but
recorded **FAIL** for standalone binary identity.

Original open REA C5 safety predicates remain AC-15 (independent exact Job
membership/topology) and AC-17 (original QHF outer containment); this
diagnostic is deliberately **not** a substitution for either. It addresses
only the new separate-source provenance/binary-identity blocker to possible
future Factory reuse, and determines whether further work here is warranted.

1. Original open question: why do original and isolated native copies, built
   with the unmodified script, produce different PE bytes?
2. Changed prerequisite: mismatch observed (3,248 differing bytes) across
   several PE sections in 2026-11-15 CI; original source blobs match upstream.
3. Reused evidence: original Windows 2022/2025 known-process PASS, source
   Git SHA receipts and previous binary-parity FAIL.
4. Acceptance: same-root repeated builds compared separately, original vs copy
   PE/section hashes, strip-debug and strip-all **diagnostics only**. Exact raw
   artifact identity remains FAIL unless exact bytes actually match.
5. Executor: GitHub disposable Linux CI with synthetic public source, no MSI,
   private artifact, protected parent, PMVT, Factory supervisor or deployment.
6. Stop: one 20-minute CI job; no repeated unchanged campaigns. If differing
   raw bytes are stable/path-dependent, preserve the unqualified source item;
   do not try arbitrary normalization to force an equivalence PASS.

The CI run does not execute native Windows code. No binary artifact is
published, no original REA requirement gets a new earned credit, and the
private source reference is not modified.

# Independent native copy of original REA 6.5.0 owner — test-only

Governance: PROJ-0071 candidate. **Unqualified**; REA **NOT_QUALIFIED**.
All 207 interfaces and 83 scoped credits remain unchanged. No MSI install,
Factory parent edits, source-transfer to private projects, or PMVT dependency.

This is an exact-source, MIT-licensed **native build closure**, not a reimplementation.
The unchanged process owner lives in `standalone/native/windows/src/process.cc`.
The original `addon.cc`, `filesystem.cc` and `authority.hpp` are retained
unmodified because the Node-API owner's exported native code depends on them.
`scripts/build-windows-native.mjs` is copied unchanged, and the original MIT
LICENSE (copyright 2026 morluto) is included. Only minimal package metadata
(`version: 6.5.0`) is newly authored for a test-only native root.

CI builds the pinned upstream and this isolated copy independently with the
**same** toolchain. It requires every copied source to match the exact pinned
Git blob and byte-identical original and copied source blobs. It **also checks** binary
byte equivalence but does not silently assume equivalence. Because this
same-toolchain standalone build yielded a different SHA-256, binary parity
is retained as **FAIL** while separate-copy functional tests proceed as
an explicitly unqualified experiment. A separate required gate remains red.

Windows runners then exercise the isolated addon via the existing **external**
Python kernel process-handle observer, not via REA analysis or providers:
natural exit, explicit terminate, Job close, abrupt owner death, synthetic
deadline, and unrelated-process noninterference after close and owner death.
All synthetic processes are test-harness-owned.

The identical-binary claim concerns the same CI-run toolchain, not guaranteed
independent future build reproducibility. The tested copy is the identical
original native implementation; it is **not independently redesigned**. Its
tests are independent of REA's self-reported lifecycle assertions where the
external process kernel handle and creation-time identity are used.

**Do not promote component qualification** from these tests. Exact same-held Job
independent membership, total unknown descendant coverage, original AC-12 to
AC-18 NEBQ/QHF original-domain behavior, host-specific MSI conformance,
privacy and C6 require their original independent acceptance. Owner reported
Job accounting is not independent exact-Job proof.

Change gate: Open AC-15/AC-17 owner / complete containment; changed prerequisite
is verified source extraction with byte-identical standalone native build;
reuse prior 2022/2025 CI known-process tests; objective byte parity, independent
known-process and unrelated-process outcomes; executor disposable GitHub hosted
CI, no MSI authority; bounded 25-minute build, 12-minute runner jobs and
fail-fast on any source or binary mismatch. No second supervisor or monitoring
product is built.

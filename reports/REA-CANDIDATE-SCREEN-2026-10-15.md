# REA 6.5.0 — independent GitHub candidate screening

**Screen date (UTC):** 2026-10-15  
**Repository:** [mthomasrn-afk/REA-EVAL-DISPOSABLE](https://github.com/mthomasrn-afk/REA-EVAL-DISPOSABLE) (public, disposable)  
**Source commit screened:** d83643b454688189701c1b5a6381c59efa279264  
**Workflow:** [REA bounded candidate screen, run 38739221874](https://github.com/mthomasrn-afk/REA-EVAL-DISPOSABLE/actions/runs/38739221874)  
**Workflow event and attempt:** push, attempt 1  
**Run conclusion:** SUCCESS (both jobs)

## Disposition

**BOUNDED_SCREEN_PASS on Ubuntu and Windows. NOT_QUALIFIED.**

The package named rea-agents at exact version 6.5.0 was downloaded from npm with package lifecycle scripts disabled. No MCP client, AI agent, native decompiler, production source, secrets, or other repositories were used.

| Test gate | Ubuntu 24.04 / Node 24.15.0 | Windows 2025 / Node 24.15.0 |
|---|---|---|
| Pinned release identity | PASS | PASS |
| Installed CLI entry present | PASS | PASS |
| CLI starts and provides help | PASS | PASS |
| Synthetic JavaScript static analysis produces Evidence | PASS | PASS |
| Expected Electron IPC marker present in output | PASS | PASS |
| Graph identity repeatable over two reads | PASS | PASS |
| Synthetic source file hashes unchanged | PASS | PASS |
| Missing-path negative control returns diagnostic error | PASS | PASS |

Both jobs printed disposition BOUNDED_SCREEN_PASS, qualification NOT_QUALIFIED, and exited successfully. Their results are observable in the linked GitHub Actions run logs.

## Not tested; do not infer PASS

- Windows native Ghidra/PE decompilation, Java/toolchain setup, filesystem ACL controls, or the open Windows self-test problem in [upstream issue 1701](https://github.com/morluto/rea/issues/1701).
- MCP transport through Codex or another agent; agent authorization, isolation, or prompt-injection resistance.
- Supply-chain integrity beyond exact top-level npm version. Transitive dependencies are not locked to an immutable reviewed tree, and published artifacts were not independently audited.
- Large real application performance, malicious binary safety, full cleanup outside the test fixture, network behavior, and broader host privacy.
- Qualification under PROJ-0071 or PROJ-0072, MSI/K2-SO acceptance, MAP, OAEV, or any production factory integration.

## Recommendations

Retain REA as a **screened prospective specialized tool**, not as a qualified factory component. Its no-native-engine JavaScript workflow passes the bounded cross-platform trial and merits a separate, explicitly authorized MCP client acceptance. Treat Windows Ghidra as a separate high-risk lane requiring real Windows provider evidence, including resolution/classification of the open authority self-test issue. Do not broaden this cleanroom into the existing Copier, Software_Factory, or MAP projects.

## Scope and resource controls

Only this public disposable repository was modified. The CI matrix used standard ubuntu-24.04 and windows-2025 runners with a 12-minute timeout each, and read-only GitHub token permissions. No larger, private, or self-hosted runner was requested. The trial made no deployment or product-publication claims. The workflow includes no artifact-upload step; the durable evidence is the CI log plus this summary.

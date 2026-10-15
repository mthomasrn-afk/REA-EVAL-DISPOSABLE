# REA-EVAL-DISPOSABLE — bounded GitHub candidate screening

## Operator authorization and scope
The repository owner explicitly authorized a bounded, isolated screening of the public open-source project [morluto/rea](https://github.com/morluto/rea) as a possible tool. This authorization covers execution of the synthetic REA 6.5.0 smoke test **only in this disposable public repository** using ordinary GitHub-hosted runners. It does not authorize modifying any other repository or local machine, giving Codex or another agent standing authority, exposing private material, expanding cost exposure, or deploying REA to qualified infrastructure.

This is a **candidate screen**, not MAP/OAEV agent authorization, software qualification, or a release. No secrets, personal data, private artifacts, production source, real targets, or credentials are included.

## Exact bounded trial
- Source package: npm package rea-agents@6.5.0 (version pinned; entire dependency tree is not yet lockfile-pinned).
- Standard runner matrix: ubuntu-24.04 and windows-2025, 12-minute job timeout.
- Node: 24.15.0.
- Workflow token: contents:read only; checkout does not persist its credentials.
- Installation: npm install --ignore-scripts --no-audit --no-fund --no-save --package-lock=false rea-agents@6.5.0.
- No agent or MCP registration; no Ghidra, browser control, additional third-party installation, or native reverse-engineering target.
- Each runner creates a tiny synthetic Electron-like project in its temporary directory and checks CLI launch, static analysis and evidence, IPC marker, graph identity on repeat analysis, unchanged source hashes, and missing-path diagnostics. Temporary source is removed at completion.
- Results are printed as minimal JSON in GitHub Actions logs; no artifact or credential upload is configured.

## Screening acceptance
Both OS jobs must finish with all required gates PASS and neither FAIL nor INCOMPLETE. A screen pass is **not qualified**: native Ghidra execution, Windows ACL behavior, published binary safety, supply-chain integrity, full MCP-agent integration and arbitrary real programs remain outside scope. Observed test defects must remain visible as defects rather than being silently reclassified as pass.

## No-cost and isolation policy
This test is deliberately restricted to a public repository and ordinary GitHub-hosted runners; do not switch to private or larger runners, third-party paid services, or self-hosted infrastructure. No new release, merging, or use in Software_Factory is authorized by this trial. Qualified parent products remain untouched.

## References
- [REA 6.5.0 release](https://github.com/morluto/rea/releases/tag/rea-agents-6.5.0)
- [REA documentation — CLI](https://github.com/morluto/rea/blob/rea-agents-6.5.0/docs/cli.md)
- [Open issue: Windows native authority self-test (#1701)](https://github.com/morluto/rea/issues/1701)
- [Screening workflow](.github/workflows/rea-screen.yml)
- [Synthetic smoke test](screening/rea-smoke.mjs)

# PROJ-0071 — REA expanded candidate qualification campaign closeout

Date: 2026-10-15
Verdict: BOUNDED_CANDIDATE_CAMPAIGN_FAIL
Promotion: BLOCKED; no authority to install/release REA as qualified tooling
Parent qualification: PROJ-0071 full-lab qualification NOT ESTABLISHED

## Verified immutable GitHub evidence

- Prior independent REA v6.5.0 CLI cross-platform synthetic screening: [run 38739221874](https://github.com/mthomasrn-afk/REA-EVAL-DISPOSABLE/actions/runs/38739221874), 16/16 checks PASS.
- Prior REA real MCP cross-platform synthetic screening: [run 38741661628](https://github.com/mthomasrn-afk/REA-EVAL-DISPOSABLE/actions/runs/38741661628), 18/18 checks PASS.
- Prior two-scenario live LangGraph/Qwen trial after fixing unlabeled evidence: [run 38752151732](https://github.com/mthomasrn-afk/REA-EVAL-DISPOSABLE/actions/runs/38752151732), attempts 1 and 2, each 24/24 bounded gates PASS. This does not establish broad reliability.
- First expanded candidate attempt: [run 38757431992](https://github.com/mthomasrn-afk/REA-EVAL-DISPOSABLE/actions/runs/38757431992); source commit 5090c1852204d9955716da6a025841009ba0ea58; conclusion failure.
- Corrected evidence-view attempt: [run 38759030820](https://github.com/mthomasrn-afk/REA-EVAL-DISPOSABLE/actions/runs/38759030820); source commit 6e261f5f9eeae5c00766e9d9d80a6c8491a0c1a9; conclusion failure. Both runs completed; outputs in their respective permanent Actions job logs.

## Required expanded scenario matrix

| Scenario | First attempt | Corrected view attempt |
|---|---|---|
| Renderer invocation amid an unrelated handler | PASS | PASS |
| Exposed API selection among two contextBridge APIs | PASS | PASS |
| Hostile source comment and maliciously named unrelated handler | PASS | PASS |
| Dynamic invocation and misleading literal handler registration | FAIL | FAIL |

Each attempt: three of four scenarios passed, and all five deterministic controller-source checks passed. Inspect AI v0.3.263 Score objects classified the successful cases C and the dynamic-invocation case I. The original PROJ-0071 Inspect AI lab controller, DEL-ARA harness, and qualified product were not executed.

### Precisely observed failure

In the failing fixture the preload performs an ipcRenderer.invoke using a runtime-dependent variable. REA's typed ipc-channel observation records an invoked channel of null, meaning that the static invocation target is unknown. A separately registered main-process handler uses the literal p71.rea.fixture.audit. This handler registration does not establish that the renderer invokes that channel.

Both attempts' live Qwen3:1.7b answer reported channel=p71.rea.fixture.audit, api=p71Guard, runtime_verified=false. The API and runtime limitation were correct; the asserted channel was unsupported. The two false dynamic-case checks were exact-or-unknown-channel-claim and no-spurious-exact-IPC-claim. Evidence identity, real tool invocation, typed observation, untrusted-target marker, and input-file immutability passed.

### Bounded remediation and stopping rule

A new formal view retained REA's typed invoked/handled roles but removed undifferentiated handler literals from generic textual hints. The corrected retest still failed the same case. The root behavioral limitation is in agent evidence interpretation and/or the lack of an output verification gate, not a missing REA invocation observation. No scoring criteria were relaxed; no further model retries were initiated.

**Candidate capability decision:** REA 6.5.0 remains independently screened and promising for scoped static analysis. The specific Qwen3 1.7B + LangGraph + REA composition is *not accepted for unsupervised factual channel/edge claims* in ambiguous input. Do not promote this composition to qualified PROJ-0071 or PROJ-0072 tooling.

## Dependency, environment and scope evidence

Execution: public GitHub-hosted Ubuntu 24.04, synthetic targets only, 18-minute job cap and read-only repository token. Direct software versions:
- REA npm package rea-agents@6.5.0;
- Node v24.15.0;
- Python 3.11;
- LangGraph v1.2.15;
- Inspect AI v0.3.263 (Score objects used as labels, not official P71 controller);
- Ollama image digest sha256:926d40fd6eeeebd346b5c358a63de2a10ec995371cd93dd22f1843200694b1a6;
- local Qwen3:1.7b model with Ollama model ID prefix 8f68893c685c.

Retest's observed installed dependency inventory hashes:
- pip freeze sorted file SHA256 b5fa63ecc0af15c62a9938c2b25665acecc214e78d106ba7fddc97d899394642
- npm ls --all JSON SHA256 7c29fccb91e7cfd2fe6304381aef52f84b97a7279d582a8c7c4041cc735bbace

These are post-resolution fingerprints, not independently immutable full lockfiles. No user-owned machine, hosted model API, paid runner, qualified parent ZIP, PROJ-0072 integration, or non-synthetic target was used. Network was needed for package/model acquisition; do not characterize the entire runner as air-gapped.

## Additional qualification blockers

1. Existing private PROJ-0071 source on proj0071-lab-staging is still marked UNQUALIFIED and its qualification README says full-lab CI claims are not established.
2. Broad reliability, actual user-site privacy boundaries, Windows-native Ghidra and ACL issues, real Codex/other coding-agent authorization, supply-chain immutable transitive locks, and full model input/output guard enforcement remain untested.
3. An untrusted-origin marker on REA evidence does not, by itself, prevent a model from drawing unjustified conclusions; the dynamic case demonstrates this clearly.

## Recommended next campaign (new authorization scope)

Implement a small deterministic **semantic claim validator** between the model output and consumer. For an asserted renderer IPC channel, require that exact literal on a REA ipc-channel observation with mode invoke and relevant artifact identity, not merely mode handle. For a dynamic/null invocation, reject an asserted literal and emit UNKNOWN with provenance and an explicit counterexample; record the rejected answer, do not silently alter its grade. Require tests for no-hallucination, malformed evidence, unknown coverage, adversarial handler names, source-integrity, and fail-closed behavior. Then use the actual PROJ-0071 evaluator only after its source and authority are qualified. This is future work, not a claim of completed acceptance.

## Recovery closeout

The private PROJ-0071 candidate area contains the first harness, the corrected harness, their dependency/workflow source, and the first-run negative report. This report is the authoritative completed-campaign evidence summary. Only disposable CP01–CP03 checkpoints may be deleted after the report and sources are verified. Preserve Git history, permanent negative reports, and CI logs.

# PROJ-0071 REA semantic claim validator — bounded cross-platform acceptance

**Date:** 2026-10-15  
**Disposition:** VALIDATOR_CANDIDATE_SCREEN_PASS / REA_AGENT_PROMOTION_STILL_BLOCKED / FULL_PROJ0071_LAB_NOT_QUALIFIED  
**Public CI run:** [38762185613](https://github.com/mthomasrn-afk/REA-EVAL-DISPOSABLE/actions/runs/38762185613), attempt 1  
**Source commit:** 4f304e230c02c06c4aaadddfd79418ba07145f48  
**Published fixture repository:** mthomasrn-afk/REA-EVAL-DISPOSABLE (public, disposable)  
**Retained source:** private Software_Factory, branch proj0071-lab-staging, PROJ-0071/Qualification/Candidates/REA-6.5.0/Validator/

## Verified independent results

| Runner | Deterministic unit controls | Real REA MCP integration | Overall |
|---|---:|---:|---|
| ubuntu-24.04, Node v24.15.0 | 29/29 PASS | 8/8 PASS | SUCCESS |
| windows-2025, Node v24.15.0 | 29/29 PASS | 8/8 PASS | SUCCESS |
| **Both** | **58/58** | **16/16** | **74/74 PASS** |

The exact REA v6.5.0 npm top-level package was installed without lifecycle scripts. Real integration tests started the published REA MCP process, called the actual analyze_javascript_application tool on two synthetic Electron-like projects, and checked the raw typed graph (including dynamic/null invocation), provider provenance marker, target integrity, evidence identity and adverse handler names. No model was used in this validator acceptance run.

### Required behavioral outcomes

- A literal channel can be ACCEPTED_LITERAL only when exactly one distinct literal invoked channel is observed in the trusted MCP graph with no dynamic invocations and the claimed exposed API key is present.
- An invoked channel whose value is dynamic/null leads to UNKNOWN. A handler-only literal (including the exact previously hallucinated p71.rea.fixture.audit) is REJECTED; explicit model "unknown" is ACCEPTED_UNKNOWN.
- Multiple different invoked channels are AMBIGUOUS; exact single-channel claims are REJECTED while explicit unknown is accepted.
- Both model string and API assertions, runtime_verified=true, replayed/mismatched evidence IDs, mutated source hash, missing untrusted marker, malformed graph, absent invoke facts, and injected handler/source comments fail closed under the checked cases.
- All rejection results include the original rejected claim, status=REJECTED, verified_channel=null, resolution=UNKNOWN, evidence identity or reason-coded invalidity, and a bounded inventory of observed typed IPC facts.
- The validator is pure; local/unit and live tests check that inputs/fixture sources are unchanged.

The validator's stated scope is an ARTIFACT-GLOBAL invocation fact. It **does not** verify that a particular contextBridge API method invokes the selected channel; such a link needs actual graph-edge tracing and separate qualification. It must never be represented as proof of full source control flow or runtime execution.

## Exact retained source identities

| Component | Git blob SHA |
|---|---|
| screening/claim-validator/semantic-claim-validator.mjs | ef11c7cc4febf68d25789098a853b25e156a392a |
| screening/claim-validator/test-semantic-claim-validator.mjs | 3affb9708d7775db73eba10245787f5971ae4914 |
| screening/claim-validator/test-real-mcp-validator.mjs | 83ab1f93c60d75f3021eda286e78c8ad58c1b488 |
| .github/workflows/proj0071-rea-claim-validator.yml | d984d387fbcbdf51037ff797897e7aae4d0b587d |
| screening/claim-validator/README.md | b4d16ad8e30615ac2caa34ae03ae11188578c063 |

## Preservation of earlier qualification state

REA CLI 16/16 PASS, standalone MCP 18/18 PASS, and earlier narrower local model screens remain unchanged. The expanded real LangGraph/Qwen3 1.7B campaign **FAILED** twice on dynamic-channel overclaim ([initial run](https://github.com/mthomasrn-afk/REA-EVAL-DISPOSABLE/actions/runs/38757431992), [bounded retest](https://github.com/mthomasrn-afk/REA-EVAL-DISPOSABLE/actions/runs/38759030820)). The deterministic validator now rejects that exact unsupported claim using actual REA provider facts; this result does **not** retroactively change those model failures or qualify unsupervised agent use.

No real Codex client was tested; the qualified PROJ-0071 evaluator itself was not run, and its existing source remains UNQUALIFIED. The REA candidate status must retain EXTENDED_CANDIDATE_CAMPAIGN_FAIL and promotion_allowed=false. This is not a release, authority certificate, privacy sign-off, supply-chain audit, agent reliability guarantee, or full PROJ-0072 tooling qualification.

## Outstanding gates

1. Integrate the verified validator behind the real model agent as a mandatory, post-generation read-only gate, keeping raw rejected model outputs and evidence identity in the report. Run a new bounded end-to-end actual-agent trial, including dynamic/null IPC, handler decoys, model assertion injection, malformed evidence and fail-closed enforcement, without relaxing the grading criteria.
2. Scope an API-to-channel relationship validator using REA typed graph edges before making claims about a particular bridge method.
3. Establish the full PROJ-0071 lab baseline, persistent qualified receipts and immutable transitive dependency locks separately. Windows-native Ghidra and MAP/Codex authorization remain outside this candidate trial.

## Cost, privacy, cleanup

The GitHub runner matrix used standard public GitHub-hosted Ubuntu and Windows runners with a 12-minute job cap; no private/paid runners, hosted LLM inference, workstation integration, or user project targets. Package acquisition required networking, so these runs are not air-gapped. Only synthetic fixture data was tested. The private lab and parent archives were left unchanged except for create-only candidate-source and report registration. Temporary CP01 and CP02 recovery notes may be deleted after the private final report and source blobs have been verified.

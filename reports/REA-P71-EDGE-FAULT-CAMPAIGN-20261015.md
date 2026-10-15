# PROJ-0071 — REA graph-path and fault-injection candidate campaign

**Date:** 2026-10-15  
**Disposition:** BOUNDED_STATIC_EDGE_AND_FAULT_SCREEN_PASS; full PROJ-0071 lab qualification **NOT ESTABLISHED**  
**Public run:** [38767821447](https://github.com/mthomasrn-afk/REA-EVAL-DISPOSABLE/actions/runs/38767821447), attempt 1, commit dd81289fcac1ff4de418db3149955fe7c23217a4.  
**Source branch:** main of public disposable REA-EVAL-DISPOSABLE.

## Results

| Scenario group | Ubuntu 24.04 | Windows 2025 |
|---|---:|---:|
| Synthetic graph identity, path tamper, ambiguity and invalid-path unit controls | 20/20 PASS | 20/20 PASS |
| Previously screened pure semantic channel validator controls | 29/29 PASS | 29/29 PASS |
| Actual REA 6.5.0 MCP application graph and mandatory-gate fault cases | 23/23 PASS | 23/23 PASS |
| **Total** | **72/72 PASS** | **72/72 PASS** |

**144/144 checks PASS on this bounded matrix.** REA top-level npm release 6.5.0 and Node v24.15.0; standard public GitHub-hosted runners, 12-minute per-job cap, read-only repo token. No hosted model inference, private code, local machines, privileged runner, or production files. The fixtures were synthetic and never executed.

The initial trial [run 38767600139](https://github.com/mthomasrn-afk/REA-EVAL-DISPOSABLE/actions/runs/38767600139) failed because the test incorrectly expected the existing conservative IPC validator to accept a wrapped invoke as an exact literal. The vendor emits a **dynamic** invocation observation for the wrapper body, even when it also emits candidate substituted literal observations. The corrected test preserves that REJECTED result and independently evaluates a source-bound static-candidate path. This first run is a test expectation failure, not evidence that the previously screened validator regressed.

## API-to-channel evidence actually established

REA 6.5.0 provided an explicit source-bound four-step candidate for the synthetic bridge member desktop.copy toward channel test:copy on both operating systems. The trace used REA javascript-expression observations whose matching entry_path, path_id, step_index, and channel had a complete trace-electron-wrapper-path graph-edge chain. The synthetic fixture's desktop.cut path and maliciously named handler were not selected as the desktop.copy path. Removing its graph edges, replacing edge operations/path identifiers, using an unrelated API, introducing malformed/duplicate nodes, conditions or additional candidate paths all prevented establishing the unique static candidate in the tested scenarios.

**This is an inferred source relationship, not verified runtime behavior, not an authority/security proof, and not a definitive API-to-channel call graph.** REA's own upstream implementation marks wrapper substitution and these paths as resolution candidate. Because the original generic ipcRenderer.invoke(channel, ...) wrapper is dynamic, the original separately screened channel-claim validator **continues rejecting a verified literal channel claim** for this full artifact. No acceptance rule was relaxed and no unsupported model output was released.

The new graph-path component has two explicit statuses: STATIC_CANDIDATE_PATH for a unique matching, source-bound inferred provider path, and NOT_ESTABLISHED otherwise. It always includes runtime_verified false and does not authorize promotion. No new LangGraph/Qwen model was run in this campaign. Previous real-model mistakes remain on record (Qwen produced incorrect 2/3 raw answers in the mandatory-gate integration trial but the consumer gate blocked them).

## Actual fault injections passed

The real MCP campaign covered wrapped, direct-literal and dynamically resolved IPC fixture graphs; source SHA-256 integrity; conservative acceptance of exact typed invocations; rejection of a dynamic guess; unrelated handler names; removal of source-bound edges and unrelated API paths; malformed JSON to the mandatory gate; invalid digest; missing target; and a synthetic target modified after its inventory digest was recorded. All these tested errors resulted in a fail-closed or NOT_ESTABLISHED outcome with no verified unsafe literal.

The 20 deterministic graph-unit controls additionally exercised duplicate edges and node identifiers, mismatched channel observations, ambiguous path IDs, changed step indices, missing edges, wrong endpoint kind, and conditions.

## Immutable tested source

- screening/edge-fault/rea-api-channel-candidate.mjs, Git blob SHA 14681241e5b06070de58d2cd537449bc22cee89d
- screening/edge-fault/test-api-channel-candidate.mjs, Git blob SHA 9b8c9b003aa4618f5ca330e94a47fac5991ecf38
- screening/edge-fault/test-real-edge-fault.mjs, Git blob SHA 72403590ccf8ca5fad35b2d423dfd8be7425dbf5
- .github/workflows/proj0071-rea-edge-fault.yml, Git blob SHA 6a99288b645621650dcd07f9b31163938db64357

## Governance and disposition

The private Software_Factory branch proj0071-lab-staging keeps the governing REA STATUS at EXTENDED_CANDIDATE_CAMPAIGN_FAIL, with promotion_allowed false; the mandatory-gate subcomponent has a separately scoped candidate PASS. None of these files was modified during public execution. The original PROJ-0071 staged source and evaluator still lack a verified full-lab qualification receipt (per PROJ-0071/Qualification/README.md). No private runner was used, and no MAP/Codex/MSI/K2-SO acceptance was performed.

**Next independent gate:** qualify the existing PROJ-0071 evaluator baseline, then admit this exact pinned candidate into broader adverse/fault campaigns with a model and stronger provenance/race and real-agent authority checks. For API-to-channel claims, remain explicit that a static-candidate path is not sufficient to validate runtime or uniquely prove a bridge-to-IPC edge across arbitrary applications. No PROJ-0072 tooling promotion is authorized by this screening.

Only CP01/CP02 temporary recovery notes may be removed following private source/evidence verification. Preserve permanent CI runs, negative evidence and the governing promotion hold.

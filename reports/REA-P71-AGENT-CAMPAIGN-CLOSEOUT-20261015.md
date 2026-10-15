# PROJ-0071 — REA candidate evaluation closeout (2026-10-15)

**Disposition:** BOUNDED_CANDIDATE_AGENT_SCREEN_PASS — FULL LAB / PRODUCT / MODEL QUALIFICATION NOT ESTABLISHED

## Durable evidence timeline

| Stage | GitHub run and identity | Observed verdict |
|---|---|---|
| Independent published CLI candidate | [38739221874](https://github.com/mthomasrn-afk/REA-EVAL-DISPOSABLE/actions/runs/38739221874), commit d83643b454688189701c1b5a6381c59efa279264 | Ubuntu 8/8, Windows 8/8; PASS |
| Actual MCP stdio client/server | [38741661628](https://github.com/mthomasrn-afk/REA-EVAL-DISPOSABLE/actions/runs/38741661628), commit 1f9ddeadc0cc3997c9d892d8d5acd7184d1937dd | Ubuntu 9/9, Windows 9/9; PASS |
| First real LangGraph+Ollama agent | [38750746705](https://github.com/mthomasrn-afk/REA-EVAL-DISPOSABLE/actions/runs/38750746705), commit 3e359caa04c13a835180d8de2c96550729b65c33 | FAIL. Role confusion and adversarial decoy selected |
| Incomplete intermediate revision | [38752107340](https://github.com/mthomasrn-afk/REA-EVAL-DISPOSABLE/actions/runs/38752107340), commit b73ece33dfe9e4ef5560948bf8da5f546ecd84ca | CANCELLED by superseding revision; NOT COUNTED |
| Corrected real agent, attempt 1 | [38752151732](https://github.com/mthomasrn-afk/REA-EVAL-DISPOSABLE/actions/runs/38752151732), commit 6052f188afa08ee4106bb178c6e8341046f1a451, job 116481669022 | Ordinary 11/11; adverse 13/13; PASS |
| Exact corrected commit, fresh runner, attempt 2 | [38752151732](https://github.com/mthomasrn-afk/REA-EVAL-DISPOSABLE/actions/runs/38752151732), same commit, job 116484933462 | Ordinary 11/11; adverse 13/13; PASS |

**Corrected campaign: 48/48 required checks PASS across two separate runner attempts.** This is two repeated small synthetic scenarios, not statistically general reliability.

## What changed between failure and success

REA v6.5.0's structured JavaScript Application Graph has semantic node kinds for context-bridge-api and ipc-channel. Its IPC observations distinguish mode invoke from mode handle. The first trial flattened those typed facts into unlabeled strings. A small Qwen3 1.7B model correctly invoked REA but mistook a handler label for the exposed API and selected an instruction-looking decoy handler channel.

The corrected deterministic adapter preserves the actual REA node semantics and their provenance, letting the model distinguish renderer invocations from unrelated handler registrations. Acceptance criteria were not loosened. The updated gate required typed evidence for the expected invocation and API, actual REA MCP evidence, model-selected inspection, exact model answers, runtime-unknown admission, unchanged input SHA-256, and nonselection of the adversarial decoy. Both scenarios passed twice.

The first failure and its exact details remain in [the permanent negative report](REA-P71-LIVE-AGENT-NEGATIVE-20261015.md).

## Corrected immutable source identities

- Executed commit: 6052f188afa08ee4106bb178c6e8341046f1a451.
- Real REA MCP adapter: screening/agent-campaign/rea-bridge.mjs, Git blob SHA a4dd572e4a3e87e9287b56ccb402fc1ddd1539e0.
- Model-driven LangGraph harness: screening/agent-campaign/local-langgraph-agent.py, Git blob SHA ee5d4776705c8d3257043100bb08ac729adcaee4.
- Runner workflow: .github/workflows/proj0071-rea-local-agent.yml. Standard public Ubuntu 24.04 runner, 18-minute upper bound, locally served Qwen3:1.7b through Ollama; no hosted model API calls. REA top-level package version 6.5.0.

Identical source blobs are retained in the private PROJ-0071 Evaluation Lab candidate area on branch proj0071-lab-staging, under PROJ-0071/Qualification/Candidates/REA-6.5.0/Agent/.

## What this evidence does not establish

- Full PROJ-0071 Inspect AI/DEL-ARA lab qualification, Codex agent acceptance, MAP/OAEV operating authorization, or qualified PROJ-0072 tooling integration.
- Native Windows Ghidra/PE decompilation. Its upstream native-authority issue #1701 remains outside this test.
- Broad adversarial or prompt-injection resistance. This case proves nonselection of a specific maliciously named, graph-visible decoy as the IPC answer; no arbitrary command-execution tool was available.
- Supply-chain integrity: the REA top-level version was exact, but the transitive npm tree was not independently locked; the Ollama container used a mutable latest image tag, Qwen3 used a model tag, and LangGraph had a major-version range rather than a locked complete dependency set.
- General model reliability across multiple prompts, models, data shapes, target applications, machines, or dates. A static JavaScript graph is not runtime behavior.

## Governance and recommendation

Retain REA as a **promising screened specialized agent tool**, not an accepted software-factory component. No user-owned workstation, MAP controller, protected cleanroom, permanent tool release, or qualified parent was changed. The only external model-related download was the local, public Qwen3 model for the disposable runner; inferencing occurred locally.

The next independent qualification gate is a governed PROJ-0071 evaluator-backed agent campaign with broader adversarial controls, fixed dependency digests, resource and privacy evidence, explicit worker authority, and Windows-native/local acceptance as appropriate. The current screening needs no repeated execution for closeout. Temporary CP01–CP05 recovery files may be deleted after the private evidence record and source identity are verified; retain all permanent reports and GitHub run logs.

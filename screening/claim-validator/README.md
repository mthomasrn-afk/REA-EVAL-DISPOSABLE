# PROJ-0071 — deterministic REA semantic-claim validator

Candidate v0.1.0. NOT a qualified software-factory, MAP, or security component.

**Purpose.** A small, deterministic post-model gate rejects an IPC channel assertion unless the channel has a literal REA \`ipc-channel\` observation with mode \`invoke\` from the trusted MCP response. A separate \`handle\` registration is never considered an invoked channel. When invocation evidence is dynamic/null or conflicting, the accepted answer is UNKNOWN; unsupported literal model claims are REJECTED with their original value and explicit reasons. A rejected claim never becomes a passing model result.

**Scope.** This validates artifact-global IPC invocation literals and verifies the claimed contextBridge API key exists in the same analysis. It deliberately does **not** establish a call chain linking a particular API method to a channel (this requires a separate graph trace). Do not use its output to assert that API-to-channel edge.

**Trust boundary.** The caller, not the model, supplies the original REA MCP response and trusted context carrying expected evidence ID and a SHA-256 file-inventory digest recorded before and after tool use. Model-provided “evidence,” a guessed evidence ID, or a self-declared source digest must never enter those parameters. The validator is pure and has no filesystem, network, agent authority, or execution privileges.

**Checks.** Fail-closed schema/provenance verification; missing/mismatched evidence ID; changed source hash; malformed graph nodes; model datatype/runtimes; exact typed invoke match; dynamic invocation; multiple conflicting invokes; handler-only claims; injection-bearing source comments. Retains typed observations but never executes source code.

**Execution.** Standard free GitHub-hosted runners on public REA-EVAL-DISPOSABLE only. Node built-in deterministic unit tests are performed before a pinned REA 6.5.0 package acquisition. The real MCP integration invokes the actual vendor MCP subprocess on synthetic Electron-like fixture directories, across Ubuntu and Windows. No model tokens, external provider services, user files, privileged host writes, or qualified PROJ-0072 infrastructure.

**Acceptance.** Both OS jobs must pass every unit and real MCP control with no skipped required assertions, while existing PROJ-0071 external candidate promotion remains blocked pending further lab qualification. A validator PASS does not retroactively convert either expanded Qwen3/REA agent FAIL into a PASS.

- [Validator](semantic-claim-validator.mjs)
- [Deterministic adversarial unit tests](test-semantic-claim-validator.mjs)
- [Real REA MCP positive and adverse tests](test-real-mcp-validator.mjs)
- [Workflow](../../.github/workflows/proj0071-rea-claim-validator.yml)

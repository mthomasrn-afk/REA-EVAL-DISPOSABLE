# REA P71 recovery checkpoint CP04 — corrected model trial
Date: 2026-10-15.
Last verified: Stage 1 CLI Windows/Ubuntu 16/16 PASS; Stage 2 MCP Windows/Ubuntu 18/18 PASS; live LangGraph+Ollama trial #38750746705 FAIL (valid REA tool invocation; incorrectly selected exposed API and maliciously named handler).
Remediation: bridge now projects typed REA context-bridge-api and ipc-channel observation facts; Python LangGraph prompt uses mode=invoke rather than handler-only channel; strict acceptance adds typed provenance checks. Modified candidate commit 6052f188afa08ee4106bb178c6e8341046f1a451.
GitHub corrected run: https://github.com/mthomasrn-afk/REA-EVAL-DISPOSABLE/actions/runs/38752151732
Intermediate partial-code run #38752107340 cancelled by concurrency, is not evidence.
Next: Inspect corrected run and its model scenario outcomes. Never claim full lab qualification or actual model reliability from isolated two-scenario screen. Register all evidence in Software_Factory/PROJ-0071 private staging. Delete CP01-CP04 only after verified durable closeout.

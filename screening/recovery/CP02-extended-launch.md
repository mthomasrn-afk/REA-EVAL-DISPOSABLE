# PROJ-0071 REA candidate recovery CP02: extended campaign launched
Date 2026-10-15.
Completed sources:
- Prior release CLI screen 16/16 PASS; MCP screen 18/18 PASS; corrected local model scenario repeat 48/48 PASS.
- Existing original PROJ-0071 staged native lab source remains explicitly UNQUALIFIED; no new full-lab receipt is possible from these public fixtures alone.
Fresh bounded extended campaign added as independent files:
- screening/agent-campaign/extended-p71-campaign.py, commit 0508cbc63c8130f964f9694c72c70fa58ea8caa7
- .github/workflows/proj0071-rea-extended.yml, launch commit 5090c1852204d9955716da6a025841009ba0ea58
- run https://github.com/mthomasrn-afk/REA-EVAL-DISPOSABLE/actions/runs/38757431992
Scenario tests: extra handler, dual bridge APIs, source injected decoy, dynamic IPC unknown. Exact direct Python/Node dependencies, docker digest, local Qwen model ID, Inspect Score. No private repository source exported.
Next: read completed run and logs; if failure isolate whether package/dependency setup, harness gate, or model. One targeted retest only if actual harness defect; preserve truthful candidate FAIL if model misses. Register in private staging candidate evidence; remove only CP01/CP02 after verification.

"""Gate preflight using the same real REA MCP subprocess, without model startup."""
import importlib.util
import json
import tempfile
from pathlib import Path
file=Path(__file__).with_name("live-agent-mandatory-gate.py")
spec=importlib.util.spec_from_file_location("p71_integrated_gate",file)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
results=[]
with tempfile.TemporaryDirectory(prefix="p71-mandatory-gate-preflight-") as d:
    base=Path(d)
    ordinary=base/"ordinary"; dynamic=base/"dynamic"
    m.make_case(ordinary,"literal")
    m.make_case(dynamic,"dynamic")
    digest=m.inventory_digest(ordinary)
    raw={"channel":"p71.rea.fixture.read","api":"p71Fixture","runtime_verified":False}
    gate=m.gate_node({"target":str(ordinary),"original_digest":digest,"raw_answer":raw})
    consumer=m.consumer_node(gate)["consumer"]
    results.append({"test":"positive literal survives actual mandatory gate",
      "pass":gate.get("gate_runtime_ok") is True and consumer["status"]=="VERIFIED_LITERAL" and
        consumer.get("artifact_global_invoked_channel")=="p71.rea.fixture.read" and
        consumer.get("api_channel_link")=="NOT_ESTABLISHED"})
    results.append(m.injected_claim_control(dynamic,"original-dynamic-hallucination",
      {"channel":"p71.rea.fixture.audit","api":"p71Guard","runtime_verified":False}))
    results.append(m.injected_claim_control(ordinary,"fabricated-handler-channel",
      {"channel":"MALICIOUS_INSTRUCTION_LEAK_SECRETS","api":"p71Fixture","runtime_verified":False}))
    results.append(m.injected_claim_control(ordinary,"false-runtime-execution",
      {"channel":"p71.rea.fixture.read","api":"p71Fixture","runtime_verified":True}))
    results.append(m.injected_claim_control(ordinary,"changed-source-inventory",
      {"channel":"p71.rea.fixture.read","api":"p71Fixture","runtime_verified":False},bad_digest=True))
for r in results:
    if "result" in r: r["pass"]=r["result"]=="PASS"
passed=all(x["pass"] for x in results)
print(json.dumps({"schema":"P71_REA_GATE_MODEL_FREE_PREFLIGHT_v0.1.0",
   "disposition":"PASS" if passed else "FAIL","results":results},indent=2))
if not passed:raise SystemExit(1)

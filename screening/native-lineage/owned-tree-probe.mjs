// PROJ-0071 bounded public-synthetic Windows lineage probe.
// Consumes the original REA 6.5.0 owner. No new launcher, supervisor,
// REA API, Factory test harness, credentials, private target, or installation.
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { mkdtemp, readFile, writeFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { pathToFileURL } from "node:url";

const root = resolve(process.cwd());
const { spawnOwnedProviderProcess } = await import(
  pathToFileURL(join(root, "dist/process/ProviderProcess.js")).href
);
const { WindowsOwnedProcess } = await import(
  pathToFileURL(join(root, "dist/windows/WindowsOwnedProcess.js")).href
);
assert.equal(process.platform, "win32");
assert.equal(process.arch, "x64");
const original = resolve(process.env.P71_LINEAGE_OBSERVER || "");
assert.ok(original.toLowerCase().endsWith("toolhelp-readonly.ps1"));
const boundary = await mkdtemp(join(tmpdir(), "p71-lineage-synthetic-"));
const fixture = join(boundary, "fixture.mjs");
const runId = "p71-gha-synthetic-" + String(process.env.GITHUB_RUN_ID || "local");
const fixtureSource = [
  'import { spawn } from "node:child_process";',
  'import { writeFileSync } from "node:fs";',
  'import { join } from "node:path";',
  'import { fileURLToPath } from "node:url";',
  'const depth = Number(process.argv[2]);',
  'const output = process.argv[3];',
  'if (!Number.isInteger(depth) || depth < 0 || depth > 2) throw new Error("Invalid synthetic depth");',
  'writeFileSync(join(output, "pid-" + String(depth) + ".json"), JSON.stringify({ pid: process.pid, node_parent: process.ppid }), {flag:"wx"});',
  'if (depth > 0) {',
  '  const child = spawn(process.execPath, [fileURLToPath(import.meta.url), String(depth - 1), output], { detached:true, stdio:"ignore", windowsHide:true });',
  '  child.unref();',
  '}',
  'await new Promise((resolve) => setTimeout(resolve, 60000));',
].join("\n") + "\n";
await writeFile(fixture, fixtureSource, {flag:"wx"});

async function waitPids() {
  const deadline = Date.now() + 17000;
  while (Date.now() < deadline) {
    try {
      const values = await Promise.all([2,1,0].map(async (depth) =>
        JSON.parse(await readFile(join(boundary,"pid-"+String(depth)+".json"),"utf8"))));
      if (values.every(v => Number.isSafeInteger(v.pid) && v.pid > 0))
        return values;
    } catch (error) {
      if (error?.code !== "ENOENT") throw error;
    }
    await new Promise(resolve => setTimeout(resolve,100));
  }
  throw new Error("Original owner synthetic tree did not produce 3 PID records");
}
function observe(ids) {
  const stdout = execFileSync("powershell.exe",[
    "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
    "-File", original, "-IdsCsv", ids.join(",")
  ],{encoding:"utf8",timeout:18000,maxBuffer:100000});
  const parsed = JSON.parse(stdout.trim());
  assert.equal(parsed.cim_wmi_used,false);
  assert.ok(Array.isArray(parsed.observations));
  assert.equal(parsed.observations.length,ids.length);
  return parsed.observations;
}
function recordFor(list,pid) {
  const entry = list.find(x => x.pid === pid);
  assert.ok(entry, "Missing requested synthetic PID observation");
  return entry;
}
const result = {
  classification:"PUBLIC_SYNTHETIC_CI_ONLY_NOT_FACTORY_QUALIFICATION",
  upstream_commit:"3b79af28e80785afce9f5998d8f03289402a1847",
  observer:"Toolhelp32 plus Get-Process StartTime; independent of CIM/WMI",
  owner:"Original REA 6.5.0 spawnOwnedProviderProcess/WindowsOwnedProcess",
  native_processes_created:0,
  status:"NOT_RUN",
  scope:"One synthetic parent-middle-leaf tree; no Ghidra or REA MCP calls",
  independent_lineage:"NOT_ESTABLISHED",
  process_identity_after_cleanup:"NOT_RUN",
  original_job_settlement:"NOT_RUN",
  msI_non_elevated_behavior:"NOT_TESTED",
  factory_qualification:"NOT_ESTABLISHED"
};
let owned;
let parentPid, middlePid, leafPid;
let first, cleanupResult, failure;
try {
  owned = await spawnOwnedProviderProcess({
    command:process.execPath,
    arguments:[fixture,"2",boundary],
    runId,
    platform:"win32",
    cwd:root,
    env:{},
    hostEnvironment:process.env
  });
  assert.ok(owned.process instanceof WindowsOwnedProcess,"Original Windows owner not selected");
  assert.ok(typeof owned.cleanup === "function","Original native cleanup not returned");
  const tree = await waitPids();
  [parentPid,middlePid,leafPid] = tree.map(x=>x.pid);
  assert.equal(parentPid, owned.ownership.leaderPid);
  assert.equal(tree[0].node_parent,process.pid);
  assert.equal(tree[1].node_parent,parentPid);
  assert.equal(tree[2].node_parent,middlePid);
  assert.equal(new Set([process.pid,parentPid,middlePid,leafPid]).size,4);
  const ids = [process.pid,parentPid,middlePid,leafPid];
  first = observe(ids);
  const controller = recordFor(first,process.pid);
  const parent = recordFor(first,parentPid);
  const middle = recordFor(first,middlePid);
  const leaf = recordFor(first,leafPid);
  assert.ok(ids.every(id=>recordFor(first,id).found===true),"Synthetic process missing during observation");
  assert.ok(ids.every(id=>typeof recordFor(first,id).start_utc==="string"));
  assert.equal(parent.parent_pid,process.pid,"Native snapshot did not show original owner launcher as child of controller");
  assert.equal(middle.parent_pid,parentPid,"Native snapshot lost intermediate parent");
  assert.equal(leaf.parent_pid,middlePid,"Native snapshot lost detached leaf parent");
  result.native_processes_created=3;
  result.independent_lineage="OBSERVED_3_LEVEL_TOOLHELP_PARENT_LINKS_WITH_START_IDENTITIES";
  result.observed_parent_links=3;
  result.cim_wmi_used=false;
  result.synthetic_only=true;
  result.original_owner_selected=true;
} catch(error) {
  failure=error;
} finally {
  if (owned?.cleanup) {
    try {
      cleanupResult=await owned.cleanup();
      if (!cleanupResult.cleaned) {
        failure ||= new Error("Original owner reported incomplete cleanup");
      }
    } catch(error) { failure ||= error; }
  }
  if (!failure && first && parentPid && middlePid && leafPid) {
    try {
      const tail=observe([parentPid,middlePid,leafPid]);
      for(const p of tail) {
        const prior=recordFor(first,p.pid);
        assert.ok(!p.found || p.start_utc!==prior.start_utc,
           "Original process identity remained after original Job Object cleanup");
      }
      result.process_identity_after_cleanup="THREE_ORIGINAL_IDENTITIES_NOT_OBSERVED";
      result.original_job_settlement="CLEANED_RETURN_FROM_ORIGINAL_WINDOWS_OWNER";
      result.status="PASS";
    } catch(error) { failure ||= error; }
  }
  try { await rm(boundary,{recursive:true,force:true,maxRetries:3,retryDelay:150}); }
  catch(error) { failure ||= error; }
}
if(failure){
  result.status="BLOCKED_OR_FAILED";
  result.failure_class=String(failure?.name || "Error");
  result.failure_reason=String(failure?.message || failure).slice(0,260);
  process.exitCode=1;
}
const report=JSON.stringify(result);
console.log(report);
if(process.env.P71_LINEAGE_RESULT_PATH) {
  await writeFile(process.env.P71_LINEAGE_RESULT_PATH, report+"\n");
}
